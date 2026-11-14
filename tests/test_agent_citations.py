import pytest

from agent.citations import AnswerCitations


def chunk(**changes):
    return {'knowledge_base_id': 'kb-1', 'document_id': 'doc-1', 'chunk_id': 'doc-1_chunk_0',
            'document_name': '相同标题.md', 'content': '最大连接数为 50。', **changes}


def registry(*chunks, scope=('kb-1',)):
    citations = AnswerCitations(scope)
    citations.register('knowledge.search', {'results': list(chunks) or [chunk()]})
    return citations


def test_scope_and_duplicate_source_identity():
    citations = registry(chunk(), chunk(), chunk(knowledge_base_id='unselected'))
    assert len(citations.references) == 1
    assert citations.references[0]['content'] == '最大连接数为 50。'
    assert not registry(chunk(), scope=()).references


@pytest.mark.parametrize('changes', [
    {'chunk_id': 'graph:kb-1:entity'}, {'document_id': ''}, {'knowledge_base_id': ''}, {'chunk_id': ''},
    {'content': '  '}, {'content': None}, {'citation_eligible': False}, {'type': 'graph_context'},
    {'type': 'wiki_section'}, {'evidence_layer': 'wiki'}, {'tag_kwd': ['graphrag']}, {'tag_kwd': 10},
])
def test_synthetic_or_incomplete_chunks_never_become_evidence(changes):
    assert not registry(chunk(**changes)).references


@pytest.mark.parametrize('tool', ['knowledge.get_graph', 'knowledge.wiki_search', 'rerun_collection', 'search_knowledge', 'web_search'])
def test_other_tool_outputs_cannot_register_document_evidence(tool):
    citations = AnswerCitations(['kb-1'])
    citations.register(tool, {'results': [chunk()]})
    assert not citations.references


@pytest.mark.parametrize('native,success', [
    ({'results': [chunk()]}, False), ({'results': [chunk()], 'isError': True}, True),
    ({'results': [chunk()], 'success': False}, True), ({'results': [chunk()], 'errorCode': 4001}, True),
    ({'results': [chunk()], 'evidence_layer': 'wiki'}, True), ({'results': 'invalid'}, True),
])
def test_failed_or_invalid_results_do_not_register(native, success):
    citations = AnswerCitations(['kb-1'])
    citations.register('knowledge.search', native, success)
    assert not citations.references


def test_entity_chunks_keep_actual_locations_and_do_not_mutate_native_output():
    original = chunk(chunk_index=3, toc_path='配置 / 连接池', page_start=2, page_end=3,
                     source_locators=[{'type': 'pdf', 'page': 2}])
    citations = AnswerCitations(['kb-1'])
    citations.register('knowledge.list_entity_chunks', {'chunks': [original]})
    ref = citations.references[0]
    assert ref['source_locators'] == original['source_locators']
    assert ref['page_start'] == 2 and ref['chunk_index'] == 3
    assert original == chunk(chunk_index=3, toc_path='配置 / 连接池', page_start=2, page_end=3,
                             source_locators=[{'type': 'pdf', 'page': 2}])
    assert 'source_locators' not in registry().references[0]


def test_rest_compatible_original_chunk_fields():
    citations = AnswerCitations(['kb-1'])
    citations.register('knowledge.search', {'chunks': [{'kb_id': 'kb-1', 'doc_id': 'doc-1',
        'chunk_id': 'source-1', 'docnm_kwd': '来源', 'content_with_weight': '原文', 'similarity': .7}]})
    assert citations.references[0]['id'] == 'source-1'
    assert citations.references[0]['title'] == '来源'
    assert citations.references[0]['score'] == .7


def test_source_identity_uses_real_library_document_and_chunk_ids():
    citations = registry(chunk(), chunk(document_id='doc-2', chunk_id='doc-2_chunk_0'),
                         chunk(knowledge_base_id='kb-2'), chunk(document_id='doc-3'), scope=('kb-1', 'kb-2'))
    assert [(ref['knowledge_base_id'], ref['knowledge_id'], ref['id']) for ref in citations.references] == [
        ('kb-1', 'doc-1', 'doc-1_chunk_0'), ('kb-1', 'doc-2', 'doc-2_chunk_0'),
        ('kb-2', 'doc-1', 'doc-1_chunk_0'), ('kb-1', 'doc-3', 'doc-1_chunk_0'),
    ]
    assert {ref['title'] for ref in citations.references} == {'相同标题.md'}
    assert AnswerCitations(['kb-1']).references == []
