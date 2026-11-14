"""在独立子进程中执行平台采集与官方同步任务，PostgreSQL 锁防双跑。"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from common.env_sanitize import sanitize_no_proxy
from governance.contextdb_sync import enqueue_sync
from governance.store import Store, data_dir, now
from governance.database import connection


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def restore_retry_artifacts(previous_dir, output):
    if output.exists() or not previous_dir.exists():
        return
    temporary = output.with_name(output.name + '.copy.tmp')
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(previous_dir, temporary)
    temporary.replace(output)


def create_zip_file(source_dir, zip_filename, cancel_check=None):
    partial = Path(str(zip_filename) + '.part')
    try:
        with ZipFile(partial, 'w', ZIP_DEFLATED) as archive:
            for path in sorted(Path(source_dir).rglob('*')):
                if cancel_check:
                    cancel_check()
                if path.is_file() and not path.name.endswith('.part'):
                    archive.write(path, path.relative_to(source_dir))
        partial.replace(zip_filename)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def process_job(store, job):
    from crawlers.base import CrawlCancelled
    from registry import create_crawler

    job_id = job['task_id']
    capture_message = None
    submission_queued = False
    if job.get('owner_id'):
        from webapi.auth import client_for_user
        store.owner_id = job['owner_id']
        store.client = client_for_user(job['owner_id'])
    if job.get('attempt_token'):
        store.active_attempt = (job_id, job['attempt_token'])

    def cancel_check():
        if store.get_job(job_id)['cancel_requested']:
            raise CrawlCancelled('任务已取消')
        store.guard_attempt()

    def progress(current, total, message):
        cancel_check()
        phase = 'crawling'
        if '清洗' in message or '解析' in message:
            phase = 'cleaning'
        elif '质量' in message or '检查' in message or '审查' in message:
            phase = 'quality_check'
        elif '数据集' in message or '保存' in message:
            phase = 'packaging'
        store.log(job_id, message, phase=phase, completed_pages=current, total_pages=total,
                  progress=int(100 * current / total) if total else 0,
                  current_item=message.partition(':')[2].strip())

    try:
        cancel_check()
        if job['kind'] == 'ctxdb_sync':
            from governance.contextdb_sync import run_sync
            store.update_job(job_id, status='running', phase='syncing', progress=0,
                             message='开始同步 ContextDB 知识库')
            run_sync(store, job)
            return
        output = Path(job['output_dir'])
        if job.get('retry_of') and not output.exists():
            previous = store.get_job(job['retry_of'])
            previous_dir = Path(previous['output_dir'])
            restore_retry_artifacts(previous_dir, output)
        output.mkdir(parents=True, exist_ok=True)
        summary_path = output / 'summary.json'
        incomplete_collection = False
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
            incomplete_collection = bool(summary.get('failed_documents') or summary.get('error_count'))
            if incomplete_collection:
                summary = None
        else:
            summary = None
        if summary is None:
            store.log(job_id, '正在连接数据源并采集原件', phase='connecting')
            crawler = create_crawler(job['entry'], save_dir=str(output), progress_callback=progress, **job['params'])
            crawler.source_only = True
            source_file = output / 'source_documents.jsonl'
            if source_file.exists() and source_file.stat().st_size:
                summary = asdict(crawler.reprocess_sources(
                    str(source_file), resume_collection=not (output / 'collection_complete.json').exists() or
                    (incomplete_collection and job['entry'] == 'web'),
                    selected_ids=job['selected_ids'], selected_titles=job['selected_titles']))
            else:
                summary = asdict(crawler.crawl(selected_ids=job['selected_ids'], selected_titles=job['selected_titles']))
            write_json(summary_path, summary)
        cancel_check()
        documents = read_jsonl(output / 'rag_documents.jsonl')
        sources = {str(r['id']): r for r in read_jsonl(output / 'source_documents.jsonl')}
        chunks = read_jsonl(output / 'rag_chunks.jsonl')
        store.ingest(job, documents, sources, chunks)
        partial = bool(summary.get('failed_documents') or summary.get('error_count'))
        video_references = summary.get('video_reference_documents', 0)
        message = f"来源检查完成：成功 {len(documents)} 条，失败 {summary.get('failed_documents', 0)} 条"
        if video_references:
            message += f'；其中 {video_references} 条仅保存视频链接，视频内容未采集'
        if partial:
            message += '；请查看失败明细后重试'
        archive = output.with_suffix('.zip')
        create_zip_file(output, archive, cancel_check)
        store.update_job(job_id, status='partial' if partial else 'completed',
                         summary=summary, capture_complete=not partial,
                         failed_pages=summary.get('failed_documents', 0),
                         completed_pages=len(sources), total_pages=len(sources),
                         phase='completed', progress=100, end_time=now(), zip_file=str(archive),
                         message=message)
        if not partial:
            capture_message = message
            publish(store, job_id)
            submission_queued = True
            store.update_job(job_id, phase='submitted',
                message=message + '；已自动加入 ContextDB 提交队列，评审、入库与 Wiki 编译状态请查看治理进度')
    except CrawlCancelled:
        store.update_job(job_id, status='cancelled', phase='cancelled', end_time=now(), message='任务已取消，已保存的原文可重试')
    except Exception as exc:
        message = str(exc)
        for name, value in job.get('params', {}).items():
            if any(key in name.lower() for key in ('token', 'password', 'secret', 'key')) and isinstance(value, str) and value:
                message = message.replace(value, '[redacted]')
        if capture_message is not None:
            detail = ('已加入 ContextDB 提交队列，评审、入库与 Wiki 编译状态请查看治理进度' if submission_queued else
                      f'自动提交失败: {message[:1000]}；可在任务中重试提交')
            store.update_job(job_id, status='completed', phase='submitted' if submission_queued else 'submission_failed',
                end_time=now(), message=f'{capture_message}；{detail}')
        else:
            store.update_job(job_id, status='failed', phase='failed', end_time=now(), message=f'处理失败: {message[:1500]}')


def publish(store, job_id):
    with connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (f'publish:{store.owner_id}:{job_id}',))
        return _publish(store, job_id)


def _publish(store, job_id):
    existing = store._find('release', job_id=job_id)
    if existing:
        release_id=existing['metadata']['release_id']
        with connection() as conn:
            linked=conn.execute("SELECT 1 FROM runtime_records WHERE owner_id=%s AND kind='job' AND payload->>'kind'='ctxdb_sync' AND payload->'params'->>'release_id'=%s LIMIT 1", (store.owner_id or '',release_id)).fetchone()
        if not linked:enqueue_sync(store,release_id,existing['metadata']['scope'])
        return release_id
    scope, generation, documents = store.release_inputs(job_id)
    release_id = str(uuid.uuid4())
    root = data_dir() / 'releases'
    root.mkdir(parents=True, exist_ok=True)
    archive_path = root / f'{release_id}.zip'
    temporary = archive_path.with_suffix('.zip.part')
    manifest = {'id': release_id, 'job_id': job_id, 'created_at': now(),
                'version_ids': [d['version_id'] for d in documents], 'generation': generation}
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        records, chunks, copied_assets = [], [], set()
        for doc in documents:
            artifact_base = f"artifacts/{doc['job_id']}"
            record = {**{k: doc.get(k) for k in ('id', 'version_id', 'title', 'category', 'content', 'metadata', 'resources', 'source_format')}, 'artifact_base': artifact_base}
            source_path = doc.get('source', {}).get('source_path')
            if source_path:
                original = (Path(doc['artifact_dir']) / source_path).resolve()
                if not original.is_relative_to(Path(doc['artifact_dir']).resolve()) or not original.is_file():
                    raise ValueError('源文件缺失或不在采集目录内')
                record['archive_source'] = f"originals/{doc['id']}{original.suffix}"
                archive.write(original, record['archive_source'])
            records.append(record)
            for chunk in doc.get('chunks', []):
                chunks.append({**chunk, 'document_id': doc['id'], 'version_id': doc['version_id'], 'artifact_base': artifact_base})
            archive.writestr(f"{artifact_base}/{doc['id']}.md", doc.get('content', ''))
            root_dir = Path(doc['artifact_dir']).resolve()
            resources = [item for values in doc.get('resources', {}).values() for item in values]
            for item in resources:
                url = urlsplit(item.get('url', ''))
                relative = unquote(url.path)
                if url.scheme or url.netloc or not relative.startswith('assets/'):
                    continue
                resource = (root_dir / relative).resolve()
                if resource.is_file() and resource.is_relative_to(root_dir):
                    target = f"{artifact_base}/{resource.relative_to(root_dir)}"
                    if target not in copied_assets:
                        archive.write(resource, target)
                        copied_assets.add(target)
        archive.writestr('rag_documents.jsonl', '\n'.join(json.dumps(r, ensure_ascii=False) for r in records) + '\n')
        archive.writestr('rag_chunks.jsonl', '\n'.join(json.dumps(r, ensure_ascii=False) for r in chunks) + '\n')
    temporary.replace(archive_path)
    store.create_release(job_id, scope, generation, manifest['version_ids'], archive_path, release_id)
    enqueue_sync(store, release_id, scope)
    return release_id


def main():
    from dotenv import load_dotenv
    sanitize_no_proxy()
    load_dotenv()
    parser = argparse.ArgumentParser(description='持久化数据治理 worker')
    parser.add_argument('--once', action='store_true', help='处理一个排队任务后退出')
    parser.add_argument('--job', help=argparse.SUPPRESS)
    args = parser.parse_args()
    store = Store()
    store.initialize()
    if args.job:
        # 子进程:监督者已持有 claim;SIGALRM 兜底终止孤儿子进程
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.alarm(max(1, int(os.getenv('GOVERNANCE_JOB_TIMEOUT', '1800'))))
        job = store.get_job(args.job)
        if job['status'] in {'running', 'cancelling'}:
            process_job(store, job)
        return
    # 监督者独占锁:insert-if-absent,409 即已有监督者;心跳超时视为崩溃残留锁,接管
    def acquire_supervisor():
        store._create('claim', 'supervisor', {'role': 'supervisor', 'claimed_at': now()},
                      {'type': 'claim', 'job_id': 'supervisor', 'role': 'supervisor',
                       'claimed_at': now(), 'updated_at': now()})
    try:
        acquire_supervisor()
    except Exception:
        if store._find('claim', job_id='supervisor') and store.worker_alive():
            raise SystemExit('已有治理 worker 正在运行')
        store.release_claim('supervisor')
        # 云端删除异步生效,同名创建短时仍冲突
        for _ in range(10):
            time.sleep(2)
            try:
                acquire_supervisor()
                break
            except Exception:
                continue
        else:
            raise SystemExit('已有治理 worker 正在运行')
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        store.recover_jobs(reset_all=True)
        while True:
            store.recover_jobs()
            store.heartbeat()
            job = store.claim()
            if job is None:
                if args.once:
                    return
                time.sleep(2)
                continue
            process = subprocess.Popen([sys.executable, '-m', 'governance.worker', '--job', job['task_id']])
            started = time.monotonic()
            cancelled_at = None
            try:
                while process.poll() is None:
                    store.heartbeat()
                    current = store.get_job(job['task_id'])
                    if current['cancel_requested']:
                        cancelled_at = cancelled_at or time.monotonic()
                    timed_out = time.monotonic() - started > int(os.getenv('GOVERNANCE_JOB_TIMEOUT', '1800'))
                    if timed_out or (cancelled_at and time.monotonic() - cancelled_at > 10):
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        status = 'cancelled' if cancelled_at else 'failed'
                        store.update_job(job['task_id'], status=status, phase=status, end_time=now(),
                                         message='任务已取消' if cancelled_at else '处理超时，已保存的阶段产物可重试')
                        break
                    time.sleep(2)
                final = store.get_job(job['task_id'])
                if final['status'] in {'running', 'cancelling'}:
                    store.update_job(job['task_id'], status='failed', phase='failed', end_time=now(),
                                     message='处理进程异常退出，可重试已保存产物')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                store.release_claim(job['task_id'])
            if args.once:
                return
    finally:
        store.release_claim('supervisor')


if __name__ == '__main__':
    main()
