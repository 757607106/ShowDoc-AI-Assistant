import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { reactive } from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

const file = new URL('./ContextDBPolicies.vue', import.meta.url)
const profile = (kb: string, permission = 'kb_manage') => ({ mode: 'advanced', evaluation_state: 'active', member: { role: 'member', status: 'active' }, knowledge_base_permissions: [{ knowledge_base_id: kb, current_permission: permission }] })
async function setup(t: TestContext, options: { kb?: string; section?: string; contributor?: boolean; permissions?: () => Promise<any>; libraries?: () => Promise<any> } = {}) {
  const f = fixture(t), route = reactive({ params: { kbId: options.kb || 'one' }, query: { section: options.section || 'settings', keep: 'retained' } }), replacements: any[] = []
  const api = f.evaluate(readFileSync(new URL('../../api/contextdb.ts', import.meta.url), 'utf8'), {
    '@/utils/request': {}, '@/utils/contextdbDocumentName': { documentDisplayName() {} },
  })
  let permissions = options.permissions || (async () => profile(route.params.kbId))
  const { vm, close } = f.component(file, {
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace: async (value: any) => { replacements.push(JSON.parse(JSON.stringify(value))); route.query = value.query }, push() {} }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => options.contributor !== false }) },
    '@/api/contextdb': { knowledgeAccess: api.knowledgeAccess, listBases: options.libraries || (async () => ({ data: [{ id: route.params.kbId, name: route.params.kbId }] })), getBasePermissions: () => permissions() },
  })
  await flush(); return { vm, route, replacements, close, setPermissions: (value: () => Promise<any>) => { permissions = value } }
}
test('the original opaque KB identity and section survive tab navigation and route reuse', async t => {
  const f = await setup(t, { kb: '原始/知识库?#', section: 'templates' })
  assert.equal(f.vm.kbId, '原始/知识库?#'); assert.equal(f.vm.section, 'templates')
  f.vm.section = 'settings'; await flush()
  assert.deepEqual(f.replacements, [{ query: { section: 'settings', keep: 'retained' } }])
  f.route.query.section = 'templates'; await flush(); assert.equal(f.vm.section, 'templates'); assert.equal(f.replacements.length, 1)
  f.route.params.kbId = 'two'; await flush(); assert.equal(f.vm.kbId, 'two'); assert.equal(f.vm.bases[0].id, 'two')
})
test('policy and template editors require KB management and clear stale permissions during refresh failures', async t => {
  const f = await setup(t, { permissions: async () => profile('one', 'write') })
  assert.equal(f.vm.access.write, true); assert.equal(f.vm.access.manage, false)
  assert.match(readFileSync(file, 'utf8'), /ContextDBTemplates[^>]+:can-edit="access\.manage"/)
  f.setPermissions(async () => profile('one')); await f.vm.load(); assert.equal(f.vm.access.manage, true)
  let fail!: (error: Error) => void
  f.setPermissions(() => new Promise((_, reject) => { fail = reject }))
  const pending = f.vm.load(); assert.equal(f.vm.profile, null); assert.equal(f.vm.access.manage, false)
  fail(new Error('permissions unavailable')); await pending
  assert.equal(f.vm.access.manage, false); assert.equal(f.vm.error, 'permissions unavailable')
})
test('late reads from a previous library cannot restore its list or permissions', async t => {
  let oldLibraries!: (value: any) => void, oldPermissions!: (value: any) => void, lists = 0, permissions = 0
  const f = await setup(t, {
    libraries: () => ++lists === 1 ? new Promise(resolve => { oldLibraries = resolve }) : Promise.resolve({ data: [{ id: 'two', name: 'current' }] }),
    permissions: () => ++permissions === 1 ? new Promise(resolve => { oldPermissions = resolve }) : Promise.resolve(profile('two')),
  })
  f.route.params.kbId = 'two'; await flush(); assert.equal(f.vm.access.manage, true)
  oldLibraries({ data: [{ id: 'one', name: 'old' }] }); oldPermissions(profile('one')); await flush()
  assert.equal(f.vm.bases[0].id, 'two'); assert.equal(f.vm.profile.knowledge_base_permissions[0].knowledge_base_id, 'two')
})
test('local read-only roles remain read-only even with a remote administrator profile', async t => {
  const f = await setup(t, { contributor: false, permissions: async () => ({ member: { role: 'owner', status: 'active' } }) })
  assert.equal(f.vm.access.manage, false); assert.equal(f.vm.access.write, false)
})
