"""Real upload/crawl acceptance in one retained, disposable knowledge space.

Run with project Python. Re-running resumes recorded IDs; it never deletes data,
starts workers, or changes any other space. Credentials stay in memory.
"""
import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'output/verification/knowledge-names-20261116/flow.json'
SOURCE_URL = 'https://www.showdoc.com.cn/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--report', type=Path, default=REPORT, help='Evidence file; a new file creates a separate disposable space')
    parser.add_argument('--check-only', action='store_true', help='Only read names, chunks, retrieval, Wiki and graph for recorded IDs')
    args = parser.parse_args()
    report_path = args.report.resolve()
    load_dotenv(ROOT / '.env')
    from common.env_sanitize import sanitize_no_proxy
    sanitize_no_proxy()
    report = json.loads(report_path.read_text()) if report_path.exists() else {
        'scope': 'name-check-' + uuid.uuid4().hex[:12],
        'name': '名称验收·文件与网页·20261116', 'source_url': SOURCE_URL,
        'jobs': {}, 'reviews_confirmed': [], 'resources_retained': True,
    }
    assert report['scope'].startswith('name-check-')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report['updated_at'] = datetime.now(timezone.utc).isoformat()
        temporary = report_path.with_suffix('.json.part')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(report_path)

    session = requests.Session()

    def api(method, path, **kwargs):
        response = session.request(method, args.base_url + path, timeout=90, **kwargs)
        body = response.json()
        if response.status_code >= 400 or body.get('success') is False:
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {body.get("message", "request failed")}')
        return body

    login = api('POST', '/api/v1/auth/login', json={
        'email': os.environ['PLATFORM_ADMIN_EMAIL'], 'password': os.environ['PLATFORM_ADMIN_PASSWORD']})
    session.headers['Authorization'] = 'Bearer ' + login['access_token']
    assert report.get('owner_id', login['user']['id']) == login['user']['id'], 'Recorded resources belong to another account'
    report['owner_id'] = login['user']['id']
    save()

    def event(label, value):
        print(json.dumps({'stage': label, 'value': value}, ensure_ascii=False), flush=True)

    def check_pipeline():
        from webapi.auth import client_for_user
        client = client_for_user(report['owner_id'])
        space = api('GET', f'/api/kb/spaces/{report["scope"]}')['space']
        report['space'] = space
        checks = {'bases': [], 'documents': [], 'queries': {}}
        ids = {space['wiki_kb_id'], space['graph_kb_id']}
        for base in api('GET', '/api/kb/bases')['bases']:
            if base['id'] in ids:
                checks['bases'].append({key: base.get(key) for key in ('id', 'name', 'display_name')})
        for mode in ('wiki', 'graph'):
            kb_id = space[mode + '_kb_id']
            documents = api('GET', '/api/kb/documents', params={'kb_id': kb_id})['documents']
            assert len(documents) == 2, 'Own library should contain exactly two captured sources'
            expected_names = {document['id']: document.get('display_name') for document in documents}
            nodes = api('GET', '/api/contextdb/v1/knowledge/nodes', params={
                'knowledge_base_id': kb_id, 'page_size': 100})['data']['items']
            assert all(node.get('document_display_name') == expected_names[node['document_id']]
                       for node in nodes if node.get('document_id') in expected_names), 'Directory names must match document names'
            reviews = api('GET', '/api/kb/reviews', params={'kb_id': kb_id, 'lifecycle_state': 'approved'})['reviews']
            assert reviews and all(review.get('document_display_name') == expected_names[review['document_id']]
                                   for review in reviews), 'Review names must match document names'
            if mode == 'wiki':
                runs = api('GET', '/api/contextdb/v1/knowledge/wiki/compile-runs', params={
                    'knowledge_base_id': kb_id, 'limit': 50})['data']['items']
                assert runs and all(run.get('document_display_name') == expected_names[run['document_id']]
                                    for run in runs), 'Compile names must match document names'
            for document in documents:
                chunks = client._request('GET', '/v1/knowledge/documents/chunks', params={
                    'knowledge_base_id': kb_id, 'document_id': document['id'], 'offset': 0, 'limit': 20})
                detail = client.get_document(kb_id, document['id'])
                checks['documents'].append({
                    **{key: document.get(key) for key in ('id', 'name', 'display_name')}, 'mode': mode,
                    **{key: detail.get(key) for key in ('ingest_status', 'wiki_status', 'graph_status')},
                    'title': document.get('metadata', {}).get('title'),
                    'filename': document.get('metadata', {}).get('filename'),
                    'chunk_count': chunks.get('total'),
                    'search_token_in_chunks': report['search_token'] in json.dumps(chunks, ensure_ascii=False),
                })
            result = api('POST', '/api/kb/search', json={
                'question': report['search_token'] + ' ContextDB Wiki 图谱', 'kb_ids': [kb_id],
                'view': 'source', 'top_k': 6, 'threshold': 0.2, 'query_rewrite': False})
            checks['queries'][mode] = {'chunks': len(result.get('chunks', [])),
                'names': [{key: chunk.get(key) for key in ('doc_id', 'docnm_kwd', 'document_display_name', 'similarity')}
                          for chunk in result.get('chunks', [])]}
        wiki = client.wiki_search([space['wiki_kb_id']], '.+', mode='regex', limit=20)
        checks['wiki'] = {'pages': len(wiki['pages']), 'titles': [page.get('title') for page in wiki['pages']]}
        graph = client.graph_visual(space['graph_kb_id'], max_nodes=100, max_edges=100)
        checks['graph'] = {'entities': graph.get('entity_total'), 'relations': graph.get('relation_total')}
        checks['all_ingested'] = all(item['ingest_status'] == 'succeeded' for item in checks['documents'])
        checks['all_have_chunks'] = all(item['chunk_count'] for item in checks['documents'])
        checks['names_visible'] = all(item.get('display_name') and not item['display_name'].startswith('doc-')
                                     for item in checks['documents'])
        checks['uploaded_names_exact'] = all(item.get('display_name') == report['uploaded_filename']
                                            for item in checks['documents'] if item.get('filename'))
        checks['base_names_exact'] = {item['display_name'] for item in checks['bases']} == {
            report['name'], report['name'] + '（知识图谱）'}
        checks['retrieval_named'] = all(result['chunks'] and all(
            item.get('document_display_name') and not item['document_display_name'].startswith('doc-')
            for item in result['names']) for result in checks['queries'].values())
        checks['wiki_compiled'] = all(item['wiki_status'] == 'compiled' for item in checks['documents'] if item['mode'] == 'wiki')
        checks['graph_built'] = bool(checks['graph']['entities'] and checks['graph']['relations'])
        checks['wiki_searchable'] = checks['wiki']['pages'] > 0
        failures = [key for key in ('all_ingested', 'all_have_chunks', 'names_visible',
                    'uploaded_names_exact', 'base_names_exact', 'retrieval_named', 'wiki_compiled',
                    'graph_built', 'wiki_searchable') if not checks[key]]
        checks['passed'] = not failures
        report['checks'] = checks
        save()
        event('checks', checks)
        assert not failures, 'Acceptance failed: ' + ', '.join(failures)

    if args.check_only:
        check_pipeline()
        return

    def wait_job(job_id):
        deadline, previous = time.monotonic() + args.timeout, None
        while True:
            item = api('GET', f'/task_status/{job_id}')
            state = (item.get('status'), item.get('phase'), item.get('progress'))
            if state != previous:
                event(job_id, {'status': state[0], 'phase': state[1], 'progress': state[2]})
                previous = state
            report.setdefault('job_states', {})[job_id] = {
                key: item.get(key) for key in ('status', 'phase', 'progress', 'message', 'metrics')}
            save()
            if item['status'] == 'completed':
                return item
            if item['status'] in ('failed', 'partial', 'cancelled'):
                raise RuntimeError(f'Own job {job_id} ended as {item["status"]}: {item.get("message")}')
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Own job {job_id} is still {item["status"]}; resume this script later')
            time.sleep(3)

    if not report.get('space_created'):
        api('POST', '/api/kb/spaces', json={
            'scope': report['scope'], 'name': report['name'], 'graph_enabled': True})
        report['space_created'] = True
        save()
        event('created_space', report['scope'])
    if 'file' not in report['jobs']:
        token = report.setdefault('search_token', 'NameCheck' + report['scope'].rsplit('-', 1)[-1])
        body = (f'# 中文文件名称验收\n\n验收检索标识：{token}。\n\n'
                '名称验收系统使用 ContextDB 管理知识。Wiki 知识库保存可阅读知识页面；'
                '图谱知识库保存实体与关系。Python 是编程语言，支持自动化文件处理。'
                '平台上传的中文文档应保留原始文件名，并可通过知识检索找到。\n')
        name = '中文名称验收（完整版）.md'
        report['uploaded_filename'] = name
        result = api('POST', '/api/uploads', data={'space_scope': report['scope']},
                     files={'files': (name, body.encode('utf-8'), 'text/markdown')})
        report['jobs']['file'] = result['task_id']
        save()
    if 'web' not in report['jobs']:
        report['source_url'] = SOURCE_URL
        result = api('POST', '/entries/web/start', json={
            'space_scope': report['scope'], 'url': SOURCE_URL,
            'crawl_mode': 'page', 'max_pages': 1, 'max_depth': 1})
        report['jobs']['web'] = result['task_id']
        save()
    for job_id in report['jobs'].values():
        wait_job(job_id)
    if not report.get('release_id'):
        result = api('POST', f'/tasks/{report["jobs"]["web"]}/publish')
        report['release_id'] = result['release_id']
        save()
        event('published', report['release_id'])

    progress = api('GET', f'/api/kb/spaces/{report["scope"]}/progress')
    own_sync = next(item for item in progress['jobs']
                    if item['params']['release_id'] == report['release_id'])
    report['sync_job_id'] = own_sync['task_id']
    save()
    wait_job(own_sync['task_id'])
    deadline, previous = time.monotonic() + args.timeout, None
    while True:
        progress = api('GET', f'/api/kb/spaces/{report["scope"]}/progress')
        mappings = progress['mappings']
        report['space'] = progress['space']
        report['mappings'] = mappings
        assert len(mappings) == 4, 'Expected two sources in each of Wiki and graph libraries'
        states = [(row['target_mode'], row['document_id'], row.get('official', {}).get('ingest_status'),
                   row.get('official', {}).get('graph_status'), row.get('official', {}).get('wiki_status'))
                  for row in mappings]
        if states != previous:
            event('official_processing', states)
            previous = states
        save()
        own_documents = {row['document_id'] for row in mappings}
        for kb_id in {row['knowledge_base_id'] for row in mappings}:
            reviews = api('GET', '/api/kb/reviews', params={
                'kb_id': kb_id, 'lifecycle_state': 'pending_human', 'page_size': 100})['reviews']
            for review in reviews:
                review_id = review['review_id']
                if review.get('document_id') not in own_documents or review_id in report['reviews_confirmed']:
                    continue
                api('POST', f'/api/kb/reviews/{review_id}/action', json={'action': 'confirm'})
                report['reviews_confirmed'].append(review_id)
                save()
                event('confirmed_review', review_id)
        if any(row.get('official', {}).get('ingest_status') == 'failed' for row in mappings):
            raise RuntimeError('An own document failed ingestion; see retained official state in report')
        if all(row.get('official', {}).get('ingest_status') == 'succeeded' for row in mappings):
            report['all_ingested'] = True
            save()
            wiki_done = all(row.get('official', {}).get('wiki_status') == 'compiled'
                            for row in mappings if row['target_mode'] == 'wiki')
            graph_done = any(row.get('official', {}).get('graph_status') == 'succeeded'
                             for row in mappings if row['target_mode'] == 'graph')
            if wiki_done and graph_done:
                event('all_ingested_and_built', report['scope'])
                break
        if time.monotonic() >= deadline:
            raise TimeoutError('Official ingestion/review still pending; resume this script later')
        time.sleep(4)
    check_pipeline()
    event('report', str(report_path))


if __name__ == '__main__':
    main()
