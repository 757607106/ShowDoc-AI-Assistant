<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { nativeAPI, listBases, listMembers } from '@/api/contextdb'
import { useAuthStore } from '@/stores/auth'
import { memberRoleLabel, permissionLabel } from '@/utils/platformPresentation'

const auth=useAuthStore(), profile=ref<any>(null), groups=ref<any[]>([]), members=ref<any[]>([]), acls=ref<any[]>([]), bases=ref<any[]>([])
const error=ref(''), kbId=ref(''), page=ref(1), total=ref(0), profilePage=ref(1), saving=ref(false)
const groupName=ref(''), groupId=ref<number>(), memberId=ref(''), groupRole=ref('member'), canCreateGroup=ref(false)
const principalType=ref('member'), principalId=ref(''), permission=ref('read')
const advanced=computed(()=>profile.value?.mode==='advanced')
const managedGroups=computed(()=>groups.value.filter(group=>group.actions?.can_manage_membership))
const principalOptions=computed(()=>principalType.value==='member'
  ? members.value.map(member=>({value:member.member_id,label:member.member_name}))
  : groups.value.map(group=>({value:String(group.group_id),label:group.name})))
const permissionColumns=computed(()=>[
  {colKey:'knowledge_base_name',title:'知识库'}, {colKey:'current_permission',title:'当前有效权限'},
  ...(!advanced.value?[{colKey:'advanced_permission',title:'高级模式预计权限'}]:[]), {colKey:'direct_permission',title:'直接授权'},
])
async function attempt(fn:()=>Promise<void>){error.value='';try{await fn()}catch(e:any){error.value=e.message}}
async function save(fn:()=>Promise<void>){
  if(saving.value)return
  saving.value=true
  try{await attempt(fn)}finally{saving.value=false}
}
async function loadProfile(){await attempt(async()=>{profile.value=(await nativeAPI.get('workspaces/members/self/permissions',{page:profilePage.value,page_size:35})).data})}
let aclRequest=0
async function loadAcls(){
  const request=++aclRequest, target=kbId.value
  if(!target){acls.value=[];total.value=0;return}
  await attempt(async()=>{
    const res=await nativeAPI.get('workspaces/knowledge_acls',{knowledge_base_id:target,page:page.value,page_size:35})
    if(request===aclRequest){acls.value=res.data.acls;total.value=res.data.total}
  })
}
async function loadGroups(){
  const result:any[]=[]
  for(let page=1;;page++){
    const res=await nativeAPI.get('workspaces/groups',{page,page_size:500})
    result.push(...res.data.groups);canCreateGroup.value=!!res.data.can_create_group
    if(res.data.groups.length<500||result.length>=res.data.total)break
  }
  groups.value=result
}
async function createGroup(){await save(async()=>{
  if(!groupName.value.trim())throw new Error('请输入用户组名称')
  await nativeAPI.post('workspaces/groups',{name:groupName.value.trim()});groupName.value='';await loadGroups()
  MessagePlugin.success('用户组已创建')
})}
async function addMember(){await save(async()=>{
  if(!groupId.value||!memberId.value)throw new Error('请选择用户组和成员')
  await nativeAPI.post('workspaces/groups/members',{group_id:groupId.value,member_id:memberId.value,role:groupRole.value});memberId.value=''
  MessagePlugin.success('组成员已保存')
})}
async function grant(){await save(async()=>{
  if(!kbId.value||!principalOptions.value.some(item=>item.value===principalId.value))throw new Error('请选择知识库和授权对象')
  await nativeAPI.post('workspaces/knowledge_acls',{knowledge_base_id:kbId.value,principal_type:principalType.value,principal_id:principalId.value,permission:permission.value})
  await loadAcls();await loadProfile();MessagePlugin.success('授权已保存')
})}
async function revoke(item:any){await save(async()=>{await nativeAPI.del('workspaces/knowledge_acls?acl_id='+encodeURIComponent(item.acl_id));await loadAcls();await loadProfile()})}
watch(principalType,()=>{principalId.value='';if(principalType.value==='group'&&permission.value==='kb_manage')permission.value='read'})
watch(kbId,()=>{page.value=1;if(advanced.value)void loadAcls()})
void attempt(async()=>{
  await loadProfile();bases.value=(await listBases()).data
  if(advanced.value){await Promise.all([loadGroups(),listMembers().then(result=>members.value=result)]);kbId.value=bases.value[0]?.id||''}
})
</script>

<template>
  <div>
    <h3>知识库权限</h3><t-alert v-if="error" theme="error" :message="error"/>
    <t-descriptions v-if="profile" :column="1">
      <t-descriptions-item label="知识库账号">{{profile.member?.member_name}}</t-descriptions-item>
      <t-descriptions-item label="知识库角色">{{memberRoleLabel(profile.member?.role)}}</t-descriptions-item>
      <t-descriptions-item label="权限模式">{{advanced?'高级权限模式':profile.mode==='personal_compatibility'?'普通模式':'未知模式'}}</t-descriptions-item>
    </t-descriptions>
    <t-table row-key="knowledge_base_id" :data="profile?.knowledge_base_permissions || []" :columns="permissionColumns">
      <template #current_permission="{row}">{{permissionLabel(row.current_permission)}}</template>
      <template #advanced_permission="{row}">{{permissionLabel(row.advanced_permission)}}</template>
      <template #direct_permission="{row}">{{permissionLabel(row.direct_permission)}}</template>
    </t-table>
    <t-pagination :total="profile?.total || 0" :current="profilePage" :page-size="35" :show-page-size="false" @current-change="(v:number)=>{profilePage=v;loadProfile()}"/>
    <template v-if="advanced">
      <h3>知识库授权</h3><t-select v-model="kbId" filterable placeholder="选择知识库" :options="bases.map(b=>({value:b.id,label:b.name}))"/>
      <t-table row-key="acl_id" :data="acls" :columns="[{colKey:'principal_name',title:'授权对象'},{colKey:'principal_type',title:'对象类型'},{colKey:'permission',title:'直接授权'},{colKey:'operation',title:'操作'}]">
        <template #principal_name="{row}">{{row.principal_name||'名称未获取'}}</template>
        <template #principal_type="{row}">{{row.principal_type==='member'?'成员':row.principal_type==='group'?'用户组':'未知类型'}}</template>
        <template #permission="{row}">{{permissionLabel(row.permission)}}</template>
        <template #operation="{row}"><t-popconfirm v-if="row.actions?.can_delete" content="撤销这条直接授权？其他权限来源仍可能保留访问权限。" @confirm="revoke(row)"><t-button :disabled="saving" variant="text" theme="danger">撤销授权</t-button></t-popconfirm></template>
      </t-table>
      <t-pagination :total="total" :current="page" :page-size="35" :show-page-size="false" @current-change="(v:number)=>{page=v;loadAcls()}"/>
      <t-form v-if="auth.hasRole('contributor')" label-align="top" @submit.prevent>
        <t-form-item label="授权对象" required><t-space break-line><t-select v-model="principalType" :options="[{value:'member',label:'成员'},{value:'group',label:'用户组'}]"/><t-select v-model="principalId" filterable :placeholder="principalType==='member'?'选择成员':'选择用户组'" :options="principalOptions"/></t-space></t-form-item>
        <t-form-item label="授予权限"><t-select v-model="permission" :options="[{value:'read',label:'只读'},{value:'write',label:'读写'},...(principalType==='member'&&['owner','admin'].includes(profile?.member?.role)?[{value:'kb_manage',label:'管理'}]:[])]"/></t-form-item>
        <t-button :disabled="!kbId||!principalId" :loading="saving" @click="grant">授权</t-button>
      </t-form>
      <h3>用户组</h3>
      <t-table row-key="group_id" :data="groups" :columns="[{colKey:'name',title:'用户组名称'}]"/>
      <t-space v-if="auth.hasRole('contributor')&&canCreateGroup"><t-input v-model="groupName" placeholder="用户组名称"/><t-button :loading="saving" @click="createGroup">创建用户组</t-button></t-space>
      <t-form v-if="auth.hasRole('contributor')&&managedGroups.length" label-align="top" @submit.prevent>
        <t-form-item label="用户组" required><t-select v-model="groupId" filterable placeholder="选择用户组" :options="managedGroups.map(g=>({value:g.group_id,label:g.name}))"/></t-form-item>
        <t-form-item label="成员" required><t-select v-model="memberId" filterable placeholder="选择成员" :options="members.map(member=>({value:member.member_id,label:member.member_name}))"/></t-form-item>
        <t-form-item label="组内角色"><t-select v-model="groupRole" :options="[{value:'member',label:'组成员'},{value:'group_admin',label:'组管理员'}]"/></t-form-item>
        <t-button :disabled="!groupId||!memberId" :loading="saving" @click="addMember">保存组成员</t-button>
      </t-form>
    </template>
  </div>
</template>
