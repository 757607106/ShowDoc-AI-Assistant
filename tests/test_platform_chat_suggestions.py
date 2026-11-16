"""Recommendation contracts with real PostgreSQL, a fake model and native-shaped MCP tools."""
import json
import os

import pytest
from flask import Flask, g
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from agent import config, registry, sessions
from governance.database import connection
from psycopg.types.json import Jsonb
from governance.store import StoreError
from webapi import chat_suggestions as suggestions


class KnowledgeClient:
    api_key = 'ctxdb-fake'

    def list_knowledge_bases(self, **kwargs):
        return {'knowledge_bases': [{'id': 'a', 'name': 'Knowledge'}], 'total': 1}

    def get_knowledge_base(self, kb_id):
        if kb_id != 'a':
            raise StoreError('denied', 403)
        return {'id': 'a'}

    def get_document(self, kb_id, document_id):
        if document_id != 'doc-a':
            raise StoreError('denied', 403)
        return {'id': document_id, 'knowledge_base_id': 'a'}


@pytest.fixture
def client(monkeypatch):
    owner = os.environ['TEST_PLATFORM_USER']
    app = Flask(__name__)
    app.register_blueprint(suggestions.chat_suggestions_bp)
    app.before_request(lambda: setattr(g, 'user', {'id': owner, 'role': 'admin'}))
    @app.errorhandler(StoreError)
    def error(exc):
        return {'success': False, 'message': str(exc)}, exc.status
    monkeypatch.setattr(suggestions, 'client_for_user', lambda *args: KnowledgeClient())
    monkeypatch.setattr(registry, 'model_config', lambda *args, **kwargs: {
        'type': 'KnowledgeQA', 'parameters': {'api_key': 'fake'}})
    return app.test_client()


def agent(settings):
    return config.save_agent({'name': 'Question helper', 'config': {'kb_selection_mode': 'selected',
        'knowledge_bases': ['a'], 'question_suggestions': settings}}, os.environ['TEST_PLATFORM_USER'])['id']


def completed_turn(settings, answer='Completed answer'):
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    effective = config.validate_config({'kb_selection_mode': 'selected', 'knowledge_bases': ['a'],
        'question_suggestions': {'follow_ups': settings}, '_whole_knowledge_bases': ['a']})
    with connection() as conn:
        conn.execute("UPDATE agent_sessions SET agent_config='{}' WHERE id=%s", (sid,))
        conn.execute("INSERT INTO agent_runs(id,session_id,owner_id,status,query,answer,request_json) VALUES ('answer',%s,%s,'completed','Original question',%s,%s)",
                     (sid, owner, answer, Jsonb({'agent_config': effective, 'knowledge_base_ids': ['a']})))
    return sid, f'/api/v1/sessions/{sid}/messages/answer/suggestions'


@pytest.fixture
def native_search(monkeypatch):
    calls = []
    async def search(query: str, knowledge_base_ids: list[str], top_k: int = 6):
        calls.append({'query': query, 'knowledge_base_ids': knowledge_base_ids, 'top_k': top_k})
        return {'chunks': [{'knowledge_base_id': 'a', 'document_id': 'doc-a', 'chunk_id': 'chunk-a',
            'content': '如何按日期查询经营利润？\n打开经营利润报表选择日期。', 'document_name': '经营利润指南'},
            {'knowledge_base_id': 'outside', 'document_id': 'secret', 'chunk_id': 'outside',
             'content': 'Secret question?', 'document_name': 'Hidden'},
            {'knowledge_base_id': 'a', 'document_id': 'doc-a', 'chunk_id': 'graph:synthetic',
             'content': 'Synthetic question?', 'document_name': 'Graph'}]}
    tool = StructuredTool.from_function(coroutine=search, name='knowledge.search', description='Official-shaped read tool')
    async def load(**kwargs):
        assert kwargs['api_key'] == 'ctxdb-fake' and kwargs['agent_config']['access_level'] == 'read_only'
        return [tool]
    monkeypatch.setattr(suggestions, 'load_knowledge_mcp_tools', load)
    return calls


def test_curated_starters_are_real_authored_questions_and_do_not_need_provider(client, monkeypatch):
    aid = agent({'starters': {'enabled': True, 'mode': 'curated', 'count': 2, 'items': ['First?', 'First?', 'Second?']}})
    monkeypatch.setattr(suggestions, 'build_model', lambda *args: pytest.fail('Curated suggestions must not call a model'))
    monkeypatch.setattr(suggestions, 'client_for_user', lambda *args: pytest.fail('Curated suggestions do not read knowledge'))
    response = client.get(f'/api/v1/agents/{aid}/suggested-questions')
    assert response.status_code == 200
    assert response.json['data']['questions'] == [{'question': 'First?', 'source': 'agent_config'}, {'question': 'Second?', 'source': 'agent_config'}]


def test_knowledge_starters_use_mcp_and_preserve_scope_and_source(client, native_search):
    aid = agent({'starters': {'enabled': True, 'mode': 'knowledge', 'count': 2}})
    url = f'/api/v1/agents/{aid}/suggested-questions?knowledge_ids=doc-a'
    result = client.get(url).json['data']['questions']
    assert result == [{'question': '如何按日期查询经营利润？', 'source': 'document', 'knowledge_base_id': 'a', 'knowledge_id': 'doc-a'}]
    assert native_search[0]['knowledge_base_ids'] == ['a']
    assert client.get(url).json['data']['questions'] == result and len(native_search) == 1
    assert client.get(f'/api/v1/agents/{aid}/suggested-questions?knowledge_base_ids=outside').status_code == 403
    assert client.get(f'/api/v1/agents/{aid}/suggested-questions?tag_scopes=[]').status_code == 501


def test_generated_followups_cache_regenerate_and_record_real_events(client, monkeypatch):
    sid, url = completed_turn({'enabled': True, 'mode': 'generated', 'count': 2, 'allow_regenerate': True,
                               'knowledge_fallback': False})
    calls = []
    def model(*args):
        calls.append(args)
        return FakeMessagesListChatModel(responses=[AIMessage(content=json.dumps({'questions': [
            {'text': f'Question {len(calls)}?', 'category': 'deepen'}, {'text': 'Original question', 'category': 'action'}]}))])
    monkeypatch.setattr(suggestions, 'build_model', model)
    first = client.post(url, json={}).json['data']
    assert first['status'] == 'ready' and len(first['questions']) == 1
    assert first['questions'][0]['source'] == 'model'
    assert client.post(url, json={}).json['data']['id'] == first['id'] and len(calls) == 1
    assert client.get(url).json['data']['questions'] == first['questions']
    question = first['questions'][0]
    event_url = f'/api/v1/sessions/{sid}/suggestion-events'
    for event_type in ('impression', 'click', 'dismiss'):
        assert client.post(event_url, json={'suggestion_set_id': first['id'], 'event_type': event_type, 'question_id': question['id']}).status_code == 204
    assert client.post(event_url, json={'suggestion_set_id': first['id'], 'event_type': 'click', 'question_id': 'forged'}).status_code == 400
    for _ in range(4):
        assert client.post(url, json={'regenerate': True}).json['data']['status'] == 'ready'
    assert client.post(url, json={'regenerate': True}).status_code == 429 and len(calls) == 5
    recorded = registry.records('suggestion-event', os.environ['TEST_PLATFORM_USER'])
    assert {item['event_type'] for item in recorded} == {'impression', 'click', 'dismiss', 'regenerate'}


def test_knowledge_followup_attribution_is_session_and_member_bound(client, native_search):
    sid, url = completed_turn({'enabled': True, 'mode': 'knowledge', 'count': 2})
    result = client.post(url, json={}).json['data']
    assert result['status'] == 'ready'
    question = result['questions'][0]
    assert question['knowledge_base_ids'] == ['a'] and question['source'] == 'document'
    attribution = {'suggestion_set_id': result['id'], 'question_id': question['id']}
    owner = os.environ['TEST_PLATFORM_USER']
    assert suggestions.validate_suggestion_attribution(sid, owner, question['text'], attribution) == {
        'knowledge_base_id': 'a', 'knowledge_id': 'doc-a'}
    for target_sid, target_owner in ((sid, 'another-owner'), ('another-session', owner)):
        with pytest.raises(StoreError, match='不存在'):
            suggestions.validate_suggestion_attribution(target_sid, target_owner, question['text'], attribution)
    with pytest.raises(StoreError, match='不符'):
        suggestions.validate_suggestion_attribution(sid, owner, 'Changed text', attribution)


def test_missing_provider_is_failed_not_a_synthetic_success(client, monkeypatch):
    sid, url = completed_turn({'enabled': True, 'mode': 'generated', 'knowledge_fallback': False})
    monkeypatch.setattr(registry, 'model_config', lambda *args: {'parameters': {}})
    monkeypatch.setattr(suggestions, 'build_model', lambda *args: pytest.fail('Missing provider should not be called'))
    result = client.post(url, json={}).json['data']
    assert result['status'] == 'failed' and result['questions'] == [] and result['error_code'] == 'generation_unavailable'
    monkeypatch.setattr(registry, 'model_config', lambda *args: {'parameters': {'api_key': 'configured'}})
    monkeypatch.setattr(suggestions, 'build_model', lambda *args: FakeMessagesListChatModel(responses=[
        AIMessage(content='{"questions":[{"text":"A real provider response?","category":"deepen"}]}')]))
    retried = client.post(url, json={}).json['data']
    assert retried['status'] == 'ready' and retried['questions'][0]['text'] == 'A real provider response?'


def test_question_answer_suppresses_followups_without_model_calls(client, monkeypatch):
    sid, url = completed_turn({'enabled': True, 'mode': 'generated'}, '请选择需要查询的日期？')
    monkeypatch.setattr(suggestions, 'build_model', lambda *args: pytest.fail('A question answer must be suppressed'))
    result = client.post(url, json={}).json['data']
    assert result['status'] == 'suppressed' and result['suppression_reason'] == 'answer_asks_question'
    assert client.post(url, json={'regenerate': True}).status_code == 400
    assert client.post(url, json=[]).status_code == 400
