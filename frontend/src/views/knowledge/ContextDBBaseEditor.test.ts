import assert from 'node:assert/strict'
import test,{type TestContext} from 'node:test'
import {fixture,flush} from '../../test-utils/vueFixture.ts'
async function setup(t:TestContext,mode:'create'|'edit'='create',write?:()=>Promise<any>){
  const f=fixture(t),calls:any[]=[]
  const {vm}=f.component(new URL('./ContextDBBaseEditor.vue',import.meta.url),{
    'tdesign-vue-next':{MessagePlugin:{error(){},warning(){},success(){}}},
    '@/api/contextdb':{
      getBase:async()=>({data:{name:'官方名称',space_name:'旧别名',wiki_enabled:false,graph_enabled:true,review_enabled:false}}),
      createBase:async(body:any)=>{calls.push(body);return write?write():{data:{id:'created'}}},
      updateBase:async(id:string,body:any)=>{calls.push({id,body});return {data:{id}}},
    },
  },{visible:true,mode,kbId:mode==='edit'?'original':undefined})
  await flush();return {vm,calls}
}
test('new form defaults to Wiki with review off and explicitly saves all six combinations',async t=>{
  const f=await setup(t);assert.equal(f.vm.mode,'wiki');assert.equal(f.vm.reviewEnabled,false)
  for(const mode of ['search','graph','wiki'])for(const review of [false,true]){
    f.vm.name='业务资料';f.vm.mode=mode;f.vm.reviewEnabled=review;await f.vm.save()
    assert.deepEqual(JSON.parse(JSON.stringify(f.calls.at(-1))),{name:'业务资料',description:'',review_enabled:review,indexing_strategy:{wiki_enabled:mode==='wiki',graph_enabled:mode==='graph'}})
  }
})
test('editing reads the official name and current mode, review remains adjustable',async t=>{
  const f=await setup(t,'edit');assert.equal(f.vm.name,'官方名称');assert.equal(f.vm.mode,'graph');assert.equal(f.vm.reviewEnabled,false)
  f.vm.reviewEnabled=true;await f.vm.save();assert.equal(f.calls[0].id,'original');assert.equal(f.calls[0].body.review_enabled,true)
})
test('official name limit accepts 255 characters and rejects 256 before requesting',async t=>{
  const f=await setup(t)
  f.vm.name='知'.repeat(255);await f.vm.save();assert.equal(f.calls[0].name.length,255)
  f.vm.name='知'.repeat(256);await f.vm.save();assert.equal(f.calls.length,1)
})
test('duplicate create clicks cannot submit two libraries',async t=>{
  let finish!:(value:any)=>void
  const f=await setup(t,'create',()=>new Promise(resolve=>{finish=resolve}))
  f.vm.name='业务';const first=f.vm.save();await f.vm.save();assert.equal(f.calls.length,1)
  finish({data:{id:'one'}});await first;assert.equal(f.vm.saving,false)
})
