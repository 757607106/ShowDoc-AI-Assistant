<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getBasePermissions, knowledgeAccess, listBases, type BasePermissionProfile } from '@/api/contextdb'
import ContextDBReviewSettings from './ContextDBReviewSettings.vue'
import ContextDBTemplates from './ContextDBTemplates.vue'
const route=useRoute(),router=useRouter(),auth=useAuthStore()
const kbId=computed(()=>String(route.params.kbId||'')),bases=ref<any[]>([]),profile=ref<BasePermissionProfile|null>(null),error=ref(''),loading=ref(false)
const section=ref(route.query.section==='templates'?'templates':'settings')
const access=computed(()=>knowledgeAccess({id:kbId.value},profile.value,auth.hasRole('contributor')))
let request=0
async function load(){const token=++request;loading.value=true;profile.value=null;error.value='';try{const [libraries,permissions]=await Promise.all([listBases(),getBasePermissions()]);if(token===request){bases.value=libraries.data;profile.value=permissions}}catch(e:any){if(token===request)error.value=e.message}finally{if(token===request)loading.value=false}}
watch(kbId,load,{immediate:true})
watch(()=>route.query.section,value=>{section.value=value==='templates'?'templates':'settings'})
watch(section,value=>{if(route.query.section!==value)void router.replace({query:{...route.query,section:value}})})
onUnmounted(()=>{request++})
</script>
<template>
  <section class="knowledge-policies"><header class="console-intro"><h1>策略与模板</h1><p>整理记忆、提炼知识，并管理演进策略与模板。</p></header><div class="policy-body"><div class="policy-tabs"><span>知识评审</span><t-radio-group v-model="section" variant="default-filled"><t-radio-button value="settings">评审策略</t-radio-button><t-radio-button value="templates">重写模板</t-radio-button></t-radio-group></div><div class="policy-library"><label>知识库</label><t-select :value="kbId" filterable :options="bases.map(base=>({value:base.id,label:base.name}))" aria-label="知识库" @change="(value:any)=>router.push({path:'/platform/knowledge-bases/'+encodeURIComponent(String(value))+'/policies',query:{section}})" /><t-button variant="outline" :loading="loading" @click="load">刷新</t-button><t-button variant="text" @click="router.push('/platform/knowledge-bases/'+encodeURIComponent(kbId))">返回知识库</t-button></div><t-alert v-if="error" theme="error" :message="error" /><ContextDBReviewSettings v-if="section==='settings'" :kb-id="kbId" :can-edit="access.manage" /><ContextDBTemplates v-else :kb-id="kbId" :can-edit="access.manage" /></div></section>
</template>
<style scoped lang="less">
.knowledge-policies{font-family:var(--app-font-family);font-size:var(--app-text-base);height:100%;overflow:auto;background:var(--td-bg-color-container);}.console-intro{padding:20px 36px;min-height:104px;box-sizing:border-box;background:var(--td-bg-color-container)}.console-intro h1{font-size:var(--app-text-4xl);font-weight:600;line-height:34px;margin:0 0 10px}.console-intro p{font-size:var(--app-text-md);color:var(--td-text-color-secondary);margin:0;line-height:22px}.policy-body{padding:20px 36px}.policy-tabs{display:flex;align-items:center;gap:16px;padding-bottom:20px;border-bottom:1px solid var(--td-component-stroke);margin-bottom:20px}.policy-library{display:flex;align-items:center;gap:12px;margin-bottom:20px;font-size:var(--app-text-base)}.policy-library>.t-select__wrap{width:440px}.knowledge-policies :deep(.t-button),.knowledge-policies :deep(.t-input){border-radius:var(--app-radius-md)}.policy-body>.t-alert{margin-bottom:16px}
.policy-tabs>span{font-size:var(--app-text-3xl);font-weight:600}
</style>
