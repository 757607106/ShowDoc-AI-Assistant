import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { runInNewContext } from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'

const source = readFileSync(new URL('./RetrievalSettings.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const script = compileScript(descriptor, { id: 'retrieval-settings-test' }).content
const compiled = ts.transpileModule(script, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText

const baseConfig = {
  top_k: 8,
  similarity_threshold: 0.55,
  vector_weight: 0.65,
  query_rewrite: false,
}

type SettingsState = {
  localConfig: Record<string, unknown>
  handleParamChange: () => void
}

async function editConfig(
  config: Record<string, unknown>,
  edit: (state: SettingsState) => void,
  canEdit = true,
) {
  let mounted: (() => Promise<void>) | undefined
  const timers = new Map<number, () => void>()
  let timerID = 0
  const setTimeout = (callback: () => void) => {
    timers.set(++timerID, callback)
    return timerID
  }
  const clearTimeout = (id: number) => timers.delete(id)
  const writes: Record<string, unknown>[] = []
  const mocks: Record<string, unknown> = {
    // 这组序列化测试直接执行 setup；卸载行为由真实挂载的自动保存测试覆盖。
    vue: { ...vue, onMounted: (callback: () => Promise<void>) => { mounted = callback }, onUnmounted() {} },
    'tdesign-vue-next': { MessagePlugin: { success() {}, error() {} } },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => canEdit }) },
    '@/api/retrieval': {
      getTenantRetrievalConfig: async () => ({ data: config }),
      updateTenantRetrievalConfig: async (body: Record<string, unknown>) => {
        // Exercise the JSON serialization used for the PUT request.
        writes.push(JSON.parse(JSON.stringify(body)))
        return { data: body }
      },
    },
  }
  const sandbox = {
    exports: {} as { default: { setup: (props: object, ctx: object) => SettingsState } },
    require: (name: string) => {
      assert.ok(name in mocks, `Unexpected component import: ${name}`)
      return mocks[name]
    },
    console, setTimeout, clearTimeout, window: { setTimeout, clearTimeout },
  }
  runInNewContext(compiled, sandbox)
  const state = sandbox.exports.default.setup({}, { expose() {} })
  assert.ok(mounted)
  await mounted()
  assert.equal(writes.length, 0, 'loading the config must not save it')
  for (const [id, callback] of timers) {
    timers.delete(id)
    callback()
  }
  edit(state)
  for (const [id, callback] of timers) {
    timers.delete(id)
    callback()
  }
  await Promise.resolve()
  return writes
}

test('editing Top K preserves the other ContextDB query parameters in the serialized PUT body', async () => {
  const writes = await editConfig(baseConfig, state => {
    state.localConfig.top_k = 5
    state.handleParamChange()
  })
  assert.equal(writes.length, 1)
  assert.deepEqual(writes[0], { ...baseConfig, top_k: 5 })
})

for (const [field, value] of [
  ['similarity_threshold', 0.25],
  ['vector_weight', 0.45],
] as const) {
  test(`editing ${field} saves the new value and preserves the other settings`, async () => {
    const writes = await editConfig(baseConfig, state => {
      state.localConfig[field] = value
      state.handleParamChange()
    })
    assert.deepEqual(writes, [{ ...baseConfig, [field]: value }])
  })
}

test('toggling query rewrite saves the new value and preserves the other settings', async () => {
  const writes = await editConfig(baseConfig, state => {
    state.localConfig.query_rewrite = true
    state.handleParamChange()
  })
  assert.deepEqual(writes, [{ ...baseConfig, query_rewrite: true }])
})

test('a partial server response falls back to the platform defaults for missing keys', async () => {
  const writes = await editConfig({ top_k: 7 }, state => {
    state.localConfig.top_k = 3
    state.handleParamChange()
  })
  assert.deepEqual(writes[0], {
    top_k: 3,
    similarity_threshold: 0.6,
    vector_weight: 0.7,
    query_rewrite: true,
  })
})

test('non-admins cannot change retrieval configuration', async () => {
  const writes = await editConfig(baseConfig, state => {
    state.localConfig.top_k = 3
    state.handleParamChange()
  }, false)
  assert.deepEqual(writes, [])
})
