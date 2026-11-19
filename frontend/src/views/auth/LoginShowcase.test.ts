import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createSSRApp, h, type Component } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createI18n } from 'vue-i18n'
import vue from '@vitejs/plugin-vue'
import { createServer, type ViteDevServer } from 'vite'
import zh from '../../i18n/locales/zh-CN'
import en from '../../i18n/locales/en-US'

let server: ViteDevServer
let Showcase: Component

before(async () => {
  server = await createServer({
    configFile: false,
    optimizeDeps: { noDiscovery: true, entries: [] },
    plugins: [vue()],
    server: { middlewareMode: true, hmr: false },
    appType: 'custom',
  })
  Showcase = (await server.ssrLoadModule('/src/views/auth/LoginShowcase.vue')).default
})

after(async () => { await server?.close() })

async function render(locale: 'zh-CN' | 'en-US') {
  const app = createSSRApp({ render: () => h(Showcase) })
  app.use(createI18n({
    legacy: false,
    locale,
    messages: { 'zh-CN': zh, 'en-US': en },
  }))
  return renderToString(app)
}

test('the production showcase renders four localized controls and a named current illustration', async () => {
  for (const locale of ['zh-CN', 'en-US'] as const) {
    const output = await render(locale)
    assert.equal([...output.matchAll(/data-slide="[0-3]"/g)].length, 4)
    assert.equal([...output.matchAll(/aria-pressed="true"/g)].length, 1)
    assert.match(output, /aria-labelledby="login-scene-title-0"/)
    assert.match(output, /<h1 id="login-scene-title-0"/)
    assert.match(output, /aria-labelledby="login-art-title login-art-description"/)
    assert.doesNotMatch(output, /platform\.loginShowcase\./)
    assert.match(output, locale === 'zh-CN' ? /每次提问，都有依据/ : /Every answer has a source/)
  }
})

test('all shared vector references resolve to unique definitions in the rendered component', async () => {
  const output = await render('zh-CN')
  const ids = [...output.matchAll(/\bid="([^"]+)"/g)].map(match => match[1])
  assert.equal(new Set(ids).size, ids.length, 'duplicate SVG or heading IDs')
  const references = [
    ...[...output.matchAll(/url\(#([^)]*)\)/g)].map(match => match[1]),
    ...[...output.matchAll(/href="#([^"]+)"/g)].map(match => match[1]),
  ]
  assert(references.length > 10)
  for (const reference of references) {
    assert(ids.includes(reference), 'missing vector definition ' + reference)
  }
})
