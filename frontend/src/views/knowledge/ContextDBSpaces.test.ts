import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, ref } from 'vue'
import ts from 'typescript'
import { spaceName, stateLabel, stateTheme } from '../../utils/platformPresentation.ts'

const source = readFileSync(new URL('./ContextDBSpaceProgress.vue', import.meta.url), 'utf8')
const start = source.indexOf('const data = ref')
const end = source.indexOf('watch(() => props.scope', start)
const script = ts.transpileModule(source.slice(start, end) + '\nreturn {data,error,loading,page,load,retry,processingLabel,canRetryUpload,uploadState}', {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText
function fixture(read: (scope: string, page: number) => Promise<any> = async () => ({ space: { graph_enabled: true }, mappings: [] })) {
  const props = { scope: 'space-a' }, writes: any[] = [], messages: any[] = [], events: any[] = []
  const state = new Function('ref', 'props', 'getSpaceProgress', 'retrySpaceTarget', 'MessagePlugin', 'emit', 'stateLabel', 'stateTheme', script)(
    ref, props, read, async (scope: string, body: any) => { writes.push({ scope, body }) },
    { success: (text: string) => messages.push(text), error: (text: string) => messages.push(text) },
    (...event: any[]) => events.push(event), stateLabel, stateTheme,
  )
  return { state, props, writes, messages, events }
}

test('upload retry is limited to failed target batches and enabled graph ranges', () => {
  const { state } = fixture()
  state.data.value = { space: { graph_enabled: true } }
  const partial = { status: 'partial', params: { target_modes: ['wiki', 'graph'] }, summary: { targets: {
    wiki: { status: 'submitted', uploaded: 2, skipped: 1, errors: [] }, graph: { status: 'failed', errors: ['timeout'] },
  } } }
  assert.equal(state.canRetryUpload(partial, 'wiki'), false)
  assert.equal(state.canRetryUpload(partial, 'graph'), true)
  assert.equal(state.canRetryUpload({ ...partial, status: 'running' }, 'graph'), false)
  assert.equal(state.canRetryUpload({ ...partial, params: { target_modes: ['wiki'] } }, 'graph'), false)
  state.data.value.space.graph_enabled = false
  assert.equal(state.canRetryUpload(partial, 'graph'), false)
  assert.equal(state.uploadState({ params: { target_modes: ['wiki'] } }, 'graph'), '未选择')
  assert.equal(state.uploadState({}, 'wiki'), '尚无提交结果')
  assert.equal(state.uploadState(partial, 'wiki'), '已提交 · 已提交 2 / 未变化 1')
})

test('a late response cannot replace the selected space or report success after read failure', async () => {
  let resolve!: (value: any) => void
  const f = fixture(scope => scope === 'space-a' ? new Promise(yes => { resolve = yes }) : Promise.reject(new Error('官方状态不可用')))
  const old = f.state.load()
  f.props.scope = 'space-b'
  await f.state.load()
  resolve({ space: { scope: 'space-a' }, mappings: [{ status: 'succeeded' }] }); await old
  assert.equal(f.state.data.value, null)
  assert.equal(f.state.error.value, '官方状态不可用')
  assert.equal(f.state.loading.value, false)
  assert.deepEqual(f.events, [])
})

test('retry preserves the selected native stage and source and refreshes authoritative state', async () => {
  const f = fixture()
  await f.state.retry({ source_id: 'source-1', target_mode: 'graph', stage: 'graph' }, 'source-1graph')
  assert.deepEqual(f.writes, [{ scope: 'space-a', body: { source_id: 'source-1', target_mode: 'graph', stage: 'graph' } }])
  assert.deepEqual(f.events.map(event => event[0]), ['refreshSpace', 'spaceLoaded'])
  assert.ok(f.messages[0].includes('受理'))
})

test('unbuilt graph actions say build while failed graph actions say retry', async () => {
  const f = fixture()
  assert.equal(f.state.processingLabel('ingest', {}), '重试入库')
  assert.equal(f.state.processingLabel('graph', { official: { graph_status: 'failed' } }), '重试图谱构建')
  for (const graph_status of ['skipped', null, '']) {
    const label = f.state.processingLabel('graph', { official: { graph_status } })
    assert.equal(label, '构建图谱')
    await f.state.retry({ source_id: 'source-1', target_mode: 'graph', stage: 'graph' }, 'source-1graph', label)
    assert.equal(f.messages.at(-1), '构建图谱已受理，请继续查看处理状态')
  }
})

test('embedded and legacy document views share the ingestion route instead of uploading to one library', () => {
  const component = readFileSync(new URL('./ContextDBKnowledge.vue', import.meta.url), 'utf8')
  const start = component.indexOf('function addDocuments()')
  const end = component.indexOf('async function loadFolders', start)
  const fn = ts.transpileModule(component.slice(start, end) + '\nreturn addDocuments', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  for (const scope of ['product-a', undefined]) {
    let location: any
    const add = new Function('props', 'router', 'kbId', fn)({ spaceScope: scope }, { push: (value: any) => { location = value } }, { value: 'kb-1' })
    add()
    assert.deepEqual(location, { path: '/platform/collect', query: { mode: 'file', ...(scope ? { space: scope } : { kb_id: 'kb-1' }) } })
  }
  assert.ok(!component.includes("postUpload('/api/contextdb/v1/knowledge/files'"))
})

test('a second create click cannot create another space while the first request is pending', async () => {
  const component = readFileSync(new URL('./ContextDBSpaces.vue', import.meta.url), 'utf8')
  const start = component.indexOf('async function save()')
  const end = component.indexOf('const open =', start)
  const fn = ts.transpileModule(component.slice(start, end) + '\nreturn save', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  let resolve!: (value: any) => void, calls = 0
  const saving = ref(false), routes: string[] = []
  const save = new Function('saving', 'name', 'wikiId', 'graphId', 'graphEnabled', 'dialog', 'createSpace', 'router', 'MessagePlugin', fn)(
    saving, ref('产品知识'), ref('wiki-original'), ref(''), ref(false), ref(true),
    async () => { calls++; return new Promise(yes => { resolve = yes }) },
    { push: (path: string) => routes.push(path) }, { error: assert.fail, warning: assert.fail },
  )
  const first = save(); await save()
  assert.equal(calls, 1)
  resolve({ space: { scope: 'product:a' } }); await first
  assert.equal(saving.value, false)
  assert.deepEqual(routes, ['/platform/knowledge-spaces/product%3Aa'])
})

test('business cards use only configured libraries and existing Wiki associations preserve native IDs', async () => {
  const source = readFileSync(new URL('./ContextDBSpaces.vue', import.meta.url), 'utf8')
  const script = source.split('<script setup lang="ts">')[1]!.split('</script>')[0]!.replace(/^import .*$/gm, '')
  const code = ts.transpileModule(script + '\nreturn {load,spaces,filtered,wikiBases,graphBases,query,linking,openCreate,name,wikiId,graphId,graphEnabled,save}', {
    compilerOptions: {target:ts.ScriptTarget.ES2022},
  }).outputText
  const writes: any[] = [], routes: string[] = []
  const nativeWiki = {id:'wiki-original',name:'已有 Wiki',wiki_enabled:true}
  const state = new Function('ref','computed','onMounted','onUnmounted','useRouter','useAuthStore','getSpaces','createSpace','MessagePlugin','spaceName',code)(
    ref,computed,()=>{},()=>{},()=>({push:(path:string)=>routes.push(path)}),()=>({hasRole:()=>true}),
    async()=>({spaces:[{scope:'default',name:'默认知识空间'}],available_bases:[nativeWiki,{id:'graph-original',name:'已有图谱',graph_enabled:true}]}),
    async(data:any)=>{writes.push(data);return {space:{scope:'product:existing'}}},
    {warning:assert.fail,error:assert.fail},spaceName,
  )
  await state.load()
  assert.equal(state.filtered.value.length,1)
  state.query.value='默认知识库'
  assert.equal(state.filtered.value[0].scope,'default')
  assert.deepEqual(state.wikiBases.value.map((base:any)=>base.id),['wiki-original'])
  assert.deepEqual(state.graphBases.value.map((base:any)=>base.id),['graph-original'])
  state.linking.value=true;state.openCreate(nativeWiki)
  assert.equal(state.linking.value,false)
  assert.equal(state.wikiId.value,'wiki-original')
  assert.equal(state.graphEnabled.value,false)
  await state.save()
  assert.deepEqual(writes,[{name:'已有 Wiki',graph_enabled:false,wiki_kb_id:'wiki-original'}])
  assert.deepEqual(routes,['/platform/knowledge-spaces/product%3Aexisting'])
  state.openCreate();state.name.value='新业务知识库';await state.save()
  assert.deepEqual(writes[1],{name:'新业务知识库',graph_enabled:false})
})

test('settings may bind an empty primary library but cannot silently replace existing native IDs', async () => {
  const source = readFileSync(new URL('./ContextDBSpaceDetail.vue', import.meta.url), 'utf8')
  const start = source.indexOf('async function save()'), end = source.indexOf('async function syncCurrent()',start)
  const code = ts.transpileModule(source.slice(start,end)+'\nreturn save',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const writes: any[] = [], space=ref<any>({scope:'product-a',wiki_kb_id:null,graph_kb_id:null})
  const save = new Function('saving','name','scope','space','wikiId','graphId','graphEnabled','settings','updateSpace','MessagePlugin','acceptSpace',code)(
    ref(false),ref('产品知识'),ref('product-a'),space,ref('wiki-original'),ref('graph-original'),ref(true),ref(true),
    async(scope:string,data:any)=>{writes.push({scope,data});return {space:{...space.value,...data}}},
    {warning:assert.fail,error:assert.fail,success(){}}, (next:any)=>{space.value=next},
  )
  await save()
  assert.deepEqual(writes[0],{scope:'product-a',data:{name:'产品知识',graph_enabled:true,wiki_kb_id:'wiki-original',graph_kb_id:'graph-original'}})
  await save()
  assert.deepEqual(writes[1],{scope:'product-a',data:{name:'产品知识',graph_enabled:true}})
})

test('space documents reuse the original page without single-library mutation controls', () => {
  const wrapper=readFileSync(new URL('./ContextDBKnowledge.vue',import.meta.url),'utf8')
  assert.match(wrapper, /<KnowledgeBase[^>]+embedded/)
  const source=readFileSync(new URL('./KnowledgeBase.vue',import.meta.url),'utf8')
  const start=source.indexOf('const canEdit = computed('), end=source.indexOf('// Can manage',start)
  const script=ts.transpileModule(source.slice(start,end)+'\nreturn canEdit.value',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  assert.equal(new Function('computed','IS_CONTEXTDB',script)((fn:()=>boolean)=>({value:fn()}),true),false)
})

test('native Wiki libraries open Wiki while document and embedded links keep their selected views', async () => {
  const source=readFileSync(new URL('./KnowledgeBase.vue',import.meta.url),'utf8')
  const start=source.indexOf('let kbMetadataRequest ='), end=source.indexOf('const loadKnowledgeList =',start)
  const code=ts.transpileModule(source.slice(start,end)+'\nreturn loadKnowledgeBaseInfo',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  for (const [wiki, query, view, expected] of [
    [true, {}, undefined, 'wiki'],
    [false, {}, undefined, 'documents'],
    [true, {tab:'documents'}, undefined, 'documents'],
    [true, {}, 'documents', 'documents'],
    [true, {document_id:'doc-a'}, undefined, 'wiki'],
  ] as const) {
    const kbInfo=ref<any>(null), activeKbTab=ref('documents'), noop=()=>{}
    const dependencies={
      chatResources:{fetchKnowledgeBaseById:async()=>({indexing_strategy:{wiki_enabled:wiki}})},
      getKnowledgeBaseById:async()=>({data:{indexing_strategy:{wiki_enabled:wiki}}}), kbLoadError:ref(null),
      isCurrentKb:()=>true, kbInfo, activeKbTab, kbLoading:ref(false), IS_CONTEXTDB:true,
      props:{view}, route:{query}, isWiki:computed(()=>!!kbInfo.value?.indexing_strategy?.wiki_enabled),
      isFAQ:ref(false), selectedTagIds:ref([]), selectedTagNames:ref({}), uiStore:{clearSelectedTagIds:noop},
      loadKnowledgeFiles:noop, loadFolderTree:noop, loadTags:noop, cardList:ref([]), total:ref(0), folderTree:ref(null),
    }
    const load=new Function('dependencies',`const {${Object.keys(dependencies).join(',')}}=dependencies; ${code}`)(dependencies)
    await load('kb-a')
    assert.equal(activeKbTab.value,expected)
  }

  const watchStart=source.indexOf('watch(activeKbTab,'), watchEnd=source.indexOf('watch(() => kbId.value',watchStart)
  const watchCode=ts.transpileModule(source.slice(watchStart,watchEnd),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const routes:any[]=[]
  new Function('watch','activeKbTab','props','route','router','IS_CONTEXTDB',watchCode)(
    (_source:any,callback:(tab:string)=>void)=>callback('documents'),ref('wiki'),{},
    {query:{tab:'wiki'}},{replace:(route:any)=>routes.push(route)},true,
  )
  assert.deepEqual(routes,[{query:{tab:'documents'}}])
})

test('business knowledge spaces default to Wiki and preserve explicit document links', () => {
  const source=readFileSync(new URL('./ContextDBSpaceDetail.vue',import.meta.url),'utf8')
  const start=source.indexOf('const tab = computed('), end=source.indexOf('const spaces=',start)
  const code=ts.transpileModule(source.slice(start,end)+'\nreturn tab',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  for(const requested of [undefined,'documents','wiki']) {
    const route={query:{tab:requested}}, navigations:any[]=[]
    const tab=new Function('computed','ref','route','router',code)(computed,ref,route,{replace:(next:any)=>navigations.push(next)})
    assert.equal(tab.value,requested || 'wiki')
    tab.value='history'
    assert.equal(route.query.tab,requested,'the editor guard runs before the view changes')
    assert.equal(navigations[0].query.tab,'history')
  }
})

test('rebuilding a missing Wiki submits only that target and prevents duplicate requests', async () => {
  const source=readFileSync(new URL('./ContextDBSpaceDetail.vue',import.meta.url),'utf8')
  const start=source.indexOf('async function rebuildCurrent()'), end=source.indexOf('watch(scope,',start)
  const code=ts.transpileModule(source.slice(start,end)+'\nreturn rebuildCurrent',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  let resolve!:()=>void
  const writes:any[]=[], submitting=ref(false), tab=ref('wiki')
  const rebuild=new Function('submitting','targetStatus','scope','mode','submitSpace','tab','MessagePlugin','load',code)(
    submitting,ref('missing'),ref('default'),ref('wiki'),async(...args:any[])=>{writes.push(args);await new Promise<void>(yes=>{resolve=yes})},tab,
    {success(){},error:assert.fail},async()=>{},
  )
  const first=rebuild();await rebuild()
  assert.deepEqual(writes,[['default',['wiki']]])
  resolve();await first
  assert.equal(tab.value,'progress')
  assert.equal(submitting.value,false)
})

test('graph document deep links keep the graph library until another knowledge view is selected', () => {
  const source=readFileSync(new URL('./ContextDBSpaceDetail.vue',import.meta.url),'utf8')
  const tabStart=source.indexOf('const tab ='), tabEnd=source.indexOf('const spaces=',tabStart)
  const modeStart=source.indexOf('const mode=computed('), modeEnd=source.indexOf('\n',modeStart)
  const code=ts.transpileModule(source.slice(tabStart,tabEnd)+source.slice(modeStart,modeEnd)+'\nreturn {tab,mode}',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const route={query:{tab:'documents',target:'graph',document_id:'graph-doc'}}, replacements:any[]=[]
  const state=new Function('computed','ref','route','router',code)(computed,ref,route,{replace:(value:any)=>replacements.push(value)})
  assert.equal(state.mode.value,'graph')
  state.tab.value='wiki'
  assert.equal(replacements[0].query.target,undefined)
  assert.equal(replacements[0].query.tab,'wiki')
  assert.equal(replacements[0].query.document_id,undefined)
})
