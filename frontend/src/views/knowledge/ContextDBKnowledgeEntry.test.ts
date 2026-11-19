import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import * as vue from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

const plain = (value: any) => JSON.parse(JSON.stringify(value))
async function setup(t: TestContext, options: { query?: Record<string, string>; base?: any; failure?: Error; permission?: any; getBase?: (id: string) => Promise<any> } = {}) {
  const f = fixture(t), routes: any[] = [], pushed: any[] = [], reads: string[] = []
  const route = vue.reactive({ params: { kbId: 'native-kb' }, query: options.query || {} })
  const helper = f.evaluate(readFileSync(new URL('../../api/contextdb.ts', import.meta.url), 'utf8'), { '@/utils/request': {}, '@/utils/contextdbDocumentName': {} })
  const { vm } = f.component(new URL('./ContextDBKnowledge.vue', import.meta.url), {
    'vue-router': { useRoute: () => route, onBeforeRouteLeave() {}, onBeforeRouteUpdate() {}, useRouter: () => ({
      replace: (value: any) => { routes.push(value); if (value.query) route.query = value.query },
      push: (value: any) => { pushed.push(value); routes.push(value); if (value.query) route.query = value.query },
    }) },
    'tdesign-vue-next': { MessagePlugin: { warning() {} } },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) }, '@/stores/ui': { useUIStore: () => ({}) },
    '@/api/contextdb': { ...helper,
      getBase: async (id: string) => { reads.push(id); if (options.failure) throw options.failure; return { data: options.getBase ? await options.getBase(id) : { id, name: 'Knowledge', wiki_enabled: true, ...options.base } } },
      getBasePermissions: async () => options.permission || { member: { role: 'owner' } },
    },
  })
  await flush(); await flush(); return { vm, route, props: vm.$.props, routes, pushed, reads }
}
test('native entries keep their exact library ID and default to files for every compilation mode', async t => {
  for (const base of [{ wiki_enabled: true }, { wiki_enabled: false, graph_enabled: true }, { wiki_enabled: false, graph_enabled: false }]) await t.test(JSON.stringify(base), async t => {
    const f = await setup(t, { base }); assert.deepEqual(f.reads, ['native-kb']); assert.equal(f.vm.tab, 'documents')
    assert.equal(f.routes.some(route => route.path?.includes('knowledge-spaces')), false)
    assert.deepEqual(Array.from(f.vm.viewTabs, (tab: any) => tab.key), ['documents', ...(base.wiki_enabled ? ['wiki'] : []), ...(base.graph_enabled ? ['graph'] : [])])
    assert.equal(f.vm.viewTabs[0].label, '文件')
  })
})
test('legacy directory and ontology links open files and history remains compatible only for a Wiki library', async t => {
  for (const [base, query, expected] of [
    [{ wiki_enabled: true }, { tab: 'nodes' }, 'documents'], [{ wiki_enabled: true }, { tab: 'history', wikiPageId: 'page-a' }, 'history'],
    [{ wiki_enabled: false, graph_enabled: true }, { tab: 'history' }, 'documents'], [{ wiki_enabled: false }, { tab: 'wiki' }, 'documents'],
    [{ wiki_enabled: true }, { view: 'wiki' }, 'wiki'],
    [{ wiki_enabled: false, graph_enabled: true }, { tab: 'ontology' }, 'documents'],
    [{ wiki_enabled: false, graph_enabled: true }, { view: 'ontology' }, 'documents'],
  ] as const) await t.test(JSON.stringify(query), async t => {
    const f = await setup(t, { base, query }); assert.equal(f.vm.tab, expected)
    assert.equal(f.vm.viewTabs.some((tab: any) => tab.key === 'history'), false)
  })
})
test('source links select files and pass the original ID to the inline document component', async t => {
  for (const key of ['document_id', 'documentId', 'knowledge_id']) await t.test(key, async t => {
    const f = await setup(t, { query: { [key]: 'source', tab: 'wiki' } })
    assert.equal(f.vm.documentId, 'source'); assert.equal(f.vm.tab, 'documents')
    f.vm.open({ id: 'another' }); assert.equal(f.vm.documentId, 'another'); assert.equal(f.vm.tab, 'documents')
    assert.deepEqual(f.reads, ['native-kb'])
  })
})
test('changing a document deep link within the same library updates the inline preview target', async t => {
  const f = await setup(t, { query: { document_id: 'one' } }); f.route.query.document_id = 'two'; await flush()
  assert.equal(f.vm.documentId, 'two'); assert.equal(f.vm.tab, 'documents')
  f.route.query = { tab: 'nodes' }; await flush(); assert.equal(f.vm.tab, 'documents')
  f.route.query = { tab: 'history' }; await flush(); assert.equal(f.vm.tab, 'history')
})
test('returning to the library list restores search and sort without detail parameters', async t => {
  const f = await setup(t, { query: { q: '业务', sort: 'name', tab: 'wiki', wikiPageId: 'page-a' } })
  f.vm.backToList()
  assert.deepEqual(plain(f.pushed[0]), { path: '/platform/knowledge-bases', query: { q: '业务', sort: 'name' } })
})
test('an unavailable library reports the error while missing write grants leave visible content read-only', async t => {
  await t.test('unavailable', async t => { const f = await setup(t, { failure: new Error('knowledge base not found') }); assert.equal(f.vm.base, null); assert.match(f.vm.error, /not found/) })
  await t.test('read-only', async t => {
    const f = await setup(t, { permission: { member: { role: 'member' }, knowledge_base_permissions: [{ knowledge_base_id: 'native-kb', current_permission: 'read' }] } })
    assert.equal(f.vm.editable, false); assert.equal(f.vm.manageable, false); assert.ok(f.vm.base)
  })
})
test('a stale knowledge-base response cannot replace a newly selected library', async t => {
  let complete!: (value: any) => void
  const f = await setup(t, { getBase: id => id === 'native-kb' ? new Promise(resolve => { complete = resolve }) : Promise.resolve({ id, name: 'New', graph_enabled: true }) })
  f.route.params.kbId = 'new-kb'; await flush(); complete({ id: 'native-kb', name: 'Old', wiki_enabled: true }); await flush()
  assert.equal(f.vm.base.id, 'new-kb'); assert.equal(f.vm.tab, 'documents'); assert.deepEqual(f.reads, ['native-kb', 'new-kb'])
})
test('unsaved Wiki changes veto switching views and refreshing until the editor permits navigation', async t => {
  const f = await setup(t, { query: { tab: 'wiki' } }); f.vm.wikiRef = { permitNavigation: () => false }
  f.vm.selectTab('documents'); await f.vm.loadBase(); assert.equal(f.vm.tab, 'wiki'); assert.deepEqual(f.reads, ['native-kb'])
  f.vm.wikiRef = { permitNavigation: () => true }; f.vm.selectTab('documents'); await flush(); assert.equal(f.vm.tab, 'documents')
})
test('historical spaces resolve to their original library IDs while preserving source links', async t => {
  for (const graph of [false, true]) await t.test(String(graph), async t => {
    const f = fixture(t), routes: any[] = []
    const query = { tab: graph ? 'documents' : 'wiki', ...(graph ? { target: 'graph' } : {}), document_id: 'original-doc', wikiPageId: 'original-page' }
    f.component(new URL('./ContextDBLegacySpace.vue', import.meta.url), {
      'vue-router': { useRoute: () => ({ params: { scope: 'legacy' }, query, fullPath: '/old' }), useRouter: () => ({ replace: (value: any) => routes.push(value), push() {} }) },
      '@/api/knowledgeSpaces': { getSpace: async () => ({ space: { knowledge_base_id: 'wiki-old', mode: 'wiki', wiki_kb_id: 'wiki-old', graph_kb_id: null, legacy_targets: { wiki: 'wiki-old', graph: 'graph-old' } } }) },
    })
    await flush(); assert.equal(routes[0].path, '/platform/knowledge-bases/' + (graph ? 'graph-old' : 'wiki-old'))
    assert.equal(routes[0].query.document_id, 'original-doc'); assert.equal(routes[0].query.target, undefined)
    assert.equal(plain(routes[0].query).wikiPageId, 'original-page')
  })
})
test('view switches remove legacy view and source aliases instead of being forced back into files', async t => {
  const f = await setup(t, { query: { view: 'documents', document_id: 'old-source', documentId: 'older-source', knowledge_id: 'oldest-source', kept: 'yes' } })
  f.vm.selectTab('wiki'); await flush()
  assert.equal(f.vm.tab, 'wiki'); assert.equal(f.vm.documentId, '')
  assert.deepEqual(plain(f.route.query), { tab: 'wiki', kept: 'yes' })
  f.vm.openWikiPage('page-new'); await flush()
  assert.equal(f.vm.tab, 'wiki'); assert.deepEqual(plain(f.route.query), { tab: 'wiki', kept: 'yes', wikiTab: 'read', wikiPageId: 'page-new' })
})
test('opening a graph source survives the router update and returning to the graph clears its preview target', async t => {
  const f = await setup(t, { base: { wiki_enabled: false, graph_enabled: true }, query: { view: 'graph', kept: 'yes' } })
  assert.equal(f.vm.tab, 'graph'); f.vm.open({ id: 'graph-source' }); await flush()
  assert.equal(f.vm.tab, 'documents'); assert.equal(f.vm.documentId, 'graph-source')
  assert.deepEqual(plain(f.route.query), { tab: 'documents', document_id: 'graph-source', kept: 'yes' })
  f.vm.selectTab('graph'); await flush()
  assert.equal(f.vm.tab, 'graph'); assert.equal(f.vm.documentId, ''); assert.deepEqual(plain(f.route.query), { tab: 'graph', kept: 'yes' })
})
test('Wiki navigation guards also preserve the current source target and URL for source/page jumps', async t => {
  const f = await setup(t, { query: { tab: 'wiki', wikiPageId: 'page-current' } }); f.vm.wikiRef = { permitNavigation: () => false }
  const before = plain(f.route.query); f.vm.open({ id: 'new-source' }); f.vm.openWikiPage('new-page'); await flush()
  assert.equal(f.vm.tab, 'wiki'); assert.equal(f.vm.documentId, ''); assert.deepEqual(plain(f.route.query), before)
})


test('import directory links select files and view switches clear the directory deep link',async t=>{
 const f=await setup(t,{query:{tab:'wiki',folder_id:'import-root'}})
 assert.equal(f.vm.tab,'documents');assert.equal(f.vm.folderId,'import-root')
 f.vm.selectTab('wiki');await flush();assert.equal(f.vm.tab,'wiki');assert.equal(f.route.query.folder_id,undefined)
 f.vm.selectTab('documents');await flush();assert.equal(f.vm.folderId,'import-root')
})

test('file navigation writes the document and folder and returning clears legacy document aliases', async t => {
  const f = await setup(t, { query: { kept: 'yes' } })
  f.vm.navigateDocuments('folder-a'); await flush()
  assert.deepEqual(plain(f.route.query), { kept: 'yes', tab: 'documents', folder_id: 'folder-a' })
  f.vm.navigateDocuments('folder-a', 'doc-a'); await flush()
  assert.deepEqual(plain(f.route.query), { kept: 'yes', tab: 'documents', folder_id: 'folder-a', document_id: 'doc-a' })
  assert.equal(f.vm.documentId, 'doc-a'); assert.equal(f.pushed.length, 2)
  f.route.query = { kept: 'yes', folder_id: 'folder-a', documentId: 'doc-a', knowledge_id: 'legacy' }; await flush()
  f.vm.navigateDocuments('folder-a'); await flush()
  assert.deepEqual(plain(f.route.query), { kept: 'yes', tab: 'documents', folder_id: 'folder-a' })
  assert.equal(f.vm.documentId, ''); assert.equal(f.vm.folderId, 'folder-a'); assert.equal(f.pushed.length, 2)
})

test('a file write keeps the current view until the operation completes', async t => {
  const f = await setup(t)
  f.vm.documentsRef = { writeInProgress: true }
  f.vm.selectTab('wiki')
  assert.equal(f.vm.tab, 'documents'); assert.equal(f.routes.length, 0)
  f.vm.documentsRef = { writeInProgress: false }
  f.vm.selectTab('wiki'); await flush()
  assert.equal(f.vm.tab, 'wiki')
})
