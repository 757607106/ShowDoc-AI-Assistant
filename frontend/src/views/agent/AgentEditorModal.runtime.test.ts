import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import test, { type TestContext } from 'node:test'
import { fileURLToPath } from 'node:url'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture'

const componentFile = new URL('./AgentEditorModal.vue', import.meta.url)
const sourceRoot = fileURLToPath(new URL('../../', import.meta.url))
const requestRequire = createRequire(import.meta.url)
const quickFields = ['enable_query_expansion', 'enable_rewrite', 'embedding_top_k', 'keyword_threshold',
  'vector_threshold', 'rerank_top_k', 'rerank_threshold', 'rerank_model_id', 'context_template',
  'context_template_id', 'fallback_prompt', 'fallback_response', 'intent_prompts', 'fallback_strategy']
const defaults = {
  'quick-answer': { agent_mode: 'quick-answer', max_iterations: 8, temperature: 0.3, allowed_tools: null,
    multi_turn_enabled: true, history_turns: 0, retain_retrieval_history: true, access_level: 'confirm', sandbox_config_id: 'state-backend' },
  'smart-reasoning': { agent_mode: 'smart-reasoning', max_iterations: 50, temperature: 0.7, allowed_tools: null,
    multi_turn_enabled: true, history_turns: 5, retain_retrieval_history: true, access_level: 'confirm', sandbox_config_id: 'state-backend' },
}

async function editorFixture(t: TestContext, agent?: any, runtimeDefaults: any = defaults, asyncSupported = true) {
  const fx = fixture(t)
  Object.assign(fx.window, { setInterval, clearInterval })
  const calls: Array<{ url: string; payload: any }> = []
  const messages: string[] = []
  const visibility: boolean[] = []
  let submitError: Error | null = null
  const submit = async (url: string, payload: any) => {
    calls.push({ url, payload: JSON.parse(JSON.stringify(payload)) })
    if (submitError) throw submitError
    return { data: { ...payload, id: agent?.id || 'created' } }
  }
  const model = { id: 'model', name: 'Model', type: 'KnowledgeQA', capabilities: { reasoning: false, input: ['text'] } }
  const resources = vue.reactive({
    agentTypePresets: [{ id: 'rag-qa', config: { allowed_tools: ['knowledge.search'], retain_retrieval_history: true } }],
    agentRuntimeDefaults: runtimeDefaults,
    unsupportedQuickFields: runtimeDefaults ? quickFields : null,
    agentTools: { tools: [{ name: 'knowledge.search', group: 'knowledge' }, { name: 'ask_user', group: 'interaction' }],
      default_tools: ['knowledge.search', 'ask_user'], switch_managed_tools: [] },
    promptTemplates: { system_prompt: [{ id: 'quick-prompt', content: 'Quick instructions', default: true }],
      agent_system_prompt: [], context_template: [{ id: 'context', content: 'Go context', default: true }],
      rewrite: [], fallback: [] },
    storageStatus: [], placeholders: null, tenantRetrievalConfig: null, mcpServices: [], skillCatalog: [],
    async prefetchAgentEditorDeps() {}, async ensureSkills() {}, async ensureSkillCatalog() {},
    async ensureAgentTypePresets() { this.agentRuntimeDefaults = defaults; this.unsupportedQuickFields = quickFields },
  })
  const chat = vue.reactive({ allModels: [model], rawKnowledgeBases: [{ id: 'kb', name: 'KB', capabilities: { wiki: true, vector: true } }],
    webSearchProviders: [], sandboxConfigs: [], async ensureModels() {}, async ensureKnowledgeBases() {},
    async ensureWebSearchProviders() {}, async ensureSandboxConfigs() {} })
  const overrides: Record<string, unknown> = {
    vue, 'vue-router': { useRouter: () => ({ push() {} }) },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key, locale: vue.ref('zh-CN') }) },
    'tdesign-vue-next': { MessagePlugin: { error: (message: string) => messages.push(message), warning() {}, success() {} } },
    '@/stores/ui': { useUIStore: () => vue.reactive({ showSettingsModal: false }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true, isLiteMode: false }) },
    '@/stores/organization': { useOrganizationStore: () => ({ sharedKnowledgeBases: [] }) },
    '@/stores/chatResources': { useChatResourcesStore: () => chat },
    '@/stores/editorResources': { useEditorResourcesStore: () => resources },
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({ isSupported: (key: string) => key !== 'agents.async' || asyncSupported, async ensureLoaded() {} }) },
    '@/api/embed': { listEmbedChannels: async () => ({ data: [] }) },
    '@/utils/clipboard': { copyWithToast() {} }, '@/utils/assistantDataChange': { useAssistantDataChange() {} },
    '@/composables/useAssistantPageContext': { useAssistantPageContext() {} },
    '@/composables/useModalShell': { useModalShell: () => ({ markClean() {}, requestClose() {} }) },
  }
  const request = { get: async () => ({ data: [] }), post: submit, put: submit, del: async () => ({}) }
  const cache = new Map<string, any>()
  function load(file: string): any {
    file = path.resolve(file)
    if (file === path.join(sourceRoot, 'utils/request.ts')) return request
    if (cache.has(file)) return cache.get(file)
    let source = readFileSync(file, 'utf8')
    if (file.endsWith('.vue')) source = compileScript(parse(source, { filename: file }).descriptor, { id: 'runtime-test' }).content
      .replace(/__expose\([^\n;]*\);?/g, '').replace('return __returned__', '__expose(__returned__); return __returned__')
    const result = fx.evaluate(source, overrides, name => {
      if (name.endsWith('.vue')) return { default: {} }
      if (name.startsWith('@/') || name.startsWith('.')) {
        const candidate = name.startsWith('@/') ? path.join(sourceRoot, name.slice(2)) : path.resolve(path.dirname(file), name)
        return load(existsSync(candidate + '.ts') ? candidate + '.ts' : path.join(candidate, 'index.ts'))
      }
      return requestRequire(name)
    })
    cache.set(file, result)
    return result
  }
  const component = load(fileURLToPath(componentFile)).default
  component.render = () => null
  const props = vue.reactive({ visible: false, mode: agent ? 'edit' : 'create', agent })
  const mounted = fx.mount(vue.defineComponent({ setup: () => () => vue.h(component, { ...props,
    'onUpdate:visible': (value: boolean) => visibility.push(value) }) }))
  props.visible = true
  await flush(); await flush()
  const state = mounted.vm.$.subTree.component.exposed
  assert.equal(state.editorInitializing.value, false)
  const config = () => state.formData.value.config
  state.formData.value.name ||= 'Agent'
  config().model_id ||= 'model'
  config().system_prompt ||= config().system_prompt_id ? '' : 'Custom instructions\n'
  return { state, config, calls, messages, resources, props, chat, visibility,
    failSave: (error: Error | null) => { submitError = error } }
}

test('new native quick mode saves canonical runtime settings without Go RAG defaults', async t => {
  const { state, config, calls } = await editorFixture(t)
  assert.equal(config().access_level, 'confirm')
  state.agentMode.value = 'quick-answer'
  await flush()
  await state.handleSave()
  assert.equal(calls.length, 1)
  const saved = calls[0]!.payload.config
  assert.equal(saved.max_iterations, 8)
  assert.equal(saved.allowed_tools, null)
  assert.equal(saved.multi_turn_enabled, true)
  assert.equal(saved.history_turns, 0)
  assert.equal(saved.retain_retrieval_history, true)
  for (const field of quickFields) assert.equal(saved[field], undefined, field)
  assert.equal(saved.model_id, 'model')
  assert.equal(saved.system_prompt, 'Custom instructions\n')
  assert.equal(state.showRerankModelField.value, false)
  assert.deepEqual(Array.from(state.promptNavItems.value, (item: any) => item.key), ['system'])
})

test('legacy quick values remain until explicit adoption and save preserves supported choices', async t => {
  const agent = { id: 'old', name: 'Legacy', is_builtin: false, config: {
    ...defaults['quick-answer'], max_iterations: 1, allowed_tools: [], model_id: 'model',
    kb_selection_mode: 'selected', knowledge_bases: ['kb'], system_prompt: ' User instructions\n',
    retain_retrieval_history: false, multi_turn_enabled: false, history_turns: 5,
    enable_rewrite: false, enable_query_expansion: true, embedding_top_k: 10, intent_prompts: {},
    context_template: 'Old context', context_template_id: 'context', fallback_strategy: 'model',
  }, config_issues: [{ field: 'retain_retrieval_history', message: 'Unsupported history' }] }
  const before = JSON.stringify(agent)
  const { state, config, calls, messages } = await editorFixture(t, agent)
  assert.equal(config().retain_retrieval_history, false)
  assert.equal(config().multi_turn_enabled, false)
  assert.equal(config().max_iterations, 1)
  assert.equal(config().context_template, 'Old context')
  assert.equal(calls.length, 0)
  await state.handleSave()
  assert.equal(calls.length, 0)
  assert.equal(messages.at(-1), 'agent.editor.nativeRuntime.resolveBeforeSave')
  const fields = Array.from(state.runtimeChanges.value, (item: any) => item.field)
  assert.ok(fields.includes('context_template_id'))
  assert.ok(!fields.includes('enable_rewrite'))
  assert.ok(!fields.includes('fallback_strategy'))
  state.adoptRuntimeSettings()
  assert.equal(config().retain_retrieval_history, true)
  assert.equal(config().history_turns, 0)
  assert.equal(config().context_template, undefined)
  assert.equal(calls.length, 0, 'adoption only changes the draft')
  assert.equal(JSON.stringify(agent), before, 'the incoming record remains unchanged')
  await state.handleSave()
  const saved = calls[0]!.payload.config
  assert.equal(saved.max_iterations, 1)
  assert.deepEqual(saved.allowed_tools, [])
  assert.deepEqual(saved.knowledge_bases, ['kb'])
  assert.equal(saved.system_prompt, ' User instructions\n')
  assert.equal(saved.enable_rewrite, false)
  assert.equal(saved.fallback_strategy, 'model')
  assert.deepEqual(saved.intent_prompts, {})
})

test('loaded quick null tools, prompt refs and copied configurations survive editing', async t => {
  const agent = { id: 'copied', name: 'Copy', is_builtin: false, config: {
    ...defaults['quick-answer'], model_id: 'model', allowed_tools: null,
    system_prompt: '', system_prompt_id: 'quick-prompt', kb_selection_mode: 'none',
  } }
  const { state, config, calls } = await editorFixture(t, agent)
  assert.equal(config().system_prompt, 'Quick instructions')
  await state.handleSave()
  assert.equal(calls[0]!.payload.config.allowed_tools, null)
  assert.equal(calls[0]!.payload.config.system_prompt, '')
  assert.equal(calls[0]!.payload.config.system_prompt_id, 'quick-prompt')
  assert.equal(calls[0]!.payload.config.context_template_id, undefined)
})

test('an unresolved template reference is preserved for backend validation instead of replaced by a default', async t => {
  const agent = { id: 'missing-template', name: 'Template', is_builtin: false, config: {
    ...defaults['quick-answer'], model_id: 'model', system_prompt: '', system_prompt_id: 'missing',
  } }
  const { state, config, calls } = await editorFixture(t, agent)
  assert.equal(config().system_prompt, '')
  await state.handleSave()
  assert.equal(calls[0]!.payload.config.system_prompt_id, 'missing')
  assert.equal(calls[0]!.payload.config.system_prompt, '')
})

for (const text of ['', '   ']) {
  test(`clearing a hydrated system prompt to ${JSON.stringify(text)} removes its reference and blocks save`, async t => {
    const agent = { id: 'clear-template', name: 'Template', is_builtin: false, config: {
      ...defaults['quick-answer'], model_id: 'model', system_prompt: '', system_prompt_id: 'quick-prompt',
    } }
    const { state, config, calls, messages } = await editorFixture(t, agent)
    assert.equal(config().system_prompt, 'Quick instructions')
    config().system_prompt = text
    state.handlePromptInput()
    await state.handleSave()
    assert.equal(config().system_prompt_id, undefined)
    assert.equal(calls.length, 0)
    assert.equal(messages.at(-1), 'agent.editor.systemPromptRequired')
  })
}

test('typing custom system instructions clears the old reference while selecting a template restores it', async t => {
  const agent = { id: 'edit-template', name: 'Template', is_builtin: false, config: {
    ...defaults['quick-answer'], model_id: 'model', system_prompt: '', system_prompt_id: 'quick-prompt',
  } }
  const { state, config, calls } = await editorFixture(t, agent)
  config().system_prompt = ' Exact custom instructions\n'
  state.handlePromptInput()
  assert.equal(config().system_prompt_id, undefined)
  await state.handleSave()
  assert.equal(calls[0]!.payload.config.system_prompt, ' Exact custom instructions\n')
  assert.equal(calls[0]!.payload.config.system_prompt_id, undefined)
  state.handleSystemPromptTemplateSelect({ id: 'quick-prompt', content: 'Quick instructions' })
  assert.equal(config().system_prompt_id, 'quick-prompt')
  await state.handleSave()
  assert.equal(calls[1]!.payload.config.system_prompt, '')
  assert.equal(calls[1]!.payload.config.system_prompt_id, 'quick-prompt')
})

test('missing defaults blocks save; retry permits canonical quick configuration', async t => {
  const { state, calls, messages } = await editorFixture(t, undefined, null)
  state.agentMode.value = 'quick-answer'
  await flush()
  await state.handleSave()
  assert.equal(calls.length, 0)
  assert.equal(messages.at(-1), 'agent.editor.nativeRuntime.defaultsUnavailable')
  await state.retryRuntimeDefaults()
  await state.handleSave()
  assert.equal(calls.length, 1)
  assert.equal(calls[0]!.payload.config.max_iterations, 8)
  assert.equal(calls[0]!.payload.config.history_turns, 0)
  assert.equal(calls[0]!.payload.config.allowed_tools, null)
  assert.equal(calls[0]!.payload.config.access_level, 'confirm')
  for (const field of quickFields) assert.equal(calls[0]!.payload.config[field], undefined, field)
})

test('retry preserves supported input entered while canonical defaults were unavailable', async t => {
  const { state, config, calls } = await editorFixture(t, undefined, null)
  config().system_prompt = 'Changed while loading\n'
  config().temperature = 0.4
  state.kbSelectionMode.value = 'selected'
  config().knowledge_bases = ['kb']
  state.keepAllowedToolsUnset.value = false
  state.agentMode.value = 'quick-answer'
  await flush()
  await state.retryRuntimeDefaults()
  await state.handleSave()
  const saved = calls[0]!.payload.config
  assert.equal(saved.system_prompt, 'Changed while loading\n')
  assert.equal(saved.temperature, 0.4)
  assert.deepEqual(saved.knowledge_bases, ['kb'])
  assert.deepEqual(saved.allowed_tools, [])
})

for (const mode of ['quick-answer', 'smart-reasoning'] as const) {
  test(`retry preserves a custom iteration limit entered while ${mode} defaults were unavailable`, async t => {
    const { state, config, calls } = await editorFixture(t, undefined, null)
    state.agentMode.value = mode
    await flush()
    config().max_iterations = 17
    await state.retryRuntimeDefaults()
    assert.equal(config().max_iterations, 17)
    assert.equal(config().multi_turn_enabled, true)
    assert.equal(config().history_turns, defaults[mode].history_turns)
    await state.handleSave()
    assert.equal(calls[0]!.payload.config.max_iterations, 17)
  })
}

test('retry retains edited incompatible history values until explicit adoption', async t => {
  const agent = { id: 'waiting', name: 'Waiting', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Preserve prompt',
  } }
  const { state, config, calls, messages } = await editorFixture(t, agent, null)
  state.agentMode.value = 'quick-answer'
  await flush()
  config().max_iterations = 17
  config().multi_turn_enabled = false
  config().history_turns = 7
  await state.retryRuntimeDefaults()
  assert.equal(config().max_iterations, 17)
  assert.equal(config().multi_turn_enabled, false)
  assert.equal(config().history_turns, 7)
  const fields = Array.from(state.runtimeChanges.value, (change: any) => change.field)
  assert.ok(fields.includes('multi_turn_enabled'))
  assert.ok(fields.includes('history_turns'))
  await state.handleSave()
  assert.equal(calls.length, 0)
  assert.equal(messages.at(-1), 'agent.editor.nativeRuntime.resolveBeforeSave')
  state.adoptRuntimeSettings()
  await state.handleSave()
  assert.equal(calls[0]!.payload.config.max_iterations, 17)
  assert.equal(calls[0]!.payload.config.multi_turn_enabled, true)
  assert.equal(calls[0]!.payload.config.history_turns, 0)
})

for (const mode of ['quick-answer', 'smart-reasoning'] as const) {
  test(`editing ${mode} after metadata failure never injects Go RAG defaults`, async t => {
    const originalConfig: any = {
      agent_mode: mode, model_id: 'model', system_prompt: 'Original instructions', allowed_tools: [],
      multi_turn_enabled: true, history_turns: defaults[mode].history_turns, retain_retrieval_history: true,
      kb_selection_mode: 'selected', knowledge_bases: ['kb'],
    }
    if (mode === 'smart-reasoning') Object.assign(originalConfig, { max_iterations: 17, access_level: 'read_only' })
    const agent = { id: `metadata-${mode}`, name: 'Metadata', is_builtin: false, config: originalConfig }
    const before = JSON.stringify(agent)
    const { state, config, calls } = await editorFixture(t, agent, null)
    for (const field of quickFields) assert.equal(Object.hasOwn(config(), field), false, `initial ${field}`)
    assert.equal(config().max_iterations, originalConfig.max_iterations)
    assert.equal(config().access_level, originalConfig.access_level)
    config().system_prompt = 'Edited while waiting\n'
    config().temperature = 0.4
    await state.retryRuntimeDefaults()
    for (const field of quickFields) assert.equal(Object.hasOwn(config(), field), false, `retry ${field}`)
    assert.equal(state.runtimeChanges.value.length, 0)
    assert.equal(config().max_iterations, originalConfig.max_iterations ?? defaults[mode].max_iterations)
    assert.equal(config().access_level, originalConfig.access_level ?? 'confirm')
    assert.equal(JSON.stringify(agent), before)
    await state.handleSave()
    const saved = calls[0]!.payload.config
    for (const field of quickFields) assert.equal(Object.hasOwn(saved, field), false, `saved ${field}`)
    assert.equal(saved.max_iterations, originalConfig.max_iterations ?? defaults[mode].max_iterations)
    assert.equal(saved.access_level, originalConfig.access_level ?? 'confirm')
    assert.equal(saved.system_prompt, 'Edited while waiting\n')
    assert.equal(saved.temperature, 0.4)
    assert.deepEqual(saved.allowed_tools, [])
    assert.deepEqual(saved.knowledge_bases, ['kb'])
  })
}

test('metadata retry preserves incompatible stored quick values for explicit adoption', async t => {
  const agent = { id: 'stored-pipeline', name: 'Stored pipeline', is_builtin: false, config: {
    ...defaults['quick-answer'], model_id: 'model', system_prompt: 'Keep prompt', embedding_top_k: 12,
  } }
  const { state, config, calls } = await editorFixture(t, agent, null)
  await state.retryRuntimeDefaults()
  assert.equal(config().embedding_top_k, 12)
  assert.ok(state.runtimeChanges.value.some((change: any) => change.field === 'embedding_top_k'))
  await state.handleSave()
  assert.equal(calls.length, 0)
})

test('native mode and knowledge scope changes preserve explicit and retired tools without seeding', async t => {
  const agent = { id: 'custom', name: 'Custom', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', allowed_tools: [], system_prompt: 'Custom', kb_selection_mode: 'none',
  } }
  const { state, config } = await editorFixture(t, agent)
  state.agentMode.value = 'quick-answer'; await flush()
  state.agentMode.value = 'smart-reasoning'; await flush()
  state.kbSelectionMode.value = 'all'; await flush()
  assert.deepEqual(Array.from(config().allowed_tools), [])
  config().allowed_tools = ['wiki_read_page']
  state.agentMode.value = 'quick-answer'; await flush()
  assert.deepEqual(Array.from(config().allowed_tools), ['wiki_read_page'])
})

test('native fields round trip with distinct inherited and empty child selections and legacy consumers', async t => {
  const native = {
    response_format: { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] },
    permissions: [{ operations: ['write'], paths: ['/state/private/**'], mode: 'deny' }],
    interrupt_on: { execute: { allowed_decisions: ['approve', 'reject'], description: 'Confirm execution' } },
    subagents: [
      { name: 'research', description: 'Research', allowed_tools: null, selected_skills: [] },
      { name: 'review', description: 'Review', allowed_tools: [], selected_skills: null,
        execution_mode: 'async', mode: 'fork', update_strategy: 'enqueue',
        response_format: null, permissions: [{ operations: ['read'], paths: ['/state/private/**'], mode: 'deny' }] },
    ],
  }
  const legacy = { vlm_model_id: 'old-vision', utility_model_id: 'old-title', asr_model_id: 'old-asr',
    audio_upload_enabled: true, attachment_ocr_max_pages: 9, image_storage_provider: 'old-storage',
    question_suggestions: { starters: { items: [' Keep spacing '] } },
    skills_selection_mode: 'selected', selected_skills: ['unlisted-skill'] }
  const agent = { id: 'native', name: 'Native', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Keep prompt', ...native, ...legacy,
  } }
  const before = JSON.stringify(agent)
  const { state, calls, config } = await editorFixture(t, agent)
  assert.equal(config().sandbox_config_id, 'state-backend')
  assert.equal(state.runtimeSelection.value, '')
  assert.deepEqual(Array.from(state.selectableSkills.value, (skill: any) => skill.name), ['unlisted-skill'])
  await state.handleSave()
  assert.equal(calls.length, 1)
  for (const [key, value] of Object.entries({ ...native, ...legacy })) assert.deepEqual(calls[0]!.payload.config[key], value, key)
  assert.equal(JSON.stringify(agent), before)
})

test('an unavailable async service blocks save and leaves stored children intact for explicit repair', async t => {
  const agent = { id: 'async-offline', name: 'Background', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Original',
    subagents: [{ name: 'research', description: 'Research', execution_mode: 'async' }],
  } };
  const before = JSON.stringify(agent);
  const { state, config, calls, messages } = await editorFixture(t, agent, defaults, false);
  await state.handleSave();
  assert.equal(calls.length, 0);
  assert.match(messages.at(-1)!, /nativeAgent.asyncUnavailable/);
  assert.equal(config().subagents[0].execution_mode, 'async');
  assert.equal(JSON.stringify(agent), before);
  config().subagents[0].execution_mode = 'sync';
  await state.handleSave();
  assert.equal(calls.length, 1);
  assert.equal(calls[0]!.payload.config.subagents[0].execution_mode, 'sync');
});

test('invalid native schema and child configuration blocks save before any request', async t => {
  const { state, config, calls, messages } = await editorFixture(t)
  for (const response_format of [[], { type: 'unknown' }, { $ref: 'https://external.invalid/schema' }]) {
    config().response_format = response_format
    await state.handleSave()
    assert.equal(calls.length, 0)
    assert.equal(state.currentSection.value, 'native')
    assert.match(messages.at(-1)!, /nativeAgent.invalidSchema/)
  }
  config().response_format = null
  config().subagents = [{ name: 'same', description: 'One' }, { name: 'same', description: 'Two' }]
  await state.handleSave()
  assert.match(messages.at(-1)!, /nativeAgent.invalidChildName/)
  state.nativeConfigError.value = { field: 'permissions', key: 'nativeAgent.invalidJson' }
  config().subagents = []
  await state.handleSave()
  assert.equal(calls.length, 0)
  assert.match(messages.at(-1)!, /nativeAgent.invalidJson/)
})

test('cancel closes an edited native draft without a save or mutation to the incoming agent', async t => {
  const agent = { id: 'cancel-native', name: 'Native', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Original',
    subagents: [{ name: 'review', description: 'Original review', allowed_tools: null, selected_skills: [] }],
  } }
  const before = JSON.stringify(agent)
  const { state, calls, config, visibility } = await editorFixture(t, agent)
  config().subagents[0].description = 'Draft only'
  state.updateNativeFields({ response_format: { type: 'object' }, permissions: [] })
  state.nativeConfigDraft.value = '{ invalid JSON'
  state.handleClose()
  assert.equal(calls.length, 0)
  assert.equal(JSON.stringify(agent), before)
  assert.equal(visibility.at(-1), false)
})

test('a full schema rejection from the server retains the native draft for correction', async t => {
  const agent = { id: 'server-schema', name: 'Native', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Original',
  } }
  const { state, config, calls, messages, visibility, failSave } = await editorFixture(t, agent)
  config().response_format = { type: 'object', properties: { answer: { type: 'invalid' } } }
  failSave(new Error('response_format must be a valid JSON Schema'))
  await state.handleSave()
  assert.equal(calls.length, 1)
  assert.equal(visibility.length, 0)
  assert.equal(config().response_format.properties.answer.type, 'invalid')
  assert.match(messages.at(-1)!, /valid JSON Schema/)
  config().response_format.properties.answer.type = 'string'
  failSave(null)
  await state.handleSave()
  assert.equal(calls.length, 2)
  assert.equal(visibility.at(-1), false)
})

test('native quick mode exposes native capabilities and accepts wiki knowledge without Go RAG constraints', async t => {
  const { state, chat, config } = await editorFixture(t)
  state.agentMode.value = 'quick-answer'
  state.kbOptions.value = [{ value: 'wiki-only', label: 'Wiki', capabilities: { wiki: true, vector: false, keyword: false } }]
  await flush()
  const nav = Array.from(state.navItems.value, (item: any) => item.key)
  for (const key of ['tools', 'mcp', 'skills', 'native']) assert.ok(nav.includes(key), key)
  for (const key of ['websearch', 'retrieval', 'suggestions', 'conversation']) assert.ok(!nav.includes(key), key)
  assert.equal(state.filteredKbOptionsForPreset.value[0].disabled, false)
  chat.sandboxConfigs = [
    { id: 'opensandbox-local', name: 'Local', enabled: true },
    { id: 'retired', name: 'Retired', enabled: false },
  ] as any
  assert.equal(state.runtimeOptions.value.find((item: any) => item.value === 'opensandbox-local').disabled, false)
  assert.equal(state.runtimeOptions.value.find((item: any) => item.value === 'retired').disabled, true)
  assert.equal(config().sandbox_config_id, 'state-backend', 'loading runtimes does not enable Shell')
  state.runtimeSelection.value = 'opensandbox-local'
  assert.equal(config().sandbox_config_id, 'opensandbox-local')
})

test('disabled catalog skills cannot be newly selected while saved unavailable names can be removed explicitly', async t => {
  const agent = { id: 'skills-boundary', name: 'Skills', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Original',
    skills_selection_mode: 'selected', selected_skills: ['disabled-saved', 'unknown-saved'],
  } }
  const { state, config } = await editorFixture(t, agent)
  state.skillCatalog.value = [
    { name: 'available', enabled: true }, { name: 'disabled-new', enabled: false },
    { name: 'disabled-saved', enabled: false },
  ]
  const rows = () => JSON.parse(JSON.stringify(state.selectableSkills.value))
  assert.deepEqual(rows().map((row: any) => row.name), ['available', 'disabled-saved', 'unknown-saved'])
  assert.deepEqual(rows().filter((row: any) => row.unavailable).map((row: any) => row.name), ['disabled-saved', 'unknown-saved'])
  assert.deepEqual(Array.from(config().selected_skills), ['disabled-saved', 'unknown-saved'])
  config().selected_skills = []
  await flush()
  assert.deepEqual(rows().map((row: any) => row.name), ['available'])
})

test('legacy unsupported web search and reflection can only be disabled through explicit adoption', async t => {
  const agent = { id: 'old-switches', name: 'Old switches', is_builtin: false, config: {
    ...defaults['smart-reasoning'], model_id: 'model', system_prompt: 'Keep prompt',
    web_search_enabled: true, reflection_enabled: true,
  }, config_issues: [
    { field: 'web_search_enabled', message: 'Unsupported web search' },
    { field: 'reflection_enabled', message: 'Unsupported reflection' },
  ] }
  const before = JSON.stringify(agent)
  const { state, config, calls } = await editorFixture(t, agent)
  assert.equal(config().web_search_enabled, true)
  assert.equal(config().reflection_enabled, true)
  state.agentMode.value = 'quick-answer'; await flush()
  assert.equal(config().web_search_enabled, true)
  assert.equal(config().reflection_enabled, true)
  state.agentMode.value = 'smart-reasoning'; await flush()
  await state.handleSave()
  assert.equal(calls.length, 0)
  assert.equal(state.runtimeAdoptLabel.value, 'agent.editor.nativeRuntime.adoptRuntime')
  assert.deepEqual(Array.from(state.runtimeChanges.value, (change: any) => [change.field, change.after]),
    [['web_search_enabled', false], ['reflection_enabled', false]])
  state.adoptRuntimeSettings()
  assert.equal(config().web_search_enabled, false)
  assert.equal(config().reflection_enabled, false)
  assert.equal(calls.length, 0)
  assert.equal(JSON.stringify(agent), before)
  await state.handleSave()
  assert.equal(calls[0]!.payload.config.web_search_enabled, false)
  assert.equal(calls[0]!.payload.config.reflection_enabled, false)
  assert.equal(calls[0]!.payload.config.system_prompt, 'Keep prompt')
})

test('quick mode offers explicit adoption when an unsupported sandbox is its only issue', async t => {
  const agent = { id: 'legacy-sandbox', name: 'Sandbox', is_builtin: false, config: {
    ...defaults['quick-answer'], model_id: 'model', system_prompt: 'Keep prompt', sandbox_config_id: 'docker',
    max_iterations: 17, allowed_tools: [], kb_selection_mode: 'selected', knowledge_bases: ['kb'],
  }, config_issues: [{ field: 'sandbox_config_id', message: 'Unsupported sandbox' }] }
  const before = JSON.stringify(agent)
  const { state, config, calls } = await editorFixture(t, agent)
  assert.equal(config().sandbox_config_id, 'docker')
  assert.deepEqual(Array.from(state.runtimeChanges.value, (change: any) => [change.field, change.before, change.after]),
    [['sandbox_config_id', 'docker', 'state-backend']])
  await state.handleSave()
  assert.equal(calls.length, 0)
  state.adoptRuntimeSettings()
  assert.equal(config().sandbox_config_id, 'state-backend')
  assert.equal(calls.length, 0)
  assert.equal(JSON.stringify(agent), before)
  await state.handleSave()
  assert.equal(calls.length, 1)
  assert.ok(['', 'state-backend'].includes(calls[0]!.payload.config.sandbox_config_id))
  assert.equal(calls[0]!.payload.config.max_iterations, 17)
  assert.deepEqual(calls[0]!.payload.config.allowed_tools, [])
  assert.deepEqual(calls[0]!.payload.config.knowledge_bases, ['kb'])
})
