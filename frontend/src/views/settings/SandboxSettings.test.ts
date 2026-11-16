import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture'
import { matchesResourceQuery } from '../../utils/resourceListSearch'

const file = new URL('./SandboxSettings.vue', import.meta.url)

const records = [
  { id: 'state-backend', name: 'Session files', sandbox_type: '', config: {} },
  { id: 'old-docker', name: 'Old analysis', description: 'Invoices', sandbox_type: 'docker', config: {} },
  { id: 'old-host', name: 'Old host', sandbox_type: 'host', config: {} },
]

async function setup(t: TestContext, initiallyUnavailable = false) {
  let unavailable = initiallyUnavailable
  const errors: string[] = [], successes: string[] = [], writes: unknown[] = []
  const { vm } = fixture(t).component(file, {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'vue-router': { useRouter: () => ({ push() {} }) },
    'tdesign-vue-next': { MessagePlugin: { error: (message: string) => errors.push(message), success: (message: string) => successes.push(message) } },
    '@/components/settings/useConfirmDelete': { useConfirmDelete: () => () => {} },
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({ ensureLoaded: async () => {}, isSupported: () => true }) },
    '@/api/chat/index': { getSession: async () => ({}) },
    '@/utils': { formatStringDate: (value: string) => value },
    '@/utils/docsUrl': { docsUrl: () => '' },
    '@/utils/resourceListSearch': { matchesResourceQuery },
    '@/api/system': {
      listSandboxConfigs: async () => {
        if (unavailable) throw new Error('offline')
        return { data: records, workspace_scripts_disabled: true }
      },
      NAMED_SANDBOX_BACKEND_TYPES: ['cube', 'e2b', 'docker'],
      isNamedSandboxBackend: (type: string) => ['cube', 'e2b', 'docker'].includes(type),
      parseSandboxConflict: () => null,
      setSandboxWorkspacePolicy: async (disabled: boolean) => { writes.push({ disabled }); throw new Error('Policy unsupported') },
      deleteSandboxConfig: async (id: string, force: boolean) => { writes.push({ deleted: id, force }); throw new Error('Deletion unsupported') },
    },
  })
  await flush()
  return { vm, errors, successes, writes, restoreConnection: () => { unavailable = false } }
}

test('official sandbox filters retain archived configurations and saved row identity', async t => {
  const { vm } = await setup(t)
  assert.deepEqual(Array.from(vm.filteredRecords, (item: any) => item.id), records.map(item => item.id))
  vm.searchQuery = ' invoices '
  assert.deepEqual(Array.from(vm.filteredRecords, (item: any) => item.id), ['old-docker'])
  assert.equal(vm.filteredRecords[0], vm.records[1])
  vm.searchQuery = ''
  vm.activeType = 'docker'
  assert.deepEqual(Array.from(vm.filteredRecords, (item: any) => item.id), ['old-docker'])
  assert.equal(vm.records.length, 3)
  assert.equal(vm.workspaceScriptsDisabled, true)
  assert.equal(vm.loading, false)
})

test('a failed sandbox list read is surfaced and can be explicitly retried', async t => {
  const f = await setup(t, true)
  assert.deepEqual(f.errors, ['offline'])
  assert.equal(f.vm.loading, false)
  assert.equal(f.vm.records.length, 0)
  f.restoreConnection()
  await f.vm.load()
  assert.equal(f.vm.records.length, 3)
  assert.equal(f.vm.loading, false)
})

test('unsupported sandbox policy and deletion requests keep the current state', async t => {
  const f = await setup(t)
  await f.vm.setScriptsDisabled(false)
  assert.equal(f.vm.workspaceScriptsDisabled, true)
  assert.equal(f.vm.policySaving, false)
  await f.vm.removeRecord(f.vm.records[1])
  assert.equal(f.vm.records.length, 3)
  assert.deepEqual(f.writes, [{ disabled: false }, { deleted: 'old-docker', force: false }])
  assert.deepEqual(f.errors, ['Policy unsupported', 'Deletion unsupported'])
  assert.deepEqual(f.successes, [])
})
