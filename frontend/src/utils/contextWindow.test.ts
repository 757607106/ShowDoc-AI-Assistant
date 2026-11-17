import assert from 'node:assert/strict'
import test from 'node:test'

import {
  effectiveContextWindow,
  formatContextWindow,
  formatTokenCount,
  isUnknownContextWindow,
  modelContextWindow,
  modelHasContextWindow,
} from './contextWindow.ts'

test('unknown context windows remain unknown', () => {
  for (const value of [undefined, null, 0, -1, NaN, Infinity]) {
    assert.equal(effectiveContextWindow(value), null)
    assert.equal(formatContextWindow(value, 'Unknown'), 'Unknown')
    assert.equal(isUnknownContextWindow(value), true)
  }
  assert.equal(effectiveContextWindow(256000), 256000)
})

test('read-only limits prefer resolved capabilities while preserving raw editor values', () => {
  const model = { parameters: { context_window: 32768, spec: { context_window: 65536 } },
    capabilities: { context_window: 65536 } } as Parameters<typeof modelContextWindow>[0]
  assert.equal(modelContextWindow(model), 65536)
  assert.equal(formatContextWindow(modelContextWindow(model)), '64K')
  assert.equal(model?.parameters.context_window, 32768)
  assert.equal(modelContextWindow({ parameters: { context_window: 32768, spec: { context_window: 65536 } } }), 65536)
  assert.equal(modelContextWindow({ parameters: { context_window: 32768 } }), 32768)
  assert.equal(modelContextWindow({ parameters: {} }), null)
})

test('formatTokenCount uses K/M for round thousands', () => {
  assert.equal(formatTokenCount(128000), '128K')
  assert.equal(formatTokenCount(200000), '200K')
  assert.equal(formatTokenCount(131072), '128K')
  assert.equal(formatTokenCount(1_000_000), '1M')
  assert.equal(formatTokenCount(1048576), '1M')
  assert.equal(formatTokenCount(8192), '8K')
})

test('formatContextWindow uses a neutral placeholder when unset', () => {
  assert.equal(formatContextWindow(undefined), '—')
  assert.equal(formatContextWindow(128000), '128K')
})

test('modelHasContextWindow is chat and VLM only', () => {
  assert.equal(modelHasContextWindow('KnowledgeQA'), true)
  assert.equal(modelHasContextWindow('VLLM'), true)
  assert.equal(modelHasContextWindow('chat'), true)
  assert.equal(modelHasContextWindow('Embedding'), false)
  assert.equal(modelHasContextWindow('Rerank'), false)
  assert.equal(isUnknownContextWindow(0), true)
  assert.equal(isUnknownContextWindow(200000), false)
})
