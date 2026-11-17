import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import { effectScope, nextTick, ref, watch } from 'vue'

const source = readFileSync(new URL('./AgentEditorModal.vue', import.meta.url), 'utf8')

test('editing an agent closes the editor after a successful save', () => {
  assert.match(
    source,
    /await updateAgent\(formData\.value\.id, payload\);\s*MessagePlugin\.success\(t\('agent\.messages\.updated'\)\);\s*emit\('success'\);\s*handleClose\(\);/
  )
})

test('the first successful create stays open for further agent configuration', () => {
  const createBranch = source.match(
    /if \(editorMode\.value === 'create'\) \{([\s\S]*?)^\s{4}\} else \{/m
  )?.[1]

  assert.ok(createBranch, 'expected to find the create branch')
  assert.doesNotMatch(createBranch, /handleClose\(\)/)
  assert.match(createBranch, /savedAgent\.value = created;/)
})

test('save button labels distinguish create from save-and-close', () => {
  assert.match(
    source,
    /const saveButtonLabel = computed\(\(\) =>\s*editorMode\.value === 'create'\s*\? t\('agent\.editor\.buttons\.create'\)\s*: t\('agent\.editor\.buttons\.saveAndClose'\)\s*\)/
  )
  assert.match(source, /saveButtonLabel/)
})

test('shows a post-create hint after the first successful save', () => {
  assert.match(source, /const isPostCreateSession = computed\(\(\) => !!savedAgent\.value\)/)
  assert.match(source, /settings-footer-note/)
  assert.match(source, /agent\.editor\.postCreateHint\.title/)
})

// Locate a settings row by the i18n key of its label and return the attributes
// that sit before class="setting-row" — i.e. whatever v-if guards that row.
// Anchoring on the label keeps these assertions stable across reformatting.
function settingRowGuard(labelKey) {
  const key = labelKey.replace(/\./g, '\\.')
  const row = source.match(
    new RegExp(
      `<div([^>]*)class="setting-row">\\s*<div class="setting-info">\\s*<label>\\{\\{ \\$t\\('${key}'\\) \\}\\}`
    )
  )
  assert.ok(row, `expected to find the ${labelKey} row`)
  return row[1]
}

test('legacy conversation settings are unavailable in ContextDB mode', () => {
  assert.match(source, /v-if="!IS_CONTEXTDB" v-show="currentSection === 'conversation'"/)
  assert.match(source, /if \(!IS_CONTEXTDB\) items\.push\(\{ key: 'conversation'/)
})

test('history turns stays hidden in smart-reasoning mode', () => {
  // The agent path sizes history by the context window and never reads
  // history_turns (session_agent_qa.go -> LoadAgentHistory), so an input there
  // would change nothing. KnowledgeQA still caps its history by it.
  const guard = settingRowGuard('agent.editor.historyTurns')
  assert.match(guard, /v-if="usesLocalRag && formData\.config\.multi_turn_enabled"/)
  assert.match(source, /const usesLocalRag = computed\(\(\) => !IS_CONTEXTDB && !isAgentMode\.value\)/)
})

test('multi-turn switch stays hidden in smart-reasoning mode', () => {
  // CustomAgent.EnsureDefaults pins MultiTurnEnabled to true for smart-reasoning,
  // so an editable switch would silently revert after save.
  const guard = settingRowGuard('agent.editor.multiTurn')
  assert.match(guard, /v-if="usesLocalRag"/)
})

test('query rewrite stays hidden in smart-reasoning mode', () => {
  // enable_rewrite is consumed by the KnowledgeQA pipeline only.
  const guard = settingRowGuard('agent.editor.enableRewrite')
  assert.match(guard, /usesLocalRag/)
})

test('the section description matches what the mode actually shows', () => {
  // The default copy mentions query rewriting, which agent mode does not show.
  assert.match(source, /isAgentMode\.value\s*\?\s*t\('agentEditor\.desc\.conversationSectionAgent'\)/)
  assert.match(source, /<p class="section-description">\{\{ conversationSectionDesc \}\}<\/p>/)
})

test('history turns can be raised beyond the old 20 cap', () => {
  // KnowledgeQA history is capped by turns alone; 20 was too tight for the
  // windows current models have.
  const input = source.match(/<t-input-number v-model="formData\.config\.history_turns"[^>]*>/)
  assert.ok(input, 'expected to find the history turns input')
  assert.match(input[0], /:max="100"/)
})

test('native retention is read-only while the upstream Go switch remains knowledge-scoped', () => {
  const guard = settingRowGuard('agent.editor.retainRetrievalHistory')
  assert.match(guard, /v-if="IS_CONTEXTDB"/)
  assert.match(source, /v-else-if="isAgentMode && hasKnowledgeBase"/)
  assert.match(source, /setting-control"><code>\{\{ formData\.config\.retain_retrieval_history \}\}<\/code>/)
})

test('native skills and runtime remain available in both native modes', () => {
  assert.match(source, /v-show="currentSection === 'skills' && \(IS_CONTEXTDB \|\| isAgentMode\)"/)
  assert.match(source, /v-model="runtimeSelection"/)
  assert.match(source, /config\.enabled !== true/)
  assert.match(source, /sandbox: 'skills'/)
  assert.match(source, /pickItems\(\['multimodal', 'tools', 'mcp', 'skills', 'native'\]\)/)
})

test('native skills select directory names without installations, automatic pruning or progress drawers', () => {
  assert.match(source, /v-for="skill in selectableSkills"/)
  assert.match(source, /v-model="formData\.config\.selected_skills"/)
  assert.match(source, /await editorResources\.ensureSkillCatalog\(force\)/)
  assert.doesNotMatch(source, /installSkillCatalog|SandboxSkillsPanel|catalogSkillRows|pruneSelectedSkills|autoBindSoleSandbox/)
})

test('native editor binds structured output, policies and subagents to the isolated draft', () => {
  assert.match(source, /<NativeAgentConfig :config="formData\.config"/)
  assert.match(source, /@update:fields="updateNativeFields"/)
  assert.match(source, /validateNativeAgentConfig\(formData\.value\.config, deploymentCapabilities\.isSupported\('agents\.async'\)\)/)
  assert.match(source, /nativeDraft: nativeConfigDraft\.value/)
})

test('native agent editing does not mount retired sharing or channel requests', () => {
  assert.doesNotMatch(source, /AgentShareSettings|listEmbedChannels|listIMChannels|loadAgentIntegrationCounts/)
})

test('retrieval strategy settings are hidden in agent mode, where search_knowledge ignores them', () => {
  // search_knowledge reads the global retrieval configuration; showing the
  // per-agent thresholds in agent mode let users tune values with no effect.
  assert.match(source, /v-show="currentSection === 'retrieval' && hasKnowledgeBase && usesLocalRag"/)
  assert.match(source, /if \(hasKnowledgeBase\.value && usesLocalRag\.value\) \{\s*items\.push\(\{ key: 'retrieval'/)
  const modeWatch = source.match(/watch\(isAgentMode, \(isAgent\) => \{([\s\S]*?)^\}\);/m)?.[1] ?? ''
  assert.match(modeWatch, /isAgent && \([^)]*currentSection\.value === 'retrieval'/)
})

async function mcpFixture(t, config) {
  const init = source.match(/const initMcpSelectionMode = \(\) => \{[\s\S]*?^\};/m)?.[0]
  const start = source.indexOf('watch(mcpSelectionMode,')
  const end = source.indexOf('// 监听 Skills 选择模式变化', start)
  assert.ok(init && start >= 0 && end > start, 'expected MCP initialization and watchers')
  const state = {
    watch,
    formData: ref({ config: { mcp_selection_mode: 'none', mcp_services: [] } }),
    loadedConfig: structuredClone(config),
    mcpSelectionMode: ref('none'),
    isInitializing: ref(true),
  }
  const scope = effectScope()
  t.after(() => scope.stop())
  // Run the component's actual initialization and watchers with Vue's scheduler.
  scope.run(() => runInNewContext(`${source.slice(start, end)}\n${init}\nformData.value = { config: loadedConfig };\ninitMcpSelectionMode();`, state))
  await nextTick(() => { state.isInitializing.value = false })
  return state
}

test('legacy empty MCP config opens as all without rewriting persisted config', async t => {
  const config = { mcp_selection_mode: '', mcp_services: [] }
  const state = await mcpFixture(t, config)
  assert.equal(state.mcpSelectionMode.value, 'all')
  assert.deepEqual(state.formData.value.config, config)
})

test('MCP hydration preserves saved modes and legacy service lists', async t => {
  for (const mode of ['', 'none', 'selected', 'all']) {
    const config = { mcp_selection_mode: mode, mcp_services: ['service-a'] }
    const state = await mcpFixture(t, config)
    assert.equal(state.mcpSelectionMode.value, mode || 'selected')
    assert.deepEqual(state.formData.value.config, config)
  }
})

test('editing a legacy service list persists selected mode without toggling the radio', async t => {
  const state = await mcpFixture(t, { mcp_selection_mode: '', mcp_services: ['service-a'] })
  assert.equal(state.mcpSelectionMode.value, 'selected')
  // t-select replaces the v-model array while leaving the radio unchanged.
  state.formData.value.config.mcp_services = ['service-b']
  await nextTick()
  assert.deepEqual(state.formData.value.config, {
    mcp_selection_mode: 'selected', mcp_services: ['service-b'],
  })
})

test('clearing a legacy service list persists selected with no services', async t => {
  const state = await mcpFixture(t, { mcp_selection_mode: '', mcp_services: ['service-a'] })
  state.formData.value.config.mcp_services.splice(0)
  await nextTick()
  assert.equal(state.formData.value.config.mcp_selection_mode, 'selected')
  assert.deepEqual(state.formData.value.config.mcp_services, [])
})

test('switching MCP modes still clears lists only for all and none', async t => {
  const state = await mcpFixture(t, { mcp_selection_mode: '', mcp_services: ['service-a'] })
  for (const mode of ['all', 'selected', 'none']) {
    state.mcpSelectionMode.value = mode
    await nextTick()
    assert.equal(state.formData.value.config.mcp_selection_mode, mode)
    assert.equal(state.formData.value.config.mcp_services.length, 0)
    if (mode === 'selected') {
      state.formData.value.config.mcp_services = ['service-b']
      await nextTick()
      assert.deepEqual(state.formData.value.config.mcp_services, ['service-b'])
    }
  }
})
