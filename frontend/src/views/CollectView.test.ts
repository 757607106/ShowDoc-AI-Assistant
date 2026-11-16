import assert from 'node:assert/strict'
import test, {type TestContext} from 'node:test'
import {reactive} from 'vue'
import {fixture,flush} from '../test-utils/vueFixture.ts'
async function setup(t:TestContext,failUpload=false,writable=true,directFailure=false){
  const f=fixture(t),calls:any[]=[]
  const route=reactive({query:{kb_id:'a'},fullPath:'/collect?kb_id=a'})
  const {vm}=f.component(new URL('./CollectView.vue',import.meta.url),{
    'vue-router':{useRoute:()=>route,useRouter:()=>({push(){}})},
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/api/backend':{
      entries:async()=>({entries:[{key:'web'},{key:'file'}]}),
      startTask:async(entry:string,payload:any)=>{calls.push({entry,payload});return {task_id:'crawl-1'}},
      uploadFiles:async(files:File[],id:string)=>{calls.push({files,id});if(failUpload)throw new Error('upload unavailable');return {task_id:'file-1'}},
    },
    '@/api/knowledgeSpaces':{getSpaces:async()=>({spaces:[]})},
    '@/api/contextdb':{
      listBases:async()=>({data:[{id:'a',name:'A',wiki_enabled:false,graph_enabled:false},{id:'b',name:'B',graph_enabled:true}]}),
      getBasePermissions:async()=>({}),knowledgeAccess:()=>({write:writable}),knowledgeModeLabel:()=> '零编译',
      uploadDocumentFile:async(id:string,file:File)=>{calls.push({direct:id,file});if(directFailure)throw new Error('direct unavailable');return {data:{id:'large-doc'}}},
      bindBase:async(id:string)=>{calls.push({binding:id});return {space:{scope:'internal-a'}}},
    },
    '@/utils/contextdbReviewSupport':{CONTEXTDB_REVIEW_FORMAT_NOTICE:''},
  })
  await flush();return {vm,calls,route}
}
test('crawler and file uploads use the chosen native library and resolve scope without a user association',async t=>{
  const f=await setup(t);f.vm.url='https://example.test';await flush();await f.vm.launch()
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
