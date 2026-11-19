<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { getBasePermissions, knowledgeAccess, listBases, type BasePermissionProfile } from '@/api/contextdb'
import ContextDBReviewSettings from './ContextDBReviewSettings.vue'
import ContextDBTemplates from './ContextDBTemplates.vue'
const route=useRoute(),router=useRouter(),auth=useAuthStore()
const kbId=computed(()=>String(route.params.kbId||'')),bases=ref<any[]>([]),profile=ref<BasePermissionProfile|null>(null),error=ref(''),loading=ref(false)
const section=ref(route.query.section==='templates'?'templates':'settings')
const access=computed(()=>knowledgeAccess({id:kbId.value},profile.value,auth.hasRole('contributor')))
type Editor = { dirty: boolean; saving: boolean; load: () => Promise<void> }
const settingsEditor = ref<Editor | null>(null), templatesEditor = ref<Editor | null>(null)
const currentEditor = computed(() => section.value === 'settings' ? settingsEditor.value : templatesEditor.value)
function permitNavigation() {
  if (currentEditor.value?.saving) {
    MessagePlugin.warning('当前操作正在提交，请等待结果。')
    return false
  }
  return !currentEditor.value?.dirty || window.confirm('放弃未保存的配置修改？')
}
onBeforeRouteLeave(permitNavigation)
onBeforeRouteUpdate(permitNavigation)
function selectSection(value: string) {
  if (value !== section.value) void router.replace({ query: { ...route.query, section: value } })
}
function backToLibrary() {
  const { section: _, ...query } = route.query
  return router.push({ name: 'knowledgeBaseDetail', params: { kbId: kbId.value }, query })
}
async function refresh() {
  if (!permitNavigation()) return
  await Promise.all([load(), currentEditor.value?.load()])
}
let request=0
async function load(){const token=++request;loading.value=true;profile.value=null;error.value='';try{const [libraries,permissions]=await Promise.all([listBases(),getBasePermissions()]);if(token===request){bases.value=libraries.data;profile.value=permissions}}catch(e:any){if(token===request)error.value=e.message}finally{if(token===request)loading.value=false}}
watch(kbId,load,{immediate:true})
watch(()=>route.query.section,value=>{section.value=value==='templates'?'templates':'settings'})
onUnmounted(()=>{request++})
</script>
<template>
  <section class="knowledge-policies">
    <header class="console-intro"><t-button variant="text" shape="square" aria-label="返回知识库" @click="backToLibrary"><t-icon name="chevron-left" /></t-button><h1>策略与模板</h1></header>
    <div class="policy-body">
      <div class="policy-tabs"><t-radio-group :value="section" variant="default-filled" aria-label="管理视图" @change="(value: unknown) => selectSection(String(value))">
        <t-radio-button value="settings">评审策略</t-radio-button><t-radio-button value="templates">重写模板</t-radio-button>
      </t-radio-group></div>
      <div class="policy-library">
        <label><span>知识库</span><t-select :value="kbId" filterable :options="bases.map(base=>({value:base.id,label:base.name}))" :disabled="loading"
          @change="(value:any)=>router.push({name:'knowledgeBasePolicies',params:{kbId:String(value)},query:{section}})" /></label>
        <t-button variant="outline" :loading="loading" @click="refresh">刷新</t-button>
      </div>
      <t-alert v-if="error" role="alert" theme="error" :message="error" />
      <ContextDBReviewSettings v-if="section==='settings'" ref="settingsEditor" :kb-id="kbId" :can-edit="access.manage" />
      <ContextDBTemplates v-else ref="templatesEditor" :kb-id="kbId" :can-edit="access.manage" />
    </div>
  </section>
</template>
<style scoped lang="less">
.knowledge-policies{font-family:var(--app-font-family);font-size:var(--app-text-base);height:100%;overflow:auto;background:var(--td-bg-color-container);}.console-intro{display:flex;align-items:center;gap:8px;padding:20px 36px;min-height:74px;box-sizing:border-box;background:var(--td-bg-color-container)}.console-intro h1{font-size:var(--app-text-4xl);font-weight:600;line-height:34px;margin:0}.policy-body{padding:20px 36px}.policy-tabs{display:flex;align-items:center;gap:16px;padding-bottom:20px;border-bottom:1px solid var(--td-component-stroke);margin-bottom:20px}.policy-library{display:flex;align-items:center;gap:12px;margin-bottom:20px;font-size:var(--app-text-base)}.policy-library{flex-wrap:wrap}.policy-library>label{display:flex;align-items:center;gap:8px;min-width:0;flex:0 1 440px}.policy-library>label>span{white-space:nowrap}.policy-library :deep(.t-select__wrap){flex:1;min-width:0}.knowledge-policies :deep(.t-button),.knowledge-policies :deep(.t-input){border-radius:var(--app-radius-md)}.policy-body>.t-alert{margin-bottom:16px}
@media(max-width:760px){.console-intro,.policy-body{padding-inline:16px}.policy-library>label{flex:1 1 220px}}
</style>
