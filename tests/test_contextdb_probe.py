"""Capability discovery uses official reads and keeps product/API support distinct."""
from unittest.mock import Mock

import pytest

from integrations.contextdb import ContextDBClient, ContextDBConflictError, ContextDBError
from scripts import contextdb_probe


@pytest.fixture
def client(monkeypatch):
    client = Mock(spec=ContextDBClient)
    client.list_knowledge_bases.return_value = {'knowledge_bases': [{'id': 'existing-kb', 'wiki_enabled': True}]}
    client.wiki_search.return_value = {'pages': [{'page_id': 'existing-page'}]}
    client.list_wiki_pages.side_effect = AssertionError('Category lists do not cover all Wiki pages')
    client.get_wiki_page.return_value = {'content': '# 完整正文', 'version': 1}

    def read(method, path, **kwargs):
        assert method == 'GET'
        assert kwargs['params']['page_id'] == 'existing-page'
        if path in ('/v1/knowledge/wiki/revisions', '/v1/knowledge/wiki/issues'):
            return {'items': [], 'next_cursor': None}
        raise ContextDBError('Forbidden', status_code=403)

    client._request.side_effect = read
    monkeypatch.setattr(contextdb_probe, 'ContextDBClient', lambda **kwargs: client)
    return client


def test_read_probe_finds_non_category_pages_without_claiming_write_contracts(client):
    report = contextdb_probe.probe()
    client.wiki_search.assert_called_once_with(['existing-kb'], '.+', mode='regex', limit=1)
    client.list_wiki_pages.assert_not_called()
    client.get_wiki_page.assert_called_once_with('existing-kb', 'existing-page')
    client.create_knowledge_base.assert_not_called()
    client.create_wiki_page.assert_not_called()
    client.update_wiki_page.assert_not_called()
    client.delete_knowledge_base.assert_not_called()
    features = report['features']
    assert features['wiki_read']['available']
    revisions = features['wiki_revisions']
    assert revisions['available'] and revisions['page_id_required']
    assert revisions['response_content'] == 'revision_metadata' and not revisions['history_full_content']
    assert features['wiki_revision_approval']['product_console_supported']
    assert features['wiki_revision_approval']['api_contract_status'] == 'not_exposed'
    assert features['wiki_history_rollback']['history_view_compare_product_supported']
    assert features['strict_manual_publish']['documented_threshold_range'] == [0, 1]
    for name in ('wiki_revision_approval', 'wiki_history_rollback', 'strict_manual_publish', 'agent_wiki_revision'):
        assert not features[name]['available']
    assert features['wiki_page_revisions']['status'] == 'unconfirmed'


def test_explicit_write_probe_preserves_cas_and_only_changes_its_disposable_resources(client):
    client.create_knowledge_base.return_value = {'id': 'disposable-kb'}
    client.create_wiki_page.return_value = {'page_id': 'disposable-page'}
    client.update_wiki_page.side_effect = [{'version': 2}, ContextDBConflictError('Stale', status_code=409)]
    report = contextdb_probe.probe(write=True)
    assert report['features']['wiki_edit']['available']
    assert report['features']['wiki_stale_rejected']['available']
    assert report['cleanup'] == {'deleted_probe_kb': 'disposable-kb'}
    assert all(call.args[:2] == ('disposable-kb', 'disposable-page') for call in client.update_wiki_page.call_args_list)
    assert all(call.args[-1] == 1 for call in client.update_wiki_page.call_args_list)
    client.delete_knowledge_base.assert_called_once_with('disposable-kb')


@pytest.fixture
def compiler_client(client, monkeypatch):
    monkeypatch.setattr(contextdb_probe.time, 'sleep', lambda _: None)
    monkeypatch.setattr(contextdb_probe, 'official_wiki_contracts', lambda: {
        'sha256': 'verified-document', 'wiki_api_articles': []})

    async def catalog(_):
        return {'status': 'available', 'tool_names': ['knowledge.search', 'knowledge.wiki_search'],
                'wiki_tools': ['knowledge.wiki_search']}
    monkeypatch.setattr(contextdb_probe, 'official_mcp_catalog', catalog)
    client.create_knowledge_base.return_value = {'id': 'disposable-kb'}
    client.create_wiki_page.return_value = {'page_id': 'disposable-page'}
    client.get_wiki_page.side_effect = [
        {'content': 'version one', 'version': 1},
        {'content': '# 独立版本验证\n\n版本二，仅供验证。', 'version': 2},
    ]
    client.update_wiki_page.side_effect = [{'version': 2}, ContextDBConflictError('Stale', status_code=409)]
    client.create_text_document.return_value = {'id': 'disposable-doc'}
    client.get_document.return_value = {'id': 'disposable-doc', 'updated_at': 'version-time', 'ingest_status': 'succeeded'}
    client.get_knowledge_base.side_effect = ContextDBError('Deleted', status_code=404)
    client.list_documents.return_value = {'total': 0, 'documents': []}
    client.list_knowledge_bases.return_value = {'knowledge_bases': []}

    def chunk_page(method, path, *, params):
        assert (method, path) == ('GET', '/v1/knowledge/documents/chunks')
        assert params['knowledge_base_id'] == 'disposable-kb' and params['document_id'] == 'disposable-doc'
        assert params['limit'] == 1
        index = params['offset']
        return {'total': 2, 'chunks': [{'chunk_id': f'chunk-{index}', 'content': f'正文 {index}'}]}
    client._request.side_effect = chunk_page
    return client


def test_compiler_readonly_gate_does_not_invent_capabilities_or_write(compiler_client):
    report = contextdb_probe.wiki_compiler_readiness()
    assert not report['ready'] and report['decision'] == 'retain_contextdb_compiler'
    assert len(report['blocked_checks']) == 5
    assert report['checks']['source_chunks']['status'] == report['checks']['page_cas']['status'] == 'not_tested'
    assert report['official_mcp']['wiki_tools'] == ['knowledge.wiki_search']
    compiler_client.create_knowledge_base.assert_not_called()
    compiler_client._request.assert_not_called()


def test_body_cas_and_complete_chunks_do_not_authorize_compiler_takeover(compiler_client):
    report = contextdb_probe.wiki_compiler_readiness(write=True)
    assert not report['ready']
    assert report['blocked_checks'] == ['page_location', 'compiler_metadata_write', 'compiler_isolation']
    assert report['checks']['source_chunks']['status'] == 'available'
    assert report['checks']['source_chunks']['chunks_read'] == 2
    assert report['checks']['source_chunks']['source_marker_stable']
    assert report['checks']['page_cas']['status'] == 'available'
    assert report['cleanup'] == {'status': 'deleted', 'probe_kb_id': 'disposable-kb'}
    compiler_client.delete_knowledge_base.assert_called_once_with('disposable-kb')
    compiler_client.list_knowledge_bases.assert_called_once_with(page=1, page_size=100)
    compiler_client.delete_documents.assert_called_once_with('disposable-kb', ['disposable-doc'])
    assert all(call.args[:2] == ('disposable-kb', 'disposable-page')
               for call in compiler_client.update_wiki_page.call_args_list)


def test_compiler_probe_reports_unprotected_cas_and_cleans_failed_reads(compiler_client):
    compiler_client.update_wiki_page.side_effect = [{'version': 2}, {'version': 3}]
    compiler_client.get_wiki_page.side_effect = [
        {'content': 'version one', 'version': 1}, *[{'content': 'stale overwrite', 'version': 3}] * 6]
    compiler_client._request.side_effect = ContextDBError('Read failed', status_code=503)
    report = contextdb_probe.wiki_compiler_readiness(write=True)
    assert report['checks']['source_chunks']['status'] == report['checks']['page_cas']['status'] == 'failed'
    assert not report['ready']
    assert report['cleanup']['status'] == 'deleted'
    compiler_client.delete_knowledge_base.assert_called_once_with('disposable-kb')


def test_compiler_probe_waits_for_updated_page_before_claiming_cas_success(compiler_client):
    compiler_client.get_wiki_page.side_effect = [
        {'content': 'version one', 'version': 1},
        {'content': 'version one', 'version': 2},
        {'content': '# 独立版本验证\n\n版本二，仅供验证。', 'version': 2},
    ]
    report = contextdb_probe.wiki_compiler_readiness(write=True)
    assert report['checks']['page_cas']['status'] == 'available'
    assert compiler_client.get_wiki_page.call_count == 3


def test_cleanup_waits_for_async_document_deletion_before_deleting_base(compiler_client):
    compiler_client.list_documents.side_effect = [{'total': 1}, {'total': 0}]
    result = contextdb_probe.delete_compiler_probe(compiler_client, 'disposable-kb', ['disposable-doc'])
    assert result['status'] == 'deleted'
    assert compiler_client.list_documents.call_count == 2
    compiler_client.delete_documents.assert_called_once_with('disposable-kb', ['disposable-doc'])
    compiler_client.delete_knowledge_base.assert_called_once_with('disposable-kb')


@pytest.mark.parametrize('status', ['processing', 'pending_review', 'failed'])
def test_compiler_does_not_read_unavailable_source_as_empty(compiler_client, status):
    compiler_client.get_document.return_value = {'id': 'disposable-doc', 'ingest_status': status}
    result = contextdb_probe.source_chunk_check(compiler_client, 'disposable-kb', 'disposable-doc')
    assert result['status'] == 'not_tested' and result['ingest_status'] == status
    compiler_client._request.assert_not_called()


def test_source_pagination_rejects_duplicate_chunks(compiler_client):
    compiler_client._request.side_effect = None
    compiler_client._request.return_value = {'total': 2, 'chunks': [{'chunk_id': 'same', 'content': '原文'}]}
    with pytest.raises(ValueError, match='重复'):
        contextdb_probe.source_chunk_check(compiler_client, 'disposable-kb', 'disposable-doc')


def test_source_changed_during_pagination_is_not_available(compiler_client):
    compiler_client.get_document.side_effect = [
        {'id': 'disposable-doc', 'updated_at': 'before', 'ingest_status': 'succeeded'},
        {'id': 'disposable-doc', 'updated_at': 'after', 'ingest_status': 'succeeded'},
    ]
    result = contextdb_probe.source_chunk_check(compiler_client, 'disposable-kb', 'disposable-doc')
    assert result['status'] == 'unconfirmed' and not result['source_marker_stable']


def test_discovery_failure_is_reported_without_exposing_error_secrets(compiler_client, monkeypatch):
    async def failed(_):
        raise RuntimeError('https://private.example/secret?key=do-not-report')
    monkeypatch.setattr(contextdb_probe, 'official_mcp_catalog', failed)
    report = contextdb_probe.wiki_compiler_readiness()
    assert report['official_mcp'] == {'status': 'failed', 'error_type': 'RuntimeError'}
    assert 'do-not-report' not in str(report)
