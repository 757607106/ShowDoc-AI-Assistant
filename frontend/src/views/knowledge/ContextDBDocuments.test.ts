import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { compileTemplate, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from 'vue/server-renderer'
import { Tree } from 'tdesign-vue-next'
import { fixture, flush } from '../../test-utils/vueFixture.ts'
import { documentDisplayName, documentDownloadName } from '../../utils/contextdbDocumentName.ts'
import { chunkAttachments } from '../../utils/contextdbResources.ts'

const plain = (value: any) => JSON.parse(JSON.stringify(value))
const folder = (id = 'folder-a', version = 7) => ({ node_id: id, node_type: 'folder', display_name: '目录', tree_version: version, has_children: true })
const file = (id = 'node-a', documentId = 'doc-a', version = 3) => ({ node_id: id, document_id: documentId, node_type: 'file', display_name: '说明.md', tree_version: version, ingest_status: 'succeeded', graph_status: 'building', size_bytes: 42, metadata: { keep: 'value' } })
const document = (id = 'doc-a') => ({ id, name: '说明.md', file_name: '说明.md', knowledge_base_id: 'kb-a', ingest_status: 'succeeded', graph_status: 'building', metadata: { keep: 'value' } })
type Call = { method: string; path: string; data?: any }
type Options = {
  canEdit?: boolean; documentId?: string; folderId?: string; reviewEnabled?: boolean;
  navigate?: (folderId: string, documentId?: string) => void;
  nodes?: (params: any) => Promise<any>; document?: (id: string) => Promise<any>;
  write?: (method: string, path: string, body: any) => Promise<any>;
  upload?: (kb: string, file: File, options: any) => Promise<any>;
  chunks?: (id: string, page: number) => Promise<any>;
}
async function setup(t: TestContext, options: Options = {}) {
  const f = fixture(t), calls: Call[] = []
  const write = async (method: string, path: string, data: any) => {
    calls.push({ method, path, data })
    return { data: options.write ? await options.write(method, path, data) : { deleted: true, results: data?.ids?.map((id: string) => ({ id, success: true })) || [] } }
  }
  const { vm } = f.component(new URL('./ContextDBDocuments.vue', import.meta.url), {
    '@/api/contextdb': {
      nativeAPI: {
        async get(path: string, params: any) {
          calls.push({ method: 'GET', path, data: params })
          return { data: options.nodes ? await options.nodes(params) : { items: [folder(), file()], total: 2, breadcrumbs: [{ node_id: 'root-a', node_type: 'root' }], parent_node: { node_id: 'root-a' } } }
        },
        post: (path: string, data: any) => write('POST', path, data),
        patch: (path: string, data: any) => write('PATCH', path, data),
        del: (path: string, data: any) => write('DELETE', path, data),
      },
      async getDocument(id: string) { calls.push({ method: 'DOCUMENT', path: id }); return { data: options.document ? await options.document(id) : document(id) } },
      async uploadDocumentFile(kb: string, upload: File, data: any) { calls.push({ method: 'UPLOAD', path: kb, data: { name: upload.name, ...data } }); return options.upload?.(kb, upload, data) },
      async updateDocumentMetadata(id: string, data: any) { return write('METADATA', id, data) },
      async retryDocument(id: string) { return write('RETRY', id, undefined) },
    },
    '@/api/backend': { downloadFile: async (path: string, name: string) => calls.push({ method: 'DOWNLOAD', path, data: name }) },
    '@/api/knowledge-base': {
      getKnowledgeDetailsCon: async (id: string, page: number) => { calls.push({ method: 'CHUNKS', path: id, data: { page } }); return options.chunks ? options.chunks(id, page) : { data: [{ id: 'chunk', content: '证据正文' }], total: 30 } },
      batchDownloadKnowledge: async (kb: string, ids: string[]) => { calls.push({ method: 'BATCH_DOWNLOAD', path: kb, data: ids }); return new Blob(['zip']) },
    },
    '@/utils/files': { formatFileSize: (value: number) => String(value), getFileIcon: () => 'file' },
    '@/utils/contextdbDocumentName': { documentDisplayName, documentDownloadName },
    '@/utils/contextdbResources': { chunkAttachments },
  }, { kbId: 'kb-a', canEdit: options.canEdit ?? true, wikiEnabled: true, graphEnabled: true, reviewEnabled: options.reviewEnabled ?? true, documentId: options.documentId, folderId: options.folderId, syncLocation: !!options.navigate, onNavigate: options.navigate })
  await flush(); await flush()
  return { vm, props: vm.$.props, calls, fixture: f }
}
test('directory labels and menu names use readable document names while preserving renamed files and folders', async t => {
  const storedName = `doc-${'a'.repeat(64)}.md`
  const items = [
    { ...file(), display_name: storedName, document_display_name: '管家婆其他系列软件版本及咨询方式.md' },
    { ...file('renamed'), display_name: '用户重命名.md', document_display_name: '原始名称.md' },
    { ...folder(), display_name: '资料目录', document_display_name: '不覆盖目录.md' },
  ]
  const original = structuredClone(items)
  const f = await setup(t, { nodes: async () => ({ items, total: items.length }) })
  const { descriptor } = parse(readFileSync(new URL('./ContextDBDocuments.vue', import.meta.url), 'utf8'))
  const template = descriptor.template!.content
  const compiled = compileTemplate({ source: template.slice(template.indexOf('<t-tree '), template.indexOf('</t-tree>') + '</t-tree>'.length), filename: 'ContextDBDocuments.vue', id: 'directory-names' })
  assert.deepEqual(compiled.errors, [])
  const actionMenu = vue.defineComponent({
    inheritAttrs: false, props: { label: String }, setup: props => () => vue.h('button', { 'aria-label': props.label }),
  })
  const components: Record<string, any> = { 't-tree': Tree, KnowledgeActionMenu: actionMenu, 't-icon': 'i' }
  const { render } = f.fixture.evaluate(compiled.code, {
    vue: { ...vue, resolveComponent: (name: string) => components[name] || name },
  })
  const html = await renderToString(vue.createSSRApp({ render: () => render(f.vm, []) }))
  const expected = ['管家婆其他系列软件版本及咨询方式.md', '用户重命名.md', '资料目录']
  for (const name of expected) {
    assert.match(html, new RegExp(`class="t-tree__label" title="${name}"`))
    assert.match(html, new RegExp(`>${name}</span>`))
    assert.match(html, new RegExp(`aria-label="更多操作 ${name}"`))
  }
  assert.deepEqual(plain(f.vm.tree.map((item: any) => item.label)), expected)
  assert.doesNotMatch(html, /doc-[a-f\d]{64}/i)
  assert.deepEqual(items, original)
})

test('narrow file lists keep selection, statuses and metadata access alongside the row menu', async t => {
  const f = await setup(t, { canEdit: false })
  const columnKeys = () => Array.from(f.vm.columns, (column: { colKey: string }) => column.colKey)
  f.vm.mainWidth = 1400
  assert.ok(columnKeys().includes('wiki_status') && columnKeys().includes('graph_status'))
  f.vm.selected = ['node-a']; f.vm.mainWidth = 328
  assert.deepEqual(columnKeys(), ['selection', 'name', 'compact_status', 'actions'])
  assert.equal(f.vm.selection[0].node_id, 'node-a')
  assert.deepEqual(Array.from(f.vm.menu(f.vm.rows[1]), (item: { value: string }) => item.value), ['enter', 'metadata'])
  await f.vm.act(f.vm.rows[1], 'metadata')
  assert.equal(f.vm.metadata.id, 'doc-a')
  await f.vm.act(f.vm.rows[1], 'enter')
  assert.equal(f.vm.preview.id, 'doc-a')
})

test('the upload picker excludes invalid files before submission without dropping valid files', async t => {
  const f = await setup(t)
  f.vm.add()
  f.vm.appendFiles([new File(['ok'], 'valid.md'), new File([], 'empty.md'), { name: 'too-large.md', size: 2 * 1024 * 1024 + 1 }])
  assert.deepEqual(Array.from(f.vm.files, (file: File) => file.name), ['valid.md'])
  assert.deepEqual(Array.from(f.vm.fileIssues), ['empty.md', 'too-large.md'])
  assert.equal(f.calls.some(call => call.method === 'UPLOAD'), false)
})
test('the current directory uses node state without depending on document detail availability', async t => {
  const f = await setup(t, { document: async () => { throw new Error('COMMON_BAD_REQUEST: document not found') } })
  assert.equal(f.vm.rows[1].id, 'doc-a'); assert.equal(f.vm.rows[1].ingest_status, 'succeeded')
  assert.equal(f.vm.tree[0].children, true); assert.equal(f.vm.rootId, 'root-a')
  assert.equal(f.vm.rows[1].size_bytes, 42); assert.deepEqual(plain(f.vm.rows[1].metadata), { keep: 'value' })
  assert.equal(f.calls.some(call => call.method === 'DOCUMENT'), false); assert.equal(f.vm.error, '')
  await f.vm.enterNode('folder-a')
  assert.equal(f.vm.parent, 'folder-a'); assert.equal(f.vm.page, 1)
  assert.equal(f.calls.filter(call => call.method === 'GET').at(-1)!.data.parent_node_id, 'folder-a')
})

test('downloads preserve the business filename while using the actual source extension from document details', async t => {
  const f = await setup(t, { document: async id => ({ ...document(id), name: 'doc-hash.md',
    document_display_name: '原始手册.html', metadata: { filename: '原始手册.html' } }) })
  await f.vm.download({ ...file(), display_name: '用户重命名.html' })
  assert.ok(f.calls.some(call => call.method === 'DOCUMENT' && call.path === 'doc-a'))
  assert.equal(f.calls.at(-1)?.method, 'DOWNLOAD')
  assert.equal(f.calls.at(-1)?.data, '用户重命名.md')
  const metadataReads = f.calls.filter(call => call.method === 'DOCUMENT').length
  await f.vm.download({ ...file(), name: 'actual.pdf', display_name: '实际手册.pdf' })
  assert.equal(f.calls.at(-1)?.data, '实际手册.pdf')
  assert.equal(f.calls.filter(call => call.method === 'DOCUMENT').length, metadataReads)
})
test('pagination and sorting reach the same official node query rather than silently reloading page one', async t => {
  const f = await setup(t); f.vm.parent = 'folder-a'; f.vm.page = 3; f.vm.pageSize = 50; f.vm.sortBy = 'updated_at'; f.vm.sortOrder = 'desc'
  await f.vm.load()
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'GET').at(-1)!.data), { knowledge_base_id: 'kb-a', parent_node_id: 'folder-a', page: 3, page_size: 50, sort_by: 'updated_at', sort_order: 'desc' })
})
test('lazy directory loading follows all pages and keeps the exact requested parent', async t => {
  const f = await setup(t, { nodes: async params => ({ items: params.page === 1 ? Array.from({ length: 100 }, (_, i) => folder(String(i))) : [folder('last')], total: 101, breadcrumbs: [] }) })
  const items = await f.vm.loadChildren({ value: 'parent-folder' })
  assert.equal(items.length, 101); assert.equal(items.at(-1).node_id, 'last')
  assert.deepEqual(f.calls.filter(call => call.method === 'GET' && call.data.parent_node_id === 'parent-folder').map(call => call.data.page), [1, 2])
})
test('inline source and Chunks views keep the document ID and independently paginate evidence', async t => {
  const f = await setup(t, { documentId: 'linked-doc' })
  assert.equal(f.vm.preview.id, 'linked-doc'); assert.equal(f.vm.previewMode, 'original')
  f.vm.previewMode = 'chunks'; await flush(); assert.equal(f.vm.chunks[0].content, '证据正文')
  f.vm.chunkPage = 2; await f.vm.loadChunks()
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'CHUNKS').at(-1)), { method: 'CHUNKS', path: 'linked-doc', data: { page: 2 } })
  await f.vm.download(f.vm.preview); assert.equal(f.calls.at(-1)!.path, '/api/contextdb/documents/linked-doc/download')
})
test('an old source response cannot reopen a preview after entering another directory', async t => {
  let complete!: (value: any) => void, delayed = false
  const f = await setup(t, { document: id => delayed && id === 'slow' ? new Promise(resolve => { complete = resolve }) : Promise.resolve(document(id)) })
  delayed = true; const opening = f.vm.open({ document_id: 'slow', node_id: 'slow-node' }); await f.vm.enterNode('folder-a')
  complete(document('slow')); await opening
  assert.equal(f.vm.preview, null); assert.equal(f.vm.parent, 'folder-a')
})
test('rename and move send the displayed CAS version and directory creation stays under its selected parent', async t => {
  const f = await setup(t); await f.vm.editNode('rename', folder()); f.vm.nodeName = '新目录'; await f.vm.saveNode()
  assert.deepEqual(plain(f.calls.find(call => call.method === 'PATCH')!.data), { node_id: 'folder-a', expected_tree_version: 7, display_name: '新目录' })
  await f.vm.editNode('move', file()); f.vm.target = 'destination'; await f.vm.saveNode()
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'PATCH').at(-1)!.data), { node_id: 'node-a', expected_tree_version: 3, parent_node_id: 'destination' })
  await f.vm.editNode('folder', folder()); f.vm.nodeName = '子目录'; await f.vm.saveNode()
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'POST').at(-1)!.data), { knowledge_base_id: 'kb-a', parent_node_id: 'folder-a', display_name: '子目录' })
})
test('batch move preserves each version and a partial failure keeps the dialog open without automatic retry', async t => {
  const f = await setup(t, { write: async () => ({ results: [{ id: 'a', success: true }, { id: 'b', success: false, error: '409 stale tree' }] }) })
  await f.vm.editNode('move', [folder('a', 1), folder('b', 2)]); f.vm.target = 'destination'; await f.vm.saveNode()
  assert.deepEqual(plain(f.calls.find(call => call.method === 'POST')!.data), { action: 'move', ids: ['a', 'b'], expected_tree_versions: { a: 1, b: 2 }, parent_node_id: 'destination' })
  assert.equal(f.vm.nodeDialog, 'move'); assert.match(f.vm.error, /409/); assert.equal(f.calls.filter(call => call.method === 'POST').length, 1)
})
test('single deletion requires its version and never broadens recursive deletion implicitly', async t => {
  const f = await setup(t); f.vm.removing = [folder('folder /?', 7)]; await f.vm.remove()
  const url = new URL(f.calls.find(call => call.method === 'DELETE')!.path, 'https://fixture.test/')
  assert.equal(url.searchParams.get('node_id'), 'folder /?'); assert.equal(url.searchParams.get('expected_tree_version'), '7'); assert.equal(url.searchParams.get('recursive'), 'false')
  f.vm.removing = [{ node_id: 'unversioned' }]; await f.vm.remove()
  assert.equal(f.calls.filter(call => call.method === 'DELETE').length, 1); assert.match(f.vm.error, /版本未返回/)
})
test('delete conflicts preserve the exact confirmation and partial batch failures retain only failed nodes', async t => {
  let items = [folder(), folder('a', 1), folder('b', 2)]
  const f = await setup(t, { nodes: async () => ({ items, total: items.length }), write: async (_method, path) => {
    if (path.startsWith('knowledge/nodes?')) throw new Error('409 stale tree')
    items = items.filter(item => item.node_id !== 'a')
    return { results: [{ id: 'a', success: true }, { id: 'b', success: false, error: 'pending review' }] }
  } })
  f.vm.removing = [folder()]; await f.vm.remove(); assert.equal(f.vm.removing[0].node_id, 'folder-a'); assert.equal(f.vm.recursiveDelete, false)
  f.vm.removing = [folder('a', 1), folder('b', 2)]; f.vm.recursiveDelete = true; await f.vm.remove()
  assert.deepEqual(plain(f.vm.removing.map((row: any) => row.node_id)), ['b']); assert.match(f.vm.error, /pending review/)
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'DELETE').at(-1)!.data), { ids: ['a', 'b'], expected_tree_versions: { a: 1, b: 2 }, recursive: true })
  assert.deepEqual(plain(f.vm.rows.map((row: any) => row.node_id)), ['folder-a', 'b'])
})
test('failed deletes refresh the list and tree and discard missing or changed confirmations', async t => {
  for (const kind of ['single', 'batch', 'changed-version']) await t.test(kind, async t => {
    let failed = false
    const initial = [file(), file('node-b', 'doc-b', 2)]
    const f = await setup(t, {
      nodes: async () => {
        const items = failed ? [file('node-b', 'doc-b', kind === 'changed-version' ? 3 : 2)] : initial
        return { items, total: items.length }
      },
      write: async () => { failed = true; throw new Error('COMMON_BAD_REQUEST: node not found') },
    })
    await f.vm.open(f.vm.rows[0])
    f.vm.selected = kind === 'single' ? ['node-a'] : ['node-a', 'node-b']
    f.vm.removing = [...f.vm.selection]
    await f.vm.remove()
    assert.deepEqual(plain(f.vm.rows.map((row: any) => row.node_id)), ['node-b'])
    assert.deepEqual(plain(f.vm.tree.map((row: any) => row.node_id)), ['node-b'])
    assert.equal(f.vm.total, 1); assert.equal(f.vm.preview, null)
    assert.deepEqual(plain(f.vm.selected), [])
    assert.deepEqual(plain(f.vm.removing.map((row: any) => [row.node_id, row.tree_version])), kind === 'batch' ? [['node-b', 2]] : [])
    assert.match(f.vm.error, /node not found/); assert.equal(f.vm.mutating, false)
    assert.equal(f.calls.filter(call => call.method === 'DELETE').length, 1)
    if (kind !== 'batch') {
      await f.vm.remove()
      assert.equal(f.calls.filter(call => call.method === 'DELETE').length, 1)
    }
  })
})
test('a failed recovery refresh clears deletion selections and preserves both errors', async t => {
  let failed = false
  const f = await setup(t, {
    nodes: async () => {
      if (failed) throw new Error('refresh unavailable')
      return { items: [file()], total: 1 }
    },
    write: async () => { failed = true; throw new Error('node not found') },
  })
  f.vm.selected = ['node-a']; f.vm.removing = [...f.vm.selection]
  await f.vm.remove()
  assert.deepEqual(plain(f.vm.selected), []); assert.deepEqual(plain(f.vm.removing), [])
  assert.deepEqual(plain(f.vm.rows), []); assert.deepEqual(plain(f.vm.tree), []); assert.equal(f.vm.total, 0)
  assert.match(f.vm.error, /node not found/); assert.match(f.vm.error, /refresh unavailable/)
  await f.vm.remove(); assert.equal(f.calls.filter(call => call.method === 'DELETE').length, 1)
})
test('confirming again sends only surviving nodes even when document details are unavailable', async t => {
  let items = [file(), file('node-b', 'doc-b')], deletes = 0
  const f = await setup(t, {
    nodes: async () => ({ items, total: items.length }),
    document: async () => { throw new Error('document not found') },
    write: async () => {
      if (++deletes === 1) { items = [file('node-b', 'doc-b')]; throw new Error('node not found') }
      items = []; return { deleted: true }
    },
  })
  f.vm.selected = ['node-a', 'node-b']; f.vm.removing = [...f.vm.selection]
  await f.vm.remove()
  assert.deepEqual(plain(f.vm.selected), [])
  assert.deepEqual(plain(f.vm.removing.map((row: any) => row.node_id)), ['node-b'])
  await f.vm.remove()
  const calls = f.calls.filter(call => call.method === 'DELETE')
  assert.equal(calls.length, 2); assert.deepEqual(plain(calls[0].data.ids), ['node-a', 'node-b'])
  assert.equal(new URL(calls[1].path, 'https://fixture.test/').searchParams.get('node_id'), 'node-b')
  assert.equal(f.calls.some(call => call.method === 'DOCUMENT'), false)
  assert.deepEqual(plain(f.vm.rows), []); assert.deepEqual(plain(f.vm.removing), [])
})
test('recovery refresh blocks duplicate deletes and cannot restore another library\'s selections', async t => {
  let failed = false, complete!: (value: any) => void
  const f = await setup(t, {
    nodes: async params => {
      if (failed && params.knowledge_base_id === 'kb-a') return await new Promise(resolve => { complete = resolve })
      return { items: [folder(params.knowledge_base_id === 'kb-a' ? 'old-folder' : 'new-folder')], total: 1 }
    },
    write: async () => { failed = true; throw new Error('old-library-error') },
  })
  f.vm.selected = ['old-folder']; f.vm.removing = [...f.vm.selection]
  const pending = f.vm.remove(); await flush()
  assert.equal(f.vm.mutating, true)
  await f.vm.remove(); assert.equal(f.calls.filter(call => call.method === 'DELETE').length, 1)
  f.props.kbId = 'kb-b'; await flush(); await flush()
  f.vm.selected = ['new-folder']; f.vm.removing = [...f.vm.selection]; f.vm.error = 'new-library-error'
  complete({ items: [folder('old-folder')], total: 1 }); await pending
  assert.equal(f.vm.error, 'new-library-error')
  assert.deepEqual(plain(f.vm.selected), ['new-folder'])
  assert.deepEqual(plain(f.vm.removing.map((row: any) => row.node_id)), ['new-folder'])
  assert.deepEqual(plain(f.vm.rows.map((row: any) => row.node_id)), ['new-folder'])
})
test('read-only users cannot create, move, delete, retry, upload or save metadata through handlers', async t => {
  const f = await setup(t, { canEdit: false }); await f.vm.editNode('folder'); assert.equal(f.vm.nodeDialog, '')
  f.vm.nodeDialog = 'folder'; f.vm.nodeName = 'denied'; await f.vm.saveNode(); f.vm.removing = [folder()]; await f.vm.remove(); await f.vm.act(file(), 'retry')
  await f.vm.editMetadata(file()); f.vm.metadataText = '{}'; await f.vm.saveMetadata(); f.vm.add(); f.vm.files = [new File(['x'], 'x.md')]; await f.vm.upload()
  assert.equal(f.calls.some(call => !['GET', 'DOCUMENT'].includes(call.method)), false); assert.equal(f.vm.uploadOpen, false)
})
test('metadata accepts objects, rejects arrays and malformed JSON, and preserves arbitrary fields', async t => {
  const f = await setup(t); await f.vm.editMetadata(f.vm.rows[1]); assert.equal(JSON.parse(f.vm.metadataText).keep, 'value')
  for (const invalid of ['[]', 'null', '{']) { f.vm.metadataText = invalid; await f.vm.saveMetadata() }
  assert.equal(f.calls.some(call => call.method === 'METADATA'), false)
  f.vm.metadataText = '{"keep":"value","title":"new"}'; await f.vm.saveMetadata()
  assert.deepEqual(plain(f.calls.find(call => call.method === 'METADATA')), { method: 'METADATA', path: 'doc-a', data: { keep: 'value', title: 'new' } })
})
test('uploads preserve the selected parent and review override while enforcing the console 1B–2MB boundary', async t => {
  const f = await setup(t); f.vm.parent = 'folder-a'; f.vm.add(); assert.equal(f.vm.review, true)
  for (const invalid of [new File([], 'empty.md'), new File(['x'.repeat(2 * 1024 * 1024 + 1)], 'large.md')]) { f.vm.files = [invalid]; await f.vm.upload() }
  assert.equal(f.calls.some(call => call.method === 'UPLOAD'), false)
  f.vm.review = false; f.vm.files = [new File(['x'], 'one.md'), new File(['x'.repeat(2 * 1024 * 1024)], 'limit.md')]; await f.vm.upload()
  assert.deepEqual(plain(f.calls.filter(call => call.method === 'UPLOAD')), [{ method: 'UPLOAD', path: 'kb-a', data: { name: 'one.md', parent_node_id: 'folder-a', review_enabled: false } }, { method: 'UPLOAD', path: 'kb-a', data: { name: 'limit.md', parent_node_id: 'folder-a', review_enabled: false } }])
  assert.equal(f.vm.uploadOpen, false); assert.equal(f.vm.files.length, 0)
})
test('a failed upload retains the failed and remaining files rather than reporting the queue complete', async t => {
  const f = await setup(t, { upload: async (_kb, upload) => { if (upload.name === 'failed.md') throw new Error('upload failed') } })
  f.vm.add(); f.vm.files = [new File(['a'], 'done.md'), new File(['b'], 'failed.md'), new File(['c'], 'remaining.md')]; await f.vm.upload()
  assert.deepEqual(plain(f.vm.files.map((upload: File) => upload.name)), ['failed.md', 'remaining.md']); assert.equal(f.vm.uploadOpen, true); assert.match(f.vm.error, /upload failed/)
})
test('a late upload from another library neither consumes nor uploads the new library queue', async t => {
  let complete!: () => void
  const f = await setup(t, { upload: async () => new Promise<void>(resolve => { complete = resolve }) })
  f.vm.add(); f.vm.files = [new File(['old'], 'old.md')]; const old = f.vm.upload()
  f.props.kbId = 'kb-b'; await flush(); f.vm.add(); f.vm.files = [new File(['new'], 'new.md')]
  complete(); await old
  assert.deepEqual(plain(f.vm.files.map((upload: File) => upload.name)), ['new.md']); assert.equal(f.calls.filter(call => call.method === 'UPLOAD').length, 1)
})
test('changing libraries rejects stale preview responses and clears destructive targets', async t => {
  let complete!: (value: any) => void, delay = false
  const f = await setup(t, { document: id => delay && id === 'old-doc' ? new Promise(resolve => { complete = resolve }) : Promise.resolve(document(id)) })
  f.vm.removing = [folder()]; f.vm.recursiveDelete = true; f.vm.nodeDialog = 'rename'; delay = true
  const old = f.vm.open({ id: 'old-doc' }); f.props.kbId = 'kb-b'; await flush(); complete(document('old-doc')); await old
  assert.equal(f.vm.preview, null); assert.deepEqual(plain(f.vm.removing), []); assert.equal(f.vm.nodeDialog, '')
  const after = f.calls.length; await f.vm.remove(); assert.equal(f.calls.length, after)
})
test('a late file-list response cannot overwrite the newly selected library', async t => {
  let complete!: (value: any) => void, delayed = false
  const f = await setup(t, { nodes: async params => {
    if (delayed && params.knowledge_base_id === 'kb-a') return await new Promise(resolve => { complete = resolve })
    return { items: [{ ...file(), document_id: params.knowledge_base_id === 'kb-a' ? 'doc-a' : 'doc-b' }], total: 1, breadcrumbs: [] }
  } })
  delayed = true; const old = f.vm.load(); f.props.kbId = 'kb-b'; await flush()
  assert.equal(f.vm.rows[0].id, 'doc-b')
  complete({ items: [file()], total: 1, breadcrumbs: [] }); await old
  assert.equal(f.vm.rows[0].id, 'doc-b')
})
test('an incomplete batch move receipt does not discard the move confirmation', async t => {
  const f = await setup(t, { write: async () => ({}) })
  await f.vm.editNode('move', [folder('a', 1), folder('b', 2)]); f.vm.target = 'destination'; await f.vm.saveNode()
  assert.equal(f.vm.nodeDialog, 'move'); assert.ok(f.vm.error)
  assert.equal(f.calls.filter(call => call.method === 'POST').length, 1)
})
test('refreshing an inline preview uses fresh document state and metadata while keeping its node identity', async t => {
  let status = 'succeeded', revision = 1
  const f = await setup(t, { document: async id => ({ ...document(id), ingest_status: status, graph_status: status, metadata: { revision } }) })
  await f.vm.open({ ...file(), ingest_status: 'processing', graph_status: 'pending', metadata: { stale: true } })
  assert.equal(f.vm.preview.ingest_status, 'succeeded'); assert.equal(f.vm.preview.metadata.revision, 1)
  status = 'failed'; revision = 2; await f.vm.open(f.vm.preview)
  assert.equal(f.vm.preview.ingest_status, 'failed'); assert.equal(f.vm.preview.graph_status, 'failed')
  assert.deepEqual(plain(f.vm.preview.metadata), { revision: 2 }); assert.equal(f.vm.preview.node_id, 'node-a'); assert.equal(f.vm.preview.tree_version, 3)
})
test('out-of-order Chunks pages and a previous file cannot overwrite current evidence', async t => {
  const completions = new Map<number, (value: any) => void>()
  const f = await setup(t, { chunks: async (_id, page) => page === 1 ? { data: [{ id: 'one', content: '第一页' }], total: 80 } : await new Promise(resolve => completions.set(page, resolve)) })
  await f.vm.open(file()); await f.vm.loadChunks()
  f.vm.chunkPage = 2; const second = f.vm.loadChunks(); f.vm.chunkPage = 3; const third = f.vm.loadChunks()
  completions.get(3)!({ data: [{ id: 'third', content: '当前第三页' }], total: 80 }); await third
  completions.get(2)!({ data: [{ id: 'second', content: '过期第二页' }], total: 80 }); await second
  assert.equal(f.vm.chunks[0].content, '当前第三页'); assert.equal(f.vm.chunkPage, 3)
  f.vm.chunkPage = 4; const oldFile = f.vm.loadChunks(); await f.vm.open(file('node-b', 'doc-b'))
  assert.deepEqual(plain(f.vm.chunks), []); assert.equal(f.vm.chunkTotal, 0); assert.equal(f.vm.previewMode, 'original')
  completions.get(4)!({ data: [{ id: 'old-file', content: '旧文件内容' }], total: 80 }); await oldFile
  assert.equal(f.vm.preview.id, 'doc-b'); assert.deepEqual(plain(f.vm.chunks), []); assert.equal(f.vm.chunkTotal, 0)
})
test('late node, metadata and delete writes cannot clear new-library drafts or replace its error state', async t => {
  for (const kind of ['node', 'metadata', 'delete']) for (const outcome of ['success', 'failure']) await t.test(`${kind} ${outcome}`, async t => {
    let complete!: (value: any) => void, reject!: (error: Error) => void
    const f = await setup(t, { write: async () => await new Promise((resolve, fail) => { complete = resolve; reject = fail }) })
    let pending: Promise<any>
    if (kind === 'node') { await f.vm.editNode('rename', folder()); f.vm.nodeName = '旧库名称'; pending = f.vm.saveNode() }
    else if (kind === 'metadata') { await f.vm.editMetadata(f.vm.rows[1]); f.vm.metadataText = '{"old":true}'; pending = f.vm.saveMetadata() }
    else { f.vm.removing = [folder()]; pending = f.vm.remove() }
    f.props.kbId = 'kb-b'; await flush(); await flush()
    if (kind === 'node') { await f.vm.editNode('rename', folder('new-folder')); f.vm.nodeName = '新库未提交名称' }
    else if (kind === 'metadata') { await f.vm.editMetadata({ document_id: 'new-doc', metadata: { new: true } }); f.vm.metadataText = '{"draft":"新库未提交稿"}' }
    else { f.vm.removing = [folder('new-folder')]; f.vm.recursiveDelete = false }
    f.vm.error = 'new-library-error'; const reads = f.calls.filter(call => call.method === 'GET').length
    if (outcome === 'success') complete({ deleted: true }); else reject(new Error('old-library-error'))
    await pending
    assert.equal(f.vm.error, 'new-library-error'); assert.equal(f.calls.filter(call => call.method === 'GET').length, reads)
    if (kind === 'node') { assert.equal(f.vm.nodeDialog, 'rename'); assert.equal(f.vm.node.node_id, 'new-folder'); assert.equal(f.vm.nodeName, '新库未提交名称') }
    else if (kind === 'metadata') { assert.equal(f.vm.metadata.document_id, 'new-doc'); assert.equal(f.vm.metadataText, '{"draft":"新库未提交稿"}') }
    else { assert.equal(f.vm.removing[0].node_id, 'new-folder'); assert.equal(f.vm.recursiveDelete, false) }
  })
})


test('directory deep links load the requested real parent and reject missing or foreign nodes',async t=>{
  const f=await setup(t,{folderId:'import-root',nodes:async params=>({items:[file()],total:1,parent_node:{node_id:params.parent_node_id||'root',node_type:params.parent_node_id?'folder':'root',knowledge_base_id:'kb-a'}})})
  assert.equal(f.vm.parent,'import-root');assert.equal(f.vm.rows[0].document_id,'doc-a');assert.equal(f.vm.error,'')
  for(const current of [{node_id:'root',node_type:'root'},{node_id:'missing',node_type:'file'},{node_id:'missing',node_type:'folder',knowledge_base_id:'other-kb'}])await t.test(JSON.stringify(current),async t=>{
    const bad=await setup(t,{folderId:'missing',nodes:async()=>({items:[file()],total:1,parent_node:current})})
    assert.equal(bad.vm.rows.length,0);assert.match(bad.vm.error,/目录不存在|无权访问/)
  })
})

test('changing a directory link ignores the old directory response',async t=>{
  let complete!:(value:any)=>void
  const f=await setup(t,{folderId:'slow',nodes:async params=>params.parent_node_id==='slow'?new Promise(resolve=>complete=resolve):{items:[],total:0,parent_node:{node_id:params.parent_node_id||'root',node_type:'folder'}}})
  f.props.folderId='new';await flush();complete({items:[file()],total:1,parent_node:{node_id:'slow',node_type:'folder'}});await flush()
  assert.equal(f.vm.parent,'new');assert.equal(f.vm.rows.length,0);assert.equal(f.vm.error,'')
})

test('routed file preview waits for the location and keeps the current folder on return', async t => {
  const navigation: [string, string?][] = []
  const row = { ...file(), display_name: '重命名的文档.md' }
  const f = await setup(t, { navigate: (...target) => navigation.push(target), nodes: async params => ({
    items: params.parent_node_id ? [row] : [folder()], total: 1,
    parent_node: params.parent_node_id ? folder(params.parent_node_id) : { node_id: 'root-a', node_type: 'root' },
  }) })
  const readsBefore = f.calls.filter(call => call.method === 'GET').length
  await f.vm.enterNode('folder-a')
  assert.deepEqual(navigation, [['folder-a']]); assert.equal(f.vm.parent, '')
  f.props.folderId = 'folder-a'; await flush()
  assert.equal(f.calls.filter(call => call.method === 'GET').length, readsBefore + 1)
  await f.vm.openFile(f.vm.rows[0], true)
  assert.deepEqual(navigation.at(-1), ['folder-a', 'doc-a']); assert.ok(!f.calls.some(call => call.method === 'DOCUMENT'))
  f.props.documentId = 'doc-a'; await flush()
  assert.equal(f.vm.preview.display_name, '重命名的文档.md')
  assert.deepEqual(f.calls.filter(call => call.method === 'DOCUMENT').map(call => call.path), ['doc-a'])
  await f.vm.closePreview()
  assert.deepEqual(navigation.at(-1), ['folder-a'])
  f.props.documentId = ''; await flush()
  assert.equal(f.vm.preview, null); assert.equal(f.vm.parent, 'folder-a'); assert.equal(f.vm.rows[0].id, 'doc-a')
  assert.equal(f.calls.filter(call => call.method === 'GET').length, readsBefore + 1)
  f.props.documentId = 'doc-a'; await flush()
  assert.equal(f.vm.preview.id, 'doc-a'); assert.equal(f.vm.parent, 'folder-a')
})

test('returning from a pending document URL invalidates the preview request', async t => {
  let complete!: (value: any) => void
  const f = await setup(t, { navigate() {}, documentId: 'slow', document: () => new Promise(resolve => complete = resolve) })
  assert.equal(f.vm.previewLoading, true)
  f.props.documentId = ''; await flush()
  complete(document('slow')); await flush()
  assert.equal(f.vm.previewLoading, false); assert.equal(f.vm.preview, null)
})
