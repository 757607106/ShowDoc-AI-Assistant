import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture'

function setup(t: Parameters<typeof fixture>[0], admin = true) {
  const f = fixture(t)
  const ui = vue.reactive({ showSettingsModal: true, settingsInitialSection: 'models', closeSettings() { this.showSettingsModal = false } })
  const route = vue.reactive({ name: 'settings', query: {} as Record<string, string> })
  const push = t.mock.fn(async (_path: string) => {})
  const writes: any[] = []
  const page = f.component(new URL('./ContextDBSettings.vue', import.meta.url), {
    'vue-router': { useRoute: () => route, useRouter: () => ({ push }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => admin }) },
    '@/stores/ui': { useUIStore: () => ui },
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({ isSupported: () => true }) },
    '@/utils/request': { get: async () => ({ data: [], users: [{ id: 'legacy', email: 'legacy-account', username: '显示名' }] }),
      post: async (path: string, body: any) => { writes.push({ method: 'POST', path, body }) },
      patch: async (path: string, body: any) => { writes.push({ method: 'PATCH', path, body }) } },
    '@/api/contextdb': {}, '@/utils/platformPresentation': {},
    'tdesign-vue-next': { MessagePlugin: { success() {} } },
  })
  return { ...f, ...page, ui, route, push, writes }
}

test('model settings opens from the composer shortcut and route navigation', async t => {
  const f = setup(t)
  assert.equal(f.vm.section, 'models')
  f.vm.section = 'account'
  f.window.dispatchEvent(new CustomEvent('settings-nav', { detail: { section: 'models' } }))
  assert.equal(f.vm.section, 'models')
  f.route.query.section = 'defaults'
  await flush()
  assert.equal(f.vm.section, 'defaults')
})

test('MCP and skills settings use the original toolbox panels', async t => {
  const f = setup(t)
  f.vm.selectSection('mcp')
  assert.equal(f.ui.showSettingsModal, false)
  assert.equal(f.push.mock.calls[0].arguments[0], '/platform/toolbox/mcp')
  f.vm.selectSection('skills')
  assert.equal(f.push.mock.calls[1].arguments[0], '/platform/toolbox/skills')
})

test('read-only members do not get the web search configuration entry', t => {
  const f = setup(t, false)
  assert.equal(f.vm.groups.some((group: any) => group.items.some((item: any) => item.key === 'websearch')), false)
  f.vm.selectSection('websearch')
  assert.equal(f.vm.section, 'models')
})

test('session files remain reachable but retired runtime settings cannot be selected', t => {
  const f = setup(t)
  f.vm.selectSection('sandbox')
  assert.equal(f.vm.section, 'sandbox')
  for (const section of ['browserconnection', 'mymemory', 'memory', 'envvars']) {
    assert.equal(f.vm.groups.some((group: any) => group.items.some((item: any) => item.key === section)), false)
    f.vm.selectSection(section)
    assert.equal(f.vm.section, 'sandbox')
  }
  assert.equal(f.push.mock.calls.length, 0)
})

test('ordinary personal settings and admin chat history remain reachable', t => {
  const f = setup(t)
  for (const section of ['general', 'userprofile', 'assistant', 'chathistory']) {
    f.vm.selectSection(section)
    assert.equal(f.vm.section, section)
  }
  assert.equal(f.push.mock.calls.length, 0)
})

test('read-only members retain personal settings but cannot enter admin history or retired memory', t => {
  const f = setup(t, false)
  f.vm.selectSection('general')
  assert.equal(f.vm.section, 'general')
  for (const section of ['memory', 'mymemory', 'chathistory']) {
    f.vm.selectSection(section)
    assert.equal(f.vm.section, 'general')
  }
})

test('member creation sends a plain account and accepts the eight-character default password', async t => {
  const f = setup(t)
  f.vm.section = 'members'; await flush()
  assert.equal(f.vm.users[0].account, 'legacy-account')
  f.vm.edit(); f.vm.account = ' worker '; f.vm.password = 'admin123'; await f.vm.save()
  assert.deepEqual(JSON.parse(JSON.stringify(f.writes)), [{ method: 'POST', path: '/api/platform/users',
    body: { account: 'worker', username: 'worker', password: 'admin123', role: 'viewer' } }])
  assert.equal(f.vm.formOpen, false)
})

test('member validation rejects a missing account or invalid password and editing can keep the password', async t => {
  const f = setup(t)
  f.vm.edit(); f.vm.password = 'admin123'; await f.vm.save()
  assert.match(f.vm.error, /账号/); assert.equal(f.writes.length, 0)
  f.vm.account = 'worker'; f.vm.password = 'short12'; await f.vm.save()
  assert.match(f.vm.error, /8 至 1024/); assert.equal(f.writes.length, 0)
  f.vm.password = 'x'.repeat(1025); await f.vm.save(); assert.equal(f.writes.length, 0)
  f.vm.edit({ id: 'legacy', email: 'legacy-account', role: 'editor' }); assert.equal(f.vm.account, 'legacy-account')
  await f.vm.save()
  assert.deepEqual(JSON.parse(JSON.stringify(f.writes)), [{ method: 'PATCH', path: '/api/platform/users/legacy', body: { role: 'editor' } }])
})
