import assert from 'node:assert/strict'
import test from 'node:test'
import { agentRuntimeChanges, applyAgentRuntimeChanges } from './agentRuntimeConfig'
import type { AgentRuntimeDefaults, CustomAgentConfig } from '../api/agent'

const defaults: AgentRuntimeDefaults = {
  'quick-answer': { multi_turn_enabled: true, history_turns: 0, retain_retrieval_history: true, sandbox_config_id: 'state-backend' },
  'smart-reasoning': { multi_turn_enabled: true, history_turns: 5, retain_retrieval_history: true, sandbox_config_id: 'state-backend' },
}
const fields = ['enable_rewrite', 'enable_query_expansion', 'embedding_top_k', 'context_template', 'intent_prompts', 'fallback_strategy']

test('runtime adoption changes only values rejected by the current backend', () => {
  const supported: CustomAgentConfig = {
    agent_mode: 'quick-answer', max_iterations: 1, allowed_tools: [], multi_turn_enabled: true, history_turns: 0,
    retain_retrieval_history: true, enable_rewrite: false, enable_query_expansion: false,
    context_template: '', intent_prompts: {}, fallback_strategy: 'model',
  }
  assert.deepEqual(agentRuntimeChanges(supported, defaults, fields), [])
  const config = { ...supported, embedding_top_k: 0, retain_retrieval_history: false, fallback_strategy: 'fixed' as const }
  const changes = agentRuntimeChanges(config, defaults, fields)
  assert.deepEqual(changes.map(change => change.field), ['retain_retrieval_history', 'embedding_top_k', 'fallback_strategy'])
  assert.equal(config.retain_retrieval_history, false, 'the preview must not change the input')
  applyAgentRuntimeChanges(config, changes)
  assert.equal(config.retain_retrieval_history, true)
  assert.equal(config.embedding_top_k, undefined)
  assert.equal(config.fallback_strategy, undefined)
  assert.equal(config.max_iterations, 1)
  assert.deepEqual(config.allowed_tools, [])
  assert.equal(config.enable_rewrite, false)
})

test('missing canonical metadata never produces speculative replacement values', () => {
  const config: CustomAgentConfig = { agent_mode: 'quick-answer', retain_retrieval_history: false, history_turns: 5 }
  assert.deepEqual(agentRuntimeChanges(config, null, fields), [])
  assert.deepEqual(agentRuntimeChanges(config, defaults, null), [])
})

test('sandbox adoption preserves all supported values and only replaces unsupported historical values', () => {
  for (const sandbox_config_id of ['', 'state-backend', 'opensandbox-local']) {
    assert.deepEqual(agentRuntimeChanges({ agent_mode: 'quick-answer', sandbox_config_id }, defaults, fields), [])
  }
  assert.deepEqual(agentRuntimeChanges({ agent_mode: 'quick-answer', sandbox_config_id: 'docker' }, defaults, fields),
    [{ field: 'sandbox_config_id', before: 'docker', after: 'state-backend' }])
})
