<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { getSpace, getSpaces, submitSpace, updateSpace, type KnowledgeSpace, spaceTargetStatus, spaceTargetNotice } from '@/api/knowledgeSpaces'
import EmptyState from '@/components/EmptyState.vue'
import ContextDBKnowledge from './ContextDBKnowledge.vue'
import ContextDBSpaceProgress from './ContextDBSpaceProgress.vue'
import KnowledgePageHeader from './components/KnowledgePageHeader.vue'
import { spaceName } from '@/utils/platformPresentation'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const scope = computed(() => String(route.params.scope)), space = ref<KnowledgeSpace | null>(null)
const tab = computed({get:()=>typeof route.query.tab==='string'?route.query.tab:route.query.document_id||route.query.knowledge_id?'documents':'wiki',set:(value:string)=>{
  if(value===route.query.tab)return
  const query:LocationQuery={...route.query,tab:value}
  if(!['documents','nodes'].includes(value)){
    delete query.target
    if(route.query.target==='graph')for(const key of ['document_id','knowledge_id','node_id','file_path','wikiPageId','slug'])delete query[key]
  }
  void router.replace({query})
}}), loading = ref(false), error = ref(''), settings = ref(false), saving = ref(false)
const spaces=ref<{id:string;name:string}[]>([])
const viewTabs=[{key:'documents',label:'文档',icon:'file'},{key:'nodes',label:'目录',icon:'folder'},{key:'wiki',label:'Wiki',icon:'book-open'},{key:'history',label:'内容问题',icon:'error-circle'},{key:'graph',label:'知识图谱',icon:'share'},{key:'progress',label:'治理进度',icon:'task'}]
const name = ref(''), wikiId = ref(''), wikiBases = ref<any[]>([]), graphEnabled = ref(false), graphId = ref(''), graphBases = ref<any[]>([])
const submitting = ref(false)
const editable = computed(() => auth.hasRole('contributor'))
const knowledgeRef=ref<{canRefresh:()=>boolean}|null>(null)
const mode=computed(() => tab.value==='graph'||(['documents','nodes'].includes(tab.value)&&route.query.target==='graph')?'graph':'wiki')
const targetStatus=computed(()=>space.value?spaceTargetStatus(space.value,mode.value):'unbound')
const targetNotice=computed(()=>space.value?spaceTargetNotice(space.value,mode.value):'')
const nativeId = computed(() => targetStatus.value==='available' ? (mode.value==='graph'?space.value?.graph_kb_id:space.value?.wiki_kb_id) : null)
const unavailable=computed(()=>['missing','forbidden','unknown'].includes(targetStatus.value))
let loadedWikiId:string|null|undefined, loadedGraphId:string|null|undefined
function clearResourceLinks(){
  const query={...route.query}
  for(const key of ['wikiPageId','slug','document_id','knowledge_id','node_id','parent_node_id','file_path'])delete query[key]
  if(Object.keys(query).length!==Object.keys(route.query).length)void router.replace({query})
}
function acceptSpace(next:KnowledgeSpace){
  const previous=mode.value==='wiki'?loadedWikiId:loadedGraphId
  const current=mode.value==='wiki'?next.wiki_kb_id:next.graph_kb_id
  if(previous!==undefined&&previous!==current)clearResourceLinks()
  loadedWikiId=next.wiki_kb_id;loadedGraphId=next.graph_kb_id;space.value=next
}
let requestId = 0
async function load() {
  if(knowledgeRef.value?.canRefresh()===false)return
  const request = ++requestId, target = scope.value
  loading.value = true; error.value = ''
  try {
    const result = await getSpace(target)
    if(request===requestId && target===scope.value){
      acceptSpace(result.space)
    }
  }
  catch(e:any) { if(request===requestId) error.value=e.message }
  finally { if(request===requestId) loading.value=false }
}
function ingest(mode: 'file' | 'crawl') { router.push({path:'/platform/collect',query:{space:scope.value,mode}}) }
async function openSettings() {
  if(!space.value) return
  name.value=spaceName(space.value.scope,[space.value]);wikiId.value=space.value.wiki_kb_id || '';graphEnabled.value=space.value.graph_enabled;graphId.value=space.value.graph_kb_id || ''
  settings.value=true
  try {
    const result=await getSpaces(), bases=result.available_bases || []
    wikiBases.value=bases.filter((base:any)=>base.wiki_enabled)
    graphBases.value=bases.filter((base:any)=>base.graph_enabled && !base.wiki_enabled)
  }
  catch(e:any) { MessagePlugin.error(e.message) }
}
async function save() {
  if(saving.value)return
  if(!name.value.trim()){MessagePlugin.warning('请输入知识库名称');return}
  const target=scope.value
  saving.value=true
  try {
    const result=await updateSpace(target,{name:name.value.trim(),graph_enabled:graphEnabled.value,
      ...(!space.value?.wiki_kb_id && wikiId.value ? {wiki_kb_id:wikiId.value} : {}),
      ...(!space.value?.graph_kb_id && graphEnabled.value && graphId.value ? {graph_kb_id:graphId.value} : {})})
    if(target!==scope.value)return
    acceptSpace(result.space);settings.value=false;MessagePlugin.success('知识库设置已保存')
  } catch(e:any){MessagePlugin.error(e.message)}
  finally{saving.value=false}
}
async function syncCurrent() {
  if(submitting.value)return
  const target=scope.value
  submitting.value=true
  try {
    await submitSpace(target)
    if(target!==scope.value)return
    tab.value='progress';MessagePlugin.success('提交任务已创建')
    await load()
  } catch(e:any){MessagePlugin.error(e.message)}
  finally{submitting.value=false}
}
async function rebuildCurrent() {
  if(submitting.value||targetStatus.value!=='missing')return
  const target=scope.value, targetMode=mode.value
  submitting.value=true
  try {
    await submitSpace(target,[targetMode])
    if(target!==scope.value)return
    tab.value='progress';MessagePlugin.success('重建目标库并重新提交最近批次的任务已创建')
    await load()
  } catch(e:any){MessagePlugin.error(e.message)}
  finally{submitting.value=false}
}
watch(scope,()=>{space.value=null;settings.value=false;loadedWikiId=undefined;loadedGraphId=undefined;void load()},{immediate:true})
onMounted(async()=>{window.addEventListener('focus',refreshAvailability);document.addEventListener('visibilitychange',refreshAvailability);try{const result=await getSpaces();spaces.value=result.spaces.map((item:KnowledgeSpace)=>({id:item.scope,name:spaceName(item.scope,result.spaces)}))}catch(e:any){MessagePlugin.error(e.message)}})
function refreshAvailability(){if(document.visibilityState!=='hidden'&&!loading.value)void load()}
onUnmounted(()=>{window.removeEventListener('focus',refreshAvailability);document.removeEventListener('visibilitychange',refreshAvailability)})
</script>

<template>
  <div class="space-detail knowledge-layout">
    <KnowledgePageHeader v-model="tab" :title="space?spaceName(space.scope,[space]):'加载中'" :current-id="scope" :choices="spaces" :tabs="viewTabs" :can-manage="editable" @navigate="router.push('/platform/knowledge-bases')" @select="id=>router.push(`/platform/knowledge-spaces/${encodeURIComponent(id)}`)" @settings="openSettings">
      <template #actions><t-space break-line><t-button variant="text" :loading="loading" @click="load">刷新</t-button><t-button v-if="nativeId" variant="outline" @click="router.push({path:'/platform/governance',query:{kb_id:nativeId,tab:'reviews'}})">知识评审</t-button><t-button v-if="editable" variant="outline" @click="ingest('crawl')">采集资料</t-button><t-button v-if="editable" @click="ingest('file')">上传资料</t-button><t-button v-if="space?.wiki_kb_id&&spaceTargetStatus(space,'wiki')==='available'" variant="outline" @click="router.push(`/platform/knowledge-bases/${space.wiki_kb_id}/creatChat`)">开始对话</t-button></t-space></template>
    </KnowledgePageHeader>
    <t-alert v-if="error" theme="error" :message="error"><template #operation><t-button variant="text" @click="load">重试读取</t-button></template></t-alert>
    <t-alert v-if="mode==='graph'&&['documents','nodes'].includes(tab)" theme="info" message="当前展示图谱库的来源资料；Wiki 与图谱库的文档和评审状态独立。" />
    <t-alert v-if="mode==='graph'&&space&&!space.graph_enabled&&nativeId" theme="info" message="后续图谱提交已关闭，仍可查看已有图谱和来源资料。" />
    <div v-if="editable && space?.has_submission && (tab==='graph' || tab==='progress')" class="sync-current"><t-tooltip content="按当前设置重新提交最近批次，不含尚未提交的新资料"><t-button variant="outline" :loading="submitting" @click="syncCurrent">重新提交最近批次</t-button></t-tooltip></div>
    <ContextDBSpaceProgress v-if="tab==='progress' && space" :key="scope" :scope="scope" @refresh-space="load" @space-loaded="acceptSpace" />
    <EmptyState v-else-if="tab==='graph' && space && !space.graph_enabled&&!space.graph_kb_id" icon="share" title="未启用知识图谱"><t-button v-if="editable" @click="openSettings">设置知识图谱</t-button></EmptyState>
    <ContextDBKnowledge ref="knowledgeRef" v-else-if="nativeId" :key="nativeId" :knowledge-base-id="nativeId" :space-scope="scope" :view="tab" embedded />
    <EmptyState v-else-if="space && unavailable && !loading" icon="folder" :title="targetNotice">
      <p>{{targetStatus==='missing'?'采集原件和提交历史已保留。可关联已有库，或重新提交最近批次来创建新目标。':space.targets?.[mode]?.error || '请检查成员权限或服务连接后重试，平台不会自动更换目标库。'}}</p>
      <t-space><t-button variant="outline" @click="load">重新核对</t-button><t-button v-if="editable&&targetStatus==='missing'" variant="outline" @click="openSettings">关联已有库</t-button><t-button v-if="editable&&targetStatus==='missing'&&space.has_submission" :loading="submitting" @click="rebuildCurrent">重建并重新提交最近批次</t-button><t-button v-if="editable&&targetStatus==='missing'&&!space.has_submission" @click="ingest('file')">添加资料并创建新库</t-button><t-button variant="text" @click="tab='progress'">查看保留的历史</t-button></t-space>
    </EmptyState>
    <EmptyState v-else-if="!loading && !error" icon="folder" :title="tab==='graph' ? '图谱知识库尚未创建' : '尚未提交资料'"><t-button v-if="editable" @click="ingest('file')">添加资料</t-button><t-button variant="outline" @click="tab='progress'">查看治理进度</t-button></EmptyState>
    <t-loading v-else-if="loading" text="正在读取知识库" />
    <t-dialog v-model:visible="settings" header="知识库设置" :confirm-btn="{content:'保存',loading:saving}" :close-on-overlay-click="!saving" @confirm="save">
      <t-form label-align="top">
        <t-form-item label="知识库名称" required><t-input v-model="name" :maxlength="100" /></t-form-item>
        <t-form-item v-if="!space?.wiki_kb_id" label="关联已有 Wiki 主库"><t-select v-model="wikiId" clearable placeholder="下次提交资料时创建，也可关联已有 Wiki 库" :options="wikiBases.map(base=>({label:base.name,value:base.id}))" /></t-form-item>
        <t-form-item label="启用知识图谱" help="启用后，同一资料分别投递到 Wiki 库和图谱库，产生两份入库和独立评审状态；Wiki 修订不会自动同步到图谱。关闭后停止后续图谱提交，已有内容保留。"><t-switch v-model="graphEnabled" /></t-form-item>
        <t-form-item v-if="graphEnabled && !space?.graph_kb_id" label="关联已有图谱库"><t-select v-model="graphId" clearable placeholder="下次提交资料时创建" :options="graphBases.map(base=>({label:base.name,value:base.id}))" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<style scoped lang="less">
@import './knowledgePageLayout.less';
.space-detail{display:flex;flex-direction:column;height:100%;min-height:0}
.space-detail :deep(.contextdb-knowledge){flex:1;min-height:0}
.sync-current{display:flex;align-items:center;flex-wrap:wrap;gap:12px;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}
</style>
