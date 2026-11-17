<script setup lang="ts">
import ContextDBPermissions from './ContextDBPermissions.vue'
import ModelSettings from './ModelSettings.vue'
import DefaultSettings from './DefaultSettings.vue'
import WebSearchSettings from './WebSearchSettings.vue'
import SandboxSettings from './SandboxSettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import UserProfile from './UserProfile.vue'
import AssistantSettings from './AssistantSettings.vue'
import ChatHistorySettings from './ChatHistorySettings.vue'
import { useDeploymentCapabilitiesStore } from '@/stores/deploymentCapabilities'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { get, post, patch } from '@/utils/request'
import { listMembers } from '@/api/contextdb'
import { memberRoleLabel } from '@/utils/platformPresentation'
import SettingsModalShell from '@/components/SettingsModalShell.vue'
import { MessagePlugin } from 'tdesign-vue-next'
const auth=useAuthStore(),ui=useUIStore(),route=useRoute(),router=useRouter()
const section=ref('account'),users=ref<any[]>([]),members=ref<any[]>([]),health=ref<any>(null),models=ref<any[]>([])
const capabilities=useDeploymentCapabilitiesStore()
const error=ref(''),formOpen=ref(false),editing=ref(''),account=ref(''),username=ref(''),password=ref(''),key=ref(''),role=ref('viewer')
const visible=computed(()=>ui.showSettingsModal||route.name==='settings')
const groups=computed(()=>[{key:'platform',label:'平台',items:[{key:'account',icon:'user',label:'当前账号'},...(auth.hasRole('admin')?[{key:'members',icon:'usergroup',label:'成员管理'}]:[]),{key:'permissions',icon:'secured',label:'知识库权限'},{key:'runtime',icon:'server',label:'运行状态'}]},
  {key:'personal',label:'个人',items:[{key:'general',icon:'setting',label:'常规设置'},{key:'userprofile',icon:'user',label:'个人资料'},{key:'assistant',icon:'chat',label:'页面助手'}]},
  {key:'agent',label:'智能体',items:[{key:'models',icon:'chat',label:'模型配置'},{key:'defaults',icon:'setting',label:'默认配置'},...(auth.hasRole('admin')?[{key:'chathistory',icon:'history',label:'对话历史'}]:[]),...(auth.hasRole('admin')&&capabilities.isSupported('settings.websearch')?[{key:'websearch',icon:'internet',label:'网络搜索'}]:[]),...(auth.hasRole('admin')&&capabilities.isSupported('settings.sandbox')?[{key:'sandbox',icon:'code',label:'会话文件'}]:[]),{key:'toolbox',icon:'tools',label:'工具箱'}]}])
function selectSection(value?:string|null){
  if(value==='mcp'||value==='skills'||value==='toolbox'){
    ui.closeSettings();void router.push(`/platform/toolbox${value==='toolbox'?'':`/${value}`}`);return
  }
  if(groups.value.some(group=>group.items.some(item=>item.key===value)))section.value=value!
}
function navigateSettings(event:Event){selectSection((event as CustomEvent).detail?.section)}
watch(()=>ui.settingsInitialSection,selectSection,{immediate:true})
watch(()=>route.query.section,value=>selectSection(typeof value==='string'?value:undefined),{immediate:true})
watch(section,value=>{if(value==='toolbox')selectSection(value)})
onMounted(()=>window.addEventListener('settings-nav',navigateSettings))
onUnmounted(()=>window.removeEventListener('settings-nav',navigateSettings))
async function attempt(fn:()=>Promise<void>){error.value='';try{await fn()}catch(e:any){error.value=e.message}}
async function load(){await attempt(async()=>{
  if(section.value==='members'&&auth.hasRole('admin')){
    users.value=((await get('/api/platform/users')).users||[]).map((user:any)=>({...user,account:user.account??user.email??''}))
    try{members.value=await listMembers()}catch{members.value=[]}
  }

  if(section.value==='runtime'){health.value=await get('/api/health');models.value=(await get('/api/v1/models')).data}
})}
function close(){ui.closeSettings();if(route.name==='settings')router.push('/platform/knowledge-bases')}
function edit(user?:any){editing.value=user?.id||'';account.value=user?.account??user?.email??'';username.value=user?.username||'';role.value=user?.role||'viewer';password.value='';key.value='';formOpen.value=true}
async function save(){await attempt(async()=>{
  if(!editing.value&&!account.value.trim())throw new Error('请输入账号')
  if((!editing.value||password.value)&&(password.value.length<8||password.value.length>1024))throw new Error('密码长度须为 8 至 1024 位')
  if(editing.value)await patch(`/api/platform/users/${editing.value}`,{role:role.value,password:password.value||undefined,contextdb_api_key:key.value||undefined})
  else await post('/api/platform/users',{account:account.value.trim(),username:username.value.trim()||account.value.trim(),password:password.value,role:role.value,contextdb_api_key:key.value||undefined})
  key.value='';password.value='';formOpen.value=false;await load();MessagePlugin.success('账号已保存')
})}
async function toggle(user:any){await attempt(async()=>{await patch(`/api/platform/users/${user.id}`,{active:!user.active});await load()})}
watch([visible,section],()=>{if(visible.value)void load()},{immediate:true})
</script>
<template>
  <SettingsModalShell :visible="visible" title="设置" v-model="section" :nav-groups="groups" @close="close">
    <div class="native-settings">
      <t-alert v-if="error" theme="error" :message="error"/>
      <template v-if="section==='account'"><h3>当前账号</h3><t-descriptions :column="1" bordered><t-descriptions-item label="显示名称">{{auth.user?.username}}</t-descriptions-item><t-descriptions-item label="账号">{{auth.user?.account||auth.user?.email}}</t-descriptions-item><t-descriptions-item label="平台角色">{{memberRoleLabel(auth.currentTenantRole)}}</t-descriptions-item></t-descriptions></template>
      <template v-else-if="section==='members'"><h3>成员管理</h3><t-button @click="edit()">添加成员</t-button>
        <t-table row-key="id" :data="users" :columns="[{colKey:'username',title:'显示名称'},{colKey:'account',title:'账号'},{colKey:'role',title:'平台角色'},{colKey:'contextdb_member_id',title:'知识库账号'},{colKey:'active',title:'账号状态'},{colKey:'operation',title:'操作'}]">
          <template #role="{row}">{{memberRoleLabel(row.role)}}</template>
          <template #contextdb_member_id="{row}"><span :title="row.contextdb_member_id">{{row.contextdb_member_id?(members.find(member=>member.member_id===row.contextdb_member_id)?.member_name||'已绑定'):'未绑定'}}</span></template>
          <template #active="{row}">{{row.active?'已启用':'已禁用'}}</template>
          <template #operation="{row}"><t-button variant="text" @click="edit(row)">编辑</t-button><t-popconfirm v-if="row.id!==auth.user?.id" :content="row.active?'禁用该账号并使登录失效？':'启用该账号？'" @confirm="toggle(row)"><t-button variant="text">{{row.active?'禁用':'启用'}}</t-button></t-popconfirm></template>
        </t-table></template>
      <ContextDBPermissions v-else-if="section==='permissions'"/>
      <GeneralSettings v-else-if="section==='general'"/>
      <UserProfile v-else-if="section==='userprofile'"/>
      <AssistantSettings v-else-if="section==='assistant'"/>
      <ChatHistorySettings v-else-if="section==='chathistory' && auth.hasRole('admin')"/>
      <ModelSettings v-else-if="section==='models'"/>
      <DefaultSettings v-else-if="section==='defaults'"/>
      <WebSearchSettings v-else-if="section==='websearch' && auth.hasRole('admin')"/>
      <SandboxSettings v-else-if="section==='sandbox' && auth.hasRole('admin')"/>
      <template v-else><h3>运行状态</h3><t-descriptions v-if="health" :column="1" bordered><t-descriptions-item label="平台数据库">{{health.database?'可用':'不可用'}}</t-descriptions-item><t-descriptions-item label="任务处理服务">{{!health.database?'状态未获取':health.worker?'运行中':'未检测到运行'}}</t-descriptions-item><t-descriptions-item label="对话模型">{{models.map(m=>m.name).join('、') || '未获取'}}</t-descriptions-item></t-descriptions></template>
    </div>
  </SettingsModalShell>
  <t-dialog v-model:visible="formOpen" :header="editing?'编辑成员':'添加成员'" @confirm="save"><t-form label-align="top"><t-form-item label="账号" :required="!editing"><t-input v-model="account" :disabled="!!editing" autocomplete="username"/></t-form-item><t-form-item label="显示名称"><t-input v-model="username" :disabled="!!editing"/></t-form-item><t-form-item label="平台角色"><t-select v-model="role" :options="[{value:'admin',label:'管理员'},{value:'editor',label:'编辑者'},{value:'viewer',label:'只读成员'}]"/></t-form-item><t-form-item :label="editing?'新密码':'密码'" help="8 至 1024 位" :required="!editing"><t-input type="password" v-model="password" :placeholder="editing?'留空保持原密码':''" autocomplete="new-password"/></t-form-item><t-form-item label="ContextDB 成员 API 密钥"><t-input type="password" v-model="key" :placeholder="editing?'留空保持原绑定':'选填，可稍后绑定'" autocomplete="off"/></t-form-item></t-form><t-alert v-if="error" theme="error" :message="error"/></t-dialog>
</template>
<style scoped>.native-settings{padding:24px}pre{white-space:pre-wrap;overflow:auto;max-height:450px}h3{margin-top:0}</style>
