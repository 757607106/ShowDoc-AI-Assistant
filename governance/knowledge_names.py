"""Read-only labels for existing knowledge identities; never rename stored assets."""
import re
import json
from pathlib import Path
from uuid import UUID

from governance.database import connection


def document_name(document):
    metadata = document.get('metadata') or document.get('doc_metadata') or {}
    filename = metadata.get('filename')
    if isinstance(filename, str) and filename.strip():
        return filename.strip()
    name = (document.get('name') or document.get('document_name') or document.get('doc_name') or document.get('docnm_kwd')
            or document.get('display_name') or '')
    title = metadata.get('title')
    if not isinstance(title, str) or not title.strip():
        return name
    title = title.strip()
    extension = re.search(r'\.[a-z\d]{1,12}$', name, re.I)
    suffix = extension[0] if extension else ''
    return title + suffix if suffix and not title.lower().endswith(suffix.lower()) else title


def _captured_attachment_name(capture):
    from common.converter import clean_filename
    metadata = capture.get('metadata') or {}
    path = Path(capture.get('source_path') or '')
    title = capture.get('title')
    if (not metadata.get('parent_document_id') or path.parts[:2] != ('assets', 'attachments')
            or metadata.get('filename') != path.name or not isinstance(title, str) or not title.strip()):
        return None
    prefix, separator, suffix = path.name.partition('_')
    try:
        if str(UUID(prefix)) != prefix.lower():
            return None
    except ValueError:
        return None
    return title if separator and suffix == clean_filename(title) else None


class KnowledgeNames:
    def __init__(self, owner_id):
        self.owner_id = owner_id
        self._spaces = None
        self._documents = None

    def base(self, base):
        if self._spaces is None:
            with connection() as conn:
                spaces = conn.execute("SELECT payload FROM runtime_records WHERE owner_id=%s AND kind='knowledge_space'",
                                      (self.owner_id or '',)).fetchall()
                mappings = conn.execute('SELECT DISTINCT scope,target_mode,knowledge_base_id FROM knowledge_sync WHERE owner_id=%s',
                                        (self.owner_id or '',)).fetchall()
            self._spaces = {}
            configured = {row['payload']['scope']: row['payload'] for row in spaces}
            candidates = {}
            for row in mappings:
                scope, mode = row['scope'], row['target_mode']
                if scope not in configured:
                    candidates.setdefault(row['knowledge_base_id'], set()).add((scope, mode, scope))
            for space in configured.values():
                for mode in ('wiki', 'graph'):
                    match = (space['scope'], mode, space.get('name') or space['scope'])
                    for kb_id in space.get('previous_knowledge_base_ids', {}).get(mode, []):
                        candidates.setdefault(kb_id, set()).add(match)
            self._spaces = {kb_id: next(iter(matches)) for kb_id, matches in candidates.items() if len(matches) == 1}
            current = {}
            for space in configured.values():
                for mode in ('wiki', 'graph'):
                    kb_id = space.get(mode + '_kb_id')
                    if kb_id:
                        current.setdefault(kb_id, set()).add((space['scope'], mode, space.get('name') or space['scope']))
            for kb_id, matches in current.items():
                self._spaces.pop(kb_id, None)
                if len(matches) == 1:
                    self._spaces[kb_id] = next(iter(matches))
        label = base.get('name', '')
        result = dict(base)
        match = self._spaces.get(base.get('id'))
        if match:
            scope, mode, label = match
            if scope == 'default' and label in ('default', '默认知识空间'):
                label = '默认知识库'
            result.update(space_scope=scope, space_name=label, space_mode=mode)
            if mode == 'graph':
                label += '（知识图谱）'
        elif label in ('knowledge-default', 'knowledge-default-graph'):
            label = '默认知识库' + ('（知识图谱）' if label.endswith('-graph') else '')
        result['display_name'] = label
        return result

    def _load_documents(self):
        if self._documents is None:
            with connection() as conn:
                rows = conn.execute('''SELECT s.knowledge_base_id,s.document_id,d.metadata,
                        v.metadata AS version_metadata,v.payload AS version_payload,
                        j.payload->'params' AS upload_params,j.payload->>'entry' AS entry
                    FROM (SELECT owner_id,source_id,knowledge_base_id,document_id,source_version FROM knowledge_sync WHERE owner_id=%s
                        UNION ALL SELECT owner_id,payload->>'source_id',payload->>'knowledge_base_id',
                            payload->>'document_id',payload->>'source_version' FROM runtime_records
                        WHERE owner_id=%s AND kind='knowledge_sync_history') s
                    JOIN runtime_records d ON d.owner_id=s.owner_id
                      AND d.kind='doc' AND d.record_key=s.source_id
                    LEFT JOIN runtime_records v ON v.owner_id=s.owner_id AND v.kind='version'
                      AND v.record_key=COALESCE(s.source_version,d.metadata->>'current_version')
                    LEFT JOIN runtime_records j ON j.owner_id=s.owner_id AND j.kind='job' AND j.record_key=v.metadata->>'job_id'
                    WHERE s.document_id IS NOT NULL''', (self.owner_id or '', self.owner_id or '')).fetchall()
            self._documents = {}
            for row in rows:
                metadata = dict(row['metadata'])
                title = (row['version_metadata'] or {}).get('title') or metadata.get('title')
                metadata['title'] = title
                metadata['_source_extension'] = {'html': '.html', 'text': '.txt', 'markdown': '.md'}.get(
                    (row['version_metadata'] or {}).get('source_format'), '')
                if row['entry'] == 'tiantong' and (row['version_metadata'] or {}).get('source_format') == 'file':
                    capture = row['version_payload'] or {}
                    if capture.get('_capture_path'):
                        from governance.store import data_dir
                        path = Path(capture['_capture_path']).resolve()
                        try:
                            capture = json.loads(path.read_text(encoding='utf-8')) if path.is_relative_to(data_dir()) else {}
                        except (OSError, ValueError):
                            capture = {}
                    filename = _captured_attachment_name(capture)
                    if filename:
                        metadata.update(filename=filename, _stored_filename=capture['metadata']['filename'])
                if row['entry'] == 'file' and row['upload_params']:
                    from common.upload_names import upload_name
                    params = row['upload_params']
                    for index, path in enumerate(params.get('file_paths', [])):
                        originals = params.get('file_names') or []
                        name = upload_name(path, index, originals[index] if index < len(originals) else None)
                        if title in (Path(path).stem, Path(name).stem):
                            metadata.update(filename=name, title=Path(name).stem,
                                            _stored_filename=Path(path).name)
                            break
                self._documents[(row['knowledge_base_id'], row['document_id'])] = metadata

    def document(self, document, *, reference=False, kb_id=None):
        self._load_documents()
        identifier = document.get('document_id') or document.get('doc_id') or document.get('id')
        base_id = document.get('knowledge_base_id') or document.get('kb_id') or kb_id
        metadata = self._documents.get((base_id, identifier), {})
        if not base_id:
            matches = [value for (base, doc), value in self._documents.items() if doc == identifier]
            metadata = matches[0] if matches else {}
        local = metadata
        metadata = {**local, **(document.get('metadata') or document.get('doc_metadata') or {})}
        for field in ('filename', 'title'):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                metadata[field] = local.get(field)
        stored = local.get('_stored_filename')
        if stored:
            if metadata.get('filename') == stored:
                metadata['filename'] = local['filename']
            if metadata.get('title') == Path(stored).stem:
                metadata['title'] = local['title']
        result = dict(document)
        source = {**document, 'metadata': metadata}
        if (isinstance(metadata.get('title'), str) and metadata['title'].strip()
                and not any(source.get(key) for key in ('name', 'document_name', 'doc_name', 'docnm_kwd', 'display_name'))):
            source['name'] = local.get('_source_extension', '')
        label = document_name(source)
        result['document_display_name' if reference else 'display_name'] = label
        path = document.get('toc_path')
        name = (document.get('name') or document.get('document_name') or document.get('doc_name')
                or document.get('docnm_kwd'))
        if isinstance(path, str) and name and (path == name or path.startswith(name + '/')):
            result['display_toc_path'] = label + path[len(name):]
        return result

    def _source_label(self, value, kb_id, source_ids=None):
        if not isinstance(value, str) or (not kb_id and not source_ids):
            return value
        match = re.match(r'^(doc-[a-f\d]{64}\.[a-z\d]{1,12})(?=$|/| - Summary(?:$|/))', value, re.I)
        if not match:
            return value
        self._load_documents()
        name = match[1]
        candidates = set()
        for (base, doc), metadata in self._documents.items():
            if (kb_id and base != kb_id) or (source_ids is not None and doc not in source_ids):
                continue
            if name.rsplit('.', 1)[0] != 'doc-' + str(metadata.get('doc_id', '')):
                continue
            candidates.add(self.document({'id': doc, 'knowledge_base_id': base, 'name': name})['display_name'])
        return next(iter(candidates)) + value[len(name):] if len(candidates) == 1 else value

    def wiki_page(self, page, kb_id=None):
        base = page.get('knowledge_base_id') or page.get('kb_id') or kb_id
        sources = page.get('source_document_ids')
        result = {**page, 'display_title': self._source_label(page.get('title'), base, sources)}
        if isinstance(page.get('heading_path'), str):
            result['display_heading_path'] = self._source_label(page['heading_path'], base, sources)
        for key in ('ancestors', 'links', 'backlinks'):
            if isinstance(page.get(key), list):
                result[key] = [self.wiki_page(item, base) if isinstance(item, dict) else item for item in page[key]]
        return result

    def present(self, resource, payload, *, kb_id=None):
        if not isinstance(payload, dict):
            return payload
        if isinstance(payload.get('data'), dict):
            return {**payload, 'data': self.present(resource, payload['data'], kb_id=kb_id)}
        if resource == 'knowledge/knowledge_bases':
            return {**payload, 'knowledge_bases': [self.base(item) for item in payload.get('knowledge_bases', [])]}
        if resource == 'knowledge/knowledge_bases/detail':
            return self.base(payload)
        if resource == 'knowledge/documents/detail':
            return self.document(payload, kb_id=kb_id)
        collections = {
            'knowledge/documents': ('documents', False),
            'knowledge/reviews': ('reviews', True),
            'knowledge/wiki/compile-runs': ('items', True),
            'knowledge/nodes': ('items', True),
        }
        if resource in collections:
            key, reference = collections[resource]
            return {**payload, key: [self.document(item, reference=reference, kb_id=kb_id)
                    if resource != 'knowledge/nodes' or item.get('node_type') == 'file' else item
                    for item in payload.get(key, [])]}
        if resource == 'knowledge/reviews/detail':
            return self.document(payload, reference=True, kb_id=kb_id)
        if resource in ('knowledge/wiki/pages/detail', 'knowledge/wiki/summary'):
            return self.wiki_page(payload, kb_id)
        if resource in ('knowledge/wiki/pages', 'knowledge/wiki/search'):
            return {**payload, **{key: [self.wiki_page(item, kb_id) for item in payload[key]]
                    for key in ('items', 'pages') if isinstance(payload.get(key), list)}}
        if resource == 'knowledge/wiki/index':
            return {**payload, 'groups': [{**group, 'items': [self.wiki_page(item, kb_id) for item in group.get('items', [])]}
                    for group in payload.get('groups', [])]}
        if resource in ('knowledge/query', 'knowledge/documents/chunks', 'knowledge/entities/chunks'):
            result = {**payload, **{key: [self.document(item, reference=True, kb_id=kb_id)
                    if item.get('type') != 'graph_context' and item.get('citation_eligible') is not False
                    and not str(item.get('chunk_id', '')).startswith('graph:') and 'graphrag' not in (item.get('tag_kwd') or []) else item
                    for item in payload[key]] for key in ('chunks', 'results') if isinstance(payload.get(key), list)}}
            if isinstance(payload.get('wiki_items'), list):
                result['wiki_items'] = [self.wiki_page(item, kb_id) for item in payload['wiki_items']]
            return result
        return payload
