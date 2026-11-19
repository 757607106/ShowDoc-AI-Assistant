import assert from 'node:assert/strict'
import test from 'node:test'
import { isDefaultModelForType, modelSupportsType, selectInitialModelId } from './modelDefaults'

test('creation picks independent vision, chat and ASR defaults', () => {
  const models = [
    { id: 'chat', type: 'KnowledgeQA', is_default: true, parameters: { supports_vision: true } },
    { id: 'vision', type: 'KnowledgeQA', default_for: ['VLLM'], parameters: { supports_vision: true } },
    { id: 'asr-first', type: 'ASR' },
    { id: 'asr-default', type: 'ASR', is_default: true },
  ]
  assert.equal(selectInitialModelId(models, 'KnowledgeQA'), 'chat')
  assert.equal(selectInitialModelId(models, 'VLLM'), 'vision')
  assert.equal(selectInitialModelId(models, 'ASR'), 'asr-default')
  assert.equal(isDefaultModelForType(models[0], 'VLLM'), false)
  assert.equal(isDefaultModelForType(models[1], 'VLLM'), true)
  assert.equal(isDefaultModelForType(models[1], 'KnowledgeQA'), false)
})

test('vision fallback prefers a native default and skips unavailable models', () => {
  const models = [
    { id: 'chat', type: 'KnowledgeQA', is_default: true, parameters: { supports_vision: true } },
    { id: 'inactive', type: 'VLLM', default_for: ['VLLM'], status: 'downloading' },
    { id: 'native', type: 'VLLM', is_default: true },
  ]
  assert.equal(selectInitialModelId(models, 'VLLM'), 'native')
  assert.equal(selectInitialModelId(models.slice(0, 2), 'VLLM'), 'chat')
  assert.equal(selectInitialModelId(models, 'ASR'), null)
})

test('declared image input takes precedence over visual type or the legacy flag', () => {
  const text = { capabilities: { input: ['text'] }, parameters: { supports_vision: true }, default_for: ['VLLM'] }
  const invalid = [{ ...text, id: 'text-chat', type: 'KnowledgeQA' }, { ...text, id: 'text-vllm', type: 'VLLM' }]
  const image = { id: 'vision-chat', capabilities: { input: ['text', 'image'] } }
  assert.equal(selectInitialModelId(invalid, 'VLLM'), null)
  assert.equal(selectInitialModelId([...invalid, { ...image, type: 'KnowledgeQA' }], 'VLLM'), 'vision-chat')
  assert.equal(modelSupportsType({ ...image, type: 'Embedding' }, 'VLLM'), false)
})
