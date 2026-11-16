"""Opt-in ContextDB acceptance in six owned disposable libraries; never opens Store/DB."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from common.converter import prepare_review_file
from common.env_sanitize import sanitize_no_proxy
from integrations.contextdb import ContextDBClient, ContextDBError

REPORT = Path(__file__).resolve().parents[1] / 'docs/architecture/contextdb-pipeline-smoke.json'
PREFIX = 'ctxdb-accept-'


def assert_owned(fixture, base):
    if (not fixture.get('id') or base.get('id') != fixture['id'] or
            base.get('name') not in fixture['owned_names'] or
            not all(name.startswith(PREFIX + fixture['run_id'] + '-') for name in fixture['owned_names'])):
        raise RuntimeError('Resource identity mismatch; cleanup refused')


def missing_base(error):
    return isinstance(error, ContextDBError) and (error.status_code == 404 or
        error.error_code == 1001 and 'knowledge base not found' in str(error).lower())


def verify_graph_crud(client, kb_id, run_id):
    def request(method, path, **kwargs):
        return client._request(method, '/v1/knowledge/' + path, **kwargs)
    ids = []
    renamed = '手工验收应用已更名-' + run_id
    for name in ('手工验收应用-' + run_id, '手工验收数据库-' + run_id):
        entity = request('POST', 'entities', json_body={'knowledge_base_id': kb_id, 'entity_name': name,
            'entity_type': '验收对象', 'description': '隔离验收实体', 'aliases': []})
        ids.append(entity['entity_id'])
    entity = request('PUT', 'entities', json_body={'knowledge_base_id': kb_id, 'entity_id': ids[0],
        'entity_name': renamed, 'entity_type': '验收对象', 'description': '已更新', 'aliases': ['验收别名']})
    assert entity['entity_id'] == ids[0]
    relation = request('POST', 'entity-relations', json_body={'knowledge_base_id': kb_id,
        'source_entity_id': ids[0], 'target_entity_id': ids[1], 'relation_type': '连接',
        'description': '仅供验收', 'keywords': [], 'weight': 0.5})
    relation_id = relation['relation_id']
    updated = request('PUT', 'entity-relations', json_body={'knowledge_base_id': kb_id,
        'relation_id': relation_id, 'relation_type': '依赖', 'description': '更新关系', 'keywords': ['验收'], 'weight': 0.7})
    assert updated['relation_id'] == relation_id
    detail = request('GET', 'entities/detail', params={'knowledge_base_id': kb_id, 'entity_id': ids[0]})
    assert detail['entity_name'] == renamed
    request('GET', 'entity-relations/detail', params={'knowledge_base_id': kb_id, 'relation_id': relation_id})
    request('DELETE', 'entity-relations', params={'knowledge_base_id': kb_id, 'relation_id': relation_id})
    for entity_id in ids:
        assert request('DELETE', 'entities', params={'knowledge_base_id': kb_id, 'entity_id': entity_id})['deleted']
    visual = client.graph_visual(kb_id, max_nodes=20, max_edges=30)
    return {'knowledge_base_id': kb_id, 'entity_crud': True, 'relation_crud': True,
            'entity_total': visual.get('entity_total'), 'relation_total': visual.get('relation_total')}


def run(*, execute=False, timeout=300, report_path=REPORT):
    if not execute:
        return {'status': 'dry_run', 'mutations': False,
                'plan': 'Create three modes × review on/off, verify only returned IDs, then delete only those IDs.'}
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    sanitize_no_proxy()
    client = ContextDBClient(timeout=20, max_retries=0)
    if not client.configured():
        raise RuntimeError('CONTEXTDB_API_KEY is not configured')
    run_id = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:10]
    started = time.monotonic()
    deadline = started + min(300, max(90, timeout))
    work_deadline = deadline - 50
    report = {'schema_version': 2, 'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'run_id': run_id, 'status': 'running', 'mutations': True,
        'isolation': {'production_store_or_database': False, 'cleanup_by_returned_ids_only': True},
        'fixtures': [], 'checks': [], 'cleanup': [],
        'not_checked': ['Real Wiki conflict resolution requires a naturally occurring conflict.',
                        'No concurrency/load test or production migration.',
                        'Ontology invitation-only APIs are outside this acceptance.']}
    documents = []

    def save():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    def safe_error(exc):
        message = str(exc).replace(client.api_key, '[redacted]')
        return re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[redacted-token]', message)[:600]

    def check(name, callback):
        try:
            details = callback() or {}
            report['checks'].append({'name': name, 'status': 'checked', **details})
            print(json.dumps({'check': name, 'status': 'checked'}), flush=True)
            return details
        except Exception as exc:
            report['checks'].append({'name': name, 'status': 'blocked', 'error': safe_error(exc)})
            print(json.dumps({'check': name, 'status': 'blocked', 'error': safe_error(exc)}), flush=True)
            return None
        finally:
            save()

    def request(method, path, **kwargs):
        return client._request(method, '/v1/knowledge/' + path, **kwargs)

    def create(mode, review):
        local = ContextDBClient(api_key=client.api_key, base_url=client.base_url, timeout=20, max_retries=0)
        name = f'{PREFIX}{run_id}-{mode}-{int(review)}'
        base = local.create_knowledge_base(name, wiki_enabled=mode == 'wiki', graph_enabled=mode == 'graph',
            review_enabled=review, chunk_size=512, chunk_overlap=76)
        return {'id': base['id'], 'name': name, 'owned_names': [name], 'run_id': run_id,
                'mode': mode, 'review_enabled': review, 'document_ids': []}

    def verify_and_rename(fixture):
        base = client.get_knowledge_base(fixture['id'])
        assert_owned(fixture, base)
        assert bool(base.get('wiki_enabled')) == (fixture['mode'] == 'wiki')
        assert bool(base.get('graph_enabled')) == (fixture['mode'] == 'graph')
        assert bool(base.get('review_enabled')) == fixture['review_enabled']
        renamed = fixture['name'] + '-renamed'
        fixture['owned_names'].append(renamed)
        client.update_knowledge_base(fixture['id'], name=renamed)
        base = client.get_knowledge_base(fixture['id'])
        assert_owned(fixture, base)
        assert base['name'] == renamed
        fixture['name'] = renamed
        if fixture['review_enabled']:
            settings = client.update_review_settings(fixture['id'], high_threshold=1.0,
                rewrite_enabled=True, rewrite_auto_ingest_enabled=False, max_rewrite_iterations=3)
            assert settings.get('rewrite_auto_ingest_enabled') is False
        return {'knowledge_base_id': fixture['id'], 'mode': fixture['mode'], 'review_enabled': fixture['review_enabled']}

    def submit(fixture, body, case='original', *, html=False):
        with tempfile.TemporaryDirectory(prefix='ctxdb-accept-upload-') as directory:
            path = Path(directory) / ('source.html' if html else 'source.md')
            path.write_text(body)
            name, sent, fingerprint = prepare_review_file(client, fixture['id'], path.name, path)
            adopted = sent.read_text()
            doc = client.upload_file(fixture['id'], f'{case}-{name}', sent,
                metadata={'smoke_run': run_id, 'smoke_case': case}, mime_type='text/markdown' if name.endswith('.md') else None)
        return {'fixture': fixture, 'id': doc['id'], 'case': case, 'adopted': adopted,
            'review_handled': not fixture['review_enabled'], 'ready': False,
            'conversion_fingerprint': fingerprint}

    def remember(doc):
        fixture = doc['fixture']
        fixture['document_ids'].append(doc['id'])
        documents.append(doc)
        fixture.setdefault('documents', []).append({'id': doc['id'], 'case': doc['case'],
            'conversion_fingerprint': doc.get('conversion_fingerprint', '')})
        save()

    def nodes(fixture):
        kb_id = fixture['id']
        parent = request('POST', 'nodes', json_body={'knowledge_base_id': kb_id, 'display_name': 'Parent'})['node']
        child = request('POST', 'nodes', json_body={'knowledge_base_id': kb_id, 'display_name': 'Child'})['node']
        updated = request('PATCH', 'nodes', json_body={'node_id': child['node_id'],
            'display_name': 'Renamed child', 'parent_node_id': parent['node_id'],
            'expected_tree_version': child['tree_version']})['node']
        listed = request('GET', 'nodes', params={'knowledge_base_id': kb_id, 'parent_node_id': parent['node_id']})
        assert any(node['node_id'] == child['node_id'] and node['display_name'] == 'Renamed child' for node in listed['items'])
        try:
            request('PATCH', 'nodes', json_body={'node_id': child['node_id'], 'display_name': 'Must fail',
                'expected_tree_version': child['tree_version']})
        except ContextDBError as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError('stale file-tree version was accepted')
        request('DELETE', 'nodes', params={'node_id': updated['node_id'], 'expected_tree_version': updated['tree_version']})
        parent_now = request('GET', 'nodes', params={'knowledge_base_id': kb_id, 'parent_node_id': parent['node_id']})['parent_node']
        request('DELETE', 'nodes', params={'node_id': parent['node_id'], 'expected_tree_version': parent_now['tree_version']})
        return {'knowledge_base_id': kb_id, 'stale_version_rejected': True, 'create_move_rename_delete': True}

    def multipart(fixture, document_id=None):
        params = {'file_name': 'multipart.md', 'metadata': json.dumps({'smoke_run': run_id})}
        params.update({'document_id': document_id} if document_id else {'knowledge_base_id': fixture['id'], 'name': 'multipart.md'})
        upload = request('PUT' if document_id else 'POST', 'files/init-upload', params=params)
        fixture['document_ids'].append(upload['document_id'])
        headers = {**client._headers(), 'X-Upload-Ticket': upload['upload_ticket']}
        body = ('# 分片验收\n\n' + ('更新后的端口为 4242。' if document_id else '初始端口为 8080。')).encode()
        try:
            part = client._payload(client._session.post(client.base_url + '/v1/knowledge/files/chunks',
                data={'part_number': 1}, files={'data': ('part', body)}, headers=headers, timeout=20))
            result = client._payload(client._session.post(client.base_url + '/v1/knowledge/files/complete',
                json={'parts': [{'part_number': part['part_number'], 'etag': part['etag']}]}, headers=headers, timeout=20))
            final_id = result['document_id']
            fixture['document_ids'].append(final_id)
            detail = client.get_document(fixture['id'], final_id)
            doc = {'fixture': fixture, 'id': detail['id'], 'case': 'multipart-update' if document_id else 'multipart',
                'adopted': body.decode(), 'review_handled': True, 'ready': False}
            remember(doc)
            return {'knowledge_base_id': fixture['id'], 'document_id': final_id, 'init_document_id': upload['document_id'],
                    'operation': 'PUT' if document_id else 'POST'}
        except Exception:
            try:
                client._session.post(client.base_url + '/v1/knowledge/files/abort', headers=headers, timeout=20)
            except Exception:
                pass
            raise

    def settle(until):
        while time.monotonic() < until:
            pending = [doc for doc in documents if not doc.get('ready') and not doc.get('failed')]
            if not pending:
                return
            review_lists = {}
            for doc in pending:
                fixture = doc['fixture']
                try:
                    detail = client.get_document(fixture['id'], doc['id'])
                    doc['last_status'] = detail.get('ingest_status')
                    if not doc['review_handled']:
                        if fixture['id'] not in review_lists:
                            review_lists[fixture['id']] = client.list_reviews(fixture['id'], page_size=100).get('reviews', [])
                        reviews = review_lists[fixture['id']]
                        review = next((item for item in reviews if item.get('document_id') == doc['id']), None)
                        if review and review.get('lifecycle_state') == 'auto_accepted' and not doc.get('retracted'):
                            client.review_action(review['review_id'], 'retract')
                            doc['retracted'] = True
                        elif review and review.get('lifecycle_state') == 'pending_human':
                            if doc['case'] == 'edited':
                                adopted = '# 人工核定稿\n\n人工核定的验收端口为 4242，部署前先验证连接。'
                                client.review_action(review['review_id'], 'accept_rewrite', edited_content=adopted)
                                doc['adopted'] = adopted
                            elif doc['case'] == 'ai-rewrite':
                                full = client.get_review(review['review_id'])
                                rewritten = full.get('rewritten_content')
                                if rewritten:
                                    client.review_action(review['review_id'], 'accept_rewrite')
                                    doc['adopted'] = rewritten
                                    report['checks'].append({'name': 'adopt-existing-ai-rewrite', 'status': 'checked', 'document_id': doc['id']})
                                else:
                                    report['checks'].append({'name': 'adopt-existing-ai-rewrite', 'status': 'blocked',
                                        'document_id': doc['id'], 'error': 'Official review produced no AI rewrite; no content was fabricated.'})
                                    client.review_action(review['review_id'], 'confirm')
                            else:
                                client.review_action(review['review_id'], 'confirm')
                            doc['review_handled'] = True
                            report['checks'].append({'name': 'official-review-' + doc['case'], 'status': 'checked',
                                'knowledge_base_id': fixture['id'], 'document_id': doc['id']})
                    if detail.get('ingest_status') == 'succeeded' and doc['review_handled']:
                        doc['ready'] = True
                    elif detail.get('ingest_status') in ('failed', 'deleted'):
                        raise RuntimeError(detail.get('ingest_error_message') or detail['ingest_status'])
                except Exception as exc:
                    doc['failed'] = True
                    report['checks'].append({'name': 'ingest-' + fixture['mode'] + '-' + doc['case'],
                        'status': 'blocked', 'document_id': doc['id'], 'error': safe_error(exc)})
            save()
            time.sleep(2)

    def original_evidence(doc):
        if not doc.get('ready'):
            raise RuntimeError('Official ingest not completed: ' + str(doc.get('last_status')))
        result = client.query('说明这份验收材料的端口、部署和连接要求', knowledge_base_ids=[doc['fixture']['id']],
            document_ids=[doc['id']], knowledge_view='source', similarity_threshold=0, top_k=6)
        source = [chunk for chunk in result.get('chunks', []) if (chunk.get('doc_id') or chunk.get('document_id')) == doc['id']
                  and 'graphrag' not in (chunk.get('tag_kwd') or [])]
        assert source, 'No original evidence chunk returned'
        normalize = lambda text: re.sub(r'\s+', '', text)
        adopted = normalize(doc['adopted'])
        matched = [chunk for chunk in source if SequenceMatcher(None, adopted,
            normalize(chunk.get('content_with_weight') or chunk.get('content') or '')).find_longest_match().size >= min(16, len(adopted))]
        assert matched, 'Retrieved chunks did not contain the real adopted content'
        return {'knowledge_base_id': doc['fixture']['id'], 'document_id': doc['id'],
            'chunk_ids': [chunk.get('chunk_id') for chunk in matched],
            'adopted_content_sha256': hashlib.sha256(doc['adopted'].encode()).hexdigest()}

    def graph(fixture):
        return verify_graph_crud(client, fixture['id'], run_id)

    def graph_evidence(fixture):
        entities = request('GET', 'entities', params={'kb_id': fixture['id'], 'page_size': 20}).get('entities', [])
        sourced = [entity for entity in entities if entity.get('source_document_ids')]
        assert sourced, 'No automatically extracted entity with a real source is available yet'
        chunks = request('GET', 'entities/chunks', params={'knowledge_base_id': fixture['id'],
            'entity_ids': ','.join(entity['entity_id'] for entity in sourced[:3]), 'limit': 10}).get('chunks', [])
        assert chunks and all(chunk.get('document_id') and chunk.get('content') for chunk in chunks)
        return {'knowledge_base_id': fixture['id'], 'source_chunk_ids': [chunk['chunk_id'] for chunk in chunks]}

    def wiki(fixture):
        kb_id = fixture['id']
        created = client.create_wiki_page(kb_id, '隔离验收主题-' + run_id, '手工主题初始正文。')
        page_id = created['page_id']
        before = client.get_wiki_page(kb_id, page_id)
        assert before['published'] and before['content']
        content = '人工更新的隔离验收主题正文。'
        client.update_wiki_page(kb_id, page_id, content, before['version'])
        until = min(work_deadline, time.monotonic() + 25)
        while time.monotonic() < until:
            current = client.get_wiki_page(kb_id, page_id)
            if current.get('published') and current.get('content') == content:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Wiki edit accepted but formal content was not updated within the bound')
        try:
            client.update_wiki_page(kb_id, page_id, 'stale must fail', before['version'])
        except ContextDBError as exc:
            assert exc.status_code == 409 or exc.error_code == 4033
        else:
            raise AssertionError('Stale Wiki version was accepted')
        revisions = request('GET', 'wiki/revisions', params={'knowledge_base_id': kb_id, 'page_id': page_id}).get('items', [])
        assert len(revisions) >= 2
        revision = current.get('head_revision_id') or revisions[0]['revision_id']
        request('GET', 'wiki/revisions/diff', params={'knowledge_base_id': kb_id, 'revision_id': revision})
        request('GET', 'wiki/index', params={'knowledge_base_id': kb_id, 'limit': 2})
        request('GET', 'wiki/search', params={'knowledge_base_id': kb_id, 'query': '隔离验收', 'limit': 5})
        for action in ('pause', 'resume'):
            request('POST', 'wiki/compile-runs/actions', json_body={'knowledge_base_id': kb_id, 'action': action})
            runs = request('GET', 'wiki/compile-runs', params={'knowledge_base_id': kb_id, 'limit': 2})
            assert bool(runs.get('wiki_compile_paused')) == (action == 'pause')
        issues = request('GET', 'wiki/issues', params={'knowledge_base_id': kb_id, 'limit': 2})
        return {'knowledge_base_id': kb_id, 'page_id': page_id, 'formal_content_verified': True,
                'stale_version_rejected': True, 'revisions': len(revisions), 'issue_count_returned': len(issues.get('items', []))}

    def cleanup(fixture):
        local = ContextDBClient(api_key=client.api_key, base_url=client.base_url, timeout=15, max_retries=0)
        try:
            base = local.get_knowledge_base(fixture['id'])
        except ContextDBError as exc:
            if missing_base(exc):
                return {'knowledge_base_id': fixture['id'], 'status': 'already_absent'}
            raise
        assert_owned(fixture, base)
        while time.monotonic() < deadline:
            reviews = local.list_reviews(fixture['id'], lifecycle_state='pending_human', page_size=100).get('reviews', [])
            for review in reviews:
                if review.get('document_id') in fixture['document_ids']:
                    try:
                        local.review_action(review['review_id'], 'reject')
                    except ContextDBError as exc:
                        if not (exc.status_code == 400 and 'already actioned' in str(exc).lower()):
                            raise
            docs = local.list_documents(fixture['id'], page_size=100).get('documents', [])
            if not docs:
                try:
                    local.delete_knowledge_base(fixture['id'])
                except ContextDBError as exc:
                    if exc.error_code == 1001 and 'still has' in str(exc).lower():
                        time.sleep(2)
                        continue
                    raise
                try:
                    local.get_knowledge_base(fixture['id'])
                except ContextDBError as exc:
                    if missing_base(exc):
                        return {'knowledge_base_id': fixture['id'], 'status': 'deleted', 'identity_checked': True}
                    raise
                raise RuntimeError('KB still readable after deletion')
            for doc in docs:
                if doc['id'] not in fixture['document_ids']:
                    raise RuntimeError('Unrecognized document in owned fixture; cleanup refused')
            stable = [doc['id'] for doc in docs if doc.get('ingest_status') in ('succeeded', 'failed')]
            if stable:
                local.delete_documents(fixture['id'], stable)
            time.sleep(2)
        raise RuntimeError('Owned fixture cleanup did not complete before deadline')

    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            pending = {pool.submit(create, mode, review): (mode, review)
                for mode in ('source', 'graph', 'wiki') for review in (False, True)}
            for future in as_completed(pending):
                mode, review = pending[future]
                try:
                    fixture = future.result()
                    report['fixtures'].append(fixture)
                    save()
                    check(f'create-rename-{mode}-{int(review)}', lambda fixture=fixture: verify_and_rename(fixture))
                except Exception as exc:
                    report['checks'].append({'name': f'create-{mode}-{int(review)}', 'status': 'blocked', 'error': safe_error(exc)})
                    save()
        with ThreadPoolExecutor(max_workers=6) as pool:
            jobs = []
            for fixture in report['fixtures']:
                body = '# 验收部署手册\n\n验收应用连接验收数据库。部署时先检查网络，再使用端口 8080 建立连接。停止服务前必须先排空连接池。'
                html = fixture['mode'] == 'source' and fixture['review_enabled']
                if html:
                    body = '<h1>验收部署手册</h1><p>验收应用连接验收数据库。部署时先检查网络，再使用端口 8080 建立连接。停止服务前必须先排空连接池。</p>'
                jobs.append(pool.submit(submit, fixture, body, html=html))
                if html:
                    jobs.append(pool.submit(submit, fixture, '原始配置记为 8080，需要人工核定。', 'edited'))
                    jobs.append(pool.submit(submit, fixture, '# 临时笔记\n\n呃，那个那个，验收服务连接数据库需要端口8080。验收服务连接数据库需要端口8080。\n\n广告广告广告，不相关的随手记录。正式步骤：先检测网络，然后连接数据库。', 'ai-rewrite'))
            for future in as_completed(jobs):
                try:
                    remember(future.result())
                except Exception as exc:
                    report['checks'].append({'name': 'upload', 'status': 'blocked', 'error': safe_error(exc)})
                    save()
        source = next((item for item in report['fixtures'] if item['mode'] == 'source' and not item['review_enabled']), None)
        if source:
            check('file-tree-CAS-CRUD', lambda: nodes(source))
            multi = check('multipart-create', lambda: multipart(source))
        else:
            multi = None
        settle(work_deadline - 35)
        for doc in list(documents):
            check('source-evidence-' + doc['fixture']['mode'] + '-' + str(int(doc['fixture']['review_enabled'])) + '-' + doc['case'],
                lambda doc=doc: original_evidence(doc))
        if multi and time.monotonic() < work_deadline:
            check('multipart-update-final-id', lambda: multipart(source, multi['document_id']))
            settle(min(work_deadline, time.monotonic() + 20))
            check('multipart-update-source-evidence', lambda: original_evidence(documents[-1]))
        graph_fixture = next((item for item in report['fixtures'] if item['mode'] == 'graph' and not item['review_enabled']), None)
        if graph_fixture:
            check('graph-entity-relation-CRUD', lambda: graph(graph_fixture))
            check('graph-real-source-chunks', lambda: graph_evidence(graph_fixture))
        wiki_fixture = next((item for item in report['fixtures'] if item['mode'] == 'wiki' and not item['review_enabled']), None)
        if wiki_fixture:
            check('wiki-edit-CAS-history-compile-control', lambda: wiki(wiki_fixture))
    except Exception as exc:
        report['checks'].append({'name': 'run', 'status': 'blocked', 'error': safe_error(exc)})
    finally:
        with ThreadPoolExecutor(max_workers=6) as pool:
            pending = {pool.submit(cleanup, fixture): fixture for fixture in report['fixtures']}
            for future in as_completed(pending):
                fixture = pending[future]
                try:
                    report['cleanup'].append(future.result())
                except Exception as exc:
                    report['cleanup'].append({'knowledge_base_id': fixture['id'], 'name': fixture['name'],
                        'status': 'blocked', 'error': safe_error(exc)})
                save()
        report['elapsed_seconds'] = round(time.monotonic() - started, 2)
        report['status'] = ('passed' if len(report['fixtures']) == 6 and
            all(item['status'] == 'checked' for item in report['checks']) and
            all(item['status'] in ('deleted', 'already_absent') for item in report['cleanup']) else 'partial')
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Authorize creation and deletion of new isolated acceptance resources')
    parser.add_argument('--timeout', type=int, default=300, help='Bound async work and cleanup to at most 300 seconds')
    args = parser.parse_args()
    result = run(execute=args.execute, timeout=args.timeout)
    print(json.dumps({'status': result['status'], 'report': str(REPORT) if args.execute else None}, ensure_ascii=False))
    return 1 if args.execute and result['status'] != 'passed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
