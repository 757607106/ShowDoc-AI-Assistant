import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'

const { descriptor } = parse(readFileSync(new URL('./KnowledgeChunksList.vue', import.meta.url), 'utf8'))
const rawName = `doc-${'d'.repeat(64)}.html`

async function render(chunks: any[]) {
  const app = createSSRApp({ template: descriptor.template!.content, data: () => ({ chunks, title: '' }) })
  app.component('TTag', { template: '<span><slot /></span>' })
  app.component('TEmpty', { template: '<span />' })
  return (await renderToString(app)).replace(/<!--[\s\S]*?-->/g, '')
}

test('source labels and heading paths use readable fields without modifying original evidence', async () => {
  const chunk = { doc_id: 'source-id', doc_name: rawName, document_display_name: '采购单.html',
    toc_path: `${rawName} > 原始章节`, display_toc_path: '采购单.html > 原始章节',
    content: `原文仍引用 ${rawName}` }
  const original = structuredClone(chunk)
  const html = await render([chunk])
  assert.match(html, /<span[^>]*>采购单\.html<\/span>/)
  assert.match(html, /class="chunk-toc">采购单\.html &gt; 原始章节<\/div>/)
  assert.match(html, new RegExp(`class="chunk-content">原文仍引用 ${rawName.replaceAll('.', '\\.')}<`))
  assert.deepEqual(chunk, original)
})

test('Wiki evidence displays its readable summary title without changing native identity or content', async () => {
  const wikiItem = { title: `${rawName} - Summary`, display_title: '采购单.html - Summary',
    page_id: 'wiki-page', content: `正式原文中的 ${rawName}`, score: 0.6 }
  const original = structuredClone(wikiItem)
  const html = await render([wikiItem])
  assert.match(html, /<span[^>]*>采购单\.html - Summary<\/span>/)
  assert.ok(html.includes(wikiItem.content))
  assert.deepEqual(wikiItem, original)
})

test('older responses retain their original labels and all labels remain inert text', async () => {
  const html = await render([{ doc_name: '历史来源.md', toc_path: '历史章节', content: '原文' },
    { display_title: '<img src=x onerror=alert(1)>', display_toc_path: '<svg onload=alert(1)>', content: '原文' }])
  assert.match(html, /历史来源\.md/)
  assert.match(html, /class="chunk-toc">历史章节<\/div>/)
  assert.doesNotMatch(html, /<(?:img|svg)\b/)
  assert.match(html, /&lt;img/)
  assert.match(html, /&lt;svg/)
})
