import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { compileTemplate, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { fixture, flush } from '../test-utils/vueFixture.ts'
import { documentDisplayName, documentDownloadName } from '../utils/contextdbDocumentName.ts'
import { attachmentPath } from '../utils/contextdbResources.ts'
import { resolvePreviewKind } from '../utils/filePreview.ts'

const hosts = new WeakMap<TestContext, ReturnType<typeof fixture>>()
function host(t: TestContext) { const value = hosts.get(t) || fixture(t); hosts.set(t, value); return value }
const resource = (id: string) => ({ documentId: id, name: `${id}.md`, attachments: [], links: [], warning: '' })
const document = (id = 'doc-a', kb = 'kb-a', name = 'source.md') => ({ id, knowledge_base_id: kb, name, display_name: '业务原件.html' })

async function sources(t: TestContext, read: (id: string, kb?: string) => Promise<any>, ids = ['doc-a'], kbId = 'kb-a') {
  const calls: Array<[string, string | undefined]> = []
  const mounted = host(t).component(new URL('./ContextDBSourceResources.vue', import.meta.url), {
    '@/api/contextdbResources': { async loadDocumentResources(id: string, kb?: string) { calls.push([id, kb]); return read(id, kb) } },
  }, { documentIds: ids, kbId })
  await flush()
  return { ...mounted, props: mounted.vm.$.props, calls }
}

test('source resources load the first unique source and keep failures and retries local to each document', async t => {
  let fail = true
  const f = await sources(t, async id => { if (id === 'doc-b' && fail) throw new Error('source denied'); return resource(id) }, ['doc-a', '', 'doc-a', 'doc-b'])
  assert.deepEqual(f.calls, [['doc-a', 'kb-a']]); assert.equal(f.vm.items.length, 2)
  await f.vm.load('doc-b')
  assert.equal(f.vm.items[0].resources.documentId, 'doc-a'); assert.equal(f.vm.items[1].error, 'source denied')
  fail = false; await f.vm.load('doc-b')
  assert.equal(f.vm.items[1].error, ''); assert.equal(f.vm.items[1].resources.documentId, 'doc-b')
  await f.vm.load('doc-a'); assert.equal(f.calls.filter(([id]) => id === 'doc-a').length, 1)
})

test('changing the knowledge base ignores late source data and preserves the new loading state', async t => {
  const completions = new Map<string, (value: any) => void>()
  const f = await sources(t, async (_id, kb) => await new Promise(resolve => completions.set(kb!, resolve)))
  f.props.kbId = 'kb-b'; f.props.documentIds = ['doc-b']; await flush()
  completions.get('kb-a')!(resource('doc-a')); await flush()
  assert.equal(f.vm.items[0].id, 'doc-b'); assert.equal(f.vm.items[0].resources, undefined); assert.equal(f.vm.items[0].loading, true)
  completions.get('kb-b')!(resource('doc-b')); await flush()
  assert.equal(f.vm.items[0].resources.documentId, 'doc-b'); assert.equal(f.vm.items[0].loading, false)
})

test('equal source ID arrays do not discard loaded resources or repeat downloads', async t => {
  const f = await sources(t, async id => resource(id))
  const original = f.vm.items[0].resources
  f.props.documentIds = ['doc-a']; await flush()
  assert.equal(f.calls.length, 1); assert.equal(f.vm.items[0].resources, original)
})

test('unmounting source resources prevents a late response from restoring their contents', async t => {
  let complete!: (value: any) => void
  const f = await sources(t, async () => await new Promise(resolve => { complete = resolve }))
  const row = f.vm.items[0]; f.close(); complete(resource('doc-a')); await flush()
  assert.equal(row.resources, undefined)
})

test('partial official images and original images remain separate without relying on attachment order', async t => {
  const f = await sources(t, async id => resource(id))
  const official = { type: 'image', asset_id: 'official-image', document_id: 'doc-a', chunk_index: 0, attachment_index: 0 }
  const originalA = { type: 'image', source_image_hash: 'a'.repeat(64), document_id: 'doc-a', chunk_index: -1, attachment_index: 0 }
  const originalB = { type: 'image', source_image_hash: 'b'.repeat(64), document_id: 'doc-a', chunk_index: -1, attachment_index: 1 }
  for (const attachments of [[official, originalB, originalA], [originalA, official, originalB], [originalB, originalA, official]]) {
    const current = { ...resource('doc-a'), attachments }
    assert.deepEqual(Array.from(f.vm.primaryAttachments(current), (item: any) => item.asset_id), ['official-image'])
    assert.deepEqual(Array.from(f.vm.additionalImages(current), (item: any) => item.source_image_hash).sort(), ['a'.repeat(64), 'b'.repeat(64)])
  }
  const pending = { ...resource('doc-a'), attachments: [originalB, originalA] }
  assert.equal(f.vm.additionalImages(pending).length, 0)
  assert.deepEqual(Array.from(f.vm.primaryAttachments(pending), (item: any) => item.source_image_hash), ['b'.repeat(64), 'a'.repeat(64)])
})

test('binary original viewers mount only when expanded and disappear on close or source changes', async t => {
  const blob = new Blob(['full source'], { type: 'application/pdf' })
  const f = await sources(t, async id => ({ ...resource(id), name: '业务原件.pdf', sourceFile: { blob, name: 'uploaded.pdf', fileType: 'pdf' } }))
  const { descriptor } = parse(readFileSync(new URL('./ContextDBSourceResources.vue', import.meta.url), 'utf8'))
  const compiled = compileTemplate({ source: descriptor.template!.content, filename: 'ContextDBSourceResources.vue', id: 'lazy-original-preview' })
  assert.deepEqual(compiled.errors, [])
  const { render } = host(t).evaluate(compiled.code, { vue: { ...vue, resolveComponent: (name: string) => name } })
  function nodes() {
    const result: any[] = []
    const visit = (node: any) => { if (Array.isArray(node)) { node.forEach(visit); return }; if (!node || typeof node !== 'object') return; result.push(node); if (Array.isArray(node.children)) node.children.forEach(visit) }
    visit(render(f.vm, [])); return result
  }
  const originalDetails = () => nodes().find(node => node.type === 'details' && node.children?.some((child: any) => child.type === 'summary' && child.children === '查看来源原件'))
  assert.equal(nodes().some(node => node.type === 'DocumentPreview'), false)
  originalDetails().props.onToggle({ target: { open: true } })
  const preview = nodes().find(node => node.type === 'DocumentPreview')
  assert.equal(preview.props['source-blob'] || preview.props.sourceBlob, blob)
  assert.equal(preview.props['file-name'] || preview.props.fileName, 'uploaded.pdf')
  assert.equal(preview.props['file-type'] || preview.props.fileType, 'pdf')
  assert.equal(preview.props['display-name'] || preview.props.displayName, '业务原件.pdf')
  originalDetails().props.onToggle({ target: { open: false } })
  assert.equal(nodes().some(node => node.type === 'DocumentPreview'), false)
  originalDetails().props.onToggle({ target: { open: true } })
  f.props.kbId = 'kb-b'; await flush()
  assert.equal(f.vm.items[0].originalOpen, false); assert.equal(nodes().some(node => node.type === 'DocumentPreview'), false)
})

async function preview(t: TestContext, options: { read?: (id: string) => Promise<any>; chunks?: (id: string, page: number) => Promise<any>; download?: (id: string) => Promise<Blob> } = {}) {
  const calls: any[] = []
  const mounted = host(t).component(new URL('./ContextDBSourcePreview.vue', import.meta.url), {
    '@/api/contextdb': {
      async getDocument(id: string) { calls.push(['document', id]); return { data: options.read ? await options.read(id) : document(id) } },
      async downloadDocument(id: string) { calls.push(['download', id]); return options.download ? await options.download(id) : new Blob(['original']) },
    },
    '@/api/knowledge-base': { async getKnowledgeDetailsCon(id: string, page: number) { calls.push(['chunks', id, page]); return options.chunks ? await options.chunks(id, page) : { data: [{ id: 'chunk', content: '解析原文' }], total: 1 } } },
    '@/utils/filePreview': { resolvePreviewKind },
    '@/utils/contextdbDocumentName': { documentDisplayName, documentDownloadName },
  }, { documentId: 'doc-a', kbId: 'kb-a', title: '展示名.html' })
  await flush()
  return { ...mounted, props: mounted.vm.$.props, calls }
}

test('source preview chooses the actual uploaded format independently of its display filename', async t => {
  for (const name of ['source.md', 'source.pdf', 'source.docx', 'source.pptx', 'source.xlsx']) {
    const f = await preview(t, { read: async id => document(id, 'kb-a', name) })
    assert.equal(f.vm.fileType, name.split('.').pop()); assert.equal(f.vm.doc.name, name)
    assert.equal(f.calls.some(([kind]) => kind === 'chunks'), false)
  }
})

test('unsupported source formats retain an explicit parsed fallback instead of pretending to render the original', async t => {
  const f = await preview(t, { read: async id => document(id, 'kb-a', 'legacy.doc') })
  assert.equal(resolvePreviewKind(f.vm.fileType), 'unsupported'); assert.equal(f.vm.chunks[0].content, '解析原文')
  assert.deepEqual(f.calls.find(([kind]) => kind === 'chunks'), ['chunks', 'doc-a', 1])
})

test('unsupported previews accumulate parsed pages and retain earlier evidence if a later page fails', async t => {
  const f = await preview(t, { read: async id => document(id, 'kb-a', 'legacy.doc'), chunks: async (_id, page) => ({ data: [{ id: `chunk-${page}`, content: `正文${page}` }], total: 2 }) })
  assert.deepEqual(Array.from(f.vm.chunks, (chunk: any) => chunk.content), ['正文1', '正文2'])
  assert.deepEqual(f.calls.filter(([kind]) => kind === 'chunks').map(([, , page]) => page), [1, 2])
  const g = await preview(t, { read: async id => document(id, 'kb-a', 'legacy.doc'), chunks: async (_id, page) => {
    if (page === 2) throw new Error('later evidence unavailable')
    return { data: [{ id: 'first', content: '已读取正文' }], total: 2 }
  } })
  assert.equal(g.vm.chunks[0].content, '已读取正文'); assert.equal(g.vm.error, 'later evidence unavailable')
})

test('source metadata belonging to another document or library cannot become a preview, and retry can recover', async t => {
  for (const bad of [document('another-doc'), document('doc-a', 'another-kb')]) {
    let invalid = true
    const f = await preview(t, { read: async () => invalid ? bad : document() })
    assert.equal(f.vm.doc, null); assert.match(f.vm.error, /不属于当前知识库/)
    invalid = false; await f.vm.load()
    assert.equal(f.vm.error, ''); assert.equal(f.vm.doc.id, 'doc-a')
  }
})

test('late source metadata and fallback chunks cannot overwrite a different current document', async t => {
  let finishMetadata!: (value: any) => void
  const f = await preview(t, { read: async id => id === 'doc-a' ? await new Promise(resolve => { finishMetadata = resolve }) : document(id) })
  f.props.documentId = 'doc-b'; await flush()
  finishMetadata(document()); await flush()
  assert.equal(f.vm.doc.id, 'doc-b'); assert.equal(f.vm.loading, false)
  let finishChunks!: (value: any) => void
  const g = await preview(t, { read: async id => document(id, 'kb-a', id === 'doc-a' ? 'legacy.doc' : 'source.pdf'), chunks: async () => await new Promise(resolve => { finishChunks = resolve }) })
  g.props.documentId = 'doc-b'; await flush()
  finishChunks({ data: [{ id: 'old', content: '旧文档解析' }] }); await flush()
  assert.equal(g.vm.doc.id, 'doc-b'); assert.equal(g.vm.fileType, 'pdf'); assert.equal(g.vm.chunks.length, 0)
})

test('navigating away during source download does not open the old file or allocate a blob URL', async t => {
  let complete!: (blob: Blob) => void
  const created: Blob[] = []
  t.mock.method(URL, 'createObjectURL', (blob: Blob) => { created.push(blob); return 'blob:unexpected' })
  const f = await preview(t, { download: async () => await new Promise(resolve => { complete = resolve }) })
  const pending = f.vm.download(); f.props.documentId = 'doc-b'; await flush()
  complete(new Blob(['old original'])); await pending
  assert.equal(created.length, 0); assert.equal(f.vm.error, ''); assert.equal(f.vm.doc.id, 'doc-b')
})

async function attachment(t: TestContext, options: { type?: string; item?: any; get?: (path: string) => Promise<Blob> } = {}) {
  const calls: string[] = [], created: Blob[] = [], revoked: string[] = []
  t.mock.method(URL, 'createObjectURL', (blob: Blob) => { created.push(blob); return `blob:attachment-${created.length}` })
  t.mock.method(URL, 'revokeObjectURL', (url: string) => { revoked.push(url) })
  const mounted = host(t).component(new URL('./ContextDBAttachment.vue', import.meta.url), {
    '@/utils/request': { async getDown(path: string) { calls.push(path); return options.get ? await options.get(path) : new Blob(['source bytes']) } },
    '@/utils/contextdbResources': { attachmentPath },
  }, { attachment: options.item || { type: options.type || 'image', asset_id: 'asset-a', document_id: 'doc-a', chunk_index: 0, attachment_index: 0 }, kbId: 'kb-a' })
  await flush()
  return { ...mounted, props: mounted.vm.$.props, calls, created, revoked }
}

test('attachments use authenticated coordinates and revoke loaded blob URLs when switched or unmounted', async t => {
  const f = await attachment(t)
  assert.deepEqual(f.calls, ['/api/contextdb/assets/asset-a?knowledge_base_id=kb-a'])
  assert.equal(f.vm.url, 'blob:attachment-1')
  f.props.kbId = 'kb-b'; await flush()
  assert.equal(f.vm.url, 'blob:attachment-2'); assert.deepEqual(f.revoked, ['blob:attachment-1'])
  f.close(); assert.deepEqual(f.revoked, ['blob:attachment-1', 'blob:attachment-2'])
})

test('equal attachment coordinates preserve the loaded blob without reloading or revoking it', async t => {
  const f = await attachment(t)
  f.props.attachment = { ...f.props.attachment }; await flush()
  assert.equal(f.calls.length, 1); assert.equal(f.vm.url, 'blob:attachment-1'); assert.deepEqual(f.revoked, [])
})

test('embedded source images use their local bytes without network requests and replace and revoke stale blob URLs', async t => {
  const original = new Blob(['original image'], { type: 'image/png' })
  const f = await attachment(t, { item: { type: 'image', document_id: 'doc-a', chunk_index: -1, attachment_index: 0, embedded_key: 'word/media/image.png', source_blob: original } })
  assert.equal(f.calls.length, 0); assert.equal(f.created[0], original); assert.equal(f.vm.url, 'blob:attachment-1')
  const updated = new Blob(['updated image'], { type: 'image/png' })
  f.props.attachment = { ...f.props.attachment, source_blob: updated }; await flush()
  assert.equal(f.calls.length, 0); assert.equal(f.created[1], updated)
  assert.equal(f.vm.url, 'blob:attachment-2'); assert.deepEqual(f.revoked, ['blob:attachment-1'])
  f.close(); assert.deepEqual(f.revoked, ['blob:attachment-1', 'blob:attachment-2'])
})

test('source SVG images render as images without exposing their raw blobs as executable top-level links', t => {
  const { descriptor } = parse(readFileSync(new URL('./ContextDBAttachment.vue', import.meta.url), 'utf8'))
  const compiled = compileTemplate({ source: descriptor.template!.content, filename: 'ContextDBAttachment.vue', id: 'source-image-security' })
  assert.deepEqual(compiled.errors, [])
  const { render } = host(t).evaluate(compiled.code, { vue: { ...vue, resolveComponent: (name: string) => name } })
  const vnode = render({ attachment: { type: 'image' }, url: 'blob:svg-source', label: 'SVG', loading: false, error: '', load() {} }, [])
  const nodes: any[] = []
  const visit = (node: any) => { if (!node || typeof node !== 'object') return; nodes.push(node); if (Array.isArray(node.children)) node.children.forEach(visit) }
  visit(vnode)
  assert.ok(nodes.some(node => node.type === 'img' && node.props.src === 'blob:svg-source'))
  assert.equal(nodes.some(node => node.type === 'a' && node.props.href === 'blob:svg-source'), false)
})

test('late attachment responses do not replace a new library or allocate URLs after unmount', async t => {
  const completions = new Map<string, (blob: Blob) => void>()
  const f = await attachment(t, { get: async path => await new Promise(resolve => completions.set(path, resolve)) })
  f.props.kbId = 'kb-b'; await flush()
  completions.get(f.calls[0]!)!(new Blob(['old image'])); await flush()
  assert.equal(f.vm.url, ''); assert.equal(f.vm.loading, true); assert.equal(f.created.length, 0)
  f.close(); completions.get(f.calls[1]!)!(new Blob(['new but closed'])); await flush()
  assert.equal(f.vm.url, ''); assert.equal(f.created.length, 0)
})

test('audio and video attachments wait for explicit loading and empty or failed responses can be retried', async t => {
  let outcome = 'failure'
  const f = await attachment(t, { type: 'audio', get: async () => {
    if (outcome === 'failure') throw new Error('attachment denied')
    return new Blob(outcome === 'empty' ? [] : ['audio source'])
  } })
  assert.equal(f.calls.length, 0)
  await f.vm.load(); assert.equal(f.vm.error, 'attachment denied'); assert.equal(f.vm.url, '')
  outcome = 'empty'; f.vm.clear(); await f.vm.load(); assert.match(f.vm.error, /内容为空/)
  outcome = 'success'; f.vm.clear(); await f.vm.load()
  assert.equal(f.vm.error, ''); assert.equal(f.vm.url, 'blob:attachment-1')
  f.props.attachment = { ...f.props.attachment, type: 'video', attachment_index: 1 }; await flush()
  assert.equal(f.calls.length, 3); assert.equal(f.vm.url, '')
  await f.vm.load(); assert.equal(f.calls.length, 4)
})
