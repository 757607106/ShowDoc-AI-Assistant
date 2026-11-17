import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import { after, test } from 'node:test'
import { DOMParser as XmlParser } from '@xmldom/xmldom'
import JSZip from 'jszip'
import ts from 'typescript'
import * as resources from '../utils/contextdbResources.ts'
import { documentDisplayName } from '../utils/contextdbDocumentName.ts'

const script = ts.transpileModule(readFileSync(new URL('./contextdbResources.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
const plain = (value: any) => JSON.parse(JSON.stringify(value))
const originalParser = globalThis.DOMParser
globalThis.DOMParser = class {
  parseFromString(text: string) {
    const doc = new XmlParser().parseFromString(text || '<html/>', 'text/html')
    Object.assign(doc, { querySelectorAll: () => Array.from(doc.getElementsByTagName('a')).filter(node => node.hasAttribute('href')) })
    return doc
  }
} as unknown as typeof DOMParser
after(() => { if (originalParser) globalThis.DOMParser = originalParser; else Reflect.deleteProperty(globalThis, 'DOMParser') })
type Options = { document?: any; documentError?: Error; chunks?: (params: any) => any; download?: () => Promise<Blob>; manifest?: (path: string, params: any) => any; readLinks?: typeof resources.fileSourceLinks }
function fixture(options: Options = {}) {
  const calls: any[] = [], exports: any = {}
  const source = { id: 'doc-a', knowledge_base_id: 'kb-a', name: 'doc-hash.md', display_name: '业务原件.html', metadata: { url: 'https://example.com/docs/source.html' } }
  const contextdb = {
    async getDocument(id: string) {
      calls.push({ method: 'document', id })
      if (options.documentError) throw options.documentError
      return { data: options.document || source }
    },
    async downloadDocument(id: string) {
      calls.push({ method: 'download', id })
      return options.download ? await options.download() : new Blob(['[说明](../help)\n\n[来源](https://example.com/docs/source.html)'])
    },
    nativeAPI: { async get(path: string, params: any) {
      calls.push({ method: 'chunks', path, params })
      return { data: options.chunks ? await options.chunks(params) : { document_id: 'doc-a', chunks: [], total: 0 } }
    } },
  }
  runInNewContext(script, { exports, require(name: string) {
    if (name === './contextdb') return contextdb
    if (name === '@/utils/contextdbResources') return { ...resources, fileSourceLinks: options.readLinks || resources.fileSourceLinks }
    if (name === '@/utils/contextdbDocumentName') return { documentDisplayName }
    if (name === '@/utils/request') return { async get(path: string, config: any) {
      calls.push({ method: 'manifest', path, params: config.params })
      return { data: options.manifest ? await options.manifest(path, config.params) : { document_id: 'doc-a', images: [] } }
    } }
    throw new Error(`Unexpected dependency ${name}`)
  } })
  return { api: exports, calls }
}

test('source resources accumulate official chunk pages, deduplicate attachments and extract links using the real source format', async () => {
  const f = fixture({ chunks: params => ({ document_id: 'doc-a', total: 101, chunks: params.offset === 0
    ? Array.from({ length: 100 }, (_, index) => ({ chunk_index: index, attachments: [{ type: 'image', asset_id: 'same-image', download_url: 'https://expired.invalid/signed' }] }))
    : [{ chunk_index: 100, attachments: [{ type: 'audio', start_ms: 0, end_ms: 2000 }] }] }) })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.name, '业务原件.html'); assert.equal(result.warning, '')
  assert.deepEqual(plain(result.attachments.map((item: any) => [item.type, item.document_id, item.chunk_index])), [['image', 'doc-a', 0], ['audio', 'doc-a', 100]])
  assert.equal(JSON.stringify(result).includes('expired.invalid'), false)
  assert.deepEqual(Array.from(result.links, (link: any) => link.url), ['https://example.com/docs/source.html', 'https://example.com/help'])
  const chunkReads = f.calls.filter(call => call.method === 'chunks')
  assert.deepEqual(plain(chunkReads.map(call => call.params)), [{ document_id: 'doc-a', knowledge_base_id: 'kb-a', offset: 0, limit: 100 }, { document_id: 'doc-a', knowledge_base_id: 'kb-a', offset: 100, limit: 100 }])
  assert.equal(chunkReads.every(call => call.path === 'knowledge/documents/chunks'), true)
  assert.equal(f.calls.filter(call => call.method === 'download').length, 1)
})

test('a mismatched document or knowledge base stops all source and attachment reads', async () => {
  for (const document of [{ id: 'another-doc', knowledge_base_id: 'kb-a' }, { id: 'doc-a', knowledge_base_id: 'another-kb' }]) {
    const f = fixture({ document })
    await assert.rejects(f.api.loadDocumentResources('doc-a', 'kb-a'), /不属于当前知识库/)
    assert.deepEqual(f.calls.map(call => call.method), ['document'])
  }
  const denied = Object.assign(new Error('forbidden'), { status: 403 }), f = fixture({ documentError: denied })
  await assert.rejects(f.api.loadDocumentResources('doc-a', 'kb-a'), (error: any) => error === denied)
  assert.equal(f.calls.length, 1)
})

test('unreadable later chunk pages preserve verified earlier attachments and still return source hyperlinks with a warning', async () => {
  const f = fixture({ chunks: params => {
    if (params.offset) throw new Error('later page denied')
    return { document_id: 'doc-a', total: 2, chunks: [{ chunk_index: 0, attachments: [{ type: 'image', asset_id: 'first-page' }] }] }
  } })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.attachments.length, 1); assert.equal(result.attachments[0].asset_id, 'first-page')
  assert.match(result.warning, /later page denied/)
  assert.ok(result.links.some((link: any) => link.url === 'https://example.com/help'))
})

test('wrongly attributed chunk data is excluded while independently validated source links remain available', async () => {
  const f = fixture({ chunks: () => ({ document_id: 'another-doc', total: 1, chunks: [{ chunk_index: 0, attachments: [{ type: 'image', asset_id: 'wrong-source' }] }] }) })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.deepEqual(plain(result.attachments), []); assert.match(result.warning, /切片归属不一致/)
  assert.ok(result.links.some((link: any) => link.url === 'https://example.com/help'))
})

test('source download failures keep validated attachments and source metadata links and combine separate errors', async () => {
  const available = fixture({ chunks: () => ({ document_id: 'doc-a', total: 1, chunks: [{ chunk_index: 0, attachments: [{ type: 'video' }] }] }), download: async () => { throw new Error('original unavailable') } })
  const result = await available.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.attachments.length, 1)
  assert.deepEqual(plain(result.links), [{ url: 'https://example.com/docs/source.html', text: 'https://example.com/docs/source.html' }])
  assert.match(result.warning, /original unavailable/)
  const failed = fixture({ chunks: () => { throw new Error('chunks denied') }, download: async () => { throw new Error('original denied') } })
  const partial = await failed.api.loadDocumentResources('doc-a', 'kb-a')
  assert.match(partial.warning, /chunks denied.*original denied/)
})

test('pagination without totals stops on an empty page and never rewrites source metadata or content', async () => {
  const document = { id: 'doc-a', knowledge_base_id: 'kb-a', name: 'source.md', metadata: { url: 'javascript:alert(1)' } }
  const original = JSON.stringify(document)
  const f = fixture({ document, chunks: params => ({ document_id: 'doc-a', chunks: params.offset ? [] : [{ chunk_index: 0, attachments: [{ type: 'image', asset_id: 'image-without-signed-url' }] }] }), download: async () => new Blob(['[说明](https://example.com/help)']) })
  const result = await f.api.loadDocumentResources('doc-a')
  assert.equal(f.calls.filter(call => call.method === 'chunks').length, 2)
  assert.equal(result.attachments.length, 1); assert.equal(result.links.length, 1)
  assert.equal(result.links[0].url, 'https://example.com/help'); assert.equal(JSON.stringify(document), original)
})

test('pending-review Markdown and HTML read image coordinates from the authenticated original manifest without formal chunks', async () => {
  const key = 'a'.repeat(64)
  for (const extension of ['md', 'html']) {
    const f = fixture({ document: { id: 'doc-a', knowledge_base_id: 'kb-a', name: `source.${extension}` },
      download: async () => new Blob([extension === 'md' ? '![界面](https://example.com/image.png)' : '<html><body><img src="https://example.com/image.png"/></body></html>']),
      manifest: () => ({ document_id: 'doc-a', images: [{ image_key: key, description: '原件界面' }] }) })
    const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
    assert.equal(result.warning, ''); assert.equal(result.attachments.length, 1)
    assert.equal(result.attachments[0].source_image_hash, key); assert.equal(result.attachments[0].description, '原件界面')
    assert.equal(result.attachments[0].document_id, 'doc-a'); assert.equal(result.attachments[0].source, 'source_inline')
    assert.deepEqual(plain(f.calls.find(call => call.method === 'manifest')), { method: 'manifest', path: '/api/contextdb/documents/doc-a/source-images', params: { knowledge_base_id: 'kb-a' } })
  }
})

test('original image manifests recover pending-review images even when chunks or source download are unavailable', async () => {
  const f = fixture({ chunks: () => { throw new Error('formal chunks not available') }, download: async () => { throw new Error('link download unavailable') }, manifest: () => ({ document_id: 'doc-a', images: [{ image_key: 'b'.repeat(64) }] }) })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.attachments.length, 1); assert.match(result.warning, /formal chunks not available.*link download unavailable/)
  assert.ok(result.links.some((link: any) => link.url === 'https://example.com/docs/source.html'))
})

test('foreign or malformed original image manifests never produce attachment coordinates', async () => {
  for (const manifest of [{ document_id: 'foreign-doc', images: [{ image_key: 'c'.repeat(64) }] }, { document_id: 'doc-a', images: [{ image_key: 'c'.repeat(64) }, { image_key: '../../foreign?token=secret' }] }]) {
    const f = fixture({ manifest: () => manifest })
    const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
    assert.equal(result.attachments.length, 0); assert.match(result.warning, /图片归属不一致|图片标识无效/)
    assert.equal(JSON.stringify(result).includes('secret'), false)
  }
})

test('manifest permission failures remain visible without discarding independently readable source links', async () => {
  const f = fixture({ manifest: () => { throw Object.assign(new Error('source images forbidden'), { status: 403 }) } })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.attachments.length, 0); assert.match(result.warning, /source images forbidden/)
  assert.ok(result.links.some((link: any) => link.url === 'https://example.com/help'))
})

test('partial official image attachments retain every original image without guessing a position-based association', async () => {
  const keys = ['d'.repeat(64), 'a'.repeat(64)]
  const f = fixture({ chunks: () => ({ document_id: 'doc-a', total: 1, chunks: [{ chunk_index: 0, attachments: [{ type: 'image', asset_id: 'official-image', description: '已解析截图' }] }] }), manifest: () => ({ document_id: 'doc-a', images: keys.map((image_key, index) => ({ image_key, description: `原图${2 - index}` })) }) })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.warning, ''); assert.equal(result.attachments.length, 3)
  assert.equal(result.attachments[0].asset_id, 'official-image'); assert.equal(result.attachments[0].source_image_hash, undefined)
  assert.deepEqual(Array.from(result.attachments.slice(1), (image: any) => image.source_image_hash), keys)
  assert.equal(result.attachments.slice(1).every((image: any) => image.asset_id === undefined), true)
  assert.equal(f.calls.some(call => call.method === 'manifest'), true)
})

test('Office and EPUB preserve original archive images with absent or partially available compiled images', async () => {
  const zip = new JSZip(), bytes = new Uint8Array([137, 80, 78, 71])
  zip.file('media/screenshot.png', bytes)
  const blob = new Blob([await zip.generateAsync({ type: 'arraybuffer' })])
  for (const extension of ['docx', 'pptx', 'xlsx', 'epub']) for (const compiledImage of [false, true]) {
    const f = fixture({ document: { id: 'doc-a', knowledge_base_id: 'kb-a', name: `source.${extension}` }, download: async () => blob,
      chunks: () => ({ document_id: 'doc-a', total: compiledImage ? 1 : 0, chunks: compiledImage ? [{ chunk_index: 0, attachments: [{ type: 'image', asset_id: 'compiled-image' }] }] : [] }),
      manifest: () => assert.fail('binary sources do not use a remote-image manifest') })
    const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
    assert.equal(result.warning, ''); assert.equal(result.attachments.length, compiledImage ? 2 : 1)
    const image = result.attachments.find((item: any) => item.embedded_key)
    assert.equal(image.embedded_key, 'media/screenshot.png')
    assert.deepEqual(new Uint8Array(await image.source_blob.arrayBuffer()), bytes)
    assert.equal(result.sourceFile.blob, blob); assert.equal(result.sourceFile.name, `source.${extension}`); assert.equal(result.sourceFile.fileType, extension)
    assert.equal(f.calls.some(call => call.method === 'manifest'), false)
  }
})

test('audio and video resource inspection does not automatically download the original media file', async () => {
  const f = fixture({ document: { id: 'doc-a', knowledge_base_id: 'kb-a', name: 'large.mp4' } })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.warning, ''); assert.equal(f.calls.some(call => call.method === 'download' || call.method === 'manifest'), false)
})

test('pending PDF resources retain the original bytes for full viewing even when link extraction fails and there are no chunks', async () => {
  const blob = new Blob(['original PDF bytes'], { type: 'application/pdf' })
  const f = fixture({ document: { id: 'doc-a', knowledge_base_id: 'kb-a', name: 'uploaded.pdf', display_name: '业务文件.pdf' }, download: async () => blob, readLinks: async () => { throw new Error('PDF links unavailable') } })
  const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
  assert.equal(result.name, '业务文件.pdf'); assert.equal(result.attachments.length, 0)
  assert.equal(result.sourceFile.blob, blob); assert.equal(result.sourceFile.name, 'uploaded.pdf'); assert.equal(result.sourceFile.fileType, 'pdf')
  assert.match(result.warning, /PDF links unavailable/)
  assert.equal(f.calls.filter(call => call.method === 'download').length, 1)
})

test('Office and EPUB originals without separate media entries still provide a full original viewer source', async () => {
  const zip = new JSZip()
  zip.file('content.xml', '<document><drawing/><table/></document>')
  const blob = new Blob([await zip.generateAsync({ type: 'arraybuffer' })])
  for (const extension of ['docx', 'pptx', 'xlsx', 'epub']) {
    const f = fixture({ document: { id: 'doc-a', knowledge_base_id: 'kb-a', name: `original.${extension}`, display_name: `业务原件.${extension}` }, download: async () => blob })
    const result = await f.api.loadDocumentResources('doc-a', 'kb-a')
    assert.equal(result.attachments.length, 0); assert.equal(result.sourceFile.blob, blob)
    assert.equal(result.sourceFile.name, `original.${extension}`); assert.equal(result.sourceFile.fileType, extension)
    assert.equal(f.calls.filter(call => call.method === 'download').length, 1)
  }
})
