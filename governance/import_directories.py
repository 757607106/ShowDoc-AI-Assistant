"""Map capture sources to real ContextDB file nodes, independently of Wiki pages."""
from urllib.parse import urlsplit

from common.source_directories import import_directory
from governance.store import StoreError, data_dir, digest


class ImportDirectories:
    def __init__(self, store, knowledge_base_id, *, root_names=None):
        self.store, self.kb_id = store, knowledge_base_id
        self.sources, self.roots, self.children = {}, {}, {}
        self.root_names = root_names or {}

    def source(self, record):
        """Old release archives need their original capture to recover the source name."""
        capture = record
        if not record.get('source_key') and record.get('version_id'):
            found = self.store._find('version', version_id=record['version_id'])
            if found:
                capture = {**self.store.get_document(record['version_id']), **record}
        key = capture.get('source_key') or 'crawler'
        directory = (capture.get('metadata') or {}).get('import_directory')
        if not directory and capture.get('revision_of'):
            _, directory = self.source(self.store.get_document(capture['revision_of']))
        if not directory:
            if key not in self.sources:
                entry = key.split(':', 1)[0]
                from registry import ENTRIES, create_crawler
                root = ENTRIES[entry].display_name if entry in ENTRIES else '采集资料'
                mapped = self.store._find('import_directory', knowledge_base_id=self.kb_id, source_key=key)
                if mapped:
                    root = self.store._body(mapped['id'])['root_name']
                elif entry == 'showdoc':
                    job_id = capture.get('job_id')
                    if not job_id:
                        raise StoreError('旧 ShowDoc 记录缺少来源任务，无法确认项目名称', 409)
                    job = self.store.get_job(job_id)
                    crawler = create_crawler(entry, save_dir=str(data_dir() / '_listing'), **job['params'])
                    crawler.authenticate()
                    crawler.fetch_item_info()
                    root = crawler.project_name
                elif entry == 'web':
                    root = key.partition(':')[2] or urlsplit((capture.get('metadata') or {}).get('url', '')).netloc
                self.sources[key] = root
            category = capture.get('category') or ''
            cat_id = (capture.get('metadata') or {}).get('cat_id')
            if key.startswith('showdoc:') and category == '根目录' and cat_id is None:
                raise StoreError('旧 ShowDoc 记录缺少目录标识，无法确认“根目录”是否为真实子目录', 409)
            if ((key.startswith('showdoc:') and category == '根目录' and str(cat_id) == '0') or
                    (key.startswith('web:') and category == '网页') or
                    (key == 'file' and category == '上传文件') or
                    (key == 'tiantong' and category == '未分类')):
                category = ''
            directory = import_directory(self.sources[key], category)
        if (not isinstance(directory, dict) or not isinstance(directory.get('root_name'), str) or
                not directory['root_name'].strip() or not isinstance(directory.get('path'), list) or
                not all(isinstance(part, str) and part.strip() for part in directory['path'])):
            raise StoreError('采集目录元数据无效，请重新读取来源目录', 422)
        return key, directory

    def _save_root(self, record, value):
        metadata = {**record['metadata'], 'populated': bool(value.get('populated'))}
        self.store._write(record['id'], value, metadata)

    def root(self, key, name):
        name = self.root_names.get(key, name)
        if key in self.roots:
            return self.roots[key]
        record = self.store._find('import_directory', knowledge_base_id=self.kb_id, source_key=key)
        if record:
            value = self.store._body(record['id'])
            if not value.get('node_id'):
                raise StoreError('上次来源目录创建结果未确认，请先核对目录，避免重复创建', 409)
            parent = self.store.client.list_nodes(self.kb_id, parent_node_id=value['node_id'], page_size=1)['parent_node']
            if parent['node_type'] != 'folder':
                raise StoreError('来源目录映射已失效，请先核对目录', 409)
            # An explicit new capture label renames the mapped folder, never creates a duplicate.
            if key in self.root_names and name != value['root_name']:
                parent = self.store.client.rename_node(self.kb_id, parent['node_id'],
                    name, parent['tree_version'])['node']
                value['root_name'] = name
            value['display_name'] = parent['display_name']
            self._save_root(record, value)
        else:
            value = {'knowledge_base_id': self.kb_id, 'source_key': key, 'root_name': name,
                     'display_name': name, 'node_id': None, 'populated': False}
            record = self.store._create('import_directory', digest([self.kb_id, key]), value,
                {'knowledge_base_id': self.kb_id, 'source_key': key, 'populated': False})
            # Keep the unresolved mapping if the create response is lost; POST is not idempotent.
            node = self.store.client.create_directory(self.kb_id, name)['node']
            value['node_id'] = node['node_id']
            self._save_root(record, value)
        self.roots[key] = record, value
        return record, value

    def target(self, record):
        key, directory = self.source(record)
        root_record, root = self.root(key, directory['root_name'])
        parent = root['node_id']
        for part in directory['path']:
            if parent not in self.children:
                items = []
                page = 1
                while True:
                    result = self.store.client.list_nodes(self.kb_id, parent_node_id=parent, page=page)
                    items.extend(result['items'])
                    if len(items) >= result['total'] or not result['items']:
                        break
                    page += 1
                self.children[parent] = {item['display_name']: item['node_id']
                    for item in items if item['node_type'] == 'folder'}
            if part not in self.children[parent]:
                node = self.store.client.create_directory(self.kb_id, part, parent_node_id=parent)['node']
                self.children[parent][part] = node['node_id']
            parent = self.children[parent][part]
        return parent, (root_record, root)

    def attach(self, document_id, parent):
        node = self.store.client.ensure_document_node(document_id)['node']
        if node['parent_node_id'] == parent:
            return False
        moved = self.store.client.move_node(self.kb_id, node['node_id'], parent, node['tree_version'])['node']
        if moved.get('document_id') != document_id or moved['parent_node_id'] != parent:
            raise StoreError('目录移动结果未确认，请刷新核对后重试', 409)
        return True

    def populated(self, root):
        record, value = root
        if not value.get('populated'):
            value['populated'] = True
            self._save_root(record, value)


def imported_locations(store, knowledge_base_id, source_key=None):
    condition = {'type': 'import_directory', 'knowledge_base_id': knowledge_base_id, 'populated': True}
    if source_key:
        condition['source_key'] = source_key
    return [{'knowledge_base_id': knowledge_base_id, 'node_id': value['node_id'],
             'root_name': value.get('display_name', value['root_name'])}
        for item in store._list(condition) if (value := store._body(item['id'])).get('node_id')]


def repair_plan(store, knowledge_base_id):
    """Only mapped crawler captures are eligible; user uploads and Wiki pages are untouched."""
    from governance.database import connection
    manager = ImportDirectories(store, knowledge_base_id)
    with connection() as conn:
        rows = conn.execute('''SELECT scope, source_id, source_version, document_id FROM knowledge_sync
            WHERE owner_id=%s AND knowledge_base_id=%s AND document_id IS NOT NULL''',
            (store.owner_id or '', knowledge_base_id)).fetchall()
    plan, errors = [], []
    for row in rows:
        try:
            capture = store.get_document(row['source_version'])
            source_key, directory = manager.source(capture)
            plan.append({**row, 'source_key': source_key, 'directory': directory})
        except Exception as exc:
            errors.append({'document_id': row['document_id'], 'error': str(exc)})
    return plan, errors


def repair_documents(store, knowledge_base_id, plan, *, progress=None):
    from governance.knowledge_bases import base_write_lock
    manager = ImportDirectories(store, knowledge_base_id)
    results = []
    for item in plan:
        try:
            with base_write_lock(knowledge_base_id):
                before = store.client.get_document(knowledge_base_id, item['document_id'])
                if before.get('ingest_status') in ('deleted', 'deleting'):
                    results.append({'document_id': item['document_id'], 'skipped': before['ingest_status']})
                    if progress:
                        progress(results[-1])
                    continue
                parent, root = manager.target({'source_key': item['source_key'],
                    'metadata': {'import_directory': item['directory']}})
                moved = manager.attach(item['document_id'], parent)
                after = store.client.get_document(knowledge_base_id, item['document_id'])
                if (after['id'] != before['id'] or after.get('metadata') != before.get('metadata') or
                        after.get('latest_ingest_event_id') != before.get('latest_ingest_event_id')):
                    raise StoreError('目录整理后的文档身份或处理事件不一致，请核对官方记录', 409)
                manager.populated(root)
                results.append({'document_id': item['document_id'], 'moved': moved,
                    'parent_node_id': parent, 'root_name': root[1]['display_name'],
                    'file_path_before': before.get('file_path'), 'file_path_after': after.get('file_path')})
        except Exception as exc:
            results.append({'document_id': item['document_id'], 'error': str(exc)})
        if progress:
            progress(results[-1])
    return results
