import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import * as vue from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

async function setup(t: TestContext, options: { spaces?: any[]; query?: Record<string, string | undefined>; base?: any; failure?: Error; props?: Record<string, unknown> } = {}) {
  const f = fixture(t), routes: any[] = [], reads: string[] = [], documentReads: string[] = []
  const route = vue.reactive({ params: { kbId: 'native-kb' }, query: options.query || {} })
  const spaceAPI = f.evaluate(readFileSync(new URL('../../api/knowledgeSpaces.ts', import.meta.url), 'utf8'), {
    '@/utils/request': { get() {}, post() {}, patch() {} },
  })
  const page = f.component(new URL('./ContextDBKnowledge.vue', import.meta.url), {
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace: (value: any) => routes.push(value), push() {} }) },
    'tdesign-vue-next': { MessagePlugin: { error() {} } },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/stores/ui': { useUIStore: () => ({}) },
    '@/api/knowledgeSpaces': { ...spaceAPI, getSpaces: async () => ({ spaces: options.spaces || [] }) },
    '@/api/contextdb': {
      getBase: async (id: string) => { reads.push(id); if (options.failure) throw options.failure; return { data: options.base || { name: 'Wiki', wiki_enabled: true } } },
      listBases: async () => ({ data: [] }), getDocument: async (id: string) => {documentReads.push(id);return { data: { id } }},
      documentView: (value: any) => value, nativeAPI: { get: async () => ({ data: { items: [], total: 0 } }) },
    },
    '@/api/knowledge-base': { getKnowledgeDetailsCon: async () => ({ data: [], total: 0 }) },
    '@/utils/platformPresentation': { stateLabel: (value: string) => value, dateTime: () => '' },
    '@/utils/contextdbReviewSupport': { CONTEXTDB_REVIEW_FORMAT_NOTICE: '' },
    '@/utils/contextdbDocumentName': { documentDisplayName: () => '' },
  },options.props)
  await flush()
  return { ...page, route, routes, reads, documentReads }
}

test('current native Wiki deep links resolve to their business space without losing references', async t => {
  const query = { tab: 'history', wikiPageId: 'page-a', node_id: 'folder-a', file_path: 'guides' }
  const f = await setup(t, { query, spaces: [{ scope: 'product:a', wiki_kb_id: 'native-kb' }] })
  assert.deepEqual(JSON.parse(JSON.stringify(f.routes)), [{ path: '/platform/knowledge-spaces/product%3Aa', query }])
  assert.deepEqual(f.reads, [])
})

test('recovered historical links discard old resource IDs while keeping unrelated query parameters',async t=>{
  const query={tab:'documents',wikiPageId:'old-page',slug:'old-topic',document_id:'old-doc',knowledge_id:'old-doc',node_id:'old-node',parent_node_id:'old-parent',file_path:'old-path',filter:'keep',target:'graph'}
  for(const mode of ['wiki','graph'] as const)await t.test(mode,async t=>{
    const f=await setup(t,{query,spaces:[{scope:'default',[`${mode}_kb_id`]:'new-kb',targets:{[mode]:{previous_knowledge_base_ids:['native-kb']}}}]})
    assert.deepEqual(JSON.parse(JSON.stringify(f.routes)),[{path:'/platform/knowledge-spaces/default',query:{tab:mode,filter:'keep',...(mode==='graph'?{target:'graph'}:{})}}])
    assert.deepEqual(f.reads,[])
  })
})

test('old Wiki bookmarks and the replacement native ID both resolve after rebuilding the library', async t => {
  for(const current of [false,true])await t.test(current?'replacement ID':'historical ID',async t=>{
    const f=await setup(t,{spaces:[{scope:'default',wiki_kb_id:current?'native-kb':'replacement-kb',targets:{wiki:{previous_knowledge_base_ids:current?['old-kb']:['native-kb']}}}]})
    assert.equal(f.routes[0].path,'/platform/knowledge-spaces/default')
    assert.equal(f.routes[0].query.tab,'wiki')
    assert.deepEqual(f.reads,[])
  })
})

test('a current binding wins over another space history and ambiguous historical aliases stay native', async t => {
  const historical={scope:'previous',targets:{wiki:{previous_knowledge_base_ids:['native-kb']}}}
  await t.test('current binding',async t=>{
    const f=await setup(t,{spaces:[historical,{scope:'current',wiki_kb_id:'native-kb'}]})
    assert.equal(f.routes[0].path,'/platform/knowledge-spaces/current')
    assert.deepEqual(f.reads,[])
  })
  await t.test('ambiguous history',async t=>{
    const f=await setup(t,{spaces:[historical,{...historical,scope:'another-previous'}]})
    assert.deepEqual(f.routes.filter((value:any)=>value.path),[])
    assert.deepEqual(f.reads,['native-kb'])
  })
})

test('graph native entry defaults to graph and document references keep the graph source library', async t => {
  for (const query of [{}, { tab: 'wiki', document_id: 'doc-a', node_id: 'folder-a' }]) {
    await t.test(JSON.stringify(query), async t => {
      const f = await setup(t, { query, spaces: [{ scope: 'default', graph_kb_id: 'native-kb' }] })
      assert.deepEqual(JSON.parse(JSON.stringify(f.routes)), [{ path: '/platform/knowledge-spaces/default', query: { ...query, tab: 'document_id' in query ? 'documents' : 'graph', target: 'graph' } }])
    })
  }
})

test('unassociated libraries use their available native views and invalid tabs fall back by mode', async t => {
  for (const [base, query, expected] of [
    [{ wiki_enabled: true }, {}, 'wiki'], [{ graph_enabled: true }, { tab: 'invalid' }, 'graph'],
    [{}, { tab: 'wiki' }, 'documents'], [{ wiki_enabled: true }, { document_id: 'doc-a' }, 'documents'],
  ] as const) {
    await t.test(JSON.stringify([base, query]), async t => {
      const f = await setup(t, { base, query })
      assert.equal(f.vm.tab, expected)
      assert.deepEqual(f.routes.filter((value: any) => value.path), [])
      assert.deepEqual(f.reads, ['native-kb'])
    })
  }
})

test('an unavailable unassociated library remains an error instead of an empty successful library', async t => {
  const f = await setup(t, { failure: new Error('knowledge base not found') })
  assert.equal(f.vm.base, null)
  assert.equal(f.vm.error, 'knowledge base not found')
  assert.equal(f.vm.baseLoading, false)
})

test('document deep links have one preview owner while Wiki source previews remain available',async t=>{
  const query={tab:'documents',document_id:'graph-doc',target:'graph'}
  const f=await setup(t,{query,base:{graph_enabled:true},props:{embedded:true,knowledgeBaseId:'native-kb',view:'documents'}})
  assert.equal(f.vm.tab,'documents')
  assert.equal(f.vm.preview,null)
  assert.deepEqual(f.documentReads,[],'the embedded document page owns route-driven previews')
  assert.equal(f.route.query.document_id,'graph-doc')
  const template=readFileSync(new URL('./ContextDBKnowledge.vue',import.meta.url),'utf8').split('<template>')[1]!
  assert.match(template,/<KnowledgeBase\s+v-else-if="tab==='documents'"[^>]+embedded/)
  f.vm.tab='wiki';await flush()
  await f.vm.open({id:'wiki-source'})
  assert.equal(f.vm.preview.id,'wiki-source')
  assert.deepEqual(f.documentReads,['wiki-source'])
  f.vm.tab='documents';await flush()
  assert.equal(f.vm.preview,null,'returning to documents closes the wrapper-owned source preview')
})
