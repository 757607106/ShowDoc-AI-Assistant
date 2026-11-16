import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import { computed, reactive } from 'vue'

const source = readFileSync(new URL('./index.vue', import.meta.url), 'utf8')
const start = source.indexOf('const contextdbSettings = computed(')
const end = source.indexOf('let ismask =', start)
assert.ok(start >= 0 && end > start)

function settingsChoice(name: string, section?: string, contextdb = true) {
  const route = reactive({ name, query: { section } })
  const uiStore = reactive({ settingsInitialSection: null as string | null })
  const choice = runInNewContext(source.slice(start, end) + '\ncontextdbSettings', {
    computed, route, uiStore, IS_CONTEXTDB: contextdb,
  })
  return { route, uiStore, choice }
}

test('knowledge governance retains its approved settings shell and existing bookmarks', () => {
  for (const name of ['settings', 'home', 'collect', 'tasks', 'releases', 'governance',
    'knowledgeBaseList', 'knowledgeBaseDetail', 'knowledgeSpaceDetail']) {
    assert.equal(settingsChoice(name).choice.value, true, name)
  }
  for (const section of ['account', 'members', 'permissions', 'runtime']) {
    assert.equal(settingsChoice('settings', section).choice.value, true, section)
  }
})

test('Agent and chat use upstream Settings, including explicit requests from knowledge pages', () => {
  for (const name of ['chat', 'globalCreatChat', 'agentList', 'toolbox', 'artifactLibrary']) {
    assert.equal(settingsChoice(name).choice.value, false, name)
  }
  const f = settingsChoice('knowledgeBaseDetail')
  f.uiStore.settingsInitialSection = 'models'
  assert.equal(f.choice.value, false)
  f.uiStore.settingsInitialSection = 'sandbox'
  assert.equal(f.choice.value, false)
  f.uiStore.settingsInitialSection = 'permissions'
  assert.equal(f.choice.value, true)
  assert.equal(settingsChoice('settings', 'models').choice.value, false)
  assert.equal(settingsChoice('settings', 'sandbox').choice.value, false)
  assert.equal(settingsChoice('knowledgeBaseDetail', undefined, false).choice.value, false)
})

test('platform mounts the official panel without redirecting assistant requests to ordinary chat', () => {
  assert.match(source, /import AssistantPanel from '@\/components\/assistant\/AssistantPanel\.vue'/)
  assert.match(source, /<AssistantPanel\s*\/>/)
  assert.doesNotMatch(source, /assistant\.takePendingRequest\(\)/)
})
