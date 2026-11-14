import pytest

from agent.citations import AnswerCitations


def chunk(**changes):
    return {'knowledge_base_id': 'kb-1', 'document_id': 'doc-1', 'chunk_id': 'doc-1_chunk_0',
            'document_name': '相同标题.md', 'content': '最大连接数为 50。', **changes}


def registry(*chunks, scope=('kb-1',)):
    citations = AnswerCitations(scope)
    citations.register('knowledge.search', {'results': list(chunks) or [chunk()]})
    return citations


def render(citations, text, size=1):
    return ''.join(citations.feed(text[i:i + size]) for i in range(0, len(text), size)) + citations.flush()


def test_exact_non_uuid_ids_ignore_same_title_and_model_supplied_metadata():
    citations = registry(chunk(), chunk(document_id='doc-2', chunk_id='doc-2_chunk_0'))
    text = '<kb doc="伪造标题" chunk_id="doc-2_chunk_0" kb_id="kb-1" onclick="evil" />'
    assert render(citations, text) == '<kb doc="相同标题.md" chunk_id="doc-2_chunk_0" kb_id="kb-1" />'
    assert render(citations, '<kb doc="相同标题.md" chunk_id="1" />') == ''
    assert render(citations, '<kb doc="相同标题.md" chunk_id="DOC-1" />') == ''


def test_scope_and_duplicate_source_identity():
    citations = registry(chunk(), chunk(), chunk(knowledge_base_id='unselected'))
    assert len(citations.references) == 1
    assert citations.references[0]['content'] == '最大连接数为 50。'
    assert render(citations, '<kb chunk_id="doc-1_chunk_0" kb_id="unselected" />') == ''
    assert not registry(chunk(), scope=()).references


def test_ambiguous_ids_require_exact_library_and_document():
    citations = registry(chunk(), chunk(knowledge_base_id='kb-2'), scope=('kb-1', 'kb-2'))
    assert render(citations, '<kb chunk_id="doc-1_chunk_0" />') == ''
    assert 'kb_id="kb-2"' in render(citations, '<kb chunk_id="doc-1_chunk_0" kb_id="kb-2" />')
    citations.register('knowledge.search', {'results': [chunk(document_id='doc-2')]})
    assert render(citations, '<kb chunk_id="doc-1_chunk_0" kb_id="kb-1" />') == ''
    assert 'doc-1_chunk_0' in render(citations, '<kb chunk_id="doc-1_chunk_0" kb_id="kb-1" knowledge_id="doc-1" />')


@pytest.mark.parametrize('changes', [
    {'chunk_id': 'graph:kb-1:entity'}, {'document_id': ''}, {'knowledge_base_id': ''}, {'chunk_id': ''},
    {'content': '  '}, {'content': None}, {'citation_eligible': False}, {'type': 'graph_context'},
    {'type': 'wiki_section'}, {'evidence_layer': 'wiki'}, {'tag_kwd': ['graphrag']}, {'tag_kwd': 10},
])
def test_synthetic_or_incomplete_chunks_never_become_evidence(changes):
    assert not registry(chunk(**changes)).references


@pytest.mark.parametrize('tool', ['knowledge.get_graph', 'knowledge.wiki_search', 'rerun_collection', 'search_knowledge'])
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


def test_sources_from_previous_execution_are_not_citable():
    old = registry()
    assert old.references
    assert render(AnswerCitations(['kb-1']), '<kb chunk_id="doc-1_chunk_0" />') == ''


def test_original_metadata_is_escaped_and_no_model_html_attributes_survive():
    citations = registry(chunk(document_name='A" <img src=x> & B'))
    assert render(citations, '<kb chunk_id="doc-1_chunk_0" />') == (
        '<kb doc="A&quot; &lt;img src=x&gt; &amp; B" chunk_id="doc-1_chunk_0" kb_id="kb-1" />')
    assert render(citations, '<kb chunk_id="doc-1_chunk_0" chunk_id="forged" />') == ''


def test_plain_text_streams_while_partial_citation_waits():
    citations = registry()
    assert citations.feed('答案。<k') == '答案。'
    assert citations.feed('b chunk_id="doc-1_') == ''
    assert citations.feed('chunk_0"/>结束') == '<kb doc="相同标题.md" chunk_id="doc-1_chunk_0" kb_id="kb-1" />结束'
    assert citations.flush() == ''
    assert citations.feed('尾部<kb chunk_id="unknown') == '尾部'
    assert citations.flush() == ''


@pytest.mark.parametrize('literal', [
    '`<kb chunk_id="unknown" />`', '``<kb chunk_id="unknown" /> ` 字面``',
    '```xml\n<kb chunk_id="unknown" />\n```',
    '~~~xml\n<kb chunk_id="unknown" />\n~~~',
    '  ````xml\n```\n<kb chunk_id="unknown" />\n````',
    '    <kb chunk_id="unknown" />', '\t<kb chunk_id="unknown" />',
    '  \t<kb chunk_id="unknown" />',
    '    code `\n    <kb chunk_id="unknown" />\n    ```',
    '> ```xml\n> <kb chunk_id="unknown" />\n> ````',
    '> > ~~~xml\n> > <kb chunk_id="unknown" />\n> > ~~~~',
    '\\<kb chunk_id="unknown" />', '<kbd>按键</kbd>', 'x < y，结束 <',
])
def test_code_escaped_tags_and_non_citation_markup_stay_literal(literal):
    for size in range(1, len(literal) + 1):
        assert render(registry(), literal, size) == literal


def test_code_closing_fences_and_inline_delimiters_restore_citation_validation():
    text = '```xml\n<kb chunk_id="unknown" />\n```\n引用<kb chunk_id="doc-1_chunk_0" />'
    expected = text.replace('<kb chunk_id="doc-1_chunk_0" />',
                            '<kb doc="相同标题.md" chunk_id="doc-1_chunk_0" kb_id="kb-1" />')
    for split in range(len(text) + 1):
        citations = registry()
        assert citations.feed(text[:split]) + citations.feed(text[split:]) + citations.flush() == expected
    assert render(registry(), '`literal`<kb chunk_id="unknown" />') == '`literal`'
    assert render(registry(), '    <kb chunk_id="unknown" />\n<kb chunk_id="unknown" />') == '    <kb chunk_id="unknown" />\n'


def test_blockquote_fence_with_longer_closer_restores_validation_on_next_line():
    code = '> ```xml\n> <kb chunk_id="literal" />\n> ````\n'
    text = code + '<kb chunk_id="doc-1_chunk_0" /><kb chunk_id="forged" />'
    expected = code + '<kb doc="相同标题.md" chunk_id="doc-1_chunk_0" kb_id="kb-1" />'
    for split in range(len(text) + 1):
        citations = registry()
        assert citations.feed(text[:split]) + citations.feed(text[split:]) + citations.flush() == expected


def test_unverified_web_tags_do_not_create_a_different_kind_of_citation():
    assert render(registry(), '答案<web url="https://invented.example" title="伪造" />') == '答案'
    assert render(registry(), '`<web url="example" />`') == '`<web url="example" />`'
