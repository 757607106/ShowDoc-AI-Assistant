import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import { after, test } from 'node:test'
import { DOMParser as XmlParser } from '@xmldom/xmldom'
import JSZip from 'jszip'
import { Marked } from 'marked'
import ts from 'typescript'
import { attachmentPath, chunkAttachments, fileSourceImages, fileSourceLinks, htmlSourceLinks, markdownSourceLinks, sourceLink } from './contextdbResources.ts'

const originalParser = globalThis.DOMParser
class TestParser {
  parseFromString(text: string, type: string) {
    // Browser HTML parsing tolerates the isolated opening/closing anchor tokens emitted by marked.
    if (type === 'text/html' && /^\s*<a\b[^>]*>\s*$/i.test(text)) text += '</a>'
    if (type === 'text/html' && /^\s*<\/a>\s*$/i.test(text)) text = ''
    const doc = new XmlParser().parseFromString(type === 'text/html' ? `<html><body>${text}</body></html>` : text, type as 'text/html')
    Object.assign(doc, { querySelectorAll(selector: string) {
      assert.equal(selector, 'a[href]')
      return Array.from(doc.getElementsByTagName('*')).filter(node => node.localName === 'a' && node.hasAttribute('href'))
    } })
    return doc
  }
}
globalThis.DOMParser = TestParser as unknown as typeof DOMParser
after(() => {
  if (originalParser) globalThis.DOMParser = originalParser
  else Reflect.deleteProperty(globalThis, 'DOMParser')
})

test('source URLs resolve against their source and reject executable protocols, unresolved relatives and fragments', () => {
  assert.deepEqual(sourceLink('../guide?q=1#part', ' 使用说明 ', 'https://example.com/docs/page.html'), { url: 'https://example.com/guide?q=1#part', text: '使用说明' })
  assert.equal(sourceLink('mailto:help@example.com')?.url, 'mailto:help@example.com')
  assert.equal(sourceLink('tel:+8612345')?.url, 'tel:+8612345')
  assert.equal(sourceLink('//cdn.example.com/help', '', 'https://example.com/page')?.url, 'https://cdn.example.com/help')
  for (const url of ['', '  ', '#part', '  #part', 'javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,<script>x</script>', 'blob:https://example.com/id', 'file:///secret', 'relative.md']) {
    assert.equal(sourceLink(url), null, url)
    if (url !== 'relative.md') assert.equal(sourceLink(url, '', 'https://example.com/page'), null, url)
  }
})

test('Markdown extracts inline, reference and HTML hyperlinks while ignoring images and code examples', () => {
  const links = markdownSourceLinks([
    '[说明](https://example.com/help)', '[再次](https://example.com/help)',
    '[参考][manual]', '[manual]: ../manual?q=1 "手册"',
    '<a href="https://example.com/html?a=1&amp;b=2">HTML说明</a>',
    '![截图](https://example.com/image.png)', '`[示例](https://example.com/inline-code)`',
    '```md', '[示例](https://example.com/fenced-code)', '```',
    '[危险](javascript:alert)', '[本节](#local)',
  ].join('\n\n'), 'https://example.com/docs/source.md')
  assert.deepEqual(links.map(link => link.url).sort(), ['https://example.com/help', 'https://example.com/manual?q=1', 'https://example.com/html?a=1&b=2'].sort())
  assert.equal(links.find(link => link.url.includes('manual'))?.text, '参考')
})

test('Markdown href entities decode once while HTML and Office targets keep their existing single decode', async () => {
  const links = markdownSourceLinks('[查询](https://example.com/api?a=1&amp;b=2)\n\n[嵌套编码](https://example.com/nested?q=1&amp;amp;b=2)')
  assert.deepEqual(links.map(link => link.url), ['https://example.com/api?a=1&b=2', 'https://example.com/nested?q=1&amp;b=2'])
  const html = htmlSourceLinks('<a href="https://example.com/nested?q=1&amp;amp;b=2">HTML</a>')
  assert.equal(html[0]?.url, 'https://example.com/nested?q=1&amp;b=2')
  const zip = new JSZip()
  zip.file('word/_rels/document.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com/nested?q=1&amp;amp;b=2" TargetMode="External"/></Relationships>')
  const office = await fileSourceLinks(new Blob([await zip.generateAsync({ type: 'arraybuffer' })]), 'source.docx')
  assert.equal(office[0]?.url, 'https://example.com/nested?q=1&amp;b=2')
})

test('HTML extracts anchor text and safe relative destinations without treating scripts or images as links', () => {
  const links = htmlSourceLinks('<html><body><a href="../guide">使用 <b>说明</b></a><a href="mailto:help@example.com">邮件</a><a href="#part">本页</a><a href="javascript:alert(1)">危险</a><img src="https://example.com/p.png"/><script>"https://example.com/script"</script></body></html>', 'https://example.com/docs/page.html')
  assert.deepEqual(links, [{ url: 'https://example.com/guide', text: '使用 说明' }, { url: 'mailto:help@example.com', text: '邮件' }])
})

test('chunk attachment coordinates deduplicate assets and never retain expiring download URLs', () => {
  const chunks = [
    { chunk_index: 0, attachments: [{ type: 'image', asset_id: 'asset /?', description: '截图', download_url: 'https://signed.invalid/expired' }, { type: 'audio', start_ms: 0, end_ms: 5000, download_url: 'https://signed.invalid/audio' }] },
    { chunk_index: 1, attachments: [{ type: 'image', asset_id: 'asset /?' }, { type: 'video', description: '演示', download_url: null }, { type: 'unsupported', asset_id: 'ignored' }] },
    { attachments: [{ type: 'audio', download_url: 'https://signed.invalid/no-coordinate' }, { type: 'image', asset_id: 'standalone-image' }] },
  ]
  const original = JSON.stringify(chunks), attachments = chunkAttachments(chunks, 'doc /?')
  assert.equal(attachments.length, 4)
  assert.equal(JSON.stringify(chunks), original)
  assert.equal(JSON.stringify(attachments).includes('signed.invalid'), false)
  assert.deepEqual(attachments.map(item => item.type), ['image', 'audio', 'video', 'image'])
  assert.equal(attachmentPath(attachments[0]!, 'kb /?'), '/api/contextdb/assets/asset%20%2F%3F?knowledge_base_id=kb%20%2F%3F')
  assert.equal(attachmentPath(attachments[1]!, 'kb /?'), '/api/contextdb/documents/doc%20%2F%3F/attachments/0/1?knowledge_base_id=kb%20%2F%3F')
  assert.equal(attachmentPath(attachments[2]!), '/api/contextdb/documents/doc%20%2F%3F/attachments/1/1')
})

test('Office ZIP relationships preserve external hyperlinks across files and namespace prefixes', async () => {
  const zip = new JSZip()
  const namespace = 'http://schemas.openxmlformats.org/package/2006/relationships'
  const hyperlink = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
  zip.file('word/document.xml', '<document/>')
  zip.file('word/_rels/document.xml.rels', `<Relationships xmlns="${namespace}"><Relationship Type="${hyperlink}" Target="https://example.com/manual?a=1&amp;b=2" TargetMode="External"/><Relationship Type="${hyperlink}" Target="javascript:alert(1)" TargetMode="External"/><Relationship Type="${hyperlink}" Target="local.xml"/><Relationship Type="other/image" Target="https://example.com/image.png" TargetMode="External"/></Relationships>`)
  zip.file('ppt/slides/_rels/slide1.xml.rels', `<r:Relationships xmlns:r="${namespace}"><r:Relationship Type="${hyperlink}" Target="https://example.com/prefixed" TargetMode="External"/><r:Relationship Type="${hyperlink}" Target="https://example.com/manual?a=1&amp;b=2" TargetMode="External"/></r:Relationships>`)
  const blob = new Blob([await zip.generateAsync({ type: 'arraybuffer' })])
  for (const filename of ['source.docx', 'source.pptx', 'source.xlsx']) {
    assert.deepEqual((await fileSourceLinks(blob, filename)).map(link => link.url).sort(), ['https://example.com/manual?a=1&b=2', 'https://example.com/prefixed'])
  }
})

test('EPUB reads hyperlinks from XHTML content instead of requiring Office relationship parts', async () => {
  const zip = new JSZip()
  zip.file('mimetype', 'application/epub+zip')
  zip.file('META-INF/container.xml', '<container><rootfiles><rootfile full-path="EPUB/book.opf"/></rootfiles></container>')
  zip.file('EPUB/book.opf', '<package><manifest><item id="chapter" href="chapter.xhtml"/></manifest><spine><itemref idref="chapter"/></spine></package>')
  zip.file('EPUB/chapter.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><a href="https://example.com/book">书中链接</a><a href="chapter2.xhtml">书内章节</a><a href="javascript:alert(1)">危险</a></body></html>')
  assert.deepEqual(await fileSourceLinks(new Blob([await zip.generateAsync({ type: 'arraybuffer' })]), 'source.epub'), [{ url: 'https://example.com/book', text: '书中链接' }])
})

test('source file dispatch uses its real format and reports damaged archive contents', async () => {
  assert.deepEqual(await fileSourceLinks(new Blob(['[链接](https://example.com/md)']), 'source.MD'), [{ url: 'https://example.com/md', text: '链接' }])
  assert.deepEqual(await fileSourceLinks(new Blob(['first https://example.com/text\nsecond https://example.com/text']), 'source.txt'), [{ url: 'https://example.com/text', text: 'https://example.com/text' }])
  assert.deepEqual(await fileSourceLinks(new Blob(['https://example.com/hidden']), 'source.bin'), [])
  await assert.rejects(fileSourceLinks(new Blob(['invalid zip']), 'source.docx'))
})

test('Office and EPUB image extraction preserves embedded bytes and MIME types without needing official chunks or signed URLs', async () => {
  const zip = new JSZip()
  const files = [
    ['word/media/image.png', new Uint8Array([137, 80, 78, 71]), 'image/png'],
    ['ppt/media/image.JPG', new Uint8Array([255, 216, 255, 217]), 'image/jpeg'],
    ['EPUB/images/cover.svg', new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg"/>'), 'image/svg+xml'],
    ['xl/media/image.tif', new Uint8Array([73, 73, 42, 0]), 'image/tiff'],
  ] as const
  for (const [name, bytes] of files) zip.file(name, bytes)
  zip.file('script.js', 'steal()'); zip.file('word/document.xml', '<document/>'); zip.folder('directory.png')
  const blob = new Blob([await zip.generateAsync({ type: 'arraybuffer' })])
  for (const extension of ['docx', 'pptx', 'xlsx', 'epub']) {
    const images = await fileSourceImages(blob, `source.${extension}`, 'doc-a')
    assert.equal(images.length, 4)
    for (const [index, image] of images.entries()) {
      assert.equal(image.document_id, 'doc-a'); assert.equal(image.embedded_key, files[index]![0])
      assert.equal(image.source_blob?.type, files[index]![2]); assert.equal(image.source, 'source_embedded')
      assert.deepEqual(new Uint8Array(await image.source_blob!.arrayBuffer()), files[index]![1])
      assert.equal(image.asset_id, undefined); assert.equal(image.source_image_hash, undefined)
    }
  }
})

test('binary image extraction leaves Markdown and HTML image coordinates to the authenticated source manifest', async () => {
  assert.deepEqual(await fileSourceImages(new Blob(['![截图](https://example.com/image.png)']), 'source.md', 'doc-a'), [])
  assert.deepEqual(await fileSourceImages(new Blob(['<img src="https://example.com/image.png"/>']), 'source.html', 'doc-a'), [])
  const key = 'a'.repeat(64)
  assert.equal(attachmentPath({ type: 'image', document_id: 'doc /?', chunk_index: -1, attachment_index: 0, source_image_hash: key }, 'kb /?'), `/api/contextdb/documents/doc%20%2F%3F/source-images/${key}?knowledge_base_id=kb%20%2F%3F`)
})

function pdfFixture(pages: any[], options: { loadError?: Error; pdfjs?: any } = {}) {
  const calls: any[] = [], exports: any = {}
  const moduleUrl = new URL('./contextdbResources.ts', import.meta.url).href
  const source = ts.transpileModule(readFileSync(new URL(moduleUrl), 'utf8').replaceAll('import.meta.url', JSON.stringify(moduleUrl)), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const task = { get promise() { return options.loadError ? Promise.reject(options.loadError) : Promise.resolve({ numPages: pages.length, async getPage(number: number) { calls.push(['page', number]); return pages[number - 1] } }) }, async destroy() { calls.push(['destroy']) } }
  runInNewContext(source, { exports, URL, Blob, Uint8Array, DOMParser: TestParser, require(name: string) {
    if (name === 'marked') return { Marked }
    const pdfjs = { GlobalWorkerOptions: {}, getDocument(config: any) { calls.push(['document', config]); return task } }
    if (name === 'pdfjs-dist') return pdfjs
    if (name === '../components/source-preview/pdfjsLoader') return { loadPdfJs: async () => options.pdfjs || pdfjs }
    throw new Error(`Unexpected dependency ${name}`)
  } })
  return { api: exports, calls }
}

test('PDF hyperlink extraction visits all pages, filters unsafe annotations and releases its task', async () => {
  const cleaned: number[] = []
  const f = pdfFixture([1, 2].map(number => ({ async getAnnotations() { return number === 1 ? [{ url: 'https://example.com/pdf' }, { url: 'javascript:alert(1)' }, { unsafeUrl: 'https://example.com/unsafe' }] : [{ url: 'https://example.com/pdf' }, { url: 'https://example.com/page2' }] }, cleanup() { cleaned.push(number) } })))
  const links = await f.api.fileSourceLinks(new Blob(['PDF source']), 'source.pdf')
  assert.deepEqual(Array.from(links, (link: any) => link.url), ['https://example.com/pdf', 'https://example.com/page2'])
  assert.deepEqual(cleaned, [1, 2]); assert.ok(f.calls[0][1].data instanceof Uint8Array)
  assert.deepEqual(f.calls.at(-1), ['destroy'])
})

test('PDF load or annotation failures remain visible and still destroy the loading task', async () => {
  const failedLoad = pdfFixture([], { loadError: new Error('invalid PDF') })
  await assert.rejects(failedLoad.api.fileSourceLinks(new Blob(['bad']), 'source.pdf'), /invalid PDF/)
  assert.deepEqual(failedLoad.calls.at(-1), ['destroy'])
  const failedPage = pdfFixture([{ async getAnnotations() { throw new Error('annotation failed') }, cleanup() {} }])
  await assert.rejects(failedPage.api.fileSourceLinks(new Blob(['pdf']), 'source.pdf'), /annotation failed/)
  assert.deepEqual(failedPage.calls.at(-1), ['destroy'])
})

test('real PDF bytes retain an external link through the installed PDF parser', async () => {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs')
  pdfjs.GlobalWorkerOptions.workerSrc = new URL('../../node_modules/pdfjs-dist/legacy/build/pdf.worker.mjs', import.meta.url).href
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> /Annots [4 0 R] >>',
    '<< /Type /Annot /Subtype /Link /Rect [10 10 100 20] /A << /S /URI /URI (https://example.com/pdf-manual) >> >>',
  ]
  let bytes = '%PDF-1.7\n'
  const offsets = [0]
  objects.forEach((object, index) => { offsets.push(bytes.length); bytes += `${index + 1} 0 obj\n${object}\nendobj\n` })
  const xref = bytes.length
  bytes += `xref\n0 5\n0000000000 65535 f \n${offsets.slice(1).map(offset => String(offset).padStart(10, '0') + ' 00000 n ').join('\n')}\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  const f = pdfFixture([], { pdfjs })
  const result = await f.api.fileSourceLinks(new Blob([bytes], { type: 'application/pdf' }), 'source.pdf')
  assert.deepEqual(JSON.parse(JSON.stringify(result)), [{ url: 'https://example.com/pdf-manual', text: 'https://example.com/pdf-manual' }])
})
