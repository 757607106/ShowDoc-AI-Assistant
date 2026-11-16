"""Retry completed captures from saved sources; do not repeat login or cloud writes."""
import json
import os
from pathlib import Path
from unittest.mock import Mock

from governance.store import Store
from governance.worker import process_job
from tests.contextdb_fake import FakeContextDBClient


def test_video_only_capture_recovery_reuses_saved_sources_without_network(tmp_path, monkeypatch):
    fake=FakeContextDBClient()
    store=Store(client=fake,owner_id=os.environ['TEST_PLATFORM_USER'])
    from governance.spaces import persist_space
    kb = fake.create_knowledge_base('恢复资料', wiki_enabled=True, graph_enabled=False, review_enabled=True)
    persist_space(store, {'scope': 'default', 'name': kb['name'], 'knowledge_base_id': kb['id'],
        'mode': 'wiki', 'lifecycle': 'active'})
    monkeypatch.setattr('webapi.auth.client_for_user',lambda *args:fake)
    monkeypatch.setattr('crawlers.cyb.CYBAuthenticator.login',Mock(side_effect=AssertionError('Unexpected login')))
    monkeypatch.setattr('common.converter.RAGContentPipeline.convert',Mock(side_effect=AssertionError('Unexpected local parsing')))
    original=store.create_job('cyb',{},scope='default')
    output=Path(original['output_dir']);output.mkdir(parents=True)
    raw=[{'id':'tutorial-1','title':'视频来源','category':'教程','content':'','updated_at':'',
          'source_format':'html','metadata':{'content':'','videoUrl':'https://www.bilibili.com/video/example/'}},
         {'id':'faq-1','title':'已保存问答','category':'问答','content':'<p>已有完整正文</p>','updated_at':'',
          'source_format':'html','metadata':{}}]
    source=output/'source_documents.jsonl'
    source.write_text('\n'.join(json.dumps(row,ensure_ascii=False) for row in raw)+'\n')
    original_bytes=source.read_bytes()
    (output/'summary.json').write_text(json.dumps({'failed_documents':1,'error_count':1}))
    (output/'collection_complete.json').write_text(json.dumps({'document_ids':['tutorial-1','faq-1']})+'\n')
    store.update_job(original['task_id'],status='partial',failed_pages=1)
    retry=store.create_job('cyb',{},scope='default',retry_of=original['task_id'])
    process_job(store,retry)
    recovered=store.get_job(retry['task_id'])
    assert recovered['status']=='completed' and recovered['failed_pages']==0
    assert recovered['summary']['total_documents']==2
    assert recovered['summary']['video_reference_documents']==1
    assert '视频内容未采集' in recovered['message']
    assert source.read_bytes()==original_bytes and store.get_job(original['task_id'])['status']=='partial'
    assert len(store.list_documents(retry['task_id']))==2
    assert fake.documents=={} and set(fake.knowledge_bases)=={kb['id']}
    sync_jobs = [job for job in store.list_jobs() if job['kind'] == 'ctxdb_sync']
    assert len(sync_jobs) == 1 and recovered['phase'] == 'submitted'
    from governance.contextdb_sync import run_sync
    assert run_sync(store, sync_jobs[0])['uploaded'] == 2
    assert len(fake.documents) == 2
