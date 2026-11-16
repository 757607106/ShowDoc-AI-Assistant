from pathlib import Path
"""ContextDBClient 内存契约替身:复刻官方端点的关键语义,供测试离线使用。

复刻要点:同逻辑名 create 冲突(insert-if-absent)、metadata_condition 等值 AND
(值数组=任一)、metadata 全量覆盖、wiki 页 identity 冲突与版本 CAS、统一信封
(errorCode=0+data)与裸 JSON 两种响应形状。
"""
import itertools

from integrations.contextdb.client import BATCH_REVIEW_ACTIONS, ContextDBConflictError, ContextDBError


class FakeContextDBClient:
    def __init__(self):
        self.knowledge_bases = {}
        self.documents = {}
        self.wiki_pages = {}
        self.reviews = {}
        self.review_settings = {}
        self.events = {}
        self._ids = itertools.count(1)
        self.mcp_calls = []

    # ---------- 基础 ----------

    def configured(self):
        return True

    def _new_id(self, prefix):
        return f"{prefix}-{next(self._ids):08d}"

    def _kb(self, kb_id):
        base = self.knowledge_bases.get(kb_id)
        if base is None:
            raise ContextDBError('COMMON_BAD_REQUEST: knowledge base not found', status_code=400, error_code=1001)
        return base

    def ping(self):
        return {'status': 'ok'}

    # ---------- 知识库 ----------

    def ensure_knowledge_base(self, name, **kwargs):
        for base in self.knowledge_bases.values():
            if base['name'] == name:
                return base
        kb_id = self._new_id('kb')
        base = {'id': kb_id, 'name': name, **kwargs}
        self.knowledge_bases[kb_id] = base
        return base

    def create_knowledge_base(self, name, description=None, **kwargs):
        if any(base['name'] == name for base in self.knowledge_bases.values()):
            raise ContextDBError('name exists')
        return self.ensure_knowledge_base(name, **kwargs)

    def list_knowledge_bases(self):
        bases = list(self.knowledge_bases.values())
        return {'knowledge_bases': bases, 'total': len(bases)}

    def find_knowledge_base(self, name):
        for base in self.knowledge_bases.values():
            if base['name'] == name:
                return base
        return None

    def get_knowledge_base(self, kb_id):
        return self._kb(kb_id)

    def get_review_settings(self, knowledge_base_id):
        self._kb(knowledge_base_id)
        return dict(self.review_settings.get(knowledge_base_id, {}), knowledge_base_id=knowledge_base_id)

    def update_review_settings(self, knowledge_base_id, **fields):
        self._kb(knowledge_base_id)
        settings = self.review_settings.setdefault(knowledge_base_id, {})
        settings.update({key: value for key, value in fields.items() if value is not None})
        return dict(settings, knowledge_base_id=knowledge_base_id)

    def update_knowledge_base(self, kb_id, **fields):
        base = self._kb(kb_id)
        base.update({key: value for key, value in fields.items() if value is not None})
        return base

    def delete_knowledge_base(self, kb_id):
        self.knowledge_bases.pop(self._kb(kb_id)['id'], None)

    # ---------- 文档 ----------

    def _doc_identity(self, kb_id, name, file_path):
        return (kb_id, str(file_path or ''), str(name).lower())

    def create_text_document(self, knowledge_base_id, name, text, *, file_path=None, metadata=None,
                             mime_type=None, source_type=None, review_enabled=None, parent_node_id=None,
                             wait=False, wait_timeout=300.0):
        self._kb(knowledge_base_id)
        for doc in self.documents.values():
            if self._doc_identity(doc['knowledge_base_id'], doc['name'], doc['file_path']) == \
                    self._doc_identity(knowledge_base_id, name, file_path):
                raise ContextDBConflictError(
                    "document with same name already exists; use the corresponding PUT update API (errorCode=1003)")
        doc_id = self._new_id('doc')
        doc = {
            'id': doc_id, 'knowledge_base_id': knowledge_base_id, 'name': name,
            'file_path': file_path or '', 'text': text,
            'metadata': dict(metadata or {}), 'ingest_status': 'succeeded',
            'download_url': f"https://fake.local/{doc_id}",
        }
        self.documents[doc_id] = doc
        return dict(doc)

    def upload_file(self, knowledge_base_id, name, local_path, *, file_path=None, metadata=None,
                    mime_type=None, review_enabled=None, parent_node_id=None, review_template_id=None):
        with open(local_path, 'r', encoding='utf-8') as handle:
            text = handle.read()
        return self.create_text_document(knowledge_base_id, name, text, file_path=file_path, metadata=metadata)

    def update_file(self, document_id, name, local_path, *, metadata=None, mime_type=None,
                    review_enabled=None, review_template_id=None):
        return self.update_text_document(Path(local_path).read_text(), document_id=document_id, metadata=metadata)

    def update_text_document(self, text, *, document_id=None, knowledge_base_id=None, name=None,
                             file_path=None, metadata=None, wait=False, wait_timeout=300.0):
        doc = self.documents.get(document_id)
        if doc is None:
            if knowledge_base_id and name:
                for candidate in self.documents.values():
                    if self._doc_identity(candidate['knowledge_base_id'], candidate['name'], candidate['file_path']) == \
                            self._doc_identity(knowledge_base_id, name, file_path):
                        doc = candidate
                        break
            if doc is None:
                raise ContextDBError('document not found')
        doc['text'] = text
        if metadata is not None:
            doc['metadata'] = dict(metadata)
        return dict(doc)

    def update_document_metadata(self, metadata, *, document_id=None, knowledge_base_id=None, name=None, file_path=None):
        doc = self.documents.get(document_id)
        if doc is None and knowledge_base_id and name:
            for candidate in self.documents.values():
                if self._doc_identity(candidate['knowledge_base_id'], candidate['name'], candidate['file_path']) == \
                        self._doc_identity(knowledge_base_id, name, file_path):
                    doc = candidate
                    break
        if doc is None:
            raise ContextDBError('document not found')
        doc['metadata'] = dict(metadata)
        return {'id': doc['id'], 'metadata': dict(metadata), 'ingest_status': doc['ingest_status']}

    def _match_metadata(self, doc, condition):
        for key, expected in (condition or {}).items():
            if key not in doc['metadata']:
                return False
            actual = doc['metadata'][key]
            if isinstance(expected, list):
                if str(actual) not in {str(item) for item in expected}:
                    return False
            elif str(actual) != str(expected):
                return False
        return True

    def list_documents(self, knowledge_base_id, *, metadata_condition=None, page=1, page_size=50,
                       sort_by=None, sort_order=None, with_download_url=False):
        docs = [doc for doc in self.documents.values()
                if doc['knowledge_base_id'] == knowledge_base_id
                and self._match_metadata(doc, metadata_condition)]
        sort_key = {'created_at': 'created_at', 'updated_at': 'updated_at', 'name': 'name'}.get(sort_by, 'created_at')
        docs.sort(key=lambda item: str(item.get(sort_key) or item['id']), reverse=(sort_order != 'asc'))
        start = (page - 1) * page_size
        items = []
        for doc in docs[start:start + page_size]:
            items.append({
                'id': doc['id'], 'name': doc['name'], 'file_path': doc['file_path'],
                'metadata': dict(doc['metadata']), 'ingest_status': doc['ingest_status'],
                'created_at': doc.get('created_at'), 'updated_at': doc.get('updated_at'),
            })
        return {'documents': items, 'total': len(docs), 'page': page, 'page_size': page_size}

    def get_document(self, knowledge_base_id, document_id, *, with_download_url=False):
        doc = self.documents.get(document_id)
        if doc is None or (knowledge_base_id is not None and doc['knowledge_base_id'] != knowledge_base_id):
            raise ContextDBError('document not found')
        view = dict(doc)
        if not with_download_url:
            view.pop('download_url', None)
        return view

    def delete_documents(self, knowledge_base_id, document_ids):
        results = []
        for document_id in document_ids:
            doc = self.documents.get(document_id)
            if doc is None or doc['knowledge_base_id'] != knowledge_base_id:
                results.append({'id': document_id, 'success': False, 'error': 'not found'})
                continue
            self.documents.pop(document_id, None)
            results.append({'id': document_id, 'success': True})
        return {'errorCode': 0, 'errorMessage': None, 'requestId': 'fake', 'data': {'total': len(results), 'succeeded': len(results), 'failed': 0, 'results': results}}

    def download_document_text(self, knowledge_base_id, document_id, *, timeout=None):
        doc = self.documents.get(document_id)
        if doc is None or doc['knowledge_base_id'] != knowledge_base_id:
            raise ContextDBError('document not found')
        return doc['text']

    def wait_for_ingest(self, knowledge_base_id, document_id, timeout=300.0, poll_interval=2.0):
        return self.get_document(knowledge_base_id, document_id)

    # ---------- 检索 / Wiki ----------

    def _request(self, method, path, *, json_body=None, params=None):
        params, body = params or {}, json_body or {}
        if path == '/v1/knowledge/wiki/pages':
            if method == 'GET':
                return self.list_wiki_pages(params['knowledge_base_id'],
                    parent_page_id=params.get('parent_page_id'), page_type=params.get('page_type'),
                    cursor=params.get('cursor'), limit=int(params.get('limit', 50)))
            if method == 'POST':
                return self.create_wiki_page(body['knowledge_base_id'], body['title'], body['content'])
            if method == 'PUT':
                version = body.get('expected_version')
                if not isinstance(version, int) or isinstance(version, bool) or version < 1:
                    raise ContextDBError('expected_version is required', status_code=400)
                return self.update_wiki_page(body['knowledge_base_id'], body['page_id'], body['content'], version)
        if method == 'GET' and path == '/v1/knowledge/wiki/pages/detail':
            return self.get_wiki_page(params['knowledge_base_id'], params['page_id'])
        raise AssertionError(f'Unexpected fake ContextDB request: {method} {path}')

    def query(self, question, *, knowledge_base_ids=None, knowledge_base_names=None, document_ids=None,
              knowledge_view=None, metadata_condition=None, top_k=None, similarity_threshold=None,
              vector_weight=None, rerank=None, query_rewrite=None, context_token_budget=None,
              images=None):
        ids = list(knowledge_base_ids or [])
        for name in knowledge_base_names or []:
            for base in self.knowledge_bases.values():
                if base['name'] == name:
                    ids.append(base['id'])
        if not ids and not document_ids:
            raise ContextDBError('knowledge bases required')
        matched = []
        for doc in self.documents.values():
            if ids and doc['knowledge_base_id'] not in ids:
                continue
            if document_ids and doc['id'] not in document_ids:
                continue
            if self._match_metadata(doc, metadata_condition) and question and question.lower() in doc['text'].lower():
                matched.append(doc)
        return {'chunks': [{'content': doc['text'], 'doc_id': doc['id']} for doc in matched[:top_k or 6]],
                'total': len(matched), 'doc_aggs': [], 'wiki_items': []}

    def list_wiki_pages(self, knowledge_base_id, *, parent_page_id=None, page_type=None, cursor=None, limit=50):
        items = [{key: value for key, value in page.items() if key != 'content'} for page in self.wiki_pages.values()
                 if page['knowledge_base_id'] == knowledge_base_id
                 and page.get('parent_page_id') == parent_page_id
                 and (page_type is None or page['page_type'] == page_type)]
        offset = int(cursor or 0)
        return {'items': items[offset:offset + limit],
                'next_cursor': str(offset + limit) if offset + limit < len(items) else None, 'limit': limit}

    def create_wiki_page(self, knowledge_base_id, title, content):
        for page in self.wiki_pages.values():
            if page['knowledge_base_id'] == knowledge_base_id and page['title'] == title:
                raise ContextDBConflictError(
                    f"wiki page already exists for this identity: {page['page_id']} (errorCode=1003)", status_code=409)
        page = {'page_id': self._new_id('page'), 'knowledge_base_id': knowledge_base_id,
                'title': title, 'content': content, 'version': 1, 'page_type': 'entity',
                'slug': f"entity/{title}", 'summary': content[:60]}
        self.wiki_pages[page['page_id']] = page
        return dict(page)

    def get_wiki_page(self, knowledge_base_id, page_id):
        page = self.wiki_pages[page_id]
        assert page['knowledge_base_id'] == knowledge_base_id
        return dict(page)

    def update_wiki_page(self, knowledge_base_id, page_id, content, expected_version):
        page = self.wiki_pages.get(page_id)
        if page is None or page['knowledge_base_id'] != knowledge_base_id:
            raise ContextDBError('page not found')
        if expected_version != page['version']:
            raise ContextDBConflictError('page version stale (errorCode=1003)', status_code=409)
        page['content'] = content
        page['version'] += 1
        return dict(page)

    def wiki_search(self, knowledge_base_ids, query, *, mode='keyword', limit=10):
        pages = [dict(page) for page in self.wiki_pages.values()
                 if page['knowledge_base_id'] in knowledge_base_ids
                 and (query == '.+' or query.lower() in page['title'].lower())]
        return {'pages': pages[:limit], 'total': len(pages)}

    def mcp_tool_call(self, name, arguments):
        self.mcp_calls.append((name, arguments))
        if name == 'knowledge.wiki_search':
            return self.wiki_search(arguments['knowledge_base_ids'], arguments['query'],
                                    mode=arguments.get('mode', 'keyword'), limit=arguments.get('limit', 10))
        if name == 'knowledge.get_graph':
            return {'nodes': [], 'relations': []}
        raise ContextDBError(f'unknown tool: {name}')

    # ---------- 评审 ----------

    def list_reviews(self, knowledge_base_id=None, *, decision=None, review_status=None, lifecycle_state=None,
                     page=1, page_size=50, sort_by=None, sort_order=None):
        reviews = [review for review in self.reviews.values()
                   if knowledge_base_id is None or review['knowledge_base_id'] == knowledge_base_id]
        if review_status is not None:
            reviews = [review for review in reviews if review['review_status'] == review_status]
        if lifecycle_state is not None:
            reviews = [review for review in reviews if review.get('lifecycle_state') == lifecycle_state]
        if decision is not None:
            reviews = [review for review in reviews if review['decision'] == decision]
        return {'errorCode': 0, 'errorMessage': None, 'requestId': 'fake',
                'data': {'reviews': reviews[:page_size], 'total': len(reviews)}}

    def get_review(self, review_id, *, content_page=None):
        review = self.reviews.get(review_id)
        if review is None:
            raise ContextDBError('review not found')
        return {**review, 'content_page': content_page or 1}

    def resolve_review_conflicts(self, review_id, resolutions):
        review = self.reviews.get(review_id)
        if review is None:
            raise ContextDBError('review not found')
        review['conflict_resolutions'] = list(resolutions)
        return {'review_id': review_id, 'saved': len(resolutions)}

    _ACTION_STATES = {
        'confirm': ('pending_human', 'approved'), 'force_accept': ('pending_human', 'approved'),
        'accept_rewrite': ('pending_human', 'approved'), 'reject': ('pending_human', 'rejected'),
        'reject_reupload': ('pending_human', 'rejected'),
        'retract': (('approved', 'auto_accepted'), 'pending_human'), 'retry_review': ('failed', 'pending_human'),
    }

    def review_action(self, review_id, action, *, edited_content=None, conflict_resolutions=None):
        review = self.reviews.get(review_id)
        if review is None:
            raise ContextDBError('review not found')
        allowed, target = self._ACTION_STATES[action]
        state = review.get('lifecycle_state', 'pending_human')
        if state not in ((allowed,) if isinstance(allowed, str) else allowed):
            raise ContextDBError(f'action {action} not allowed in {state}', status_code=400)
        review['lifecycle_state'] = target
        review['human_action'] = action
        if edited_content is not None:
            review['edited_content'] = edited_content
        if conflict_resolutions is not None:
            review['conflict_resolutions'] = list(conflict_resolutions)
        review['review_status'] = 'pending' if target == 'pending_human' else 'reviewed'
        review['decision'] = {'approved': 'approved', 'rejected': 'rejected'}.get(target, 'pending_review')
        return review

    def batch_review_action(self, review_ids, action):
        if not isinstance(action, str) or action not in BATCH_REVIEW_ACTIONS:
            raise ValueError('invalid batch action')
        if not isinstance(review_ids, list) or not 1 <= len(review_ids) <= 50 or not all(
                isinstance(review_id, str) and review_id.strip() for review_id in review_ids):
            raise ValueError('ids must contain 1 to 50 nonblank review IDs')
        results = []
        for review_id in review_ids:
            try:
                if action == 'accept_rewrite' and not self.reviews.get(review_id, {}).get('rewritten_content'):
                    raise ContextDBError('rewritten_content is required')
                self.review_action(review_id, action)
                results.append({'id': review_id, 'success': True})
            except ContextDBError as exc:
                results.append({'id': review_id, 'success': False, 'error': str(exc)})
        return {'total': len(results), 'succeeded': sum(item['success'] for item in results),
                'failed': sum(not item['success'] for item in results), 'results': results}

    def get_event(self, event_id):
        return self.events[event_id]

    def wait_event(self, event_id, timeout=300.0, poll_interval=2.0):
        return self.get_event(event_id)
