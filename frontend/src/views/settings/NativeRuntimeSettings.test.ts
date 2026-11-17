import assert from 'node:assert/strict'
import test from 'node:test'
import {reactive} from 'vue'
import {fixture,flush} from '../../test-utils/vueFixture'

async function setup(t:Parameters<typeof fixture>[0],admin=true,enabled=true){
  const writes:unknown[]=[],auth=reactive({user:{id:'owner'},hasRole:()=>admin})
  let offline=false
  const {vm}=fixture(t).component(new URL('./NativeRuntimeSettings.vue',import.meta.url),{
    '@/stores/auth':{useAuthStore:()=>auth},
    '@/utils/request':{
      get:async()=>{if(offline)throw new Error('offline');return {data:[{id:'opensandbox-local',name:'OpenSandbox',enabled,read_only:true,sandbox_type:'docker'}]}},
      post:async(path:string,body:any)=>{writes.push({path,body:JSON.parse(JSON.stringify(body))});return {data:{ok:true,checks:[{name:'control',ok:true}]}}},
    },
  })
  await flush()
  return {vm,writes,auth,setOffline:(value:boolean)=>{offline=value}}
}

test('runtime does not probe or create a sandbox automatically; explicit check is shallow',async t=>{
  const f=await setup(t)
  assert.equal(f.vm.sandbox.id,'opensandbox-local');assert.deepEqual(f.writes,[])
  await f.vm.checkConnection()
  assert.deepEqual(f.writes,[{path:'/api/v1/system/sandbox-check',body:{config_id:'opensandbox-local'}}])
  assert.equal(f.vm.connection.ok,true)
})

for(const [name,admin,enabled] of [['read-only user',false,true],['unconfigured runtime',true,false]] as const){
  test(name+' cannot request a control-plane check',async t=>{
    const f=await setup(t,admin,enabled);await f.vm.checkConnection();assert.deepEqual(f.writes,[])
  })
}

test('an unavailable catalog is shown as a failure and can be retried',async t=>{
  const f=await setup(t)
  f.setOffline(true);await f.vm.load();assert.equal(f.vm.error,'offline');assert.equal(f.vm.sandbox,undefined)
  f.setOffline(false);await f.vm.load();assert.equal(f.vm.error,'');assert.equal(f.vm.sandbox.id,'opensandbox-local')
})
