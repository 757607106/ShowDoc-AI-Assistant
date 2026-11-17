import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createServer, type ViteDevServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { createSSRApp, h, type Component, type SetupContext } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createI18n } from 'vue-i18n'
import en from '../../../i18n/locales/en-US'
import zh from '../../../i18n/locales/zh-CN'

const REAL_COMPONENTS = [
  'ToolResultRenderer.vue',
  'OperationsResult.vue',
  'WeKnoraDocResult.vue',
  'CatalogValue.vue',
  'SearchResults.vue', 'ResultRow.vue', 'ContentPopup.vue',
  'ChunkDetail.vue', 'RelatedChunks.vue', 'WeKnoraGraphQueryResults.vue',
  'GrepResults.vue',
]

let server: ViteDevServer
let Renderer: Component
before(async () => {
  server = await createServer({
    configFile: false, optimizeDeps: { noDiscovery: true, entries: [] }, plugins: [
      {
        name: 'isolate-catalog-renderer',
        enforce: 'pre',
        load(id) {
          if (id.endsWith('/src/utils/clipboard.ts')) return 'export async function copyToClipboard() { return false }'
          // DOMPurify needs a browser; this suite verifies the shared-renderer boundary.
          // Its image URI and Markdown rendering behavior is covered by documentPreviewMarkdown.test.ts.
          if (id.endsWith('/src/components/DocMarkdown.vue')) {
            return `<script setup>defineProps(['content','sourceName','sourceDisplayName','attachments','kbId'])</script>
              <template><div data-shared-doc-markdown :data-source-name="sourceName" :data-display-name="sourceDisplayName" :data-kb="kbId" :data-attachments="JSON.stringify(attachments || [])">{{ content }}</div></template>`
          }
          if (id.endsWith('.vue') && !REAL_COMPONENTS.some((name) => id.endsWith(`/${name}`))) {
            return '<template><div /></template>'
          }
        },
      },
      vue(),
    ],
    resolve: { alias: { '@': fileURLToPath(new URL('../../../', import.meta.url)) } },
    server: { middlewareMode: true }, appType: 'custom',
  })
  Renderer = (await server.ssrLoadModule('/src/views/chat/components/ToolResultRenderer.vue')).default
})
after(async () => { await server?.close() })

async function render(props: Record<string, unknown>, locale = 'en-US') {
  const app = createSSRApp({ render: () => h(Renderer, props) })
  app.use(createI18n({ legacy: false, locale, messages: { 'en-US': en, 'zh-CN': zh } }))
  app.component('t-icon', { render: () => h('span') })
  app.component('t-popup', { inheritAttrs: false, setup(_props: unknown, { slots }: SetupContext) { return () => slots.content?.() } })
  return renderToString(app)
}

test('find_operations renders rows instead of raw JSON', async () => {
  const html = await render({
    displayType: 'find_operations',
    success: true,
    output: JSON.stringify({
      operations: [{
        id: 'knowledge.get', risk: 'read', summary: 'Read a knowledge base',
        description: 'Returns <script>alert(1)</script>',
        params: [{ name: 'knowledge_base_id', type: 'string', required: true, description: 'Knowledge base' }],
      }],
      unavailable: [{ id: 'knowledge.delete', risk: 'destructive', summary: 'Delete', reason: 'read-only' }],
      hint: 'Call find_operations again',
    }),
  })
  assert.match(html, /knowledge\.get/)
  assert.match(html, /title="knowledge\.get"[^>]*>Get knowledge details</)
  assert.match(html, /Read a knowledge base/)
  assert.match(html, /Read</)
  assert.match(html, /knowledge_base_id/)
  assert.match(html, /Required/)
  assert.match(html, /knowledge\.delete/)
  assert.match(html, /title="knowledge\.delete"[^>]*>Delete knowledge</)
  assert.match(html, /Destructive/)
  assert.match(html, /&lt;script&gt;/)
  assert.doesNotMatch(html, /fallback-output|hint|Call find_operations|<script>/)
})

test('run_operation renders projected fields and keeps failures out of the raw dump', async () => {
  const html = await render({
    displayType: 'run_operation',
    success: true,
    output: JSON.stringify({
      operation: 'knowledge.list',
      result: { data: [{ title: '员工手册', parse_status: 'failed' }], truncated: true },
    }),
  })
  assert.match(html, /knowledge\.list/)
  assert.match(html, /title="knowledge\.list"[^>]*>List knowledge</)
  assert.match(html, /员工手册/)
  assert.match(html, /parse_status/)
  assert.match(html, /failed/)
  assert.match(html, /Result truncated/)
  assert.doesNotMatch(html, /fallback-output/)

  const error = await render({ displayType: 'run_operation', success: false, output: 'unknown operation "nope"' })
  assert.match(error, /role="alert"/)
  assert.match(error, /unknown operation/)
  assert.doesNotMatch(error, /fallback-output/)
})

test('operation results show localized names and retain IDs as tooltips', async () => {
  for (const [operation, label] of [['model.list', '获取模型列表'], ['agent.list', '获取智能体列表'], ['future.unknown', 'future.unknown']]) {
    const html = await render({
      displayType: 'run_operation', success: true,
      output: JSON.stringify({ operation, result: { data: [] } }),
    }, 'zh-CN')
    assert.ok(html.includes(`title="${operation}"`), html)
    assert.ok(html.includes(`>${label}</span>`), html)
  }
})

test('product docs keep safe navigation and delegate full Markdown to the shared renderer', async () => {
  const search = await render({
    displayType: 'search_weknora_docs',
    success: true,
    output: JSON.stringify({
      results: [{
        path: '03-features/14-wiki', anchor: 'setup', section: '安装',
        url: 'javascript:alert(1)', snippet: '<script>alert(1)</script>',
      }],
    }),
  })
  assert.match(search, /安装/)
  assert.match(search, /03-features\/14-wiki#setup/)
  assert.match(search, /&lt;script&gt;/)
  assert.doesNotMatch(search, /javascript:|fallback-output|<script>/)

  const read = await render({
    displayType: 'read_weknora_doc',
    success: true,
    output: JSON.stringify({
      title: 'Wiki',
      path: '03-features/14-wiki',
      section: '安装',
      url: 'https://docs.example/wiki#setup',
      content: '# 安装\n\n先准备 [环境](https://docs.example/env)。\n\n![界面](https://docs.example/setup.png)\n<script>alert(1)</script>',
      outline: [{ anchor: 'setup', heading: '安装', level: 2 }],
      truncated: true,
    }),
  })
  assert.match(read, /data-shared-doc-markdown/)
  assert.match(read, /安装/)
  assert.match(read, /\[环境\]\(https:\/\/docs\.example\/env\)/)
  assert.match(read, /!\[界面\]\(https:\/\/docs\.example\/setup\.png\)/)
  assert.match(read, /href="https:\/\/docs\.example\/wiki#setup"/)
  assert.match(read, /Open in docs/)
  assert.match(read, /The page continues/)
  assert.match(read, /&lt;script&gt;/)
  assert.doesNotMatch(read, /fallback-output|"content"|<script>/)
  const component = readFileSync(new URL('./tool-results/WeKnoraDocResult.vue', import.meta.url), 'utf8')
  assert.match(component, /import DocMarkdown from '@\/components\/DocMarkdown.vue'/)
})

test('search, chunk and graph cards retain source names, media coordinates and unmodified Markdown', async () => {
  const rawName = 'doc-' + 'a'.repeat(64) + '.md'
  const result = { result_index: 1, knowledge_id: 'doc-1', knowledge_base_id: 'kb-1',
    chunk_id: 'chunk-1', chunk_index: 3, knowledge_title: rawName, document_name: rawName,
    document_display_name: '采购明细.html', content: `${rawName}\n\n[4](https://example.com/help)\n![截图](https://example.com/image.png)`,
    attachments: [{ type: 'image', asset_id: 'asset-1', download_url: 'https://signed.invalid/private' },
      { type: 'audio', download_url: 'https://signed.invalid/audio' }], score: 0.8, relevance_level: 'High Relevance' }
  const unchanged = JSON.stringify(result)
  for (const data of [
    { display_type: 'search_results', results: [result] },
    { display_type: 'graph_query_results', results: [result] },
    { display_type: 'chunk_detail', ...result },
    { display_type: 'related_chunks', chunks: [result] },
    { display_type: 'grep_results', query: '4', patterns: ['4'], chunk_results: [{ ...result, match_snippet: result.content }], knowledge_results: [], total_matches: 1 },
  ]) {
    const html = await render({ displayType: data.display_type, toolData: data, success: true })
    assert.match(html, /data-shared-doc-markdown/)
    assert.match(html, /data-display-name="采购明细.html"/)
    assert.match(html, /data-kb="kb-1"/)
    assert.match(html, /\[4\]\(https:\/\/example.com\/help\)/)
    assert.match(html, /!\[截图\]\(https:\/\/example.com\/image.png\)/)
    assert.match(html, /asset-1/)
    assert.match(html, /attachment_index/)
    assert.doesNotMatch(html, /signed.invalid/)
  }
  assert.equal(JSON.stringify(result), unchanged)
})
