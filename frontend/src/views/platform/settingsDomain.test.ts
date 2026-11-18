import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source=readFileSync(new URL('./index.vue',import.meta.url),'utf8')
const settings=readFileSync(new URL('../settings/Settings.vue',import.meta.url),'utf8')

test('every platform route uses one settings shell, including explicit bookmarks',()=>{
  assert.equal(source.match(/<Settings\s*\/>/g)?.length,1)
  assert.doesNotMatch(source,/<ContextDBSettings|contextdbSettings/)
  assert.match(settings,/<ContextDBSettings\s*\/>/)
})

test('platform retains the assistant bridge while shared knowledge context is migrated',()=>{
  assert.match(source,/import AssistantPanel from '@\/components\/assistant\/AssistantPanel\.vue'/)
  assert.match(source,/<AssistantPanel\s*\/>/)
  assert.doesNotMatch(source,/assistant\.takePendingRequest\(\)/)
})

test('user menu opens the personal workspace settings',()=>{
  const menu=readFileSync(new URL('../../components/UserMenu.vue',import.meta.url),'utf8')
  assert.match(menu,/<div v-if="!authStore\.isLiteMode"[^>]*@click="handleQuickNav\('tenant'\)"/)
})
