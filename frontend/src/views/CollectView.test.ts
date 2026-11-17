import assert from 'node:assert/strict'
import test, {type TestContext} from 'node:test'
import {reactive} from 'vue'
import {fixture,flush} from '../test-utils/vueFixture.ts'
async function setup(t:TestContext,failUpload=false,writable=true,directFailure=false,status:(id:string)=>Promise<any>=async()=>({status:'completed',directory_sync_complete:true,import_directories:[]}),options:{embedded?:boolean;upload?:(files:File[],id:string)=>Promise<any>}={}){
  const f=fixture(t),calls:any[]=[],previewCalls:any[]=[],events:any[]=[],routes:any[]=[]
  const route=reactive<any>({query:{kb_id:'a'},fullPath:'/collect?kb_id=a'})
  const {vm}=f.component(new URL('./CollectView.vue',import.meta.url),{
    'vue-router':{useRoute:()=>route,useRouter:()=>({push:(value:any)=>routes.push(value)})},
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/api/backend':{
      entries:async()=>({entries:[{key:'web'},{key:'file'}]}),
      entryDocuments:async(entry:string,params:any)=>{previewCalls.push({entry,params});return {pages:[{page_id:'one',page_title:'手册',directory_path:['介绍']}],directory:{root_name:'网站资料',source_key:'web:example'}}},
      taskStatus:status,
      startTask:async(entry:string,payload:any)=>{calls.push({entry,payload});return {task_id:'crawl-1'}},
      uploadFiles:async(files:File[],id:string)=>{calls.push({files,id});if(failUpload)throw new Error('upload unavailable');return options.upload ? options.upload(files,id) : {task_id:'file-1'}},
    },
    '@/api/knowledgeSpaces':{getSpaces:async()=>({spaces:[]})},
    '@/api/contextdb':{
      listBases:async()=>({data:[{id:'a',name:'A',wiki_enabled:false,graph_enabled:false},{id:'b',name:'B',graph_enabled:true}]}),
      getBasePermissions:async()=>({}),knowledgeAccess:()=>({write:writable}),knowledgeModeLabel:()=> '零编译',
      uploadDocumentFile:async(id:string,file:File)=>{calls.push({direct:id,file});if(directFailure)throw new Error('direct unavailable');return {data:{id:'large-doc'}}},
      bindBase:async(id:string)=>{calls.push({binding:id});return {space:{scope:'internal-a'}}},
    },
    '@/utils/contextdbReviewSupport':{CONTEXTDB_REVIEW_FORMAT_NOTICE:''},
  },{embedded:options.embedded,onCreated:(receipt:any)=>events.push({created:receipt}),'onShow-tasks':(target:any)=>events.push({target}),'onBusy-change':(busy:boolean)=>events.push({busy})})
  await flush();return {vm,calls,previewCalls,route,events,routes}
}
test('crawler and file uploads use the chosen native library and resolve scope without a user association',async t=>{
  const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.loadPages();await f.vm.launch()
  assert.deepEqual(f.calls[0],{binding:'a'});assert.equal(f.calls[1].payload.knowledge_base_id,'a')
  assert.equal(f.calls[1].payload.space_scope,undefined)
  f.vm.spaceScope='b';f.vm.selectFiles([new File(['source'],'source.md')]);await f.vm.launch()
  assert.equal(f.calls[3].id,'b');assert.equal(f.vm.taskId,'file-1');assert.equal(f.vm.files.length,0)
})
test('failed upload keeps the selected files and never announces submission',async t=>{
  const f=await setup(t,true);f.vm.selectFiles([new File(['source'],'source.md')]);await f.vm.launch()
  assert.match(f.vm.error,/upload unavailable/);assert.equal(f.vm.taskId,'');assert.equal(f.vm.files.length,1)
})
test('invalid addresses, missing libraries and denied official writes cannot enqueue collection',async t=>{
  const f=await setup(t);f.vm.url='invalid';await f.vm.launch()
  assert.match(f.vm.error,/网站地址/);assert.equal(f.calls.some(call=>call.entry),false)
  f.vm.spaceScope='missing';await f.vm.launch();assert.equal(f.calls.some(call=>call.entry),false)
  await t.test('denied official write',async t=>{const denied=await setup(t,false,false);denied.vm.url='https://example.test';await denied.vm.launch();assert.equal(denied.calls.length,0)})
})

test('large files go directly to the chosen cloud library without a false local task receipt',async t=>{
 const f=await setup(t),large=new File(['x'],'large.pdf');Object.defineProperty(large,'size',{value:101*1024*1024})
 f.vm.selectFiles([large]);await f.vm.launch()
 assert.equal(f.calls[1].direct,'a');assert.equal(f.calls.some(call=>call.files),false)
 assert.equal(f.vm.files.length,0);assert.equal(f.vm.taskId,'');assert.match(f.vm.uploadNotice,/ContextDB/)
})
test('a partial upload keeps only unfinished files and never resends accepted archived files',async t=>{
 const f=await setup(t,false,true,true),small=new File(['source'],'small.md'),large=new File(['x'],'large.pdf');Object.defineProperty(large,'size',{value:101*1024*1024})
 f.vm.selectFiles([small,large]);await f.vm.launch()
 assert.equal(f.vm.files.length,1);assert.equal(f.vm.files[0].name,'large.pdf');assert.match(f.vm.error,/direct unavailable/)
 await f.vm.launch();assert.equal(f.calls.filter(call=>call.files).length,1)
})


test('collection requires a current directory preview and submits the edited root without changing source identifiers',async t=>{
  const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.launch()
  assert.match(f.vm.error,/目录预览/);assert.equal(f.calls.some(call=>call.entry),false);assert.equal(f.vm.crawlReady,false)
  await f.vm.loadPages();assert.equal(f.vm.crawlReady,true);f.vm.rootName='';assert.equal(f.vm.crawlReady,false);f.vm.rootName='产品手册';await f.vm.launch()
  assert.equal(f.calls.find(call=>call.entry).payload.import_root_name,'产品手册')
  assert.equal(f.vm.previewTree[0].children[0].label,'介绍')
  f.vm.url='https://another.test';await flush();assert.equal(f.vm.directory,null);assert.equal(f.vm.rootName,'')
})


test('partial selection preserves the full source ancestors in the preview',async t=>{
 const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.loadPages()
 f.vm.pages=[{page_id:'one',page_title:'统计',directory_path:['进货管理','报表']},{page_id:'two',page_title:'简介',directory_path:[]}]
 f.vm.selection='selected';assert.equal(f.vm.crawlReady,false);f.vm.selectedIds=['one'];assert.equal(f.vm.crawlReady,true)
 assert.equal(f.vm.previewPages.length,1)
 assert.equal(f.vm.previewTree[0].children[0].label,'进货管理')
 assert.equal(f.vm.previewTree[0].children[0].children[0].label,'报表')
 assert.equal(f.vm.previewTree[0].children[0].children[0].children[0].label,'统计')
})

test('task directory receipts ignore old tasks and preserve multiple landed roots',async t=>{
 const pending=new Map<string,(value:any)=>void>()
 const f=await setup(t,false,true,false,async(id:string)=>new Promise(resolve=>pending.set(id,resolve)))
 f.vm.taskId='old';await flush();f.vm.taskId='new';await flush()
 const roots=[{knowledge_base_id:'a',node_id:'root-a',root_name:'文档A'},{knowledge_base_id:'a',node_id:'root-b',root_name:'文档B'}]
 pending.get('new')!({status:'completed',directory_sync_complete:true,import_directories:roots});await flush()
 assert.equal(f.vm.importRoots.length,2)
 pending.get('old')!({status:'completed',directory_sync_complete:true,import_directories:[]});await flush()
 assert.equal(f.vm.importRoots.length,2)
 const reading=f.vm.readImportDirectories();f.vm.taskId='';await flush();pending.get('new')!({import_directories:roots});await reading
 assert.equal(f.vm.importRoots.length,0)
})


test('directory preview is bound to its destination library and changing libraries clears custom roots and selection',async t=>{
 const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.loadPages()
 assert.equal(f.previewCalls[0].entry,'web');assert.equal(f.previewCalls[0].params.knowledge_base_id,'a')
 f.vm.rootName='自定义名称';f.vm.selection='selected';f.vm.selectedIds=['one'];f.vm.spaceScope='b';await flush()
 assert.equal(f.vm.directory,null);assert.equal(f.vm.rootName,'');assert.equal(f.vm.selectedIds.length,0);assert.equal(f.vm.crawlReady,false)
 await f.vm.loadPages();assert.equal(f.previewCalls[1].params.knowledge_base_id,'b');assert.equal(f.vm.rootName,'网站资料')
})

test('embedded collection announces accepted work and navigates through its parent without leaving the page',async t=>{
 const f=await setup(t,false,true,false,undefined,{embedded:true})
 f.vm.url='https://example.test';await flush();await f.vm.loadPages();await f.vm.launch()
 const receipt=f.events.find(event=>event.created).created
 assert.deepEqual([...receipt.task_ids],['crawl-1']);assert.equal(receipt.scope,'internal-a');assert.equal(receipt.knowledge_base_id,'a');assert.equal(receipt.direct_count,0)
 assert.deepEqual(f.events.filter(event=>'busy' in event).map(event=>event.busy),[true,false])
 f.vm.showTasks('crawl-1');assert.equal(f.routes.length,0)
 assert.equal(f.events.at(-1).target.task_id,'crawl-1');assert.equal(f.events.at(-1).target.scope,'internal-a')
})

test('changing unrelated unified-page query fields preserves the in-progress form and its preview',async t=>{
 const f=await setup(t,false,true,false,undefined,{embedded:true})
 f.vm.url='https://example.test';await flush();await f.vm.loadPages();f.vm.rootName='自定义目录';f.vm.selection='selected';f.vm.selectedIds=['one']
 f.route.query={...f.route.query,view:'history',add:'1'};f.route.fullPath='/platform/tasks?kb_id=a&view=history&add=1';await flush()
 assert.equal(f.vm.url,'https://example.test');assert.equal(f.vm.rootName,'自定义目录');assert.equal(f.vm.previewPages.length,1);assert.equal(f.vm.crawlReady,true)
 f.route.query={...f.route.query,mode:'file'};await flush();assert.equal(f.vm.mode,'file')
})

test('all accepted upload batches remain visible and emitted when a later batch fails, and retry sends only unfinished files',async t=>{
 let attempt=0
 const f=await setup(t,false,true,false,undefined,{embedded:true,upload:async()=>{attempt++;if(attempt===3)throw new Error('third batch failed');return {task_id:'file-'+attempt}}})
 const files=['one.pdf','two.pdf','three.pdf'].map(name=>{const file=new File(['x'],name);Object.defineProperty(file,'size',{value:60*1024*1024});return file})
 f.vm.selectFiles(files);await f.vm.launch()
 assert.match(f.vm.error,/third batch failed/);assert.deepEqual([...f.vm.taskIds],['file-1','file-2']);assert.equal(f.vm.files.length,1);assert.equal(f.vm.files[0].name,'three.pdf')
 assert.deepEqual([...f.events.filter(event=>event.created).at(-1).created.task_ids],['file-1','file-2'])
 await f.vm.launch();assert.equal(f.vm.files.length,0);assert.deepEqual([...f.vm.taskIds],['file-1','file-2','file-4'])
 assert.deepEqual(f.calls.filter(call=>call.files).map(call=>call.files[0].name),['one.pdf','two.pdf','three.pdf','three.pdf'])
})

test('each batch retains its original target while busy and direct uploads emit a receipt without fabricating a task',async t=>{
 let finish!:(value:any)=>void
 const f=await setup(t,false,true,false,undefined,{embedded:true,upload:async()=>new Promise(resolve=>finish=resolve)})
 const first=new File(['x'],'one.pdf'),second=new File(['x'],'two.pdf')
 Object.defineProperty(first,'size',{value:60*1024*1024});Object.defineProperty(second,'size',{value:60*1024*1024})
 f.vm.selectFiles([first,second]);const pending=f.vm.launch();await flush()
 f.vm.spaceScope='b';f.vm.selectFiles([new File(['replacement'],'replacement.md')]);await flush()
 finish({task_id:'first'});await flush();assert.equal(f.calls.filter(call=>call.files).at(-1).id,'a')
 finish({task_id:'second'});await pending;assert.equal(f.vm.files.length,0)
 const large=new File(['x'],'large.pdf');Object.defineProperty(large,'size',{value:101*1024*1024})
 f.vm.selectFiles([large]);await f.vm.launch()
 const receipt=f.events.filter(event=>event.created).at(-1).created
 assert.equal(receipt.knowledge_base_id,'b');assert.equal(receipt.direct_count,1);assert.equal(receipt.task_ids.length,0)
})
