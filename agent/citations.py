"""Validate answer citations against original chunks read during this execution.

Rule reference: Tencent/WeKnora internal/modelcontext/citations.go at the commit
in frontend/UPSTREAM.json; upstream notices remain in frontend/UPSTREAM-LICENSE.
"""
import html
import re


_ATTR = re.compile(r'''\s+([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')''')
_TAG_START = re.compile(r'</?(kb|web)(?=[\s/>])', re.I)
_SOURCE_TOOLS = {'knowledge.search', 'knowledge.list_entity_chunks'}
_LOCATION_FIELDS = ('chunk_index', 'toc_path', 'page_start', 'page_end', 'attachments',
                    'source_locator', 'source_locators', 'source_id', 'source_hash')


class AnswerCitations:
    def __init__(self, knowledge_base_ids):
        self.references = []
        self._scope = set(knowledge_base_ids)
        self._sources = {}
        self._pending = ''
        self._fence = None
        self._inline_ticks = 0
        self._line_prefix = True
        self._indent = 0
        self._escaped = False

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
            if key in self._sources:
                continue
            title = chunk.get('document_name') or chunk.get('doc_name') or chunk.get('docnm_kwd')
            title = title if isinstance(title, str) and title.strip() else document_id
            reference = {'id': chunk_id, 'knowledge_id': document_id, 'knowledge_base_id': kb_id,
                         'title': title, 'knowledge_title': title, 'knowledge_filename': title,
                         'content': content, 'score': chunk.get('score', chunk.get('similarity'))}
            reference.update({field: chunk[field] for field in _LOCATION_FIELDS if field in chunk})
            self._sources[key] = reference
            self.references.append(reference)

    def _citation(self, tag):
        if not re.match(r'<kb(?=[\s/>])', tag, re.I):
            return ''
        attributes, offset = {}, 3
        for match in _ATTR.finditer(tag, offset):
            if match.start() != offset:
                return ''
            name = match[1].lower()
            if name in attributes:
                return ''
            attributes[name] = html.unescape(match[2] if match[2] is not None else match[3])
            offset = match.end()
        if not re.fullmatch(r'\s*/?>', tag[offset:]):
            return ''
        chunk_id = attributes.get('chunk_id', attributes.get('chunkid'))
        kb_id = attributes.get('kb_id', attributes.get('kbid'))
        document_id = attributes.get('knowledge_id', attributes.get('document_id'))
        matches = [ref for (kb, doc, chunk), ref in self._sources.items()
                   if chunk == chunk_id and (kb_id is None or kb == kb_id)
                   and (document_id is None or doc == document_id)]
        if len(matches) != 1:
            return ''
        source = matches[0]
        return '<kb doc="{}" chunk_id="{}" kb_id="{}" />'.format(
            *(html.escape(source[field], quote=True) for field in ('title', 'id', 'knowledge_base_id')))

    def _advance(self, text):
        for char in text:
            if char == '\n':
                self._line_prefix, self._indent = True, 0
            elif self._line_prefix and char == '>' and self._indent <= 3:
                self._indent = 0
            elif self._line_prefix and char in ' \t':
                self._indent += 1 if char == ' ' else 4 - self._indent % 4
            else:
                self._line_prefix = False

    def feed(self, delta):
        self._pending += delta
        return self._drain(final=False)

    def flush(self):
        return self._drain(final=True)

    def _drain(self, final):
        text, output, i = self._pending, [], 0
        while i < len(text):
            char = text[i]
            if self._indent >= 4 and not self._fence and not self._inline_ticks:
                end = i + 1
            elif self._escaped:
                self._escaped = False
                end = i + 1
            elif char == '\\' and not self._fence and not self._inline_ticks:
                self._escaped = True
                end = i + 1
            elif char in '`~':
                end = i + 1
                while end < len(text) and text[end] == char:
                    end += 1
                if end == len(text) and not final:
                    break
                length = end - i
                at_start = self._line_prefix and self._indent <= 3
                if self._fence:
                    if at_start and char == self._fence[0] and length >= self._fence[1]:
                        newline = text.find('\n', end)
                        if newline < 0 and not final:
                            break
                        tail = text[end:newline if newline >= 0 else len(text)]
                        if not tail.strip():
                            self._fence = None
                elif self._inline_ticks:
                    if char == '`' and length == self._inline_ticks:
                        self._inline_ticks = 0
                elif at_start and length >= 3:
                    self._fence = (char, length)
                elif char == '`':
                    self._inline_ticks = length
            elif char == '<' and not self._fence and not self._inline_ticks:
                remaining = text[i:]
                if any(prefix.startswith(remaining.lower()) for prefix in ('<kb', '<web', '</kb', '</web')):
                    if not final:
                        break
                    # An unfinished citation cannot acquire a clickable target.
                    if remaining.lower() not in ('<', '</'):
                        i = len(text)
                        break
                if _TAG_START.match(remaining):
                    end = text.find('>', i) + 1
                    if not end:
                        if not final:
                            break
                        i = len(text)
                        break
                    output.append(self._citation(text[i:end]))
                    self._advance(text[i:end])
                    i = end
                    continue
                end = i + 1
            else:
                end = i + 1
            output.append(text[i:end])
            self._advance(text[i:end])
            i = end
        self._pending = text[i:]
        return ''.join(output)
