import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { toolboxLocation } from '../../config/toolbox'
import { fixture, flush } from '../../test-utils/vueFixture'

function setup(t: Parameters<typeof fixture>[0], admin = true) {
  const f = fixture(t)
  const ui = vue.reactive({ showSettingsModal: true, settingsInitialSection: 'models', closeSettings() { this.showSettingsModal = false } })
  const route = vue.reactive({ name: 'settings', path:'/platform/settings', query: {} as Record<string, string> })
  const push = t.mock.fn(async (_path: unknown) => {})
  const replace=t.mock.fn(async (_location: unknown)=>{})
  const warnings:string[]=[]
  const writes: any[] = []
  const page = f.component(new URL('./ContextDBSettings.vue', import.meta.url), {
    'vue-router': { useRoute: () => route, useRouter: () => ({ push,replace }) },
    '@/stores/auth': { useAuthStore: () => ({ user:{id:'owner'},hasRole: () => admin }) },
    '@/composables/useModalShell': { useModalShell: (options:any)=>({requestClose:options.close}) },
    '@/stores/ui': { useUIStore: () => ui },
    '@/config/toolbox':{toolboxLocation},
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({ isSupported: () => true }) },
    '@/utils/request': { get: async () => ({ data: [], users: [{ id: 'legacy', email: 'legacy-account', username: '显示名' }] }),
      post: async (path: string, body: any) => { writes.push({ method: 'POST', path, body }) },
      patch: async (path: string, body: any) => { writes.push({ method: 'PATCH', path, body }) } },
    '@/api/contextdb': {}, '@/utils/platformPresentation': {},
    'tdesign-vue-next': { MessagePlugin: { success() {},warning:(message:string)=>warnings.push(message) } },
  })
  return { ...f, ...page, ui, route, push, replace, writes, warnings }
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
  assert.deepEqual(f.push.mock.calls[0].arguments[0], toolboxLocation('mcp'))
  f.vm.selectSection('skills')
  assert.deepEqual(f.push.mock.calls[1].arguments[0], toolboxLocation('skills'))
})

test('retired bookmarks show an explicit notice without mounting their old controls', t => {
  const f=setup(t)
  for(const section of ['websearch','chathistory','ollama','weknoracloud','parser','storage','vectorstore','assistant','system-global','integration-api','integration-cli','browserconnection','envvars']){
    assert.equal(f.vm.groups.some((group:any)=>group.items.some((item:any)=>item.key===section)),false)
    f.vm.selectSection(section)
    assert.equal(f.vm.section,'retired')
    assert.equal(f.vm.retiredSection,section)
  }
  assert.equal(f.push.mock.calls.length,0)
})

test('file memory aliases and native runtime are available without legacy workspace controls', t => {
  const f=setup(t,false)
  for(const section of ['memory','mymemory']){
    f.vm.selectSection(section)
    assert.equal(f.vm.section,'memory')
  }
  f.vm.selectSection('tenant');assert.equal(f.vm.section,'tenant')
  f.vm.selectSection('sandbox');assert.equal(f.vm.section,'sandbox')
  f.vm.selectSection('system');assert.equal(f.vm.section,'runtime')
  f.vm.selectSection('general');assert.equal(f.vm.section,'general')
  f.vm.selectSection('userprofile');assert.equal(f.vm.section,'userprofile')
  assert.equal(f.vm.groups.some((group:any)=>group.items.some((item:any)=>item.key==='members')),false)
})

test('unsaved memory prevents section changes and tool navigation until saved or discarded',t=>{
  const f=setup(t)
  f.vm.selectSection('memory');f.vm.memoryDirty=true
  f.vm.selectSection('models');assert.equal(f.vm.section,'memory')
  f.vm.selectSection('toolbox');assert.equal(f.push.mock.calls.length,0)
  assert.equal(f.warnings.length,2)
  f.vm.memoryDirty=false;f.vm.selectSection('agents')
  assert.equal(f.push.mock.calls[0].arguments[0],'/platform/agents')
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
