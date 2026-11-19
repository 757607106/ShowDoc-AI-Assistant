<script setup lang="ts">
import TenantInfo from './TenantInfo.vue'
import ContextDBPermissions from './ContextDBPermissions.vue'
import ModelSettings from './ModelSettings.vue'
import DefaultSettings from './DefaultSettings.vue'
import NativeRuntimeSettings from './NativeRuntimeSettings.vue'
import MemorySettings from './MemorySettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import UserProfile from './UserProfile.vue'
import { useModalShell } from '@/composables/useModalShell'
import { toolboxLocation } from '@/config/toolbox'
import { ref, computed, watch, onMounted, onUnmounted, nextTick, useId, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { get, post, patch } from '@/utils/request'
import { listMembers } from '@/api/contextdb'
import { memberRoleLabel } from '@/utils/platformPresentation'
import { cycleDialogFocus } from '../../utils/dialogFocus'
import { registerUnsavedChanges } from '../../utils/unsavedChanges'
import SettingsModalShell from '@/components/SettingsModalShell.vue'
import { MessagePlugin } from 'tdesign-vue-next'
const auth=useAuthStore(),ui=useUIStore(),route=useRoute(),router=useRouter()
const section=ref('account'),users=ref<any[]>([]),members=ref<any[]>([]),health=ref<any>(null),models=ref<any[]>([])
const retiredSection=ref('')
const error=ref(''),formOpen=ref(false),editing=ref(''),account=ref(''),username=ref(''),password=ref(''),key=ref(''),role=ref('viewer')
const memberForm=ref<HTMLElement>(), memberSaving=ref(false), invalidMemberField=ref<''|'account'|'password'>('')
const memberFormId=useId()
const memberDialogTitle=computed(()=>editing.value?'编辑成员':'添加成员')
let memberOpener:HTMLElement|undefined
const visible=computed(()=>ui.showSettingsModal||route.name==='settings')
const groups=computed(()=>[{key:'platform',label:'平台',items:[{key:'account',icon:'user',label:'当前账号'},{key:'tenant',icon:'user-circle',label:'空间信息'},...(auth.hasRole('admin')?[{key:'members',icon:'usergroup',label:'成员管理'}]:[]),{key:'permissions',icon:'secured',label:'知识库权限'},{key:'runtime',icon:'server',label:'运行状态'}]},
  {key:'personal',label:'个人',items:[{key:'general',icon:'setting',label:'常规设置'},{key:'userprofile',icon:'user',label:'个人资料'}]},
  {key:'agent',label:'智能体',items:[{key:'models',icon:'chat',label:'模型配置'},{key:'defaults',icon:'setting',label:'空间默认配置'},{key:'memory',icon:'bookmark',label:'文件记忆'},{key:'sandbox',icon:'code',label:'运行环境'}]}])
const memberColumns=[{colKey:'username',title:'显示名称'},{colKey:'account',title:'账号'},{colKey:'role',title:'平台角色'},{colKey:'contextdb_member_id',title:'知识库账号'},{colKey:'active',title:'账号状态'},{colKey:'operation',title:'操作'}]
const compactMemberColumns=[{colKey:'member',title:'成员'},{colKey:'operation',title:'操作',width:114}]
const compactMemberMedia=window.matchMedia?.('(max-width: 760px)')
const compactMembers=ref(compactMemberMedia?.matches ?? false)
function syncMemberLayout(event:MediaQueryListEvent){compactMembers.value=event.matches}
function memberBindingLabel(id?:string){
  return id?(members.value.find(member=>member.member_id===id)?.member_name||'已绑定'):'未绑定'
}

interface DraftEditor {
  dirty:boolean
  saving:boolean
  saveDraft:()=>Promise<void>
  discardDraft:()=>void
}
const tenantEditor=ref<DraftEditor>()
const memoryEditor=ref<DraftEditor & {selectAgent:(id:string)=>void}>()
const draftEditor=computed(()=>section.value==='tenant'?tenantEditor.value:section.value==='memory'?memoryEditor.value:undefined)
const pendingDraft=shallowRef<{editor:DraftEditor;proceed:()=>void;stay:()=>void}>()
const draftSaving=ref(false),draftSaveFailed=ref(false),draftActions=ref<HTMLElement>()
let restoreDraftFocus:HTMLElement|null=null

function requestDraft(proceed:()=>void,stay=()=>{},opener?:HTMLElement){
  if(pendingDraft.value){stay();return}
  const editor=draftEditor.value
  if(!editor?.dirty){proceed();return}
  restoreDraftFocus=opener ?? document.activeElement as HTMLElement|null
  draftSaveFailed.value=false
  pendingDraft.value={editor,proceed,stay}
  void nextTick(()=>draftActions.value?.querySelector('button')?.focus({preventScroll:true}))
}
async function resolveDraft(action:'keep'|'discard'|'save'){
  const pending=pendingDraft.value
  if(!pending||draftSaving.value)return
  if(action==='save'){
    if(pending.editor.saving)return
    draftSaveFailed.value=false
    draftSaving.value=true
    try{
      await pending.editor.saveDraft()
      draftSaveFailed.value=pending.editor.dirty
    }catch{
      draftSaveFailed.value=true
    }finally{
      draftSaving.value=false
    }
    if(draftSaveFailed.value){
      await nextTick()
      draftActions.value?.querySelector('button')?.focus({preventScroll:true})
      return
    }
  }
  if(action==='discard'){
    if(pending.editor.saving)return
    pending.editor.discardDraft()
    if(pending.editor.dirty)return
  }
  pendingDraft.value=undefined
  if(action==='keep')pending.stay()
  else{
    restoreDraftFocus=null
    pending.proceed()
  }
}
function returnDraftFocus(){
  restoreDraftFocus?.focus({preventScroll:true})
  restoreDraftFocus=null
}
function switchAgent(id:string,opener?:HTMLElement){requestDraft(()=>memoryEditor.value?.selectAgent(id),undefined,opener)}

function selectSection(value?:string|null){
  if(!value)return
  const target=value==='mymemory'?'memory':value==='system'?'runtime':value==='model-catalog'?'models':value
  if(target===section.value){applySection(value,target);return}
  requestDraft(()=>applySection(value,target))
}
function applySection(value:string,target:string){
  if(value==='model-catalog')MessagePlugin.info('当前部署未提供模型目录管理，已打开模型配置。')
  if(target==='mcp'||target==='skills'||target==='toolbox'||target==='agents'){
    const location=target==='agents'?'/platform/agents':toolboxLocation(target==='toolbox'?undefined:target,ui.settingsInitialSubSection||undefined)
    ui.closeSettings();void router.push(location);return
  }
  if(groups.value.some(group=>group.items.some(item=>item.key===target))){section.value=target;retiredSection.value=''}
  else{section.value='retired';retiredSection.value=value}
  if(route.name==='settings'&&route.query.section!==target)void router.replace({path:'/platform/settings',query:{section:target}})
}
function navigateSettings(event:Event){selectSection((event as CustomEvent).detail?.section)}
watch(()=>ui.settingsInitialSection,value=>{if(visible.value)selectSection(value)},{immediate:true})
watch(()=>route.query.section,value=>{if(visible.value)selectSection(typeof value==='string'?value:undefined)},{immediate:true})
watch(groups,()=>{if(section.value!=='retired'&&!groups.value.some(group=>group.items.some(item=>item.key===section.value)))section.value='account'})
let removeRouteGuard:()=>void,removeAfterRoute:()=>void,unregisterDraft:()=>void
function warnBeforeUnload(event:BeforeUnloadEvent){
  if(visible.value&&draftEditor.value?.dirty){
    event.preventDefault()
    event.returnValue=''
  }
}
onMounted(()=>{
  window.addEventListener('settings-nav',navigateSettings)
  window.addEventListener('beforeunload',warnBeforeUnload)
  compactMemberMedia?.addEventListener('change',syncMemberLayout)
  unregisterDraft=registerUnsavedChanges(()=>visible.value&&!!draftEditor.value?.dirty)
  removeRouteGuard=router.beforeEach((to,from)=>{
    if(from.name==='settings'&&to.fullPath!==from.fullPath&&draftEditor.value?.dirty){
      return new Promise<boolean>(resolve=>requestDraft(()=>resolve(true),()=>resolve(false)))
    }
  })
  removeAfterRoute=router.afterEach((to,from,failure)=>{
    if(!failure&&from.name==='settings'&&to.name!=='settings')ui.closeSettings()
  })
})
onUnmounted(()=>{
  window.removeEventListener('settings-nav',navigateSettings)
  window.removeEventListener('beforeunload',warnBeforeUnload)
  compactMemberMedia?.removeEventListener('change',syncMemberLayout)
  removeRouteGuard()
  removeAfterRoute()
  unregisterDraft()
  pendingDraft.value?.stay()
})
async function attempt(fn:()=>Promise<void>){error.value='';try{await fn()}catch(e:any){error.value=e.message}}
async function load(){await attempt(async()=>{
  if(section.value==='members'&&auth.hasRole('admin')){
    users.value=((await get('/api/platform/users')).users||[]).map((user:any)=>({...user,account:user.account??user.email??''}))
    try{members.value=await listMembers()}catch{members.value=[]}
  }

  if(section.value==='runtime'){health.value=await get('/api/health');models.value=(await get('/api/v1/models')).data}
})}
function close(){
  ui.closeSettings()
  if(route.name==='settings'){
    const back=router.options?.history?.state?.back
    if(typeof back==='string'&&back.startsWith('/platform/'))router.back()
    else void router.push('/platform/knowledge-bases')
  }
}
const shell=useModalShell({visible:()=>visible.value,close:()=>requestDraft(close),ignoreEscape:()=>!!pendingDraft.value})
function edit(user?:any,event?:Event){
  memberOpener=event?.currentTarget as HTMLElement|undefined
  error.value='';invalidMemberField.value=''
  editing.value=user?.id||'';account.value=user?.account??user?.email??'';username.value=user?.username||'';role.value=user?.role||'viewer';password.value='';key.value=''
  formOpen.value=true
  void nextTick(()=>{
    memberForm.value?.querySelectorAll<HTMLInputElement>('input[name]').forEach(input=>{input.id=`${memberFormId}-${input.name}`})
    memberForm.value?.querySelector<HTMLElement>('input:not(:disabled)')?.focus({preventScroll:true})
  })
}
function restoreMemberFocus(){
  memberOpener?.focus({preventScroll:true})
  memberOpener=undefined
}
async function save(){
  if(memberSaving.value)return
  invalidMemberField.value=''
  await attempt(async()=>{
    if(!editing.value&&!account.value.trim()){
      invalidMemberField.value='account';throw new Error('请输入账号')
    }
    if((!editing.value||password.value)&&(password.value.length<8||password.value.length>1024)){
      invalidMemberField.value='password';throw new Error('密码长度须为 8 至 1024 位')
    }
    memberSaving.value=true
    try{
      if(editing.value)await patch(`/api/platform/users/${editing.value}`,{role:role.value,password:password.value||undefined,contextdb_api_key:key.value||undefined})
      else await post('/api/platform/users',{account:account.value.trim(),username:username.value.trim()||account.value.trim(),password:password.value,role:role.value,contextdb_api_key:key.value||undefined})
      key.value='';password.value='';formOpen.value=false;await load();MessagePlugin.success('账号已保存')
    }finally{memberSaving.value=false}
  })
  if(invalidMemberField.value)memberForm.value?.querySelector<HTMLElement>(`input[name="${invalidMemberField.value}"]`)?.focus()
}
async function toggle(user:any){await attempt(async()=>{await patch(`/api/platform/users/${user.id}`,{active:!user.active});await load()})}
watch([visible,section],()=>{if(visible.value)void load()},{immediate:true})
</script>
<template>
  <SettingsModalShell :visible="visible" title="设置" compact-nav-label="切换设置" :model-value="section" :nav-groups="groups" @update:model-value="selectSection" @close="shell.requestClose">
    <div class="native-settings">
      <t-alert v-if="error&&!formOpen&&!invalidMemberField" theme="error" :message="error"/>
      <template v-if="section==='account'"><h3>当前账号</h3><t-descriptions :column="1" bordered><t-descriptions-item label="显示名称">{{auth.user?.username}}</t-descriptions-item><t-descriptions-item label="账号">{{auth.user?.account||auth.user?.email}}</t-descriptions-item><t-descriptions-item label="平台角色">{{memberRoleLabel(auth.user?.platform_role)}}</t-descriptions-item></t-descriptions></template>
      <TenantInfo v-else-if="section==='tenant'" ref="tenantEditor"/>
      <template v-else-if="section==='members'"><h3>成员管理</h3><t-button @click="edit(undefined,$event)">添加成员</t-button>
        <t-table row-key="id" :data="users" :columns="compactMembers?compactMemberColumns:memberColumns" :show-header="!compactMembers">
          <template #member="{row}">
            <div class="member-summary">
              <strong>{{row.username||row.account}}</strong>
              <span v-if="row.username&&row.account&&row.username!==row.account">{{row.account}}</span>
              <span>{{memberRoleLabel(row.role)}} · {{row.active?'已启用':'已禁用'}}</span>
              <span>{{'知识库账号 · '+memberBindingLabel(row.contextdb_member_id)}}</span>
            </div>
          </template>
          <template #role="{row}">{{memberRoleLabel(row.role)}}</template>
          <template #contextdb_member_id="{row}"><span :title="row.contextdb_member_id">{{memberBindingLabel(row.contextdb_member_id)}}</span></template>
          <template #active="{row}">{{row.active?'已启用':'已禁用'}}</template>
          <template #operation="{row}"><t-button variant="text" @click="edit(row,$event)">编辑</t-button><t-popconfirm v-if="row.id!==auth.user?.id" :content="row.active?'禁用该账号并使登录失效？':'启用该账号？'" @confirm="toggle(row)"><t-button variant="text">{{row.active?'禁用':'启用'}}</t-button></t-popconfirm></template>
        </t-table></template>
      <ContextDBPermissions v-else-if="section==='permissions'"/>
      <GeneralSettings v-else-if="section==='general'"/>
      <UserProfile v-else-if="section==='userprofile'"/>
      <ModelSettings v-else-if="section==='models'"/>
      <DefaultSettings v-else-if="section==='defaults'"/>
      <MemorySettings v-else-if="section==='memory'" ref="memoryEditor" @switch-agent="switchAgent"/>
      <NativeRuntimeSettings v-else-if="section==='sandbox'"/>
      <template v-else-if="section==='retired'"><h3>该设置已停用</h3><t-alert theme="info" :message="`旧入口 ${retiredSection} 不再提供。知识库仍由 ContextDB 管理，Agent 使用原生工具、技能、文件记忆和运行环境。`"/><t-button variant="outline" @click="selectSection('models')">打开模型配置</t-button></template>
      <template v-else><h3>运行状态</h3><t-descriptions v-if="health" :column="1" bordered><t-descriptions-item label="平台数据库">{{health.database?'可用':'不可用'}}</t-descriptions-item><t-descriptions-item label="任务处理服务">{{!health.database?'状态未获取':health.worker?'运行中':'未检测到运行'}}</t-descriptions-item><t-descriptions-item label="对话模型">{{models.map(m=>m.name).join('、') || '未获取'}}</t-descriptions-item></t-descriptions></template>
    </div>
  </SettingsModalShell>
  <t-dialog :visible="!!pendingDraft" attach="body" placement="center" width="min(480px, calc(100vw - 32px))"
    header="有未保存修改" role="dialog" aria-modal="true" aria-label="有未保存修改"
    :close-btn="false" :close-on-overlay-click="false" :close-on-esc-keydown="!draftSaving"
    @keydown.tab="cycleDialogFocus" @close="resolveDraft('keep')" @closed="returnDraftFocus">
    <t-alert v-if="draftSaveFailed" theme="error" message="保存失败，修改已保留。" role="alert"/>
    <template #footer>
      <div ref="draftActions" class="draft-actions">
        <t-button variant="outline" :disabled="draftSaving" @click="resolveDraft('keep')">继续编辑</t-button>
        <t-button theme="danger" variant="outline" :disabled="draftSaving||pendingDraft?.editor.saving" @click="resolveDraft('discard')">放弃并继续</t-button>
        <t-button :loading="draftSaving" :disabled="pendingDraft?.editor.saving&&!draftSaving" @click="resolveDraft('save')">保存并继续</t-button>
      </div>
    </template>
  </t-dialog>
  <t-dialog v-model:visible="formOpen" attach="body" width="min(480px, calc(100vw - 32px))" placement="center"
    role="dialog" aria-modal="true" :aria-label="memberDialogTitle" :header="memberDialogTitle"
    :confirm-loading="memberSaving" :cancel-btn="{disabled:memberSaving}" :close-btn="!memberSaving"
    :close-on-overlay-click="!memberSaving" :close-on-esc-keydown="!memberSaving"
    @keydown.tab="cycleDialogFocus" @confirm="save" @closed="restoreMemberFocus">
    <div ref="memberForm">
      <t-form label-align="top" :disabled="memberSaving">
        <t-form-item label="账号" :for="`${memberFormId}-account`" :required-mark="!editing"
          :status="invalidMemberField==='account'?'error':undefined" :tips="invalidMemberField==='account'?error:undefined">
          <t-input v-model="account" name="account" :disabled="!!editing" autocomplete="username"/>
        </t-form-item>
        <t-form-item label="显示名称" :for="`${memberFormId}-username`">
          <t-input v-model="username" name="username" :disabled="!!editing"/>
        </t-form-item>
        <t-form-item label="平台角色">
          <t-select v-model="role" :options="[{value:'admin',label:'管理员'},{value:'editor',label:'编辑者'},{value:'viewer',label:'只读成员'}]"/>
        </t-form-item>
        <t-form-item :label="editing?'新密码':'密码'" :for="`${memberFormId}-password`" help="8 至 1024 位"
          :required-mark="!editing" :status="invalidMemberField==='password'?'error':undefined"
          :tips="invalidMemberField==='password'?error:undefined">
          <t-input v-model="password" type="password" name="password" :placeholder="editing?'留空保持原密码':''" autocomplete="new-password"/>
        </t-form-item>
        <t-form-item label="ContextDB 成员 API 密钥" :for="`${memberFormId}-key`">
          <t-input v-model="key" type="password" name="key" :placeholder="editing?'留空保持原绑定':'选填，可稍后绑定'" autocomplete="off"/>
        </t-form-item>
      </t-form>
      <t-alert v-if="error&&!invalidMemberField" theme="error" :message="error"/>
    </div>
  </t-dialog>
</template>
<style scoped>
.native-settings{padding:24px}
pre{white-space:pre-wrap;overflow:auto;max-height:450px}
h3{margin-top:0}
.member-summary{display:grid;gap:4px;overflow-wrap:anywhere}
.member-summary span{color:var(--td-text-color-secondary)}
.draft-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}
</style>
