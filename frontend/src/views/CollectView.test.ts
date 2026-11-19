import assert from 'node:assert/strict'
import test, {type TestContext} from 'node:test'
import {reactive} from 'vue'
import {fixture,flush} from '../test-utils/vueFixture.ts'
import * as files from '../utils/files.ts'
import * as fileTypes from '../utils/fileTypeVerification.ts'
async function setup(t:TestContext,failUpload=false,writable=true,directFailure: boolean | (() => boolean)=false,status:(id:string)=>Promise<any>=async()=>({status:'completed',directory_sync_complete:true,import_directories:[]}),options:{embedded?:boolean;upload?:(files:File[],id:string)=>Promise<any>;previewPages?:()=>unknown[] | undefined;readDocument?:(entry:string, payload:any, signal:AbortSignal)=>Promise<any>}={}){
  const f=fixture(t),calls:any[]=[],previewCalls:any[]=[],events:any[]=[],routes:any[]=[],warnings:string[]=[]
  const route=reactive<any>({query:{kb_id:'a'},fullPath:'/collect?kb_id=a'})
  const {vm}=f.component(new URL('./CollectView.vue',import.meta.url),{
    'vue-router':{useRoute:()=>route,useRouter:()=>({push:(value:any)=>routes.push(value)})},
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/api/backend':{
      entries:async()=>({entries:[{key:'showdoc',display_name:'ShowDoc'},{key:'extra',display_name:'其他平台'},{key:'web'},{key:'file'}]}),
      entryDocuments:async(entry:string,params:any)=>{previewCalls.push({entry,params});return {pages:options.previewPages?.() ?? [{page_id:'one',page_title:'手册',directory_path:['介绍']}],directory:{root_name:'网站资料',source_key:'web:example'}}},
      entryPreview:options.readDocument,
      taskStatus:status,
      startTask:async(entry:string,payload:any)=>{calls.push({entry,payload});return {task_id:'crawl-1'}},
      uploadFiles:async(files:File[],id:string)=>{calls.push({files,id});if(failUpload)throw new Error('upload unavailable');return options.upload ? options.upload(files,id) : {task_id:'file-1'}},
    },
    '@/api/knowledgeSpaces':{getSpaces:async()=>({spaces:[{scope:'legacy-b',knowledge_base_id:'b'}]})},
    '@/api/contextdb':{
      listBases:async()=>({data:[{id:'a',name:'A',wiki_enabled:false,graph_enabled:false},{id:'b',name:'B',graph_enabled:true}]}),
      getBasePermissions:async()=>({}),knowledgeAccess:()=>({write:writable}),knowledgeModeLabel:()=> '零编译',
      uploadDocumentFile:async(id:string,file:File)=>{calls.push({direct:id,file});if(typeof directFailure === 'function' ? directFailure() : directFailure)throw new Error('direct unavailable');return {data:{id:'large-doc'}}},
      bindBase:async(id:string)=>{calls.push({binding:id});return {space:{scope:'internal-a'}}},
    },
    'tdesign-vue-next':{MessagePlugin:{warning:(message:string)=>warnings.push(message)}},
    '@/utils/files':files,
    '@/utils/fileTypeVerification':fileTypes,
    '@/components/DocMarkdown.vue':{},
  },{embedded:options.embedded,onCreated:(receipt:any)=>events.push({created:receipt}),'onShow-tasks':(target:any)=>events.push({target}),'onBusy-change':(busy:boolean)=>events.push({busy})})
  await flush();return {vm,calls,previewCalls,route,events,routes,warnings}
}
test('document preview is lazy, retryable and discards a response after the source changes',async t=>{
  let complete!: (value:any)=>void
  let signal!: AbortSignal
  let reads=0
  const f=await setup(t,false,true,false,undefined,{readDocument:async (entry,payload,request)=>{
    assert.equal(entry,'showdoc');assert.equal(payload.item_id,'42');assert.equal(payload.doc_id,'one')
    signal=request
    if (++reads===1) throw new Error('来源暂时不可用')
    return new Promise(resolve=>{complete=resolve})
  }})
  f.vm.selectSource('showdoc');f.vm.projectId='42';await flush();await f.vm.loadPages()
  assert.equal(reads,0)
  await f.vm.openDocumentPreview('one','手册')
  assert.match(f.vm.documentError,/来源暂时不可用/)
  const pending=f.vm.openDocumentPreview('one','手册')
  assert.equal(f.vm.documentLoading,true)
  f.vm.projectId='43';await flush()
  assert.equal(signal.aborted,true)
  complete({content:'旧正文'});await pending
  assert.equal(f.vm.previewTarget,null);assert.equal(f.vm.documentPreview,null);assert.equal(f.vm.documentLoading,false)
  assert.deepEqual(f.calls,[])
})

test('rereading the same directory preserves the current tree, custom name and selection on failure', async t=>{
  let fails=false
  const f=await setup(t,false,true,false,undefined,{previewPages:()=>{
    if (fails) throw new Error('来源暂时不可用')
    return undefined
  }})
  f.vm.url='https://example.test';await flush();await f.vm.loadPages()
  f.vm.rootName='自定义目录';f.vm.selection='selected';f.vm.selectedIds=['one'];fails=true
  const reading=f.vm.loadPages()
  assert.equal(f.vm.listing,true);assert.equal(f.vm.pages.length,1)
  await reading
  assert.equal(f.vm.rootName,'自定义目录');assert.deepEqual([...f.vm.selectedIds],['one'])
  assert.match(f.vm.listError,/来源暂时不可用/)
})
test('crawler and file uploads use the chosen native library and resolve scope without a user association',async t=>{
  const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.loadPages();await f.vm.launch()
  assert.deepEqual(f.calls[0],{binding:'a'});assert.equal(f.calls[1].payload.knowledge_base_id,'a')
  assert.equal(f.calls[1].payload.space_scope,undefined)
  f.vm.spaceScope='b';f.vm.selectFiles([new File(['source'],'source.md')]);await f.vm.launch()
  assert.equal(f.calls[3].id,'b');assert.equal(f.vm.taskId,'file-1');assert.equal(f.vm.files.length,0)
  assert.equal(f.routes.at(-1).query.task,'crawl-1');assert.equal(f.vm.showFileReceipt,true)
  f.vm.showReceiptTasks()
  assert.equal(f.routes.at(-1).query.task,'file-1')
})
test('failed upload keeps the selected files and never announces submission',async t=>{
  const f=await setup(t,true);f.vm.selectFiles([new File(['source'],'source.md')]);await f.vm.launch()
  assert.match(f.vm.error,/upload unavailable/);assert.equal(f.vm.taskId,'');assert.equal(f.vm.files.length,1)
  assert.equal(f.vm.showFileReceipt,true);assert.equal(f.vm.fileSubmitLabel,'重试待提交文件')
  assert.equal(f.events.some(event=>event.created),false)
})
test('invalid addresses, missing libraries and denied official writes cannot enqueue collection',async t=>{
  const f=await setup(t);f.vm.url='invalid';await flush();await f.vm.loadPages()
  assert.match(f.vm.sourceError,/网站地址/);assert.equal(f.previewCalls.length,0);assert.equal(f.calls.some(call=>call.entry),false)
  f.vm.spaceScope='missing';await f.vm.launch();assert.equal(f.calls.some(call=>call.entry),false)
  await t.test('denied official write',async t=>{const denied=await setup(t,false,false);denied.vm.url='https://example.test';await denied.vm.launch();assert.equal(denied.calls.length,0)})
})

test('the picker and drop append to one queue and report unsupported, empty, duplicate and excess files',async t=>{
  const f=await setup(t)
  const first=new File(['source'],'first.md',{lastModified:1})
  const input={files:[first,new File(['invalid'],'run.exe')],value:'selected'}
  f.vm.pickFiles({target:input})
  assert.equal(input.value,'')
  assert.deepEqual(Array.from(f.vm.files,(file:File)=>file.name),['first.md'])
  assert.match(f.vm.fileIntakeIssues[0],/run\.exe.*格式不受支持/)
  const second=new File(['source'],'second.pdf')
  const duplicate=new File(['source'],'first.md',{lastModified:1})
  f.vm.dropFiles({dataTransfer:{files:[second,duplicate,new File([],'empty.md'),new File(['x'],'movie.mp4')]}})
  assert.deepEqual(Array.from(f.vm.files,(file:File)=>file.name),['first.md','second.pdf'])
  assert.match(f.vm.fileIntakeIssues[0],/first\.md.*已在待提交列表/)
  assert.match(f.vm.fileIntakeIssues[1],/empty\.md.*空文件/)
  assert.match(f.vm.fileIntakeIssues[2],/movie\.mp4.*格式不受支持/)
  const more=Array.from({length:50},(_,index)=>new File(['source'],`file-${index}.md`))
  f.vm.pickFiles({target:{files:more,value:'selected'}})
  assert.equal(f.vm.files.length,50)
  assert.match(f.vm.fileIntakeIssues[0],/上限.*2 个文件未添加/)
})
test('large files go directly to the chosen cloud library without a false local task receipt',async t=>{
 const f=await setup(t),large=new File(['x'],'large.pdf');Object.defineProperty(large,'size',{value:101*1024*1024})
 f.vm.selectFiles([large]);await f.vm.launch()
 assert.equal(f.calls[1].direct,'a');assert.equal(f.calls.some(call=>call.files),false)
 assert.equal(f.vm.files.length,0);assert.equal(f.vm.taskId,'');assert.match(f.vm.uploadNotice,/ContextDB/)
 assert.equal(f.vm.showFileReceipt,true);assert.equal(f.vm.fileReceipt.taskFiles,0)
 f.vm.openReceiptLibrary();assert.equal(f.routes.at(-1).name,'knowledgeBaseDetail');assert.equal(f.routes.at(-1).params.kbId,'a')
})
test('a partial upload keeps only unfinished files and never resends accepted archived files',async t=>{
 let directAttempts=0
 const f=await setup(t,false,true,()=>++directAttempts===1),small=new File(['source'],'small.md'),large=new File(['x'],'large.pdf');Object.defineProperty(large,'size',{value:101*1024*1024})
 f.vm.selectFiles([small,large]);await f.vm.launch()
 assert.equal(f.vm.files.length,1);assert.equal(f.vm.files[0].name,'large.pdf');assert.match(f.vm.error,/direct unavailable/)
 assert.equal(f.vm.fileReceipt.taskFiles,1);assert.equal(f.vm.fileReceipt.failed,true);assert.equal(f.vm.receiptTaskId,'file-1')
 await f.vm.launch();assert.equal(f.calls.filter(call=>call.files).length,1)
 assert.equal(directAttempts,2);assert.equal(f.vm.directCount,1);assert.equal(f.vm.files.length,0)
 assert.equal(f.vm.fileReceipt.taskFiles,1);assert.equal(f.vm.fileReceipt.failed,false);assert.equal(f.routes.length,0)
 f.vm.showReceiptTasks();assert.equal(f.routes.at(-1).query.task,'file-1')
 f.vm.openReceiptLibrary();assert.equal(f.routes.at(-1).params.kbId,'a')
})


test('collection requires a current directory preview and submits the edited root without changing source identifiers',async t=>{
  const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.launch()
  assert.match(f.warnings.at(-1)!,/目录预览/);assert.equal(f.calls.some(call=>call.entry),false)
  await f.vm.loadPages();f.vm.rootName='';await flush();await f.vm.launch();assert.match(f.vm.directoryError,/导入目录名称/);assert.equal(f.calls.some(call=>call.entry),false)
  for(const name of ['父目录/子目录','..','坏\u0000名称']){
    f.vm.rootName=name;await flush();await f.vm.launch()
    assert.match(f.vm.directoryError,/斜杠、控制字符/);assert.equal(f.calls.length,0)
  }
  f.vm.rootName='产品手册';await f.vm.launch()
  assert.equal(f.calls.find(call=>call.entry).payload.import_root_name,'产品手册')
  assert.equal(f.vm.previewTree[0].children[0].label,'介绍')
  f.vm.url='https://another.test';await flush();assert.equal(f.vm.directory,null);assert.equal(f.vm.rootName,'')
})

test('source choices default to one webpage and send registered extra platforms to their own preview',async t=>{
  const f=await setup(t)
  assert.equal(f.vm.spaceScope,'a');assert.equal(f.vm.activeSource,'web');assert.equal(f.vm.crawlMode,'page')
  assert.deepEqual([...f.vm.moreSources].map(({value,label})=>[value,label]),[['extra','其他平台']])
  f.vm.selectSource('showdoc');await flush();await f.vm.runPrimaryAction()
  assert.equal(f.vm.sourceError,'请输入项目编号');assert.equal(f.previewCalls.length,0)
  f.vm.selectSource('file');assert.equal(f.vm.activeSource,'file')
  f.vm.selectSource('extra');await flush();await f.vm.runPrimaryAction()
  assert.equal(f.vm.sourceError,'');assert.deepEqual(f.previewCalls.map(({entry,params})=>[entry,Object.entries(params)]),[['extra',[['knowledge_base_id','a']]]])
  f.route.query={kb_id:'b',mode:'file'};await flush()
  assert.equal(f.vm.spaceScope,'b');assert.equal(f.vm.activeSource,'file')
  f.route.query={kb_id:'a',url:'https://example.test/prefill'};await flush()
  assert.equal(f.vm.spaceScope,'a');assert.equal(f.vm.activeSource,'web');assert.equal(f.vm.url,'https://example.test/prefill')
  f.route.query={space:'legacy-b'};await flush()
  assert.equal(f.vm.spaceScope,'b');assert.equal(f.vm.activeSource,'web')
})

test('the footer reads the directory first and submits only a current preview',async t=>{
  let emptyPreview=false
  const f=await setup(t,false,true,false,undefined,{previewPages:()=>emptyPreview ? [] : undefined});f.vm.url='https://example.test';await flush()
  assert.equal(f.vm.needsPreview,true)
  const reading=f.vm.runPrimaryAction();await f.vm.runPrimaryAction();await reading
  assert.equal(f.previewCalls.length,1);assert.equal(f.calls.length,0);assert.equal(f.vm.needsPreview,false)
  f.vm.selection='selected';f.vm.selectedIds=['one'];await f.vm.runPrimaryAction()
  assert.deepEqual([...f.calls.find(call=>call.entry).payload.selected_ids],['one'])
  f.vm.url='https://another.test';await flush()
  assert.equal(f.vm.needsPreview,true);assert.equal(f.vm.selection,'all');assert.equal(f.vm.selectedIds.length,0)
  await f.vm.runPrimaryAction()
  assert.equal(f.previewCalls.length,2);assert.equal(f.calls.filter(call=>call.entry).length,1)
  f.vm.selection='selected';f.vm.selectedIds=['one'];emptyPreview=true;await f.vm.loadPages()
  assert.equal(f.vm.needsPreview,false);assert.equal(f.vm.selection,'all');assert.equal(f.vm.selectedIds.length,0)
})


test('partial selection preserves the full source ancestors in the preview',async t=>{
 const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.loadPages()
 f.vm.pages=[{page_id:'one',page_title:'统计',directory_path:['进货管理','报表']},{page_id:'two',page_title:'简介',directory_path:[]}]
 f.vm.selection='selected';await f.vm.launch();assert.match(f.warnings.at(-1)!,/请选择要采集的文档/);assert.equal(f.calls.some(call=>call.entry),false);f.vm.selectedIds=['one']
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
 assert.equal(f.vm.directory,null);assert.equal(f.vm.rootName,'');assert.equal(f.vm.selectedIds.length,0);f.vm.selection='all';await f.vm.launch();assert.match(f.warnings.at(-1)!,/目录预览/)
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
 assert.equal(f.vm.url,'https://example.test');assert.equal(f.vm.rootName,'自定义目录');assert.equal(f.vm.previewPages.length,1)
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
 assert.equal(f.vm.fileReceipt.taskFiles,3);assert.equal(f.vm.fileReceipt.failed,false)
 f.vm.showReceiptTasks();assert.equal(f.events.at(-1).target.scope,'internal-a');assert.equal(f.events.at(-1).target.task_id,undefined)
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
