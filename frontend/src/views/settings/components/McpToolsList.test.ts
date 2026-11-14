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

test('MCP policy controls permit only tools explicitly marked read-only', async t => {
  const writes: unknown[] = []
  const { vm } = fixture(t).component(new URL('./McpToolsList.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error: assert.fail } },
    '@/utils/mcpToolDisplay': { mcpSchemaParameters: () => [] },
    '@/api/mcp-service': {
      getMCPToolApprovals: async () => [],
      setMCPToolEnabled: async (...args: unknown[]) => { writes.push(['enabled', ...args]) },
      setMCPToolApproval: async (...args: unknown[]) => { writes.push(['approval', ...args]) },
    },
  }, { serviceId: 'service', tools: [
    { name: 'read', description: 'Read', readOnlyHint: true },
    { name: 'write', description: 'Write', readOnlyHint: false },
    { name: 'unknown', description: 'No annotation' },
  ] })
  await flush()
  for (const name of ['write', 'unknown', 'nonexistent']) {
    await vm.savePolicy(name, 'enabled', true)
    await vm.savePolicy(name, 'require_approval', false)
  }
  assert.equal(writes.length, 0)
  await vm.savePolicy('read', 'enabled', false)
  await vm.savePolicy('read', 'require_approval', true)
  assert.deepEqual(writes, [['enabled', 'service', 'read', false], ['approval', 'service', 'read', true]])
  assert.equal(vm.policy('read').enabled, false)
  assert.equal(vm.policy('read').require_approval, true)
})
