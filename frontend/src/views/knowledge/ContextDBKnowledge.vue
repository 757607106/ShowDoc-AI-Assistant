<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { getBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, type BasePermissionProfile } from '@/api/contextdb'
import EmptyState from '@/components/EmptyState.vue'
import KnowledgePageHeader from './components/KnowledgePageHeader.vue'
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
const wikiRef=ref<{permitNavigation:()=>boolean}|null>(null), issuesRef=ref<{permitNavigation:()=>boolean}|null>(null)
const canRefresh=()=>wikiRef.value?.permitNavigation()!==false && issuesRef.value?.permitNavigation()!==false
const viewTabs=computed(()=>[{key:'documents',label:'文件'},...(base.value?.wiki_enabled?[{key:'wiki',label:'知识 Wiki'}]:[]),...(base.value?.graph_enabled?[{key:'graph',label:'知识图谱'}]:[]),...(!base.value?.wiki_enabled?[{key:'ontology',label:'本体约束'}]:[])])
const permissionMode=computed(()=>permissions.value?.mode==='personal_compatibility'?'兼容权限模式':permissions.value?.mode==='advanced'?'高级权限模式':'')
let request=0
function viewQuery(value:string){const {view,document_id,documentId,knowledge_id,...query}=route.query;return {...query,tab:value}}
function selectTab(value:string){if(canRefresh()){tab.value=value;documentId.value='';if(!props.embedded)void router.replace({query:viewQuery(value)})}}
function open(item:any){if(canRefresh()){documentId.value=item.id;tab.value='documents';if(!props.embedded)void router.replace({query:{...viewQuery('documents'),document_id:item.id}})}}
function openWikiPage(pageId:string){if(canRefresh()){tab.value='wiki';documentId.value='';void router.replace({query:{...viewQuery('wiki'),wikiPageId:pageId}})}}
async function loadBase(){
  if(!canRefresh())return
  const token=++request,target=kbId.value;baseLoading.value=true;error.value=''
  try{
    const result=await getBase(target);if(token!==request)return
    base.value=result.data
    const requested=props.view||String(route.query.view||route.query.tab||'documents')
    tab.value=route.query.document_id||route.query.documentId||route.query.knowledge_id?'documents':requested==='nodes'?'documents':requested==='history'&&base.value.wiki_enabled?'history':viewTabs.value.some(item=>item.key===requested)?requested:'documents'
    documentId.value=String(route.query.document_id||route.query.documentId||route.query.knowledge_id||'')
    try{const profile=await getBasePermissions();if(token===request)permissions.value=profile}catch(e:any){if(token===request)error.value=e.message}
  }catch(e:any){if(token===request)error.value=e.message}
  finally{if(token===request)baseLoading.value=false}
}
watch(kbId,()=>{base.value=null;permissions.value=null;documentId.value='';void loadBase()},{immediate:true})
watch(()=>[props.view,route.query.tab,route.query.view,route.query.document_id,route.query.documentId,route.query.knowledge_id],()=>{
  if(!base.value||!canRefresh())return
  const id=String(route.query.document_id||route.query.documentId||route.query.knowledge_id||'')
  const value=props.view||String(route.query.view||route.query.tab||'documents')
  tab.value=id?'documents':value==='nodes'?'documents':value==='history'&&base.value.wiki_enabled?'history':viewTabs.value.some(item=>item.key===value)?value:'documents'
  documentId.value=id
})
defineExpose({canRefresh})
</script>
<template>
  <div class="contextdb-knowledge" :class="{'knowledge-console':!embedded}">
    <div v-if="!embedded" class="console-intro"><h1>知识库</h1><p>知识库用于承载上传文件和可共享的正式知识，适合沉淀产品资料、运维手册、项目文件等内容，并支持文件管理、知识图谱和 Agent 召回。</p></div>
    <KnowledgePageHeader v-if="!embedded" :model-value="tab" @update:model-value="selectTab" :title="base?.name||'加载中'" :current-id="kbId" :tabs="viewTabs" :mode-label="base?knowledgeModeLabel(base):''" :description="base?.description" :permission-mode="permissionMode" @navigate="router.push('/platform/knowledge-bases')">
      <template #actions><t-space><t-button variant="outline" @click="router.push({path:'/platform/collect',query:{kb_id:kbId}})">从外部数据源导入</t-button><t-button variant="text" @click="router.push({path:'/platform/governance',query:{kb_id:kbId}})">知识评审<t-icon name="jump" /></t-button><t-button variant="text" @click="router.push({path:'/platform/knowledge-bases/'+encodeURIComponent(kbId)+'/policies',query:{section:'settings'}})">评审策略<t-icon name="jump" /></t-button><t-button variant="text" @click="router.push({path:'/platform/knowledge-bases/'+encodeURIComponent(kbId)+'/policies',query:{section:'templates'}})">重写模板<t-icon name="jump" /></t-button></t-space></template>
    </KnowledgePageHeader>
    <div class="knowledge-body"><t-alert v-if="error" theme="error" :message="error" close />
      <EmptyState v-if="!base&&!baseLoading" icon="folder" title="暂时无法读取知识库"><t-button variant="outline" @click="loadBase">刷新</t-button></EmptyState>
      <t-loading v-else-if="!base" text="加载中" />
      <ContextDBDocuments v-else-if="tab==='documents'" :kb-id="kbId" :can-edit="editable" :wiki-enabled="base.wiki_enabled" :graph-enabled="base.graph_enabled" :review-enabled="base.review_enabled" :document-id="documentId" :base-name="base.name" />
      <ContextDBWiki ref="wikiRef" v-else-if="tab==='wiki'" :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})"><template #compile><ContextDBWikiCompile :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})" /></template></ContextDBWiki>
      <ContextDBGraph v-else-if="tab==='graph'" :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})" />
      <ContextDBWikiIssues ref="issuesRef" v-else-if="tab==='history'" :kb-id="kbId" :can-edit="editable" @open-page="openWikiPage" @open-source-doc="id=>open({id})" />
      <section v-else-if="tab==='ontology'" class="ontology-invitation"><h3>本体约束</h3><p>本体约束是 ContextDB 知识库的新能力：ContextDB 通过 AI 将业务的实体类型、属性与关系规则（"业务纲领"）显式写入知识库，系统在知识抽取、图谱构建和检索时按这些规则校验事实、生成待审项与违规报告，让图谱和 WIKI 的抽取质量更贴合业务口径、全程受业务控制。</p><t-button href="https://page.aliyun.com/form/act864207683/index.htm" target="_blank">申请邀测</t-button></section>
    </div>
    <ContextDBBaseEditor :visible="ui.showKBEditorModal" :mode="ui.kbEditorMode" :kb-id="ui.currentKBId || undefined" @update:visible="v=>ui.showKBEditorModal=v" @success="loadBase" />
  </div>
</template>
<style scoped lang="less">
.contextdb-knowledge{height:100%;display:flex;flex-direction:column;min-height:0;min-width:0;overflow:hidden;background:var(--td-bg-color-container);color:var(--td-text-color-primary)}.console-intro{flex:none;padding:20px 36px;background:var(--td-bg-color-container);min-height:104px;box-sizing:border-box}.console-intro h1{margin:0 0 10px;font-size:var(--app-text-4xl);font-weight:600;line-height:34px}.console-intro p{margin:0;font-size:var(--app-text-md);line-height:20px;color:var(--td-text-color-secondary)}.knowledge-body{display:flex;flex-direction:column;flex:1;min-height:0;padding:16px 20px 0;overflow:auto}.knowledge-body>.t-alert{margin-bottom:16px}.knowledge-console{font-family:var(--app-font-family);font-size:var(--app-text-base)}.knowledge-console :deep(.t-button){border-radius:var(--app-radius-md)}.knowledge-console :deep(.t-table__header th){background:var(--td-bg-color-secondarycontainer);color:var(--td-text-color-secondary);font-size:var(--app-text-base);font-weight:400}.knowledge-console :deep(.t-table td){font-size:var(--app-text-base)}.knowledge-console :deep(.t-input),.knowledge-console :deep(.t-select-input){border-radius:var(--app-radius-md)}.knowledge-console :deep(.contextdb-wiki){flex:1;min-height:0}
.ontology-invitation{text-align:center;max-width:580px;margin:44px auto;color:var(--td-text-color-secondary)}.ontology-invitation h3{font-size:var(--app-text-xl);font-weight:600;margin:16px 0}.ontology-invitation p{font-size:var(--app-text-md);line-height:20px;margin:0 0 56px}
.knowledge-console :deep(.t-alert--info){background:var(--td-bg-color-secondarycontainer)}.knowledge-console :deep(.t-tag--success.t-tag--light){background:var(--td-success-color-light)}
</style>
