import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import * as presentation from './contextdbGraphPresentation.ts'
import * as documentName from '../../utils/contextdbDocumentName.ts'

const source = readFileSync(new URL('./ContextDBGraph.vue', import.meta.url), 'utf8')
const script = source.slice(source.indexOf('<script setup lang="ts">') + '<script setup lang="ts">'.length, source.indexOf('</script>'))
const compiled = ts.transpileModule(script + '\nexports.state = { changed, appliedHops, maxNodes, maxEdges, settingsError, applySettings, locate, locatedId, displayName, loadRelations, changeRelationPage, relations, relationPage, relationTotal, relationType, relationError, relationLoading, props, graph, root, hops, documentId, entities, documents, documentTotal, error, busy, detail, detailOpen, detailLoading, detailError, sources, sourceLoading, sourceError, sourceResult, graphCanvas, graphScale, nodes, edges, types, scopeLabel, graphNotice, searchEntities, loadDocuments, load, changeDocument, inspect, closeDetail, expandEntity, zoom, fit };', {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText

type Call = { path: string; params: Record<string, any> }
const sampleGraph = {
  entity_total: 3, relation_total: 2, nodes_returned: 2, edges_returned: 1, truncated: true, note: '仅返回当前来源的部分实体',
  nodes: [{ id: '产品甲', label: '产品甲', group: '产品' }, { id: '组件乙', label: '组件乙', group: '组件' }],
  edges: [{ id: '产品甲→组件乙', from: '产品甲', to: '组件乙', label: '包含' }],
}
function fixture(get?: (call: Call) => Promise<any>, post?: (call: Call) => Promise<any>, contributor = true) {
  const calls: Call[] = [], posts: Call[] = [], cleanup: Array<() => void> = [], props = vue.reactive({ kbId: 'kb-a' })
  const timers = new Map<number, () => void>(); let timerId = 0
  const scope = vue.effectScope(), exports: { state?: any } = {}
  const modules: Record<string, unknown> = {
    vue: { ...vue, onMounted() {}, onUnmounted: (fn: () => void) => cleanup.push(fn), useId: () => 'test' },
    '@/api/contextdb': { nativeAPI: { async get(path: string, params: Record<string, any> = {}) {
      const call = { path, params }; calls.push(call)
      if (get) return get(call)
      if (path === 'knowledge/entities') return { data: { entities: [{ entity_id: '产品甲', entity_name: '产品甲' }] } }
      if (path === 'knowledge/documents') return { data: { documents: [{ id: 'doc-1', name: '产品手册.md' }], total: 1 } }
      if (path === 'knowledge/graph-visual') return { data: sampleGraph }
      if (path === 'knowledge/entities/chunks') return { data: { chunks: [{ chunk_id: 'chunk-1', document_id: 'doc-1', content: '原文' }], truncated: false } }
      return { data: { entity_id: params.entity_id, entity_name: '产品甲', relation_id: params.relation_id } }
    }, async post(path: string, params: Record<string, any>) {
      const call = { path, params }; posts.push(call)
      return post ? post(call) : { data: { dispatched: false, event_id: null } }
    } } },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: (role: string) => { assert.equal(role, 'contributor'); return contributor } }) },
    './ContextDBGraphCanvas.vue': {}, './contextdbGraphPresentation': presentation, '@/utils/contextdbDocumentName': documentName, './ContextDBGraphManagement.vue': {}, '@/components/DocMarkdown.vue': {}, '@/utils/platformPresentation': { dateTime: (value: unknown) => value },
  }
  scope.run(() => vm.runInNewContext(compiled, { exports, defineProps: () => props, defineEmits: () => () => {}, defineExpose() {},
    require: (id: string) => { assert.ok(id in modules, `unexpected import ${id}`); return modules[id] }, console, document: { removeEventListener() {} },
    setTimeout: (fn: () => void, delay: number) => { assert.equal(delay, 3000); timers.set(++timerId, fn); return timerId },
    clearTimeout: (id: number) => timers.delete(id),
  }))
  const flush = async () => { await vue.nextTick(); await new Promise(resolve => setImmediate(resolve)) }
  return { ...exports.state, calls, posts, props, timers, flush, tick: async () => {
    const next = timers.entries().next().value; assert.ok(next, 'poll timer exists'); timers.delete(next[0]); next[1](); await flush()
  }, dispose: () => { cleanup.forEach(fn => fn()); scope.stop() } }
}

test('official graph and entity queries preserve opaque Chinese IDs, document scope and two-hop expansion', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  f.documentId.value = 'doc-1'; f.root.value = '产品甲'; f.hops.value = 2
  await f.load(); await f.searchEntities(' 产品 ')
  const graphCall = f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').at(-1)!
  assert.deepEqual(JSON.parse(JSON.stringify(graphCall.params)), { knowledge_base_id: 'kb-a', entity_id: '产品甲', max_hops: 2, max_nodes: 100, max_edges: 200 })
  const search = f.calls.filter((call: Call) => call.path === 'knowledge/entities').at(-1)!
  assert.equal(search.params.kb_id, 'kb-a'); assert.equal(search.params.knowledge_base_id, undefined)
  assert.equal(search.params.document_id, undefined); assert.equal(search.params.keyword, '产品')
  assert.match(f.scopeLabel.value, /产品甲.*2 跳.*不受文件范围限制/)
  assert.equal(f.graph.value.note, sampleGraph.note); assert.equal(f.graph.value.truncated, true)
  await f.inspect('产品甲')
  assert.equal(f.calls.find((call: Call) => call.path === 'knowledge/entities/detail')!.params.entity_id, '产品甲')
  assert.equal(f.calls.find((call: Call) => call.path === 'knowledge/entities/chunks')!.params.entity_ids, '产品甲')
  await f.inspect('产品甲→组件乙', true)
  assert.equal(f.calls.at(-1)!.params.relation_id, '产品甲→组件乙')
  assert.equal(f.calls.at(-1)!.params.knowledge_base_id, 'kb-a')
})

test('a source failure leaves entity details readable and closing rejects delayed detail and source replies', async t => {
  const pending = new Map<string, (value: any) => void>()
  let delayed = false
  const f = fixture(async ({ path, params }) => {
    if (path.endsWith('/detail') || path.endsWith('/chunks')) {
      if (delayed) return new Promise(resolve => pending.set(path, resolve))
      if (path.endsWith('/chunks')) throw new Error('来源暂不可用')
      return { data: { entity_id: params.entity_id, entity_name: '产品甲' } }
    }
    return { data: path.endsWith('graph-visual') ? sampleGraph : {} }
  })
  t.after(f.dispose); await f.flush(); await f.inspect('产品甲')
  assert.equal(f.detail.value.entity_name, '产品甲'); assert.equal(f.detailError.value, '')
  assert.equal(f.sourceError.value, '来源暂不可用'); assert.equal(f.error.value, '')
  delayed = true
  const waiting = f.inspect('组件乙')
  assert.equal(f.detailOpen.value, true); assert.equal(f.detailLoading.value, true); assert.equal(f.sourceLoading.value, true)
  f.closeDetail()
  pending.get('knowledge/entities/detail')!({ data: { entity_id: '组件乙' } })
  pending.get('knowledge/entities/chunks')!({ data: { chunks: [{ content: 'stale' }] } })
  await waiting
  assert.equal(f.detailOpen.value, false); assert.equal(f.detail.value, null); assert.equal(f.sources.value.length, 0)
})

test('switching knowledge bases rejects old graph, selector, detail and source responses', async t => {
  const pending: Array<{ call: Call; resolve: (value: any) => void }> = []
  const f = fixture(call => call.params.knowledge_base_id === 'kb-b' || call.params.kb_id === 'kb-b'
    ? Promise.resolve({ data: call.path.endsWith('graph-visual') ? { ...sampleGraph, note: 'new graph' } : { entities: [], documents: [] } })
    : new Promise(resolve => pending.push({ call, resolve })))
  t.after(f.dispose)
  const inspecting = f.inspect('产品甲')
  f.props.kbId = 'kb-b'; await f.flush()
  for (const item of pending) item.resolve({ data: { ...sampleGraph, note: 'stale graph', entities: [{ entity_id: 'stale' }], documents: [{ id: 'stale' }], entity_id: 'stale', chunks: [{ content: 'stale' }] } })
  await inspecting; await f.flush()
  assert.equal(f.graph.value.note, 'new graph'); assert.equal(f.entities.value.length, 0); assert.equal(f.documents.value.length, 0)
  assert.equal(f.detailOpen.value, false); assert.equal(f.detail.value, null); assert.equal(f.sources.value.length, 0)
  assert.equal(f.root.value, ''); assert.equal(f.documentId.value, '')
})

test('canvas actions use the official renderer without replacing the query scope', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  const actions: any[] = []
  f.graphCanvas.value = { fit: () => actions.push(['fit']), zoom: (factor: number) => actions.push(['zoom', factor]), focus: (id: string) => actions.push(['focus', id]) }
  f.fit(); f.zoom(1.25); f.locate('产品甲'); await f.flush()
  assert.deepEqual(actions, [['fit'], ['zoom', 1.25], ['focus', '产品甲']])
  assert.equal(f.root.value, ''); assert.equal(f.locatedId.value, '产品甲')
  assert.equal(f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').length, 1)
})

test('document overview uses plain scope guidance while truncated and neighbor notes retain official detail', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  f.documentId.value = 'doc-1'; f.graph.value = { ...sampleGraph, truncated: false, note: 'graph_subgraph / graph_entity / source_document_ids' }
  assert.equal(f.graphNotice.value, '当前展示该文档的抽取结果，可能与全库合并后的实体数量不同。')
  f.graph.value.truncated = true
  assert.equal(f.graphNotice.value, f.graph.value.note)
  f.graph.value.truncated = false; f.root.value = '产品甲'
  assert.equal(f.graphNotice.value, f.graph.value.note)
})

test('document names resolve beyond the first page without changing opaque graph IDs', async t => {
  const internal = `doc-${'a'.repeat(64)}.html`
  const f = fixture(async ({ path, params }) => ({ data: path === 'knowledge/graph-visual'
    ? { nodes: [{ id: 'opaque-entity', label: internal, group: 'document' }], edges: [] }
    : path === 'knowledge/documents' ? { documents: params.page === 1
      ? Array.from({ length: 100 }, (_, i) => ({ id: `doc-${i}`, name: `other-${i}.md` }))
      : [{ id: 'source-document', name: internal, metadata: { title: '其他入库操作指南' } }], total: 101 }
    : {} }))
  t.after(f.dispose); await f.flush(); await f.flush()
  assert.equal(f.nodes.value[0].label, '其他入库操作指南'); assert.equal(f.nodes.value[0].id, 'opaque-entity')
  assert.deepEqual(f.calls.filter((call: Call) => call.path === 'knowledge/documents').map((call: Call) => call.params.page), [1, 2])
  f.locate('opaque-entity'); await f.flush()
  assert.equal(f.calls.find((call: Call) => call.path === 'knowledge/entities/detail')!.params.entity_id, 'opaque-entity')
  assert.equal(f.locatedId.value, 'opaque-entity')
})

test('settings validate official bounds, document scope returns after whole-KB expansion', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  f.maxNodes.value = 0; f.applySettings(); assert.match(f.settingsError.value, /有效/)
  assert.equal(f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').length, 1)
  f.maxNodes.value = 8000; f.maxEdges.value = 20000; f.documentId.value = 'doc-1'
  f.applySettings(); await f.flush()
  assert.equal(f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').at(-1)!.params.max_nodes, 8000)
  f.expandEntity({ entity_id: '产品甲', entity_name: '产品甲' }); await f.flush()
  assert.equal(f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').at(-1)!.params.document_id, undefined)
  assert.equal(f.documentId.value, 'doc-1')
  f.root.value = ''; await f.load()
  assert.equal(f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').at(-1)!.params.document_id, 'doc-1')
})

test('relation pagination and exact filter use official query keys and discard late replies after selection changes', async t => {
  let pending: ((value: any) => void) | undefined
  const f = fixture(async ({ path, params }) => {
    if (path === 'knowledge/entity-relations') {
      if (params.page === 3) return new Promise(resolve => { pending = resolve })
      return { data: { relations: [{ relation_id: `r-${params.page}` }], total: 25 } }
    }
    return { data: path === 'knowledge/graph-visual' ? sampleGraph : {} }
  })
  t.after(f.dispose); await f.flush(); await f.inspect('产品甲'); f.relationType.value = ' uses '
  await f.loadRelations(2)
  assert.deepEqual(JSON.parse(JSON.stringify(f.calls.at(-1)!.params)), { kb_id: 'kb-a', entity_id: '产品甲', relation_type: 'uses', page: 2, page_size: 10 })
  assert.equal(f.relations.value[0].relation_id, 'r-2'); assert.equal(f.relationPage.value, 2)
  const waiting = f.loadRelations(3); f.closeDetail(); pending!({ data: { relations: [{ relation_id: 'stale' }], total: 25 } }); await waiting
  assert.equal(f.relations.value.length, 0); assert.equal(f.relationLoading.value, false)
})


test('draft settings do not mislabel the displayed subgraph and deleting its root restores document scope', async t => {
  const f = fixture(); t.after(f.dispose); await f.flush()
  f.documentId.value = 'doc-1'; f.expandEntity({ entity_id: '产品甲', entity_name: '产品甲' }); await f.flush()
  f.hops.value = 1; assert.match(f.scopeLabel.value, /2 跳/); f.applySettings(); await f.flush(); assert.match(f.scopeLabel.value, /1 跳/)
  await f.changed({ kind: 'entity', id: '产品甲', deleted: true })
  assert.equal(f.root.value, ''); assert.equal(f.documentId.value, 'doc-1')
  const query = f.calls.filter((call: Call) => call.path === 'knowledge/graph-visual').at(-1)!.params
  assert.equal(query.entity_id, undefined); assert.equal(query.document_id, 'doc-1')
})
