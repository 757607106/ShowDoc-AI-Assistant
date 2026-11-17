import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const router = readFileSync(new URL('./index.ts', import.meta.url), 'utf8')
const platformShell = readFileSync(new URL('../views/platform/index.vue', import.meta.url), 'utf8')

function routeBlock(name) {
  const at = router.indexOf(`name: "${name}"`)
  assert.notEqual(at, -1, `route ${name} not found`)
  return router.slice(router.lastIndexOf('{', at), router.indexOf('}', at) + 1)
}

test('platform shell is the only place that mounts the settings modal', () => {
  // Two copies each fetch their own data, so a save in one leaves the other stale.
  assert.equal(platformShell.match(/<Settings\b[^>]*\/>/g)?.length, 1)
  assert.doesNotMatch(platformShell, /<ContextDBSettings|contextdbSettings/)
  assert.doesNotMatch(router, /views\/settings\/Settings\.vue/)
})

test('/platform/settings keeps a route but renders nothing into the outlet', () => {
  const block = routeBlock('settings')
  assert.match(block, /path: "settings"/)
  assert.match(block, /component: SettingsRouteOutlet/)
  assert.match(router, /const SettingsRouteOutlet = defineComponent\(\{[^}]*render: \(\) => null/)
})

test('unified settings retain file memory without mounting retired WeKnora business panels', () => {
  const settings=readFileSync(new URL('../views/settings/ContextDBSettings.vue',import.meta.url),'utf8')
  assert.match(settings,/<MemorySettings[^>]*\/>/)
  assert.match(settings,/<NativeRuntimeSettings[^>]*\/>/)
  assert.match(settings,/key:'memory'/)
  for(const name of ['MemoryWorkspaceSettings','ChatHistorySettings','SandboxSettings','OllamaSettings','WeKnoraCloudSettings','IntegrationSettingsSection'])assert.doesNotMatch(settings,new RegExp('<'+name+'\\b'))
})
