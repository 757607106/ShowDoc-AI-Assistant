import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('./contextdb.ts', import.meta.url), 'utf8')
const script = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const api: any = {}
runInNewContext(script, { exports: api, require: () => ({}) })

test('managed knowledge bases remain selectable for native retrieval and expose actual graph/wiki modes', () => {
  const kb = api.kbView({ id: 'kb', name: 'Finance', graph_enabled: true, wiki_enabled: false })
  assert.equal(kb.capabilities.vector, true)
  assert.equal(kb.capabilities.keyword, true)
  assert.equal(kb.capabilities.graph, true)
  assert.equal(kb.capabilities.wiki, false)
  assert.equal(api.kbView({ capabilities: { vector: false } }).capabilities.vector, false)
})

test('KB view uses the business name without losing cloud identity or legacy names', () => {
  const cloud = { id: 'wiki-id', name: 'knowledge-default', display_name: ' 默认知识库 ', space_scope: 'default' }
  const view = api.kbView(cloud)
  assert.equal(view.name, '默认知识库')
  assert.equal(view.original_name, 'knowledge-default')
  assert.equal(view.id, 'wiki-id')
  assert.equal(cloud.name, 'knowledge-default')
  assert.equal(api.kbView({ name: '旧项目手册', display_name: ' ' }).name, '旧项目手册')
  assert.equal(api.kbView({ name: '历史云端名' }).name, '历史云端名')
})

function editingAPI(base: any, failRename = false) {
  const calls: any[] = []
  const state = { ...base }
  const exports: any = {}
  runInNewContext(script, { exports, require: (path: string) => path === '@/api/knowledgeSpaces' ? {
    updateSpace: async (scope: string, body: any) => {
      calls.push(['space', scope, body])
      if (failRename) throw new Error('无权修改名称')
      state.space_name = body.name
      state.display_name = state.space_mode === 'graph' ? `${body.name}（知识图谱）` : body.name
    },
  } : path === '@/utils/request' ? {
    get: async () => ({ data: { ...state } }),
    put: async (path: string, body: any) => {
      calls.push(['cloud', path, body]); Object.assign(state, body)
      return { data: { ...state } }
    },
  } : {} })
  return { api: exports, calls, state }
}

test('saving a bound KB unchanged never writes its display name into the cloud name', async () => {
  const { api, calls } = editingAPI({ id: 'wiki', name: 'knowledge-default', display_name: '默认知识库', space_scope: 'default', description: '说明' })
  const result = await api.updateBase('wiki', { name: '默认知识库', description: '说明' })
  assert.equal(calls.length, 0)
  assert.equal(result.data.name, '默认知识库')
  assert.equal(result.data.original_name, 'knowledge-default')
})

test('renaming a bound KB changes its space while description updates preserve the cloud name', async () => {
  const { api, calls } = editingAPI({ id: 'wiki', name: 'knowledge-default', display_name: '默认知识库', space_scope: 'default', description: '说明' })
  const result = await api.updateBase('wiki', { name: '产品资料', description: '新说明' })
  assert.equal(calls.length, 2)
  assert.equal(calls[0][0], 'cloud')
  assert.equal(calls[0][2].name, 'knowledge-default')
  assert.equal(calls[0][2].description, '新说明')
  assert.equal(calls[1][0], 'space')
  assert.equal(calls[1][1], 'default')
  assert.equal(calls[1][2].name, '产品资料')
  assert.equal(result.data.name, '产品资料')
  assert.equal(result.data.original_name, 'knowledge-default')
})

test('unbound KBs retain native cloud rename behavior', async () => {
  const { api, calls } = editingAPI({ id: 'native', name: '旧名称', description: '说明' })
  const result = await api.updateBase('native', { name: '新名称', description: '新说明' })
  assert.equal(calls.length, 1)
  assert.equal(calls[0][0], 'cloud')
  assert.equal(calls[0][2].knowledge_base_id, 'native')
  assert.equal(calls[0][2].name, '新名称')
  assert.equal(result.data.name, '新名称')
})

test('graph editor names exclude the mode suffix and never save it to the business space', async () => {
  const { api, calls } = editingAPI({ id: 'graph', name: 'knowledge-default-graph', display_name: '默认知识库（知识图谱）',
    space_name: '默认知识库', space_scope: 'default', space_mode: 'graph', description: '' })
  await api.updateBase('graph', { name: '默认知识库', description: '' })
  assert.equal(calls.length, 0)
  const result = await api.updateBase('graph', { name: '业务资料', description: '' })
  assert.equal(calls.length, 1)
  assert.equal(calls[0][0], 'space')
  assert.equal(calls[0][2].name, '业务资料')
  assert.equal(result.data.name, '业务资料（知识图谱）')
  assert.equal(result.data.original_name, 'knowledge-default-graph')
})

test('partial save failure states which field was already saved', async () => {
  const { api, calls } = editingAPI({ name: 'knowledge-default', display_name: '默认知识库', space_scope: 'default', description: '' }, true)
  await assert.rejects(api.updateBase('wiki', { name: '新名称', description: '新说明' }), /说明已保存，但名称更新失败/)
  assert.equal(calls[0][2].name, 'knowledge-default')
})
