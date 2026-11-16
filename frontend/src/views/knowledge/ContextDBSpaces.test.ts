import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, ref } from 'vue'
import ts from 'typescript'

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
