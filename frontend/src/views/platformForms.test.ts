import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../test-utils/vueFixture.ts'
import * as presentation from '../utils/platformPresentation.ts'
import * as reviewSupport from '../utils/contextdbReviewSupport.ts'
import * as suspendedRun from '../utils/suspendedRun.ts'

function collection(t: TestContext, listing = async () => ({pages:[{page_id:'doc-123',page_title:'操作手册'}]})) {
  const requests: any[]=[]
  const f=fixture(t)
  const {vm}=f.component(new URL('./CollectView.vue',import.meta.url),{
    'vue-router':{useRoute:()=>({fullPath:'/collect',query:{}}),useRouter:()=>({push(){}})},
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/utils/platformPresentation':presentation,
    '@/utils/contextdbReviewSupport':reviewSupport,
    '@/api/knowledgeSpaces':{getSpaces:async()=>({spaces:[{scope:'space-a',name:'产品知识'}]})},
    '@/api/contextdb':{listBases:async()=>({data:[{id:'kb-a',name:'产品知识',wiki_enabled:true,graph_enabled:false}]}),getBasePermissions:async()=>({member:{role:'owner'}}),knowledgeAccess:()=>({write:true}),knowledgeModeLabel:()=> 'Wiki 编译',bindBase:async()=>({space:{scope:'space-a'}})},
    '@/api/backend':{entries:async()=>({entries:[{key:'showdoc',display_name:'ShowDoc'},{key:'web'}]}),entryDocuments:listing,
      startTask:async(entry:string,payload:any)=>{requests.push({entry,payload:JSON.parse(JSON.stringify(payload))});return {task_id:'task-1'}}},
  })
  return {vm,requests}
}

test('ordinary collection fields and named document selection retain the source identifiers in the API',async t=>{
  const {vm,requests}=collection(t);await flush()
  vm.projectId='42';await flush()
  vm.selection='selected';await vm.loadPages();vm.selectedIds=['doc-123']
  await vm.launch()
  assert.deepEqual(requests,[{entry:'showdoc',payload:{item_id:'42',knowledge_base_id:'kb-a',selected_ids:['doc-123']}}])
  vm.selectedIds=[];await vm.launch()
  assert.equal(requests.length,1);assert.equal(vm.error,'请选择要采集的文档')
})

test('web collection validates addresses and preserves explicit crawl limits',async t=>{
  const {vm,requests}=collection(t);await flush()
  vm.entryKey='web';vm.url='not a website';await flush();await vm.launch()
  assert.equal(requests.length,0);assert.match(vm.error,/网站地址/)
  vm.url='https://example.com/manual';vm.crawlMode='site';vm.maxPages=25;vm.maxDepth=2;await flush();await vm.launch()
  assert.deepEqual(requests[0].payload,{url:'https://example.com/manual',crawl_mode:'site',max_pages:25,max_depth:2,knowledge_base_id:'kb-a'})
})

test('a slow document list cannot populate the selector after its source changes',async t=>{
  let resolve!:(value:any)=>void
  const {vm}=collection(t,()=>new Promise(yes=>resolve=yes));await flush()
  vm.projectId='42';await flush()
  const pending=vm.loadPages();vm.entryKey='web';await flush()
  resolve({pages:[{page_id:'wrong-source',page_title:'旧来源'}]});await pending
  assert.equal(vm.pages.length,0);assert.equal(vm.selectedIds.length,0)
})

test('structured metadata edits preserve types, nested data, and unedited fields',t=>{
  const original={product:'A',count:2,enabled:false,nested:{versions:[1,true,null]}}
  const outputs:any[]=[]
  const {vm}=fixture(t).component(new URL('../components/StructuredFields.vue',import.meta.url),{'@/utils/platformPresentation':presentation},
    {modelValue:original,'onUpdate:modelValue':(value:any)=>outputs.push(value)})
  vm.update('count',3)
  assert.equal(outputs[0].count,3);assert.equal(typeof outputs[0].count,'number')
  assert.deepEqual(outputs[0].nested,original.nested);assert.equal(original.count,2)
  vm.rename('product','count');assert.equal(outputs.length,1);assert.match(vm.error,/重复/)
  vm.newName='__proto__';vm.add()
  assert.equal(Object.hasOwn(outputs[1],'__proto__'),true)
  assert.equal(Object.getPrototypeOf(outputs[1]).polluted,undefined)
})

test('read-only operation fields distinguish processing stages and message roles',t=>{
  const original={name:'knowledge.delete_document',ingest_status:'succeeded',graph_status:'succeeded',role:'user'}
  const outputs:any[]=[]
  const {vm}=fixture(t).component(new URL('../components/StructuredFields.vue',import.meta.url),{'@/utils/platformPresentation':presentation},
    {modelValue:original,readonly:true,'onUpdate:modelValue':(value:any)=>outputs.push(value)})
  assert.equal(vm.displayValue('name',original.name),'删除文档')
  assert.equal(vm.displayValue('ingest_status','succeeded'),'已入库')
  assert.equal(vm.displayValue('graph_status','succeeded'),'构建完成')
  assert.equal(vm.displayValue('role','user'),'用户')
  assert.equal(vm.displayValue('role','产品经理'),'产品经理')
  assert.equal(vm.displayValue('enabled',false),'否')
  assert.equal(vm.displayValue('count',0),0)
  vm.update('role','admin');vm.remove('name');vm.newName='new';vm.add()
  assert.equal(outputs.length,0)
  assert.equal(original.role,'user')
})

test('the original document selection retains range and loaded-item behavior',t=>{
  const source=readFileSync(new URL('./knowledge/KnowledgeBase.vue',import.meta.url),'utf8')
  const start=source.indexOf('const toggleSelectRow =')
  const end=source.indexOf('// Batch (multi-select)',start)
  assert.ok(start>=0&&end>start)
  const state=fixture(t).evaluate(`const cardList={value:[{id:'a'},{id:'b'},{id:'c'}]};
    const selectedIds={value:new Set<string>()};let lastSelectedIndex=-1;
    ${source.slice(start,end)}
    export {toggleSelectRow,toggleSelectAll,clearSelection,selectedIds}`,{})
  state.toggleSelectRow('a',true);state.toggleSelectRow('c',true,true)
  assert.deepEqual([...state.selectedIds.value],['a','b','c'])
  state.toggleSelectRow('b',false);assert.deepEqual([...state.selectedIds.value],['a','c'])
  state.clearSelection();assert.equal(state.selectedIds.value.size,0)
  state.toggleSelectAll(true);assert.deepEqual([...state.selectedIds.value],['a','b','c'])
  state.toggleSelectAll(false);assert.equal(state.selectedIds.value.size,0)
})

test('permission selectors use member/group identifiers and reset incompatible selections',async t=>{
  const writes:any[]=[]
  const {vm}=fixture(t).component(new URL('./settings/ContextDBPermissions.vue',import.meta.url),{
    'tdesign-vue-next':{MessagePlugin:{success(){}}},
    '@/utils/platformPresentation':presentation,
    '@/stores/auth':{useAuthStore:()=>({hasRole:()=>true})},
    '@/api/contextdb':{listMembers:async()=>[{member_id:'member-a',member_name:'张三'}],listBases:async()=>({data:[{id:'kb-a',name:'产品资料'}]}),nativeAPI:{
      get:async(path:string)=>({data:path.endsWith('permissions')?{mode:'advanced',member:{role:'owner'},knowledge_base_permissions:[]}
        :path.endsWith('groups')?{groups:[{group_id:12,name:'交付团队',actions:{can_manage_membership:true}}],total:1,can_create_group:true}
        :{acls:[],total:0}}),
      post:async(path:string,body:any)=>writes.push({path,body:JSON.parse(JSON.stringify(body))}),
    }},
  });await flush()
  vm.principalId='member-a';await vm.grant()
  assert.deepEqual(writes[0].body,{knowledge_base_id:'kb-a',principal_type:'member',principal_id:'member-a',permission:'read'})
  vm.permission='kb_manage';vm.principalType='group';await flush()
  assert.equal(vm.principalId,'');assert.equal(vm.permission,'read')
  vm.principalId='12';await vm.grant()
  assert.equal(writes[1].body.principal_id,'12');assert.equal(writes[1].body.principal_type,'group')
  vm.memberId='member-a';vm.groupId=12;await vm.addMember()
  assert.deepEqual(writes[2].body,{group_id:12,member_id:'member-a',role:'member'})
})

test('official approval posts decisions and edited arguments without mutating the source',async t=>{
  const writes:any[]=[]
  const args={actions:[{name:'knowledge.update_base',args:{knowledge_base_id:'kb-a',name:'新名称'}}]}
  const {vm}=fixture(t).component(new URL('./chat/components/ToolApprovalCard.vue',import.meta.url),{
    'vue-i18n':{useI18n:()=>({t:(key:string)=>key})},
    '@/api/mcp-service':{resolveToolApproval:async(id:string,body:any)=>{writes.push({id,...body});return {resumed:false}}},
    '@/api/embed':{resolveEmbedToolApproval:assert.fail},
    '@/utils/suspendedRun':suspendedRun,
    'tdesign-vue-next':{MessagePlugin:{success(){},error(){}}},
    '@/composables/usePromptCountdown':{usePromptCountdown:()=>({})},
    '@/composables/usePromptDock':{usePromptDock:()=>undefined,promptSubmission:()=>undefined,markPromptSubmitted(){}},
    '@/utils/promptKeys':{isSubmitKey:()=>true},
  },{pendingId:'pending-a',serviceName:'ContextDB',mcpToolName:'knowledge.update_base',argsJson:JSON.stringify(args)})
  assert.equal(vm.handleKey({target:null}),true);await flush()
  assert.equal(writes.length,1);assert.equal(writes[0].decision,'approve')
  assert.equal(writes[0].id,'pending-a')
  assert.deepEqual(JSON.parse(JSON.stringify(writes[0].modified_args)),args)
  await vm.submit('reject')
  assert.equal(writes[1].decision,'reject')
  assert.equal(writes[1].modified_args,undefined)
  vm.argsText=JSON.stringify({actions:[]})
  await vm.submit('approve')
  assert.deepEqual(JSON.parse(JSON.stringify(writes[2].modified_args)),{actions:[]})
  vm.argsText='invalid JSON'
  await vm.submit('approve')
  assert.equal(writes.length,3,'invalid JSON cannot reach the approval API')
  assert.deepEqual(args.actions[0].args,{knowledge_base_id:'kb-a',name:'新名称'})
})
