import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as pinia from 'pinia'
import * as vue from 'vue'
import { fixture } from '../test-utils/vueFixture'
import { createCachedResource } from './resourceCache'

test('agent preset cache preserves canonical metadata, reports failures and clears missing metadata', async t => {
  pinia.setActivePinia(pinia.createPinia())
  let failure = false
  let response: any = { data: [{ id: 'custom', config: null }],
    runtime_defaults: { 'quick-answer': { max_iterations: 8 }, 'smart-reasoning': { max_iterations: 50 } },
    unsupported_quick_fields: ['context_template'] }
  const fx = fixture(t)
  const { useEditorResourcesStore } = fx.evaluate(readFileSync(new URL('./editorResources.ts', import.meta.url), 'utf8'), {
    vue, pinia,
    '@/api/system': {}, '@/api/mcp-service': {}, '@/api/skill': {}, '@/api/retrieval': {},
    '@/api/agent': { getAgentTypePresets: async () => {
      if (failure) throw new Error('Unavailable')
      return response
    } },
    './storageEngineAccess': { isStorageConfigDenied: () => false },
    './resourceCache': { createCachedResource },
  })
  const store = useEditorResourcesStore()
  failure = true
  await assert.rejects(store.ensureAgentTypePresets(), /Unavailable/)
  assert.equal(store.agentRuntimeDefaults, null)
  failure = false
  await store.ensureAgentTypePresets()
  assert.equal(store.agentTypePresets[0].id, 'custom')
  assert.equal(store.agentRuntimeDefaults['quick-answer'].max_iterations, 8)
  assert.deepEqual(Array.from(store.unsupportedQuickFields), ['context_template'])
  response = { data: [] }
  await store.ensureAgentTypePresets(true)
  assert.equal(store.agentRuntimeDefaults, null)
  assert.equal(store.unsupportedQuickFields, null)
  response = { data: [], runtime_defaults: {}, unsupported_quick_fields: [] }
  await store.ensureAgentTypePresets()
  store.invalidate()
  assert.equal(store.agentRuntimeDefaults, null)
  assert.equal(store.unsupportedQuickFields, null)
})
