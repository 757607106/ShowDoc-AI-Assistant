import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('./ModelSettings.vue', import.meta.url), 'utf8')
const save = source.slice(source.indexOf('const handleModelSave ='), source.indexOf('// 删除模型'))
const kind = source.slice(source.indexOf('function getModelType('), source.indexOf('// The assistant links here'))

async function saved(parameters: Record<string, unknown>) {
  const writes: any[] = []
  const exports: any = {}
  const currentModelType = { value: 'chat' }
  runInNewContext(ts.transpileModule(save + kind + '\nexports.save = handleModelSave', {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText, {
    exports, URL, console, currentModelType, editingModel: { value: { id: 'existing' } },
    t: (key: string) => key, MessagePlugin: { success() {} },
    updateModelAPI: async (id: string, payload: unknown) => { writes.push({ id, payload }) },
    createModel: async () => { throw new Error('Editing must update the existing row') },
    loadModels: async () => {},
  })
  await exports.save({ modelName: 'fixture', source: 'remote', baseUrl: 'https://model.invalid/v1', ...parameters })
  assert.equal(writes.length, 1)
  return JSON.parse(JSON.stringify(writes[0].payload.parameters))
}

test('clearing raw limits and the last request header sends explicit empty values', async () => {
  const parameters = await saved({ contextWindow: '', maxOutputTokens: null, maxConcurrency: 0, customHeaders: [] })
  assert.equal(parameters.context_window, 0)
  assert.equal(parameters.max_output_tokens, 0)
  assert.equal(parameters.max_concurrency, 0)
  assert.deepEqual(parameters.custom_headers, {})
  assert.equal('api_key' in parameters, false)
})

test('the editor exposes the upstream per-model background concurrency field', () => {
  const editor = readFileSync(new URL('../../components/ModelEditorDialog.vue', import.meta.url), 'utf8')
  assert.equal(editor.includes('v-model.number="formData.maxConcurrency"'), true)
})

test('explicit model limits and masked request headers survive the same save path', async () => {
  const parameters = await saved({ contextWindow: 64000, maxOutputTokens: 4096, maxConcurrency: 3,
    customHeaders: [{ key: ' X-Private ', value: ' ******** ' }] })
  assert.equal(parameters.context_window, 64000)
  assert.equal(parameters.max_output_tokens, 4096)
  assert.equal(parameters.max_concurrency, 3)
  assert.deepEqual(parameters.custom_headers, { 'X-Private': '********' })
})
