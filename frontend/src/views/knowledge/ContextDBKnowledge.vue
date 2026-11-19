<script setup lang="ts">
import { ref, computed, useId, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { getBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, type BasePermissionProfile } from '@/api/contextdb'
import EmptyState from '@/components/EmptyState.vue'
import KnowledgePageHeader from './components/KnowledgePageHeader.vue'
import KnowledgeActionMenu from './components/KnowledgeActionMenu.vue'
import ContextDBBaseEditor from './ContextDBBaseEditor.vue'
import ContextDBDocuments from './ContextDBDocuments.vue'
import ContextDBGraph from './ContextDBGraph.vue'
import ContextDBWiki from './wiki/ContextDBWiki.vue'
import ContextDBWikiCompile from './wiki/ContextDBWikiCompile.vue'
import ContextDBWikiIssues from './wiki/ContextDBWikiIssues.vue'
const props=defineProps<{knowledgeBaseId?:string;spaceScope?:string;view?:string;embedded?:boolean}>()
const route=useRoute(), router=useRouter(), auth=useAuthStore(), ui=useUIStore()
const kbId=computed(()=>props.knowledgeBaseId || String(route.params.kbId))
const base=ref<any>(null), permissions=ref<BasePermissionProfile|null>(null), error=ref(''), baseLoading=ref(false)
const editable=computed(()=>knowledgeAccess({id:kbId.value},permissions.value,auth.hasRole('contributor')).write)
const manageable=computed(()=>knowledgeAccess({id:kbId.value},permissions.value,auth.hasRole('contributor')).manage)
const tab=ref('documents'), documentId=ref('')
const lastFolder = ref('')
const panelId = useId()
const selectedView = computed(() => tab.value === 'history' ? 'wiki' : tab.value)
const folderId=computed(()=>typeof route.query.folder_id==='string'?route.query.folder_id:'')
const wikiRef=ref<{permitNavigation:()=>boolean}|null>(null), issuesRef=ref<{permitNavigation:()=>boolean}|null>(null)
const documentsRef = ref<{ writeInProgress: boolean } | null>(null)
const graphRef = ref<{ writeInProgress: boolean } | null>(null)
function permitWriteNavigation() {
  if (!documentsRef.value?.writeInProgress && !graphRef.value?.writeInProgress) return true
  MessagePlugin.warning('当前操作正在提交，请等待结果后再切换视图。')
  return false
}
const canRefresh=()=>permitWriteNavigation() && wikiRef.value?.permitNavigation()!==false && issuesRef.value?.permitNavigation()!==false
if (!props.embedded) {
  onBeforeRouteLeave(permitWriteNavigation)
  onBeforeRouteUpdate(permitWriteNavigation)
}
const viewTabs=computed(()=>[{key:'documents',label:'文件'},...(base.value?.wiki_enabled?[{key:'wiki',label:'知识 Wiki'}]:[]),...(base.value?.graph_enabled?[{key:'graph',label:'知识图谱'}]:[])])
const permissionMode=computed(()=>permissions.value?.mode==='personal_compatibility'?'兼容权限模式':permissions.value?.mode==='advanced'?'高级权限模式':'')
const managementActions = computed(() => [
  { value: 'review', content: '知识评审' },
  { value: 'settings', content: '评审策略' },
  { value: 'templates', content: '重写模板' },
  ...(manageable.value ? [{ value: 'library', content: '知识库设置' }] : []),
])
let request=0
function backToList() {
  const { q, sort } = route.query
  return router.push({ path: '/platform/knowledge-bases', query: { q, sort } })
}
function manage(action: string) {
  if (!canRefresh()) return
  if (action === 'library') {
    if (manageable.value) ui.openKBSettings(kbId.value)
  } else if (action === 'review') {
    void router.push({ path: '/platform/governance', query: { kb_id: kbId.value } })
  } else {
    void router.push({ name: 'knowledgeBasePolicies', params: { kbId: kbId.value }, query: { ...route.query, section: action } })
  }
}
function viewQuery(value:string): LocationQueryRaw {const {view,document_id,documentId,knowledge_id,folder_id,...query}=route.query;return {...query,tab:value}}
function selectTab(value: string) {
  if (tab.value === value || !canRefresh()) return
  if (tab.value === 'documents') lastFolder.value = folderId.value
  const query = viewQuery(value)
  if (value === 'documents' && lastFolder.value) query.folder_id = lastFolder.value
  tab.value = value; documentId.value = ''
  if (!props.embedded) void router.replace({ query })
}
function open(item:any){if(canRefresh()){documentId.value=item.id;tab.value='documents';if(!props.embedded)void router.push({query:{...viewQuery('documents'),folder_id:lastFolder.value||undefined,document_id:item.id}})}}
function navigateDocuments(folder: string, id?: string) {
  const query = { ...viewQuery('documents'), folder_id: folder || undefined, document_id: id }
  const location = { query, hash: route.hash }
  if (!id && documentId.value && folder === folderId.value) {
    const previous = router.options?.history?.state?.back
    if (typeof previous === 'string' && previous === router.resolve(location).fullPath) router.back()
    else void router.replace(location)
    return
  }
  void router.push(location)
}
function openWikiPage(pageId:string){if(canRefresh()){tab.value='wiki';documentId.value='';void router.push({query:{...viewQuery('wiki'),wikiTab:'read',wikiPageId:pageId}})}}
async function loadBase(){
  if(!canRefresh())return
  const token=++request,target=kbId.value;baseLoading.value=true;error.value=''
  try{
    const result=await getBase(target);if(token!==request)return
    base.value=result.data
    const requested=props.view||String(route.query.view||route.query.tab||'documents')
    tab.value=route.query.document_id||route.query.documentId||route.query.knowledge_id||folderId.value?'documents':requested==='nodes'?'documents':requested==='history'&&base.value.wiki_enabled?'history':viewTabs.value.some(item=>item.key===requested)?requested:'documents'
    documentId.value=String(route.query.document_id||route.query.documentId||route.query.knowledge_id||'')
    try{const profile=await getBasePermissions();if(token===request)permissions.value=profile}catch(e:any){if(token===request)error.value=e.message}
  }catch(e:any){if(token===request)error.value=e.message}
  finally{if(token===request)baseLoading.value=false}
}
watch(kbId,()=>{base.value=null;permissions.value=null;documentId.value='';lastFolder.value='';void loadBase()},{immediate:true})
watch(()=>[props.view,route.query.tab,route.query.view,route.query.document_id,route.query.documentId,route.query.knowledge_id,route.query.folder_id],()=>{
  if(!base.value||!canRefresh())return
  const id=String(route.query.document_id||route.query.documentId||route.query.knowledge_id||'')
  const value=props.view||String(route.query.view||route.query.tab||'documents')
  tab.value=id||folderId.value?'documents':value==='nodes'?'documents':value==='history'&&base.value.wiki_enabled?'history':viewTabs.value.some(item=>item.key===value)?value:'documents'
  documentId.value=id
})
defineExpose({canRefresh})
</script>
<template>
  <div class="contextdb-knowledge" :class="{'knowledge-console':!embedded}">
    <KnowledgePageHeader v-if="!embedded" :model-value="selectedView" @update:model-value="selectTab" :title="base?.name||(baseLoading?'正在读取知识库…':'知识库')" :panel-id="panelId" :tabs="viewTabs" :mode-label="base?knowledgeModeLabel(base):''" :description="base?.description" :permission-mode="permissionMode" @navigate="backToList">
      <template #actions><KnowledgeActionMenu v-if="base" text="管理" label="管理知识库" :options="managementActions" @select="manage" /></template>
    </KnowledgePageHeader>
    <div class="knowledge-body" :id="embedded ? undefined : panelId" :role="embedded ? undefined : 'tabpanel'" :aria-busy="baseLoading"
      :aria-labelledby="embedded ? undefined : `${panelId}-${selectedView}`"><t-alert v-if="error" theme="error" :message="error" close />
      <EmptyState v-if="!base&&!baseLoading" icon="folder" title="暂时无法读取知识库"><t-button variant="outline" @click="loadBase">刷新</t-button></EmptyState>
      <t-loading v-else-if="!base" text="加载中" />
      <ContextDBDocuments ref="documentsRef" v-else-if="tab==='documents'" :kb-id="kbId" :can-edit="editable" :wiki-enabled="base.wiki_enabled" :graph-enabled="base.graph_enabled" :review-enabled="base.review_enabled" :document-id="documentId" :folder-id="folderId" :base-name="base.name" :sync-location="!embedded" :show-import="!embedded && editable" @navigate="navigateDocuments" />
      <ContextDBWiki ref="wikiRef" v-else-if="tab==='wiki'" :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})"><template #compile><ContextDBWikiCompile :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})" /></template></ContextDBWiki>
      <ContextDBGraph ref="graphRef" v-else-if="tab==='graph'" :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})" />
      <ContextDBWikiIssues ref="issuesRef" v-else-if="tab==='history'" :kb-id="kbId" :can-edit="editable" @open-page="openWikiPage" @open-source-doc="id=>open({id})" />
    </div>
    <ContextDBBaseEditor :visible="ui.showKBEditorModal" :mode="ui.kbEditorMode" :kb-id="ui.currentKBId || undefined" @update:visible="v=>ui.showKBEditorModal=v" @success="loadBase" />
  </div>
</template>
<style scoped lang="less">
.contextdb-knowledge{height:100%;display:flex;flex-direction:column;min-height:0;min-width:0;overflow:hidden;background:var(--td-bg-color-container);color:var(--td-text-color-primary)}.knowledge-body{display:flex;flex-direction:column;flex:1;min-height:0;padding:12px 20px 0;overflow:auto}.knowledge-body>.t-alert{margin-bottom:16px}.knowledge-console{font-family:var(--app-font-family);font-size:var(--app-text-base)}.knowledge-console :deep(.t-button){border-radius:var(--app-radius-md)}.knowledge-console :deep(.t-table__header th){background:var(--td-bg-color-secondarycontainer);color:var(--td-text-color-secondary);font-size:var(--app-text-base);font-weight:400}.knowledge-console :deep(.t-table td){font-size:var(--app-text-base)}.knowledge-console :deep(.t-input),.knowledge-console :deep(.t-select-input){border-radius:var(--app-radius-md)}.knowledge-console :deep(.contextdb-wiki){flex:1;min-height:0}
.knowledge-console :deep(.t-alert--info){background:var(--td-bg-color-secondarycontainer)}.knowledge-console :deep(.t-tag--success.t-tag--light){background:var(--td-success-color-light)}
</style>
