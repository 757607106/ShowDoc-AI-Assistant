import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { runInNewContext } from 'node:vm'
import test, { type TestContext } from 'node:test'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import ts from 'typescript'
import * as filePreview from '../utils/filePreview.ts'
import { buildHtmlPreview } from '../utils/htmlPreview.ts'

const require = createRequire(import.meta.url)
const file = new URL('./document-preview.vue', import.meta.url)
const source = readFileSync(file, 'utf8')
const { descriptor } = parse(source, { filename: file.pathname })
const script = compileScript(descriptor, { id: 'html-upload-preview' }).content
  .replace('__expose();', '')
  .replace('return __returned__', '__expose(__returned__); return __returned__')
const compiled = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
const htmlPosition = descriptor.template!.content.indexOf('class="preview-html"')
const iframeStart = descriptor.template!.content.indexOf('<iframe', htmlPosition)
const iframe = compileTemplate({ source: descriptor.template!.content.slice(iframeStart, descriptor.template!.content.indexOf('/>', iframeStart) + 2), filename: file.pathname, id: 'html-preview-frame' })
assert.deepEqual(iframe.errors, [])
const templateExports: any = {}
runInNewContext(ts.transpileModule(iframe.code, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: templateExports, require: () => vue })

function setup(t: TestContext, kind: 'knowledge' | 'attachment' | 'blob' | 'artifact', options: { fetch?: () => Promise<Blob>; fileType?: string; epub?: () => Promise<any>; docx?: (blob: Blob, container: any) => Promise<any>; createElement?: (tag: string) => any; sourceMode?: boolean } = {}) {
  const sourceHTML = '<!DOCTYPE html><html><body><a href="https://example.com/help">说明</a><img src="https://example.com/image.png" onerror="steal()"/><script>run()</script></body></html>'
  const sanitizedHTML = '<a href="https://example.com/help">说明</a><img src="https://example.com/image.png">'
  const original = new Blob([sourceHTML], { type: 'text/html' })
  const exports: any = {}, sanitizedInputs: string[] = [], blobs: Blob[] = [], revoked: string[] = [], indexed: any[] = []
  const props = { active: false, sourceMode: options.sourceMode, fileName: `source.${options.fileType || 'html'}`, fileType: options.fileType || 'html', ...(kind === 'knowledge' ? { knowledgeId: 'doc-a' } : kind === 'attachment' ? { sessionId: 'session', attachmentId: 'attachment' } : kind === 'artifact' ? { sessionId: 'session', messageId: 'message', artifactIndex: 0 } : { sourceBlob: original }) }
  const browserURL = Object.assign(class extends URL {}, { createObjectURL(blob: Blob) { blobs.push(blob); return `blob:html-${blobs.length}` }, revokeObjectURL(url: string) { revoked.push(url) } })
  runInNewContext(compiled, {
    exports, Blob, TextDecoder, URL: browserURL, console,
    document: { addEventListener() {}, removeEventListener() {}, activeElement: {}, body: {}, createElement: options.createElement },
    window: { addEventListener() {}, removeEventListener() {} },
    require(name: string) {
      if (name === 'vue' || name === 'highlight.js' || name === 'xlsx') return require(name)
      if (name === 'docx-preview') return { renderAsync: options.docx }
      if (name === 'vue-i18n') return { useI18n: () => ({ t: (key: string) => key }) }
      if (name === '@/utils/filePreview') return filePreview
      if (name === '@/utils/security') return { sanitizeHTML: (html: string) => { sanitizedInputs.push(html); return sanitizedHTML } }
      if (name === '@/utils/htmlPreview') return { buildHtmlPreview }
      if (name === '@/api/knowledge-base/index') return { previewKnowledgeFile: async () => options.fetch ? await options.fetch() : original }
      if (name === '@/api/chat/temporary-attachments') return { previewTemporaryAttachment: async () => options.fetch ? await options.fetch() : original }
      if (name === '@/api/chat') return { downloadArtifact: async () => options.fetch ? await options.fetch() : original }
      if (name === '@/utils/epubPreview') return { renderEpubPreview: options.epub }
      if (name === '@/utils/sourceImage') return { indexEmbeddedSourceImages: async (container: any) => { indexed.push(container) } }
      return {}
    },
  })
  exports.default.render = () => null
  const renderer = vue.createRenderer<object, object>({ createElement: () => ({}), createText: () => ({}), createComment: () => ({}), insert() {}, remove() {}, setElementText() {}, setText() {}, patchProp() {}, parentNode: () => null, nextSibling: () => null })
  const app = renderer.createApp(exports.default, props), vm: any = app.mount({})
  let mounted = true
  const close = () => { if (mounted) { mounted = false; app.unmount() } }
  t.after(close)
  return { vm, props: vm.$.props, close, blobs, revoked, sanitizedInputs, sourceHTML, sanitizedHTML, indexed }
}

for (const kind of ['knowledge', 'attachment', 'blob'] as const) test(`${kind} HTML renders a sanitized copy by default while source text and sandbox restrictions remain intact`, async t => {
  const f = setup(t, kind)
  await f.vm.loadPreview()
  assert.equal(f.vm.error, ''); assert.equal(f.vm.previewType, 'html'); assert.equal(f.vm.htmlViewMode, 'render')
  assert.deepEqual(f.sanitizedInputs, [f.sourceHTML]); assert.equal(await f.blobs[0]!.text(), f.sanitizedHTML)
  assert.equal(f.vm.textContent, f.sourceHTML); assert.equal(f.vm.allowsHtmlScriptPreview(), false)
  const rendered = templateExports.render({ htmlViewMode: f.vm.htmlViewMode, blobUrl: f.vm.blobUrl, displayFileName: 'source.html', allowsHtmlScriptPreview: f.vm.allowsHtmlScriptPreview, onPreviewFrameLoad() {} }, [])
  assert.equal(rendered.type, 'iframe'); assert.equal(rendered.props.sandbox, 'allow-popups allow-popups-to-escape-sandbox')
  assert.equal(rendered.props.referrerpolicy, 'no-referrer')
  assert.doesNotMatch(rendered.props.sandbox, /allow-scripts|allow-same-origin/)
  f.vm.cleanup(); assert.deepEqual(f.revoked, ['blob:html-1'])
})

test('generated artifact HTML retains its executable preview and only allow-scripts in the opaque sandbox', async t => {
  const f = setup(t, 'artifact')
  await f.vm.loadPreview()
  assert.equal(f.vm.error, ''); assert.equal(f.vm.allowsHtmlScriptPreview(), true); assert.deepEqual(f.sanitizedInputs, [])
  assert.equal(await f.blobs[0]!.text(), buildHtmlPreview(f.sourceHTML)); assert.equal(f.vm.textContent, f.sourceHTML)
  const rendered = templateExports.render({ htmlViewMode: 'render', blobUrl: f.vm.blobUrl, displayFileName: 'source.html', allowsHtmlScriptPreview: f.vm.allowsHtmlScriptPreview, onPreviewFrameLoad() {} }, [])
  assert.equal(rendered.props.sandbox, 'allow-scripts'); assert.doesNotMatch(rendered.props.sandbox, /allow-same-origin/)
})

test('a source download arriving after unmount cannot allocate a preview URL or restore content', async t => {
  let complete!: (blob: Blob) => void
  const f = setup(t, 'knowledge', { fetch: async () => await new Promise(resolve => { complete = resolve }) })
  const pending = f.vm.loadPreview(); f.close(); complete(new Blob(['<p>old source</p>'], { type: 'text/html' })); await pending
  assert.equal(f.blobs.length, 0); assert.equal(f.vm.blobUrl, ''); assert.equal(f.vm.textContent, '')
  assert.equal(f.sanitizedInputs.length, 0)
})

test('an older source response cannot clear the new loading state or replace its content', async t => {
  const completions: Array<(blob: Blob) => void> = []
  const f = setup(t, 'knowledge', { fetch: async () => await new Promise(resolve => completions.push(resolve)) })
  const old = f.vm.loadPreview(); f.props.knowledgeId = 'doc-b'; const current = f.vm.loadPreview()
  completions[0]!(new Blob(['<p>old source</p>'], { type: 'text/html' })); await old
  assert.equal(f.vm.loading, true); assert.equal(f.blobs.length, 0)
  completions[1]!(new Blob(['<p>current source</p>'], { type: 'text/html' })); await current
  assert.equal(f.vm.textContent, '<p>current source</p>'); assert.deepEqual(f.sanitizedInputs, ['<p>current source</p>'])
  assert.equal(f.vm.loading, false); assert.equal(f.blobs.length, 1)
})

test('closing during HTML text decoding prevents a late object URL from being created', async t => {
  let complete!: (text: string) => void
  const blob = new Blob(['pending'], { type: 'text/html' })
  Object.defineProperty(blob, 'text', { value: () => new Promise<string>(resolve => { complete = resolve }) })
  const f = setup(t, 'knowledge', { fetch: async () => blob })
  const pending = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  assert.equal(typeof complete, 'function'); f.close(); complete('<p>decoded old source</p>'); await pending
  assert.equal(f.blobs.length, 0); assert.equal(f.vm.blobUrl, '')
})

test('late EPUB decoding revokes decoder object URLs instead of retaining a closed preview', async t => {
  let complete!: (value: any) => void
  const f = setup(t, 'knowledge', { fileType: 'epub', epub: async () => await new Promise(resolve => { complete = resolve }) })
  const pending = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  f.close(); complete({ html: '<p>old chapter</p>', objectUrls: ['blob:epub-image'] }); await pending
  assert.deepEqual(f.revoked, ['blob:epub-image']); assert.equal(f.vm.epubHtml, '')
})

test('slow text decoding from the previous document cannot replace a faster current text preview', async t => {
  let complete!: (text: string) => void, reads = 0
  const slow = new Blob(['old'], { type: 'text/plain' })
  Object.defineProperty(slow, 'text', { value: () => new Promise<string>(resolve => { complete = resolve }) })
  const f = setup(t, 'knowledge', { fileType: 'txt', fetch: async () => ++reads === 1 ? slow : new Blob(['current text'], { type: 'text/plain' }) })
  const old = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  assert.equal(typeof complete, 'function')
  f.props.knowledgeId = 'doc-b'; await f.vm.loadPreview()
  assert.equal(f.vm.textContent, 'current text')
  complete('stale old text'); await old
  assert.equal(f.vm.textContent, 'current text'); assert.equal(f.vm.error, '')
})

test('slow spreadsheet bytes cannot render over the next document after its CSV preview has loaded', async t => {
  let complete!: (bytes: ArrayBuffer) => void, reads = 0
  const slow = new Blob(['old'], { type: 'text/csv' })
  Object.defineProperty(slow, 'arrayBuffer', { value: () => new Promise<ArrayBuffer>(resolve => { complete = resolve }) })
  const f = setup(t, 'knowledge', { fileType: 'csv', fetch: async () => ++reads === 1 ? slow : new Blob(['item,count\ncurrent,2'], { type: 'text/csv' }) })
  const old = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  assert.equal(typeof complete, 'function')
  f.props.knowledgeId = 'doc-b'; await f.vm.loadPreview()
  assert.equal(f.sanitizedInputs.length, 1); assert.match(f.sanitizedInputs[0]!, /current/)
  complete(new TextEncoder().encode('item,count\nstale,1').buffer); await old
  assert.equal(f.sanitizedInputs.length, 1); assert.doesNotMatch(f.sanitizedInputs[0]!, /stale/)
})

test('late DOCX rendering stays in its staging element and cannot write over the current document', async t => {
  const completions: Array<() => void> = [], stagingElements: any[] = [], replacements: any[] = []
  const visible: any = { childNodes: [], replaceChildren(...nodes: any[]) { this.childNodes = nodes; replacements.push(nodes) } }
  Object.defineProperty(visible, 'innerHTML', { set() { visible.childNodes = [] } })
  const f = setup(t, 'knowledge', { fileType: 'docx', createElement: () => ({ childNodes: [] }), docx: async (_blob, staging) => {
    const number = stagingElements.length + 1
    stagingElements.push(staging)
    await new Promise<void>(resolve => completions.push(() => { staging.childNodes = [{ text: `document ${number}` }]; resolve() }))
  } })
  f.vm.docxContainer = visible
  const old = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  f.props.knowledgeId = 'doc-b'; const current = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  assert.equal(stagingElements.length, 2); assert.ok(stagingElements.every(element => element !== visible))
  completions[1]!(); await current
  assert.equal(visible.childNodes[0].text, 'document 2'); assert.equal(f.indexed.length, 1)
  completions[0]!(); await old
  assert.equal(visible.childNodes[0].text, 'document 2'); assert.equal(replacements.length, 1); assert.equal(f.indexed.length, 1)
})

test('slow PDF source bytes cannot replace the newer document buffer', async t => {
  let complete!: (bytes: ArrayBuffer) => void, reads = 0
  const slow = new Blob(['old pdf'], { type: 'application/pdf' })
  Object.defineProperty(slow, 'arrayBuffer', { value: () => new Promise<ArrayBuffer>(resolve => { complete = resolve }) })
  const f = setup(t, 'knowledge', { fileType: 'pdf', sourceMode: true, fetch: async () => ++reads === 1 ? slow : new Blob(['current pdf'], { type: 'application/pdf' }) })
  const old = f.vm.loadPreview(); await new Promise(resolve => setImmediate(resolve))
  f.props.knowledgeId = 'doc-b'; await f.vm.loadPreview()
  complete(new TextEncoder().encode('stale old pdf').buffer); await old
  assert.equal(new TextDecoder().decode(f.vm.pdfData), 'current pdf')
})
