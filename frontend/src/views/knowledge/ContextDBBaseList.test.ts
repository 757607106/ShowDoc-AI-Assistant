import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import test,{type TestContext} from 'node:test'
import {fixture,flush} from '../../test-utils/vueFixture.ts'
const plain=(value:any)=>JSON.parse(JSON.stringify(value))
async function setup(t:TestContext,options:{permission?:any;remove?:()=>Promise<any>;list?:()=>Promise<any>}={}){
  const f=fixture(t),calls:any[]=[],routes:any[]=[]
  const helper=f.evaluate(readFileSync(new URL('../../api/contextdb.ts',import.meta.url),'utf8'),{'@/utils/request':{},'@/utils/contextdbDocumentName':{}})
  const libraries=Array.from({length:14},(_,i)=>({id:'kb-'+i,name:'业务'+String(i).padStart(2,'0'),wiki_enabled:i%3===0,graph_enabled:i%3===1,review_enabled:i%2===0,document_count:i,updated_at:'2026-11-'+String(i+1).padStart(2,'0')}))
  const {vm}=f.component(new URL('./ContextDBSpaces.vue',import.meta.url),{
    'vue-router':{useRouter:()=>({push:(value:any)=>routes.push(value)})},
    'tdesign-vue-next':{MessagePlugin:{success(){}}},
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/api/contextdb':{...helper,listBases:options.list||(async()=>({data:libraries})),
      getBasePermissions:async()=>options.permission||{member:{role:'owner'}},
      updateBase:async(id:string,body:any)=>{calls.push({id,body})},
      deleteBase:async(id:string)=>{calls.push({deleted:id});return options.remove?.()},
    },
    '@/utils/platformPresentation':{dateTime:(value:any)=>value||''},
  })
  await flush();return {vm,calls,routes,libraries}
}
test('one native library list covers all modes, server data, searching, sorting and pagination',async t=>{
  const f=await setup(t);assert.equal(f.vm.bases.length,14);assert.equal(f.vm.visibleBases.length,12)
  assert.equal(f.vm.visibleBases[0].id,'kb-13');f.vm.page=2;assert.equal(f.vm.visibleBases.length,2)
  f.vm.order='name';await flush();assert.equal(f.vm.page,1);assert.equal(f.vm.visibleBases[0].name,'业务00')
  f.vm.query='业务03';await flush();assert.equal(f.vm.filtered.length,1)
  f.vm.open(f.libraries[3],'wiki');assert.deepEqual(plain(f.routes[0]),{path:'/platform/knowledge-bases/kb-3',query:{tab:'wiki'}})
  assert.equal(f.vm.menu(f.libraries[0]).some((item:any)=>item.value==='wiki'),true)
  assert.equal(f.vm.menu(f.libraries[1]).some((item:any)=>item.value==='wiki'),false)
})
test('rename uses the original cloud ID; a failed nonempty delete never removes or clears documents',async t=>{
  const f=await setup(t,{remove:async()=>{throw new Error('409 knowledge base not empty')}})
  f.vm.act(f.libraries[0],'rename');f.vm.name='改后的业务';await f.vm.rename()
  assert.deepEqual(plain(f.calls[0]),{id:'kb-0',body:{name:'改后的业务'}})
  f.vm.act(f.libraries[0],'delete');await f.vm.remove()
  assert.equal(f.vm.deleting.id,'kb-0');assert.match(f.vm.actionError,/409.*非空/);assert.equal(f.vm.bases.length,14)
  assert.deepEqual(plain(f.calls[1]),{deleted:'kb-0'})
})
test('read-only official grants retain visible data but no create or management actions',async t=>{
  const f=await setup(t,{permission:{mode:'advanced',member:{role:'member'},knowledge_base_permissions:[{knowledge_base_id:'kb-0',current_permission:'read'}]}})
  assert.equal(f.vm.canCreate,false);assert.deepEqual(plain(f.vm.menu(f.libraries[0])),[{content:'知识 Wiki',value:'wiki'}])
  f.vm.act(f.libraries[0],'delete');assert.equal(f.vm.deleting,null);assert.equal(f.calls.length,0)
})
test('the latest refresh wins over an older delayed official library response',async t=>{
  let resolve!:(value:any)=>void,count=0
  const f=await setup(t,{list:()=>++count===1?new Promise(yes=>{resolve=yes}):Promise.resolve({data:[{id:'new',name:'新',wiki_enabled:false,graph_enabled:false}]})})
  await f.vm.load();resolve({data:[{id:'old',name:'旧'}]});await flush()
  assert.equal(f.vm.bases[0].id,'new');assert.equal(f.vm.loading,false)
})
