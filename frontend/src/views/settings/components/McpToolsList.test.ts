import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { fixture, flush } from '../../../test-utils/vueFixture'

const here = dirname(fileURLToPath(import.meta.url))
const list = readFileSync(join(here, 'McpToolsList.vue'), 'utf8')
const panel = readFileSync(join(here, 'McpMetadataPanel.vue'), 'utf8')

test('tool details open in a popup with description, parameters and schema tabs', () => {
  assert.match(list, /t-popup/)
  assert.match(list, /mcp-tool-detail-popup/)
  assert.match(list, /mcpMetadata.details/)
  assert.match(list, /mcpMetadata.description/)
  assert.match(list, /schemaView === tab/)
  assert.match(list, /mcpSchemaParameters/)
  assert.doesNotMatch(list, /t-dialog/)
  assert.doesNotMatch(list, /hideParameters/)
})

test('server documentation sits on the snapshot row as a popup', () => {
  assert.match(panel, /mcp-server-docs-popup-overlay/)
  assert.match(panel, /snapshot-meta__docs/)
  assert.doesNotMatch(panel, /<details/)
  assert.match(panel, /metadata-body/)
})

test('MCP policy controls retain effective server flags after rejected changes', async t => {
  const writes: unknown[] = []
  const errors: string[] = []
  const policies = [
    { tool_name: 'read', enabled: true, require_approval: false },
    { tool_name: 'write', enabled: false, require_approval: true },
    { tool_name: 'unknown', enabled: false, require_approval: true },
  ]
  const save = async (field: string, serviceId: string, name: string, value: boolean) => {
    writes.push([field, serviceId, name, value])
    if (name !== 'read') throw new Error('Server rejected unavailable tool')
  }
  const { vm } = fixture(t).component(new URL('./McpToolsList.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error: (message: string) => errors.push(message) } },
    '@/utils/mcpToolDisplay': { mcpSchemaParameters: () => [] },
    '@/api/mcp-service': {
      getMCPToolApprovals: async () => policies,
      setMCPToolEnabled: (...args: [string, string, boolean]) => save('enabled', ...args),
      setMCPToolApproval: (...args: [string, string, boolean]) => save('approval', ...args),
    },
  }, { serviceId: 'service', tools: [
    { name: 'read', description: 'Read', readOnlyHint: true },
    { name: 'write', description: 'Write', readOnlyHint: false },
    { name: 'unknown', description: 'No annotation' },
  ] })
  await flush()
  for (const policy of policies) assert.deepEqual(vm.policy(policy.tool_name), policy)
  for (const name of ['write', 'unknown']) {
    await vm.savePolicy(name, 'enabled', true)
    await vm.savePolicy(name, 'require_approval', false)
    assert.equal(vm.policy(name).enabled, false)
    assert.equal(vm.policy(name).require_approval, true)
  }
  assert.deepEqual(writes, [
    ['enabled', 'service', 'write', true], ['approval', 'service', 'write', false],
    ['enabled', 'service', 'unknown', true], ['approval', 'service', 'unknown', false],
  ])
  assert.deepEqual(errors, Array(4).fill('mcpMetadata.policySaveFailed'))
  assert.equal(vm.busy.size, 0)
  await vm.savePolicy('read', 'enabled', false)
  await vm.savePolicy('read', 'require_approval', true)
  assert.deepEqual(writes.slice(-2), [['enabled', 'service', 'read', false], ['approval', 'service', 'read', true]])
  assert.equal(vm.policy('read').enabled, false)
  assert.equal(vm.policy('read').require_approval, true)
  assert.equal(errors.length, 4)
})
