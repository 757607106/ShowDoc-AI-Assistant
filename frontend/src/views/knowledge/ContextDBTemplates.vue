<script setup lang="ts">
import { ref, watch } from 'vue'
import { nativeAPI } from '@/api/contextdb'
import { useAuthStore } from '@/stores/auth'
import DocMarkdown from '@/components/DocMarkdown.vue'
const props=defineProps<{kbId:string}>(),auth=useAuthStore()
const templates=ref<any[]>([]),selected=ref<any>(null),error=ref(''),visible=ref(false)
const name=ref(''),isDefault=ref(false),sections=ref<{level:number;title:string;guidance:string}[]>([])
const root='knowledge/review_templates'
function query(id?:string){return '?'+new URLSearchParams({knowledge_base_id:props.kbId,...(id?{template_id:id}:{})})}
async function attempt(fn:()=>Promise<void>){error.value='';try{await fn()}catch(e:any){error.value=e.message}}
async function load(){await attempt(async()=>{const res=await nativeAPI.get(root+query());templates.value=Array.isArray(res.data)?res.data:res.data.templates||[]})}
function edit(item?:any){selected.value=item||null;name.value=item?.name||'';isDefault.value=item?.is_default||false;sections.value=item?.sections?item.sections.map((section:any)=>({...section})):[{level:1,title:'',guidance:''}];visible.value=true}
async function save(){await attempt(async()=>{
  if(!name.value.trim()||!sections.value.length||sections.value.some(s=>!s.title.trim()||!s.guidance.trim()))throw new Error('请填写模板名称、章节标题和撰写指引')
  const payload={name:name.value,is_default:isDefault.value,sections:sections.value}
  if(selected.value)await nativeAPI.put(root+query(selected.value.id),payload)
  else await nativeAPI.post(root+query(),payload)
  visible.value=false;await load()
})}
async function remove(item:any){await attempt(async()=>{await nativeAPI.del(root+query(item.id));await load()})}
watch(()=>props.kbId,load,{immediate:true})
</script>
<template>
  <div><t-space><span>文档重写模板</span><t-button v-if="auth.hasRole('contributor')" @click="edit()">创建模板</t-button><t-button variant="text" @click="load">刷新</t-button></t-space>
    <t-alert v-if="error" theme="error" :message="error"/>
    <t-table row-key="id" :data="templates" :columns="[{colKey:'name',title:'模板名称'},{colKey:'is_default',title:'默认模板'},{colKey:'operations',title:'操作'}]"><template #is_default="{row}">{{row.is_default?'是':'否'}}</template><template #operations="{row}"><t-button variant="text" @click="edit(row)">{{auth.hasRole('contributor')?'编辑':'查看'}}</t-button><t-popconfirm v-if="auth.hasRole('contributor')" content="删除此模板？" @confirm="remove(row)"><t-button variant="text" theme="danger">删除</t-button></t-popconfirm></template></t-table>
    <t-drawer v-model:visible="visible" header="内容模板" size="640px" :confirm-btn="auth.hasRole('contributor')?'保存':null" @confirm="save"><t-form label-align="top" :disabled="!auth.hasRole('contributor')"><t-form-item label="模板名称" required><t-input v-model="name" :maxlength="128"/></t-form-item><t-form-item label="设为默认模板"><t-switch v-model="isDefault"/></t-form-item><div v-for="(item,i) in sections" :key="i" class="section-row"><t-form-item label="标题级别"><t-input-number v-model="item.level" :min="1" :max="3" :decimal-places="0" /></t-form-item><t-form-item label="章节标题" required><t-input v-model="item.title"/></t-form-item><t-form-item label="撰写指引" required><t-textarea v-model="item.guidance"/></t-form-item><t-button v-if="auth.hasRole('contributor')" variant="text" @click="sections.splice(i,1)">移除章节</t-button></div><t-button v-if="sections.length<15 && auth.hasRole('contributor')" variant="outline" @click="sections.push({level:1,title:'',guidance:''})">添加章节</t-button></t-form><DocMarkdown v-if="selected" :content="selected.content || ''"/><t-alert v-if="error" :message="error" theme="error"/></t-drawer>
  </div>
</template>
<style scoped>.section-row{margin:16px 0;padding:12px;border:1px solid var(--td-component-border);border-radius:var(--app-radius-md)}</style>
