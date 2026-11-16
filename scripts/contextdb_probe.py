"""Verify official contracts using disposable resources; never edits existing documents."""
import argparse
import asyncio
import hashlib
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from dotenv import load_dotenv

from common.env_sanitize import sanitize_no_proxy
from integrations.contextdb import ContextDBClient, ContextDBError, ContextDBConflictError


OFFICIAL_DOCS = 'https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html'


def official_wiki_contracts():
    response = requests.get(OFFICIAL_DOCS, timeout=30)
    response.raise_for_status()
    match = re.search(r'<script\b[^>]*id="article-data"[^>]*>(.*?)</script>', response.content.decode('utf-8'), re.S)
    if not match:
        raise ValueError('官方文档没有可读取的 article-data；不能据此判断接口不存在')
    articles = json.loads(match.group(1))
    wiki_apis = [page['slug'] for page in articles
                if page['slug'].startswith('api-') and '/wiki/' in page.get('body', '')]
    return {'url': OFFICIAL_DOCS, 'sha256': hashlib.sha256(response.content).hexdigest(),
            'article_count': len(articles), 'wiki_api_articles': wiki_apis,
            'reviewed_articles': ['knowledge-wiki', 'api-updateKnowledgeBase', 'api-listKnowledgeDocumentChunks']}


async def official_mcp_catalog(client):
    # Use the official SDK for discovery; this probe does not call or wrap knowledge tools.
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(headers={'X-API-Key': client.api_key}, timeout=30) as http:
        async with streamable_http_client(f'{client.base_url}/v1/mcp', http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names, cursors, cursor = [], set(), None
                while True:
                    page = await session.list_tools(cursor=cursor)
                    names.extend(tool.name for tool in page.tools)
                    cursor = page.nextCursor
                    if not cursor:
                        return {'status': 'available', 'tool_names': sorted(set(names)),
                                'wiki_tools': sorted(name for name in set(names) if 'wiki' in name.lower())}
                    if cursor in cursors:
                        raise ValueError('官方 MCP 工具目录返回重复游标，不能视为完整目录')
                    cursors.add(cursor)


def source_chunk_check(client, kb_id, document_id):
    before = client.get_document(kb_id, document_id)
    if before.get('ingest_status') != 'succeeded':
        return {'status': 'not_tested', 'ingest_status': before.get('ingest_status'),
                'reason': '资料未入库成功，待审或处理中不能作为空文档继续编译'}
    offset, ids, total = 0, set(), None
    while total is None or offset < total:
        page = client._request('GET', '/v1/knowledge/documents/chunks',
                               params={'knowledge_base_id': kb_id, 'document_id': document_id,
                                       'offset': offset, 'limit': 1})
        if page.get('review_status') == 'pending':
            return {'status': 'not_tested', 'reason': '切片读取期间文档进入待评审状态'}
        count, chunks = page.get('total'), page.get('chunks')
        if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > 200:
            raise ValueError('独立探测文档未返回可验证的切片总数')
        if total is not None and count != total:
            raise ValueError('分页期间切片总数变化，不能判定完整')
        total = count
        if not isinstance(chunks, list) or len(chunks) != 1:
            raise ValueError('切片分页缺失或未遵守 limit，不能判定完整')
        chunk = chunks[0]
        if not isinstance(chunk, dict):
            raise ValueError('切片返回格式无效')
        chunk_id = chunk.get('chunk_id')
        content = chunk.get('content')
        if not isinstance(chunk_id, str) or not chunk_id or chunk_id in ids or not isinstance(content, str) or not content.strip():
            raise ValueError('切片 ID 重复、缺失或正文为空')
        ids.add(chunk_id)
        offset += 1
    after = client.get_document(kb_id, document_id)
    stable = (after.get('ingest_status') == 'succeeded' and before.get('id') == after.get('id') == document_id
              and bool(before.get('updated_at')) and before.get('updated_at') == after.get('updated_at'))
    return {'status': 'available' if stable and total > 1 else 'unconfirmed',
            'chunks_read': len(ids), 'reported_total': total, 'pagination_verified': total > 1,
            'source_marker': 'document_id + updated_at', 'source_marker_stable': stable,
            'reason': '完整分页读取并核对来源标识；仅验证本次独立资料，不代表跨接口事务快照'}


def delete_compiler_probe(client, kb_id, document_ids):
    if document_ids:
        client.delete_documents(kb_id, document_ids)
        for _ in range(30):
            if client.list_documents(kb_id, page_size=1).get('total') == 0:
                break
            time.sleep(1)
        else:
            return {'status': 'pending_document_deletion', 'remaining_probe_kb_id': kb_id}
    client.delete_knowledge_base(kb_id)
    # The DATA API may report an absent KB as 400; verify absence by its complete readable list.
    for _ in range(10):
        bases = client.list_knowledge_bases()['knowledge_bases']
        found = any(base.get('id') == kb_id for base in bases)
        if not found:
            return {'status': 'deleted', 'probe_kb_id': kb_id}
        time.sleep(1)
    return {'status': 'delete_accepted', 'probe_kb_id': kb_id}


def wiki_compiler_readiness(write=False):
    client = ContextDBClient(max_retries=0, timeout=30)
    report = {'source': 'ContextDB official DATA API and MCP',
              'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'write_probe': write, 'checks': {}, 'cleanup': {'status': 'not_needed'}}
    checks = report['checks']
    for name in ('source_chunks', 'page_location', 'compiler_metadata_write', 'page_cas', 'compiler_isolation'):
        checks[name] = {'status': 'not_tested'}
    try:
        report['official_docs'] = official_wiki_contracts()
    except (requests.RequestException, ValueError) as exc:
        report['official_docs'] = {'status': 'failed', 'error_type': type(exc).__name__}
    try:
        report['official_mcp'] = asyncio.run(official_mcp_catalog(client))
    except Exception as exc:
        report['official_mcp'] = {'status': 'failed', 'error_type': type(exc).__name__}
    # A body-only PUT and a successful search do not establish compiler ownership or provenance writes.
    checks['page_location'] = {'status': 'unconfirmed',
        'reason': '当前页可按 ID 读取，但受影响主题及来源映射的完整定位契约未确认；50 条搜索或类别列表不足以证明完整'}
    checks['compiler_metadata_write'] = {'status': 'unconfirmed',
        'reason': '已验证接口仅覆盖正文创建与版本更新；来源切片、目录与链接的编译写契约未确认，未发送猜测字段'}
    checks['compiler_isolation'] = {'status': 'unconfirmed',
        'reason': '未确认停止或隔离目标页面云端自动编译的官方契约；未尝试猜测开关或调整业务库'}
    created, document_ids = None, []
    if write:
        try:
            created = client.create_knowledge_base('_wiki_compiler_probe_' + uuid.uuid4().hex[:12],
                wiki_enabled=True, graph_enabled=False, review_enabled=False, chunk_size=128, chunk_overlap=16)
            kb_id = created['id']
            try:
                page = client.create_wiki_page(kb_id, '独立版本验证 ' + uuid.uuid4().hex[:8], '# 独立版本验证\n\n版本一。')
                detail = client.get_wiki_page(kb_id, page['page_id'])
                expected = detail['version']
                content = '# 独立版本验证\n\n版本二，仅供验证。'
                updated = client.update_wiki_page(kb_id, page['page_id'], content, expected)
                stale_rejected = False
                try:
                    client.update_wiki_page(kb_id, page['page_id'], '过期写入不可覆盖', expected)
                except ContextDBConflictError:
                    stale_rejected = True
                current = client.get_wiki_page(kb_id, page['page_id'])
                for _ in range(5):
                    if current.get('content') == content:
                        break
                    time.sleep(2)
                    current = client.get_wiki_page(kb_id, page['page_id'])
                valid = (isinstance(expected, int) and not isinstance(expected, bool) and stale_rejected
                         and current.get('content') == content and current.get('version') == updated.get('version')
                         and isinstance(current.get('version'), int) and current['version'] > expected)
                checks['page_cas'] = {'status': 'available' if valid else 'failed',
                    'stale_rejected': stale_rejected, 'content_readback_matches': current.get('content') == content,
                    'initial_version': expected, 'update_returned_version': updated.get('version'),
                    'readback_version': current.get('version'), 'readback_wait_limit_seconds': 10}
            except (ContextDBError, KeyError, ValueError, TypeError) as exc:
                checks['page_cas'] = {'status': 'failed', 'error_type': type(exc).__name__}
            try:
                text = '\n\n'.join(f'第 {i} 项测试说明。' + '该内容只验证分页读取与来源稳定性，不属于业务资料。' * 8 for i in range(8))
                document = client.create_text_document(kb_id, '独立分页验证.txt', text, review_enabled=False)
                document_ids.append(document['id'])
                client.wait_for_ingest(kb_id, document['id'], timeout=180, poll_interval=2)
                checks['source_chunks'] = source_chunk_check(client, kb_id, document['id'])
            except (ContextDBError, KeyError, ValueError, TypeError) as exc:
                checks['source_chunks'] = {'status': 'failed', 'error_type': type(exc).__name__}
        except (ContextDBError, KeyError) as exc:
            report['resource_creation'] = {'status': 'failed', 'error_type': type(exc).__name__}
        finally:
            if created:
                try:
                    report['cleanup'] = delete_compiler_probe(client, created['id'], document_ids)
                except ContextDBError as exc:
                    report['cleanup'] = {'status': 'failed', 'remaining_probe_kb_id': created['id'],
                                         'http_status': exc.status_code}
    blocked = [name for name, check in checks.items() if check['status'] != 'available']
    report.update(ready=not blocked, blocked_checks=blocked,
                  decision='retain_contextdb_compiler' if blocked else 'eligible_for_compiler_implementation')
    return report


def probe(write=False):
    client = ContextDBClient(max_retries=0, timeout=30)
    bases = client.list_knowledge_bases()['knowledge_bases']
    wiki = next((base for base in bases if base.get('wiki_enabled')), None)
    report = {'source': 'ContextDB official DATA API and MCP', 'features': {}, 'cleanup': {}}
    features = report['features']
    page_id = None
    if wiki:
        items = client.wiki_search([wiki['id']], '.+', mode='regex', limit=1).get('pages', [])
        if items:
            page_id = items[0]['page_id']
            detail = client.get_wiki_page(wiki['id'], page_id)
            features['wiki_read'] = {'available': isinstance(detail.get('content'), str) and isinstance(detail.get('version'), int),
                                     'method': 'GET', 'path': '/v1/knowledge/wiki/pages/detail'}
    candidates = {
        'wiki_revisions': '/v1/knowledge/wiki/revisions',
        'wiki_page_revisions': '/v1/knowledge/wiki/pages/revisions',
        'wiki_pending_revisions': '/v1/knowledge/wiki/revisions/pending',
        'wiki_issues': '/v1/knowledge/wiki/issues',
    }
    if wiki and page_id:
        for name, path in candidates.items():
            try:
                result = client._request('GET', path, params={'knowledge_base_id': wiki['id'], 'page_id': page_id})
                features[name] = {'available': True, 'method': 'GET', 'path': path,
                                  'response_keys': list(result) if isinstance(result, dict) else []}
                if name == 'wiki_revisions':
                    features[name].update(page_id_required=True, response_content='revision_metadata',
                                          history_full_content=False)
            except ContextDBError as exc:
                features[name] = {'available': False, 'status': 'unconfirmed', 'http_status': exc.status_code,
                                  'error_code': exc.error_code, 'request_id': exc.request_id,
                                  'server_reason': str(exc),
                                  'reason': '此调用未通过验证；HTTP 403 本身不能证明服务不支持该能力'}
                if exc.error_code == 4007 and 'route is not declared in the DATA API contract' in str(exc):
                    features[name].update(status='not_declared', api_contract_status='not_declared')
    features['wiki_revision_approval'] = {'available': False, 'status': 'unconfirmed',
        'product_console_supported': True, 'api_contract_status': 'not_exposed',
        'reason': 'Wiki 产品指南明确支持待发布候选的接受/拒绝，但当前公开 API 未给出审批写入契约；禁止自行替代'}
    features['wiki_history_rollback'] = {'available': False, 'status': 'unconfirmed',
        'history_view_compare_product_supported': True, 'api_contract_status': 'not_exposed',
        'reason': '产品支持历史查看与版本比较，但未公开原生历史回滚契约；不回写旧正文模拟回滚'}
    features['strict_manual_publish'] = {'available': False, 'status': 'unconfirmed',
        'api_contract_status': 'not_exposed', 'documented_threshold_range': [0, 1],
        'reason': '官方阈值范围为0～1，达到阈值仍可自动入库；关闭重写自动入库只约束实际重写的文档，不保证全量人工，亦无已确认的 Wiki 全库强制人工发布契约'}
    features['agent_wiki_revision'] = {'available': False, 'status': 'unconfirmed',
        'api_contract_status': 'tool_not_exposed',
        'reason': '已发现的官方 MCP 工具未包含 Wiki 修订；禁止添加 REST 知识工具替代'}
    if write:
        created = None
        try:
            created = client.create_knowledge_base('_integration_probe_' + uuid.uuid4().hex[:12],
                                                    wiki_enabled=True, graph_enabled=False, review_enabled=False)
            page = client.create_wiki_page(created['id'], 'API 契约验证', '# API 契约验证\n\n仅供自动化接口校验。')
            detail = client.get_wiki_page(created['id'], page['page_id'])
            updated = client.update_wiki_page(created['id'], page['page_id'], '# API 契约验证\n\n已校验完整正文与版本更新。', detail['version'])
            features['wiki_edit'] = {'available': True, 'method': 'PUT', 'path': '/v1/knowledge/wiki/pages',
                                     'expected_version_required': True, 'returned_version': updated.get('version')}
            try:
                client.update_wiki_page(created['id'], page['page_id'], 'stale version must not overwrite', detail['version'])
                features['wiki_stale_rejected'] = {'available': False}
            except ContextDBConflictError:
                features['wiki_stale_rejected'] = {'available': True}
        finally:
            if created:
                try:
                    client.delete_knowledge_base(created['id'])
                    report['cleanup'] = {'deleted_probe_kb': created['id']}
                except ContextDBError as exc:
                    report['cleanup'] = {'remaining_probe_kb': created['id'], 'http_status': exc.status_code}
    return report


def main():
    load_dotenv()
    sanitize_no_proxy()
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--wiki-compiler', action='store_true', help='核查 Wiki 编译器接管条件，不改造官方 MCP')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = wiki_compiler_readiness(args.write) if args.wiki_compiler else probe(args.write)
    filename = 'contextdb-wiki-compiler-readiness.json' if args.wiki_compiler else 'contextdb-capabilities.json'
    path = Path(args.output or f'docs/architecture/{filename}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
