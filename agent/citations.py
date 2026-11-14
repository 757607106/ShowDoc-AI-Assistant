"""Collect scoped original chunks for the question-suggestion business API.

Rule reference: Tencent/WeKnora internal/modelcontext/citations.go at the commit
in frontend/UPSTREAM.json; upstream notices remain in frontend/UPSTREAM-LICENSE.
"""

_SOURCE_TOOLS = {'knowledge.search', 'knowledge.list_entity_chunks'}
_LOCATION_FIELDS = ('chunk_index', 'toc_path', 'page_start', 'page_end', 'attachments',
                    'source_locator', 'source_locators', 'source_id', 'source_hash')


class AnswerCitations:
    def __init__(self, knowledge_base_ids):
        self.references = []
        self._scope = set(knowledge_base_ids)
        self._seen = set()

    def register(self, tool_name, native, success=True):
        """Read original tool output without changing its schema or contents."""
        if (not success or tool_name not in _SOURCE_TOOLS or not isinstance(native, dict)
                or native.get('isError') is True or native.get('success') is False
                or native.get('errorCode') not in (None, 0)
                or native.get('evidence_layer') in ('wiki', 'graph', 'graph_context')):
            return
        chunks = native.get('results', native.get('chunks', []))
        if not isinstance(chunks, list):
            return
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            kb_id = chunk.get('knowledge_base_id') or chunk.get('kb_id')
            document_id = chunk.get('document_id') or chunk.get('doc_id')
            chunk_id = chunk.get('chunk_id')
            content = chunk.get('content', chunk.get('content_with_weight'))
            tags = chunk.get('tag_kwd') or []
            if (not all(isinstance(value, str) and value.strip() for value in (kb_id, document_id, chunk_id, content))
                    or kb_id not in self._scope or chunk_id.startswith('graph:')
                    or chunk.get('citation_eligible') is False
                    or chunk.get('type') in ('graph_context', 'wiki', 'wiki_section')
                    or chunk.get('evidence_layer') in ('wiki', 'graph', 'graph_context')
                    or not isinstance(tags, (list, str)) or 'graphrag' in tags):
                continue
            key = (kb_id, document_id, chunk_id)
            if key in self._seen:
                continue
            title = chunk.get('document_name') or chunk.get('doc_name') or chunk.get('docnm_kwd')
            title = title if isinstance(title, str) and title.strip() else document_id
            reference = {'id': chunk_id, 'knowledge_id': document_id, 'knowledge_base_id': kb_id,
                         'title': title, 'knowledge_title': title, 'knowledge_filename': title,
                         'content': content, 'score': chunk.get('score', chunk.get('similarity'))}
            reference.update({field: chunk[field] for field in _LOCATION_FIELDS if field in chunk})
            self._seen.add(key)
            self.references.append(reference)
