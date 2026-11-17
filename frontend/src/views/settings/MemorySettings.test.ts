import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive } from 'vue'
import { fixture,flush } from '../../test-utils/vueFixture'

async function setup(t:Parameters<typeof fixture>[0],editor=true){
  const auth=reactive({user:{id:'owner-a'},hasRole:()=>editor})
  const requests:string[]=[],writes:Array<{path:string;body:any}>=[]
  let readFailure=false,saveFailure=false
  let deferRead:((path:string)=>Promise<any>)|undefined,deferWrite:((path:string,body:any)=>Promise<any>)|undefined
  const data=(id:string)=>({content:'note for '+id,file_path:'/memories/'+id+'/AGENTS.md',effective:false})
  const page=fixture(t).component(new URL('./MemorySettings.vue',import.meta.url),{
    '@/stores/auth':{useAuthStore:()=>auth},
    '@/api/agent':{listAgents:async()=>({data:[{id:auth.user.id+'-first',name:'First'},{id:auth.user.id+'-second',name:'Second'}]})},
    '@/utils/request':{
      get:async(path:string)=>{
        requests.push(path)
        if(path.endsWith('/settings'))return {data:{enabled:false,effective:false,storage_mode:'agents_md'}}
        if(deferRead)return deferRead(path)
        if(readFailure)throw new Error('file offline')
        return {data:data(path.split('/')[4])}
      },
      put:async(path:string,body:any)=>{
        writes.push({path,body:JSON.parse(JSON.stringify(body))})
        if(deferWrite)return deferWrite(path,body)
        if(saveFailure)throw new Error('save offline')
        return path.endsWith('/settings')?{data:{enabled:body.enabled,effective:body.enabled}}:{data:{...data(path.split('/')[4]),content:body.content}}
      },
    },
    'tdesign-vue-next':{MessagePlugin:{success(){}}},
  })
  await flush();await flush()
  return {...page,auth,requests,writes,setReadFailure:(value:boolean)=>{readFailure=value},setSaveFailure:(value:boolean)=>{saveFailure=value},
    setDeferredRead:(value:typeof deferRead)=>{deferRead=value},setDeferredWrite:(value:typeof deferWrite)=>{deferWrite=value}}
}

test('file memory reads native files and writes only the personal enabled switch',async t=>{
  const f=await setup(t)
  assert.equal(f.vm.selectedAgentId,'owner-a-first')
  assert.equal(f.vm.content,'note for owner-a-first')
  assert.equal(f.vm.enabled,false)
  assert.equal(f.requests.some(path=>/items|topics|documents|consolidate|tenants/.test(path)),false)
  await f.vm.setEnabled(true)
  assert.deepEqual(f.writes,[{path:'/api/v1/memory/settings',body:{enabled:true}}])
  assert.equal(f.vm.enabled,true)
})

test('an explicit file save permits clearing content and a failure retains the unsaved draft',async t=>{
  const f=await setup(t)
  f.vm.content='';assert.equal(f.vm.dirty,true)
  await f.vm.save()
  assert.deepEqual(f.writes[0],{path:'/api/v1/agents/owner-a-first/memory-file',body:{content:''}})
  assert.equal(f.vm.dirty,false)
  f.vm.content='keep this draft';f.setSaveFailure(true);await f.vm.save()
  assert.equal(f.vm.content,'keep this draft');assert.equal(f.vm.dirty,true);assert.equal(f.vm.error,'save offline')
})

test('a failed read cannot overwrite an unavailable file and can be retried',async t=>{
  const f=await setup(t)
  f.setReadFailure(true);f.vm.selectAgent('owner-a-second');await flush()
  assert.equal(f.vm.file,null);assert.equal(f.vm.error,'file offline')
  f.vm.content='do not write';await f.vm.save();assert.equal(f.writes.length,0)
  f.setReadFailure(false);await f.vm.loadFile();assert.equal(f.vm.content,'note for owner-a-second')
})

test('read-only members can change their preference but cannot save file contents',async t=>{
  const f=await setup(t,false)
  f.vm.content='forbidden';await f.vm.save();assert.equal(f.writes.length,0)
  await f.vm.setEnabled(true);assert.equal(f.writes.length,1)
  assert.equal(f.writes[0].path,'/api/v1/memory/settings')
})

test('switching Agent cannot discard an unsaved file',async t=>{
  const f=await setup(t)
  f.vm.content='draft';f.vm.selectAgent('owner-a-second');assert.equal(f.vm.selectedAgentId,'owner-a-first')
  f.vm.discard();f.vm.selectAgent('owner-a-second');await flush()
  assert.equal(f.vm.selectedAgentId,'owner-a-second');assert.equal(f.vm.content,'note for owner-a-second')
})

test('late reads and saves cannot replace another account memory',async t=>{
  const f=await setup(t)
  let finishRead!:(value:any)=>void
  f.setDeferredRead(()=>new Promise(resolve=>{finishRead=resolve}))
  f.vm.selectAgent('owner-a-second')
  f.setDeferredRead(undefined);f.auth.user.id='owner-b';await flush();await flush()
  finishRead({data:{content:'private old file',file_path:'/old',effective:true}});await flush()
  assert.equal(f.vm.content,'note for owner-b-first')
  let finishSave!:(value:any)=>void
  f.vm.content='old edit';f.setDeferredWrite(()=>new Promise(resolve=>{finishSave=resolve}))
  const pending=f.vm.save()
  f.auth.user.id='owner-c';await flush();await flush()
  finishSave({data:{content:'old edit',file_path:'/old',effective:true}});await pending
  assert.equal(f.vm.content,'note for owner-c-first');assert.equal(f.vm.dirty,false)
})
