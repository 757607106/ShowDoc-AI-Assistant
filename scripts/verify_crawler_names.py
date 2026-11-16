"""Run real crawler/name acceptance in a new, retained, owner-scoped test space.

Only confirms original text for this run's pending reviews. Never deletes data,
changes permissions, starts workers, or changes an existing business space.
Re-run with the same report to resume; --check-only performs read checks only.
"""
import argparse
import json
import os
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'showdoc': 'ShowDoc', 'cyb': '云创业版', 'tiantong': '天通'}


def expected_name(document, capture):
    metadata = capture.get('metadata') or {}
    filename = metadata.get('filename')
    if metadata.get('parent_document_id') and Path(capture.get('title', '')).suffix:
        filename = capture['title']
    if isinstance(filename, str) and filename.strip():
        return filename.strip()
    title = capture.get('title')
    assert isinstance(title, str) and title.strip(), 'Captured title must be retained'
    suffix = re.search(r'\.[a-z\d]{1,12}$', document['name'], re.I)
    suffix = suffix[0] if suffix else ''
    title = title.strip()
    return title if title.lower().endswith(suffix.lower()) else title + suffix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry', choices=LABELS, required=True)
    parser.add_argument('--item-id', default='412')
    parser.add_argument('--selected-ids', help='Comma-separated source IDs; omitted means the entire listed source')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--timeout', type=int, default=2400)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    from common.env_sanitize import sanitize_no_proxy
    sanitize_no_proxy()
    path = args.report.resolve()
    report = json.loads(path.read_text()) if path.exists() else {
        'entry': args.entry, 'scope': 'crawler-name-check-' + args.entry + '-' + uuid.uuid4().hex[:10],
        'name': '爬虫名称验收·' + LABELS[args.entry] + '·20261116', 'resources_retained': True,
        'reviews_confirmed': [], 'params': {'item_id': args.item_id} if args.entry == 'showdoc' else {},
        'selected_ids': args.selected_ids.split(',') if args.selected_ids else [],
    }
    assert report['entry'] == args.entry and report['scope'].startswith('crawler-name-check-')
    if args.check_only:
        assert path.exists() and report.get('job_id'), 'Check-only requires an existing completed run'
    path.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report['updated_at'] = datetime.now(timezone.utc).isoformat()
        temporary = path.with_suffix(path.suffix + '.part')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)

    def event(stage, value):
        print(json.dumps({'stage': stage, 'value': value}, ensure_ascii=False), flush=True)

    session = requests.Session()

    def api(method, endpoint, **kwargs):
        response = session.request(method, args.base_url + endpoint, timeout=120, **kwargs)
        response.raise_for_status()
        body = response.json()
        if body.get('success') is False:
            raise RuntimeError(f'{method} {endpoint}: {body.get("message", "request failed")}')
        return body

    identity = api('POST', '/api/v1/auth/login', json={
        'email': os.environ['PLATFORM_ADMIN_EMAIL'], 'password': os.environ['PLATFORM_ADMIN_PASSWORD']})
    session.headers['Authorization'] = 'Bearer ' + identity['access_token']
    assert report.get('owner_id', identity['user']['id']) == identity['user']['id'], 'Report belongs to another owner'
    report['owner_id'] = identity['user']['id']

    def pages(endpoint, key, params=None, native=False, size=100, offset=False):
        output, page, seen = [], 1, set()
        while True:
            pagination = {'offset': (page - 1) * size, 'limit': size} if offset else {'page': page, 'page_size': size}
            result = api('GET', endpoint, params={**(params or {}), **pagination})
            result = result['data'] if native else result
            batch = result.get(key, [])
            if batch:
                signature = json.dumps(batch, sort_keys=True, ensure_ascii=False)
                assert signature not in seen, 'Pagination repeated a page'
                seen.add(signature)
                output.extend(batch)
            total = result.get('total')
            if not batch or (isinstance(total, int) and len(output) >= total) or len(batch) < size:
                return output
            page += 1

    def compile_rows(kb):
        output, cursor, seen = [], None, set()
        while True:
            data = api('GET', '/api/contextdb/v1/knowledge/wiki/compile-runs',
                       params={'knowledge_base_id': kb, 'limit': 100, **({'cursor': cursor} if cursor else {})})['data']
            output.extend(data.get('items', []))
            cursor = data.get('next_cursor')
            if not cursor:
                return output
            assert cursor not in seen, 'Compile cursor repeated'
            seen.add(cursor)

    def progress():
        return pages('/api/kb/spaces/' + report['scope'] + '/progress', 'mappings', size=50)

    def documents():
        space = api('GET', '/api/kb/spaces/' + report['scope'])['space']
        report['space'] = space
        return {mode: pages('/api/contextdb/v1/knowledge/documents', 'documents',
            {'knowledge_base_id': space[mode + '_kb_id']}, native=True) if space.get(mode + '_kb_id') else []
            for mode in ('wiki', 'graph')}

    def detail(doc):
        return api('GET', '/api/contextdb/v1/knowledge/documents/detail',
                   params={'knowledge_base_id': doc['knowledge_base_id'], 'document_id': doc['id']})['data']

    def reviews(kb):
        return pages('/api/kb/reviews', 'reviews', {'kb_id': kb})

    def all_nodes(kb):
        output, pending, seen = [], [None], set()
        while pending:
            parent = pending.pop()
            nodes = pages('/api/contextdb/v1/knowledge/nodes', 'items',
                {'knowledge_base_id': kb, **({'parent_node_id': parent} if parent else {})}, native=True)
            for node in nodes:
                assert node['node_id'] not in seen, 'Directory traversal repeated a node'
                seen.add(node['node_id']); output.append(node)
                if node.get('node_type') == 'folder':
                    pending.append(node['node_id'])
        return output

    def check():
        libs = documents()
        count = len(report['captured_documents'])
        captures = {row['id']: api('GET', '/api/documents/' + row['version_id'])['document']
                    for row in report['captured_documents']}
        assert {str(row['id']) for row in report['selected_documents']} <= {
            str(capture.get('source_record_id')) for capture in captures.values()}, 'Every selected source ID, including duplicate titles, must be captured'
        mapping = progress()
        assert len(mapping) == count * 2, 'Every captured document must reach both targets'
        checks = {'documents': {}, 'reviews': {}, 'queries': {}, 'document_queries': {},
                  'retrieval_coverage': 'Every captured document queried with its ID filter, plus one unfiltered representative query per target library',
                  'pages_checked': ['documents', 'directory', 'progress', 'reviews', 'Wiki compile', 'retrieval', '@ mention']}
        bases = pages('/api/contextdb/v1/knowledge/knowledge_bases', 'knowledge_bases', native=True)
        for mode, docs in libs.items():
            kb = report['space'][mode + '_kb_id']
            base = next(base for base in bases if base['id'] == kb)
            assert base['display_name'] == report['name'] + ('（知识图谱）' if mode == 'graph' else '')
            assert len(docs) == count
            expected = {}
            for doc in docs:
                source_id = doc.get('metadata', {}).get('platform_source_id')
                assert source_id in captures, 'Cloud source must match this capture, not another run'
                capture = captures[source_id]
                assert doc['name'].startswith('doc-' + source_id + '.'), 'Technical source name must retain the captured ID'
                assert doc.get('metadata', {}).get('title') == capture['title'][:200], 'Cloud title must match captured source title'
                expected[doc['id']] = expected_name(doc, capture)
            assert all(doc['display_name'] == expected[doc['id']] for doc in docs)
            for row in mapping:
                if row['target_mode'] == mode:
                    assert row['official']['display_name'] == expected[row['document_id']]
            nodes = [node for node in all_nodes(kb) if node.get('document_id') in expected]
            assert {node['document_id'] for node in nodes} == set(expected)
            assert all(node['document_display_name'] == expected[node['document_id']] for node in nodes)
            review_rows = reviews(kb)
            assert all(row.get('document_id') in expected and row['document_display_name'] == expected[row['document_id']]
                       for row in review_rows), 'Review display must match original documents'
            reviewed = {row['document_id'] for row in review_rows}
            missing = [{'document_id': doc['id'], 'name': expected[doc['id']], 'source_extension': Path(doc['name']).suffix,
                        'review': 'not_returned_by_official_service'} for doc in docs if doc['id'] not in reviewed]
            checks['reviews'][mode] = {'records': len(review_rows), 'lifecycle_states': dict(Counter(
                row.get('lifecycle_state') for row in review_rows)), 'without_review': missing,
                'native_review_verified': not missing and all(row.get('lifecycle_state') in ('approved', 'auto_accepted') for row in review_rows),
                'status': 'verified' if not missing else 'no_native_review_records' if not review_rows else 'partial_native_review_records'}
            supported_missing = [row for row in missing if row['source_extension'].lower() in ('.md', '.txt', '.pdf', '.doc', '.docx')]
            assert not supported_missing, 'Every supported source document requires an actual review record, including mixed-format batches'
            details = [detail(doc) for doc in docs]
            assert all(doc.get('ingest_status') == 'succeeded' for doc in details)
            checks['documents'][mode] = [{key: doc.get(key) for key in (
                'id', 'name', 'display_name', 'ingest_status', 'wiki_status', 'graph_status', 'chunk_count')} for doc in details]
            if mode == 'wiki':
                runs = compile_rows(kb)
                assert {row['document_id'] for row in runs} == set(expected)
                assert all(row['document_display_name'] == expected[row['document_id']] and row['run_state'] == 'compiled' for row in runs)
                checks['compile_rows'] = len(runs)
                checks['wiki_summaries'] = []
                for doc in docs:
                    summary = api('GET', '/api/contextdb/v1/knowledge/wiki/summary', params={
                        'knowledge_base_id': kb, 'document_id': doc['id']})['data']
                    if not summary:
                        continue
                    title = summary.get('title') or ''
                    source_label = title == doc['name'] or title.startswith(doc['name'] + '/') or title.startswith(doc['name'] + ' - Summary')
                    wanted_title = expected[doc['id']] + title[len(doc['name']):] if source_label else title
                    assert summary.get('display_title') == wanted_title, 'Summary display title must preserve the source name without changing the stored title'
                    checks['wiki_summaries'].append({'document_id': doc['id'], 'raw_title': title,
                        'display_title': summary['display_title'], 'page_id': summary.get('page_id')})
            question = report['selected_documents'][0]['title'] + ' 相关内容'
            result = api('POST', '/api/kb/search', json={'question': question, 'kb_ids': [kb],
                'view': 'source', 'top_k': 6, 'threshold': 0.2, 'query_rewrite': False})
            chunks = [row for row in result.get('chunks', []) if row.get('type') != 'graph_context'
                      and row.get('citation_eligible') is not False and not str(row.get('chunk_id', '')).startswith('graph:')]
            assert chunks and all(row.get('doc_id', row.get('document_id')) in expected for row in chunks)
            assert all(row['document_display_name'] == expected[row.get('doc_id', row.get('document_id'))] for row in chunks)
            checks['queries'][mode] = {'question': question, 'chunk_count': len(chunks), 'names': list({row['document_display_name'] for row in chunks})}
            checks['document_queries'][mode] = []
            for doc in docs:
                capture = captures[doc['metadata']['platform_source_id']]
                result = api('POST', '/api/kb/search', json={'question': capture['title'] + ' 内容',
                    'kb_ids': [kb], 'document_ids': [doc['id']], 'view': 'source', 'top_k': 3,
                    'threshold': 0.2, 'query_rewrite': False})
                evidence = [row for row in result.get('chunks', []) if row.get('type') != 'graph_context'
                            and row.get('citation_eligible') is not False and not str(row.get('chunk_id', '')).startswith('graph:')]
                assert evidence and all(row.get('doc_id', row.get('document_id')) == doc['id'] for row in evidence), 'Every source must actually be retrievable'
                assert all(row['document_display_name'] == expected[doc['id']] for row in evidence)
                for row in evidence:
                    toc = row.get('toc_path')
                    if isinstance(toc, str) and (toc == doc['name'] or toc.startswith(doc['name'] + '/')):
                        assert row.get('display_toc_path') == expected[doc['id']] + toc[len(doc['name']):]
                checks['document_queries'][mode].append({'document_id': doc['id'], 'name': expected[doc['id']],
                    'question': capture['title'] + ' 内容', 'chunk_count': len(evidence)})
            picker = pages('/api/v1/knowledge/search', 'data', {'keyword': report['selected_documents'][0]['title']}, size=100, offset=True)
            picked = [doc for doc in picker if doc['knowledge_base_id'] == kb]
            assert picked and all(doc['file_name'] == expected[doc['id']] and doc['knowledge_base_name'] == base['display_name'] for doc in picked)
            report['checks'] = checks; save()
        wiki = api('GET', '/api/contextdb/v1/knowledge/wiki/search', params={
            'knowledge_base_id': report['space']['wiki_kb_id'], 'query': '.+', 'mode': 'regex', 'limit': 50})['data']
        wiki_items = wiki.get('items', wiki.get('pages', []))
        assert wiki_items, 'Actual compiled Wiki must be searchable'
        checks['wiki_search'] = {'pages_returned': len(wiki_items),
                                'titles': [{'raw': row.get('title'), 'display': row.get('display_title')} for row in wiki_items],
                                'coverage': 'Representative regex search; compile provenance checked for every source'}
        graph = api('GET', '/api/kb/graph', params={'kb_id': report['space']['graph_kb_id'], 'max_nodes': 500, 'max_edges': 500})
        checks['graph'] = {key: graph.get(key) for key in ('entity_total', 'relation_total', 'truncated')}
        report['checks'] = checks; save()
        assert graph.get('entity_total') and graph.get('relation_total'), 'Actual graph must contain entities and relations'
        checks['name_checks_passed'] = True
        checks['native_review_verified'] = all(row['native_review_verified'] for row in checks['reviews'].values())
        checks['passed'] = checks['native_review_verified']
        report['checks'] = checks; save(); event('passed' if checks['passed'] else 'incomplete',
            {'scope': report['scope'], 'documents_per_target': count, 'native_review_verified': checks['native_review_verified']})
        assert checks['passed'], 'Name checks passed, but native review was not verified for every source; see explicit review status'

    if args.check_only:
        check(); return
    if 'selected_documents' not in report:
        listed = [{'id': str(row['page_id']), 'title': row['page_title'], 'category': row.get('category')}
                  for row in api('GET', f'/entries/{args.entry}/documents', params=report['params'])['pages']]
        report['source_inventory_total'] = len(listed)
        wanted = set(map(str, report['selected_ids']))
        chosen = [page for page in listed if not wanted or str(page['id']) in wanted]
        assert chosen and (not wanted or {str(page['id']) for page in chosen} == wanted)
        report['selected_documents'] = chosen
        report['selection_mode'] = 'representative_sample' if wanted else 'all_listed_documents'
        save()
    if not report.get('space_created'):
        api('POST', '/api/kb/spaces', json={'scope': report['scope'], 'name': report['name'], 'graph_enabled': True})
        report['space_created'] = True; save(); event('created_space', report['scope'])
    if not report.get('job_id'):
        job = api('POST', f'/entries/{args.entry}/start', json={**report['params'], 'space_scope': report['scope'],
            **({'selected_ids': report['selected_ids']} if report['selected_ids'] else {})})
        report['job_id'] = job['task_id']; save(); event('started_capture', report['job_id'])
    deadline, previous = time.monotonic() + args.timeout, None
    while True:
        status = api('GET', '/task_status/' + report['job_id'])
        state = (status['status'], status['phase'], status.get('completed_pages'), status.get('failed_pages'))
        if state != previous:
            event('capture', state); previous = state
        report['capture_status'] = {key: status.get(key) for key in ('status', 'phase', 'completed_pages', 'failed_pages',
            'total_pages', 'message', 'metrics', 'submission_id', 'elapsed_seconds')}; save()
        if status['status'] in ('failed', 'partial', 'cancelled'):
            raise RuntimeError('Capture did not complete; own task and artifacts retained')
        if status['status'] == 'completed':
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Capture still pending; resume using this report')
        time.sleep(5)
    captured = api('GET', '/api/documents', params={'task_id': report['job_id']})['documents']
    assert len(captured) >= len(report['selected_documents'])
    report['captured_documents'] = captured
    assert {row['title'] for row in report['selected_documents']} <= {row['title'] for row in captured}
    if not report.get('release_id'):
        report['release_id'] = api('POST', '/tasks/' + report['job_id'] + '/publish')['release_id']; save()
    deadline, previous = time.monotonic() + args.timeout, None
    while True:
        mappings = progress()
        report['mappings'] = mappings
        libs = documents()
        own = {doc['id'] for docs in libs.values() for doc in docs}
        for kb in (report['space']['wiki_kb_id'], report['space']['graph_kb_id']):
            if not kb:
                continue
            for review in reviews(kb):
                if (review.get('document_id') in own and review.get('lifecycle_state') == 'pending_human'
                        and review['review_id'] not in report['reviews_confirmed']):
                    api('POST', '/api/kb/reviews/' + review['review_id'] + '/action', json={'action': 'confirm'})
                    report['reviews_confirmed'].append(review['review_id']); save(); event('confirmed_review', review['review_id'])
        graph_requests = report.setdefault('graph_requests', {})
        for row in mappings:
            official = row.get('official') or {}
            if (row['target_mode'] == 'graph' and row.get('document_id') in own
                    and 'graph' in row.get('retry_stages', []) and not official.get('latest_graph_event_id')
                    and official.get('graph_status') in (None, '', 'skipped')
                    and row['document_id'] not in graph_requests):
                graph_requests[row['document_id']] = {'source_id': row['source_id'], 'status': 'submitting'}
                save()
                try:
                    result = api('POST', '/api/kb/spaces/' + report['scope'] + '/retry', json={
                        'target_mode': 'graph', 'stage': 'graph', 'source_id': row['source_id']})['result']
                except Exception:
                    graph_requests[row['document_id']]['status'] = 'uncertain'; save()
                    raise
                event_id = result.get('event_id') or result.get('id')
                graph_requests[row['document_id']].update(status='submitted', event_id=event_id, result=result)
                save(); event('requested_graph', {'document_id': row['document_id'], 'event_id': event_id})
        state = dict(Counter((row['target_mode'], row.get('official', {}).get('ingest_status'),
                             row.get('official', {}).get('wiki_status'), row.get('official', {}).get('graph_status'))
                            for row in mappings))
        summary = {str(key): value for key, value in state.items()}
        if summary != previous:
            event('processing', summary); previous = summary
        save()
        assert not any(row.get('official', {}).get('ingest_status') == 'failed' for row in mappings), 'Own document ingestion failed'
        enough = len(mappings) == len(captured) * 2 and all(len(docs) == len(captured) for docs in libs.values())
        ingested = enough and all(row.get('official', {}).get('ingest_status') == 'succeeded' for row in mappings)
        wiki_done = ingested and all(row.get('official', {}).get('wiki_status') == 'compiled' for row in mappings if row['target_mode'] == 'wiki')
        graph_done = ingested and all(row.get('official', {}).get('graph_status') in ('succeeded', 'skipped') for row in mappings if row['target_mode'] == 'graph')
        if wiki_done and graph_done:
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Official processing still pending; resume using this report')
        time.sleep(20)
    check()


if __name__ == '__main__':
    main()
