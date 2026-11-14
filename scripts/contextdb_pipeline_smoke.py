"""Explicit cloud integration check in disposable Wiki and graph libraries."""
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from zipfile import ZipFile

from dotenv import load_dotenv
from governance.contextdb_sync import run_sync, enqueue_sync, knowledge_kb_name
from governance.database import connection
from governance.store import Store
from integrations.contextdb import ContextDBClient, ContextDBError


def cleanup(client,kb):
    documents=client.list_documents(kb['id'],page_size=100)['documents']
    if documents:
        client.delete_documents(kb['id'],[d['id'] for d in documents])
    deadline=time.monotonic()+120
    while client.list_documents(kb['id'],page_size=100)['documents']:
        if time.monotonic()>deadline:raise RuntimeError('测试文档删除尚未完成')
        time.sleep(2)
    client.delete_knowledge_base(kb['id'])


def resume_report():
    path=Path('docs/architecture/contextdb-pipeline-smoke.json')
    report=json.loads(path.read_text())
    client=ContextDBClient()
    scope=report['scope']
    assert scope.startswith('smoke-')
    report['first_attempt_errors']=report['errors']
    report['errors']=[]
    for mode,kb_id in report['delivery']['targets'].items():
        kb=client.get_knowledge_base(kb_id)
        if kb['name']!=knowledge_kb_name(scope,mode):raise RuntimeError('探测资源身份不匹配，拒绝清理')
        documents=client.list_documents(kb_id,page_size=100)['documents']
        item={'knowledge_base_id':kb_id,'ingest_states':[d['ingest_status'] for d in documents]}
        if mode=='graph':
            graph=client.graph_visual(kb_id,max_nodes=100,max_edges=100)
            item.update(graph_states=[d['graph_status'] for d in documents],entities=graph['entity_total'],relations=graph['relation_total'])
        else:item['pages_returned']=len(client.wiki_search([kb_id],'.+',mode='regex',limit=20)['pages'])
        report['targets'][mode]=item
        cleanup(client,kb)
        report['cleanup'][mode]=True
    report['verified_after_async_completion']=True
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


def main():
    load_dotenv()
    from common.env_sanitize import sanitize_no_proxy
    sanitize_no_proxy()
    # Test scopes must never reuse explicitly configured production targets.
    os.environ.pop('CONTEXTDB_KB_ID', None)
    os.environ.pop('CONTEXTDB_GRAPH_KB_ID', None)
    with connection() as conn:
        owner = conn.execute('SELECT id FROM platform_users WHERE email=%s', (os.environ['PLATFORM_ADMIN_EMAIL'],)).fetchone()['id']
    from webapi.auth import client_for_user
    client = client_for_user(owner)
    store = Store(client=client, owner_id=owner)
    if store.worker_alive():
        raise RuntimeError('请在独立测试实例中运行，避免与任务 Worker 同时处理探测任务')
    scope = 'smoke-' + uuid.uuid4().hex[:12]
    job = release_id = None
    report = {'scope':scope, 'targets':{}, 'cleanup':{}, 'errors':[]}
    try:
        with tempfile.TemporaryDirectory(prefix='contextdb-pipeline-') as directory:
            path = Path(directory) / 'capture.zip'
            body = '# 企业知识平台\n\nContextDB 提供知识解析、检索和治理。deepagents 是 Agent 执行框架，使用 ContextDB 官方 MCP 查询知识。Docker PostgreSQL 保存平台账号、会话与任务。Wiki 库和实体关系图谱库使用独立模式。'
            with ZipFile(path,'w') as archive:
                archive.writestr('rag_documents.jsonl',json.dumps({'id':'smoke-source','version_id':'smoke-v1','title':'企业知识平台','source_format':'markdown','content':body},ensure_ascii=False)+'\n')
            release_id = store.create_release('smoke-capture',scope,1,['smoke-v1'],path)
            job = enqueue_sync(store,release_id,scope)
            store.update_job(job['task_id'],status='running')
            result = run_sync(store,job)
            report['delivery'] = result
            if result['errors'] or result['uploaded'] != 2:
                raise RuntimeError('双库上传未全部受理')
            with connection() as conn:
                mappings = conn.execute('SELECT * FROM knowledge_sync WHERE owner_id=%s AND scope=%s',(owner,scope)).fetchall()
            assert len(mappings) == 2
            for mapping in mappings:
                mode, kb, doc = mapping['target_mode'],mapping['knowledge_base_id'],mapping['document_id']
                report['targets'][mode] = {'knowledge_base_id':kb,'document_id':doc}
                detail = client.wait_for_ingest(kb,doc,timeout=180,poll_interval=2)
                if detail['ingest_status']=='pending_review':
                    reviews = client.list_reviews(kb,lifecycle_state='pending_human')['reviews']
                    review = next(r for r in reviews if r.get('document_id')==doc)
                    client.review_action(review['review_id'],'confirm')
                    deadline=time.monotonic()+180
                    while time.monotonic()<deadline:
                        detail=client.get_document(kb,doc)
                        if detail['ingest_status'] in ('succeeded','failed'):break
                        time.sleep(2)
                report['targets'][mode]['ingest_status'] = detail['ingest_status']
                if detail['ingest_status'] != 'succeeded':
                    raise RuntimeError(f'{mode} 官方入库未成功：{detail.get("ingest_error_message")}')
                if mode=='graph':
                    deadline=time.monotonic()+180
                    while detail.get('graph_status') in ('pending','queued','processing') and time.monotonic()<deadline:
                        time.sleep(2);detail=client.get_document(kb,doc)
                    graph=client.graph_visual(kb,max_nodes=100,max_edges=100)
                    report['targets'][mode].update(graph_status=detail.get('graph_status'),entities=graph.get('entity_total'),relations=graph.get('relation_total'))
                else:
                    deadline=time.monotonic()+180
                    pages=[]
                    while not pages and time.monotonic()<deadline:
                        pages=client.wiki_search([kb],'.+',mode='regex',limit=10).get('pages',[])
                        if not pages:time.sleep(3)
                    report['targets'][mode]['pages_returned']=len(pages)
    except Exception as exc:
        report['errors'].append(str(exc)[:1000])
    finally:
        for mode in ('wiki','graph'):
            kb=client.find_knowledge_base(knowledge_kb_name(scope,mode))
            if not kb:
                report['cleanup'][mode]=True
                continue
            deadline=time.monotonic()+180
            while True:
                try:
                    cleanup(client,kb)
                    report['cleanup'][mode]=True
                    break
                except ContextDBError as exc:
                    if time.monotonic()>deadline:
                        report['cleanup'][mode]={'id':kb['id'],'error':str(exc)[:300]}
                        break
                    time.sleep(3)
        with connection() as conn:
            conn.execute('DELETE FROM knowledge_sync WHERE owner_id=%s AND scope=%s',(owner,scope))
            conn.execute("DELETE FROM runtime_records WHERE owner_id=%s AND metadata->>'scope'=%s",(owner,scope))
        path = Path('docs/architecture/contextdb-pipeline-smoke.json')
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    import sys
    if '--resume-cleanup' in sys.argv:
        load_dotenv();resume_report()
    else:main()
