import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import * as documentName from '../../utils/contextdbDocumentName.ts'

const source = readFileSync(new URL('./ContextDBGraphManagement.vue', import.meta.url), 'utf8')
const script = source.slice(source.indexOf('<script setup lang="ts">') + '<script setup lang="ts">'.length, source.indexOf('</script>'))
const compiled = ts.transpileModule(script + '\nexports.state = { props, items, total, page, keyword, mode, loading, error, editorOpen, editorLoading, saving, editError, kind, editingId, form, choices, endpointOptions, endpointLoading, endpointError, deleting, deleteError, removing, load, query, closeEditor, searchEndpoints, retainEndpoint, editEntity, editRelation, save, deleteEntity, deleteRelation, remove };', {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText

type Call = { method: string; path: string; data: Record<string, any> }
function fixture(handler?: (call: Call) => Promise<any>, contributor = true) {
  const calls: Call[] = [], events: any[] = [], cleanup: (() => void)[] = []
  const props = vue.reactive({ kbId: 'kb-a', active: true, documents: [] })
  const scope = vue.effectScope(), exports: { state?: any } = {}
  async function request(method: string, path: string, data: Record<string, any> = {}) {
    const call = { method, path, data }; calls.push(call)
    if (method === 'DELETE') data = Object.fromEntries(new URLSearchParams(path.split('?')[1]))
    if (handler) return handler(call)
    if (method === 'GET' && path === 'knowledge/entities') return { data: { entities: [{ entity_id: '中文ID', entity_name: '完整名称', entity_type: 'concept', description: '列表摘要' }], total: 1 } }
    if (method === 'GET' && path === 'knowledge/entities/detail') return { data: { entity_id: data.entity_id, entity_name: '完整名称', entity_type: 'concept', description: '完整描述', aliases: ['别名'], source_document_ids: ['doc-1'] } }
    if (method === 'GET') return { data: { relation_id: data.relation_id, source_entity_id: '中文ID', source_entity_name: '完整名称', target_entity_id: 'target', target_entity_name: '目标实体', relation_type: 'uses', weight: 0.7, description: '关系描述', keywords: ['关键词'] } }
    return { data: { knowledge_base_id: data.knowledge_base_id, [path.split('?')[0]!.endsWith('entities') ? 'entity_id' : 'relation_id']: data.entity_id || data.relation_id || 'new-id', deleted: true } }
  }
  const modules: Record<string, any> = {
    vue: { ...vue, onUnmounted: (fn: () => void) => cleanup.push(fn) },
    '@/api/contextdb': { nativeAPI: Object.fromEntries(['get', 'post', 'put', 'del'].map(method => [method, (path: string, data: any) => request(method === 'del' ? 'DELETE' : method.toUpperCase(), path, data)])) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => contributor }) },
    '@/utils/contextdbDocumentName': documentName,
  }
  scope.run(() => vm.runInNewContext(compiled, { exports, defineProps: () => props, defineEmits: () => (...args: any[]) => events.push(args), defineExpose() {}, URLSearchParams,
    require: (id: string) => { assert.ok(id in modules, `unexpected import ${id}`); return modules[id] }, console }))
  const flush = async () => { await vue.nextTick(); await new Promise(resolve => setImmediate(resolve)) }
  return { ...exports.state, calls, events, props, flush, dispose: () => { cleanup.forEach(fn => fn()); scope.stop() } }
}
const plain = (value: any) => JSON.parse(JSON.stringify(value))

test('entity search uses official kb_id, matching mode and 20-item pagination', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  f.keyword.value = ' 数据库 '; f.mode.value = 'semantic'; f.page.value = 3; await f.load()
  assert.deepEqual(plain(f.calls.at(-1)!.data), { kb_id: 'kb-a', keyword: '数据库', mode: 'semantic', page: 3, page_size: 20 })
  f.query(); await f.flush(); assert.equal(f.page.value, 1)
})

test('editing refetches full entity and only sends complete editable fields', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); await f.editEntity(f.items.value[0])
  assert.equal(f.form.value.description, '完整描述'); assert.deepEqual(plain(f.form.value.aliases), ['别名'])
  f.form.value.entity_name = ' 新名称 '; f.form.value.description = ''; f.form.value.aliases = []; await f.save()
  assert.deepEqual(plain(f.calls.find((call: Call) => call.method === 'PUT')!.data), { knowledge_base_id: 'kb-a', entity_id: '中文ID', entity_name: '新名称', entity_type: 'concept', description: '', aliases: [] })
  assert.equal(f.editorOpen.value, false)
  assert.deepEqual(plain(f.events[0]), ['changed', { kind: 'entity', id: '中文ID', deleted: false }])
})

test('entity validation rejects missing fields and excessive aliases before sending', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); await f.editEntity()
  await f.save(); assert.match(f.editError.value, /名称和实体类型/)
  f.form.value.entity_name = '实体'; f.form.value.entity_type = 'concept'; f.form.value.aliases = Array.from({ length: 21 }, (_, i) => `alias-${i}`)
  await f.save(); assert.match(f.editError.value, /20/); assert.equal(f.calls.filter((call: Call) => call.method !== 'GET').length, 0)
  f.form.value.aliases = [' 别名 ', '别名', '']; await f.save()
  assert.deepEqual(plain(f.calls.find((call: Call) => call.method === 'POST')!.data.aliases), ['别名'])
})

test('relation create sends endpoints, update leaves endpoints immutable and retains decimal weight', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); await f.editRelation(undefined, { entity_id: '中文ID', entity_name: '来源' })
  f.form.value.target_entity_id = 'target'; f.form.value.relation_type = 'uses'; f.form.value.weight = 0.65; await f.save()
  assert.deepEqual(plain(f.calls.find((call: Call) => call.method === 'POST')!.data), { knowledge_base_id: 'kb-a', source_entity_id: '中文ID', target_entity_id: 'target', relation_type: 'uses', description: '', keywords: [], weight: 0.65 })
  await f.editRelation({ relation_id: 'relation-1' }); f.form.value.keywords = []; f.form.value.description = ''; await f.save()
  assert.deepEqual(plain(f.calls.find((call: Call) => call.method === 'PUT')!.data), { knowledge_base_id: 'kb-a', relation_id: 'relation-1', relation_type: 'uses', description: '', keywords: [], weight: 0.7 })
})

test('relations reject missing endpoints and invalid weights before mutating', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); await f.editRelation()
  f.form.value.relation_type = 'uses'; await f.save(); assert.match(f.editError.value, /起点实体和终点实体/)
  f.form.value.source_entity_id = 'source'; f.form.value.target_entity_id = 'target'
  for (const weight of [-1, 1.1, NaN, null, '0.5']) { f.form.value.weight = weight; await f.save(); assert.match(f.editError.value, /0 到 1/) }
  assert.equal(f.calls.filter((call: Call) => call.method !== 'GET').length, 0)
})

test('deletion requires confirmation then deletes the exact entity or relation', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); f.deleteEntity({ entity_id: '中文ID', entity_name: '实体' })
  assert.equal(f.calls.filter((call: Call) => call.method === 'DELETE').length, 0); await f.remove()
  const deleted = f.calls.find((call: Call) => call.method === 'DELETE')!
  assert.deepEqual(Object.fromEntries(new URLSearchParams(deleted.path.split('?')[1])), { knowledge_base_id: 'kb-a', entity_id: '中文ID' })
  assert.deepEqual(deleted.data, {})
  f.deleteRelation({ relation_id: 'relation-1', relation_type: 'uses' })
  assert.equal(f.deleting.value.name, '当前关系')
  await f.remove()
  assert.deepEqual(Object.fromEntries(new URLSearchParams(f.calls.filter((call: Call) => call.method === 'DELETE').at(-1)!.path.split('?')[1])), { knowledge_base_id: 'kb-a', relation_id: 'relation-1' })
})

test('reader cannot open mutation dialogs or issue writes', async t => {
  const f = fixture(undefined, false); t.after(f.dispose); await f.flush()
  await f.editEntity(); await f.editRelation(); f.deleteEntity({ entity_id: 'id' }); f.deleteRelation({ relation_id: 'id' }); await f.save(); await f.remove()
  assert.equal(f.editorOpen.value, false); assert.equal(f.deleting.value, null); assert.equal(f.calls.filter((call: Call) => call.method !== 'GET').length, 0)
})

test('failed detail cannot overwrite fields and late details cannot cross library changes', async t => {
  let reply: (value: any) => void = () => {}; let fails = true
  const f = fixture(async call => {
    if (call.path.endsWith('/detail')) { if (fails) throw new Error('读取失败'); return new Promise(resolve => { reply = resolve }) }
    return { data: { entities: [], total: 0 } }
  }); t.after(f.dispose); await f.flush()
  await f.editEntity({ entity_id: 'id' }); f.form.value.entity_name = 'name'; f.form.value.entity_type = 'type'; await f.save()
  assert.equal(f.calls.filter((call: Call) => call.method === 'PUT').length, 0)
  fails = false; const pending = f.editEntity({ entity_id: 'id' }); f.props.kbId = 'kb-b'; await f.flush()
  reply({ data: { entity_id: 'id', entity_name: 'stale' } }); await pending
  assert.equal(f.editorOpen.value, false); assert.notEqual(f.form.value.entity_name, 'stale')
})

test('duplicate submits lock and an old save cannot close a new library editor', async t => {
  let reply: (value: any) => void = () => {}
  const f = fixture(async call => call.method === 'POST' ? new Promise(resolve => { reply = resolve }) : { data: { entities: [], total: 0 } })
  t.after(f.dispose); await f.flush(); await f.editEntity(); f.form.value.entity_name = 'name'; f.form.value.entity_type = 'type'
  const pending = f.save(); await f.save(); assert.equal(f.calls.filter((call: Call) => call.method === 'POST').length, 1)
  f.props.kbId = 'kb-b'; await f.flush(); await f.editEntity(); f.form.value.entity_name = 'new'
  reply({ data: { knowledge_base_id: 'kb-a', entity_id: 'saved' } }); await pending
  assert.equal(f.editorOpen.value, true); assert.equal(f.form.value.entity_name, 'new'); assert.equal(f.events.length, 0)
})

test('documented field limits reject oversized input without issuing writes', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush(); await f.editEntity()
  f.form.value.entity_name = '名'.repeat(101); f.form.value.entity_type = 'concept'; await f.save(); assert.match(f.editError.value, /100/)
  f.form.value.entity_name = '实体'; f.form.value.description = '文'.repeat(8193); await f.save(); assert.match(f.editError.value, /8192/)
  f.form.value.description = ''; f.form.value.aliases = ['a'.repeat(129)]; await f.save(); assert.match(f.editError.value, /128/)
  await f.editRelation(); f.form.value.relation_type = 'uses'; f.form.value.source_entity_id = 'source'; f.form.value.target_entity_id = 'target'
  f.form.value.keywords = Array.from({ length: 51 }, (_, i) => `key-${i}`); await f.save(); assert.match(f.editError.value, /50/)
  assert.equal(f.calls.filter((call: Call) => call.method !== 'GET').length, 0)
})

test('older entity searches and endpoint searches cannot overwrite newer results', async t => {
  const replies: Array<(value: any) => void> = []
  const f = fixture(() => new Promise(resolve => replies.push(resolve))); t.after(f.dispose)
  f.keyword.value = 'new'; const newest = f.load()
  replies[1]!({ data: { entities: [{ entity_id: 'new', entity_name: '新' }], total: 1 } }); await newest
  replies[0]!({ data: { entities: [{ entity_id: 'old', entity_name: '旧' }], total: 1 } }); await f.flush()
  assert.equal(f.items.value[0].entity_id, 'new')
  await f.editRelation(); const searched = f.searchEndpoints('target')
  replies[3]!({ data: { entities: [{ entity_id: 'target', entity_name: '目标' }] } }); await searched
  replies[2]!({ data: { entities: [{ entity_id: 'old', entity_name: '旧' }] } }); await f.flush()
  assert.equal(f.choices.value[0].entity_id, 'target')
})
