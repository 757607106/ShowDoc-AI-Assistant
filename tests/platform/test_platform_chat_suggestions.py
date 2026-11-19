"""Question starter contracts with real PostgreSQL and native-shaped MCP tools."""
import os

import pytest
from flask import Flask, g
from langchain_core.tools import StructuredTool

from agent import config, registry
from governance.store import StoreError
from webapi.chat import chat_suggestions as suggestions


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
    return app.test_client()


def agent(settings):
    return config.save_agent({'name': 'Question helper', 'config': {'kb_selection_mode': 'selected',
        'knowledge_bases': ['a'], 'question_suggestions': settings}}, os.environ['TEST_PLATFORM_USER'])['id']


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
    monkeypatch.setattr(suggestions, 'client_for_user', lambda *args: pytest.fail('Curated suggestions do not read knowledge'))
    response = client.get(f'/api/v1/agents/{aid}/suggested-questions')
    assert response.status_code == 200
    assert response.json['data']['questions'] == [
        {'question': 'First?', 'source': 'agent_config'}, {'question': 'Second?', 'source': 'agent_config'}]


def test_knowledge_starters_use_mcp_and_preserve_scope_and_source(client, native_search):
    aid = agent({'starters': {'enabled': True, 'mode': 'knowledge', 'count': 2}})
    url = f'/api/v1/agents/{aid}/suggested-questions?knowledge_ids=doc-a'
    result = client.get(url).json['data']['questions']
    assert result == [{'question': '如何按日期查询经营利润？', 'source': 'document',
                       'knowledge_base_id': 'a', 'knowledge_id': 'doc-a'}]
    assert native_search[0]['knowledge_base_ids'] == ['a']
    assert client.get(url).json['data']['questions'] == result and len(native_search) == 1
    assert client.get(f'/api/v1/agents/{aid}/suggested-questions?knowledge_base_ids=outside').status_code == 403
    assert client.get(f'/api/v1/agents/{aid}/suggested-questions?tag_scopes=[]').status_code == 501


def test_retired_followup_routes_are_not_registered(client):
    for method in ('get', 'post'):
        assert getattr(client, method)('/api/v1/sessions/s/messages/m/suggestions').status_code == 404
    assert client.post('/api/v1/sessions/s/suggestion-events', json={}).status_code == 404
