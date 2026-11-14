import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture'
import { matchesResourceQuery } from '../../utils/resourceListSearch'

const file = new URL('./SandboxSettings.vue', import.meta.url)

test('session file settings retain archived configurations for viewing and search', async t => {
  const records = [
    { id: 'state-backend', name: 'Session files', sandbox_type: 'state' },
    { id: 'old-docker', name: 'Old analysis', description: 'Invoices', sandbox_type: 'docker' },
    { id: 'old-host', name: 'Old host', sandbox_type: 'host' },
  ]
  const { vm } = fixture(t).component(file, {
    '@/api/system': { listSandboxConfigs: async () => ({ data: records }) },
    '@/utils/resourceListSearch': { matchesResourceQuery },
  })
  await flush()
  assert.deepEqual(Array.from(vm.archived, (item: any) => item.id), ['old-docker', 'old-host'])
  vm.query = ' invoices '
  assert.deepEqual(Array.from(vm.archived, (item: any) => item.id), ['old-docker'])
  assert.equal(vm.records.length, 3, 'filtering must not remove saved configuration data')
  assert.equal(vm.loading, false)
  assert.equal(vm.error, '')
  const source = readFileSync(file, 'utf8')
  assert.match(source, /官方 StateBackend/)
  assert.match(source, /以下配置仅保留供查看/)
  assert.doesNotMatch(source, /SandboxConfigDrawer|SandboxSkillsPanel|createSandboxConfig|updateSandboxConfig|deleteSandboxConfig|installConfigSkill/)
})

test('failed archive reads are visible and an explicit retry can load them', async t => {
  let unavailable = true
  const { vm } = fixture(t).component(file, {
    '@/api/system': { listSandboxConfigs: async () => {
      if (unavailable) throw new Error('offline')
      return { data: [{ id: 'old', name: 'Archived', sandbox_type: 'docker' }] }
    } },
    '@/utils/resourceListSearch': { matchesResourceQuery },
  })
  await flush()
  assert.ok(vm.error)
  assert.equal(vm.loading, false)
  unavailable = false
  await vm.load()
  assert.equal(vm.error, '')
  assert.equal(vm.archived[0].id, 'old')
})
