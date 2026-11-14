<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { getBase, listBases, nativeAPI, documentView, getDocument } from '@/api/contextdb'
import KnowledgeBase from './KnowledgeBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import DocContent from '@/components/doc-content.vue'
import KnowledgePageHeader from './components/KnowledgePageHeader.vue'
import { getKnowledgeDetailsCon } from '@/api/knowledge-base'
import KnowledgeBaseEditorModal from './KnowledgeBaseEditorModal.vue'
import ContextDBGraph from './ContextDBGraph.vue'
import ContextDBWiki from './wiki/ContextDBWiki.vue'
import ContextDBWikiCompile from './wiki/ContextDBWikiCompile.vue'
import ContextDBWikiIssues from './wiki/ContextDBWikiIssues.vue'
import { stateLabel, dateTime } from '@/utils/platformPresentation'
import { CONTEXTDB_REVIEW_FORMAT_NOTICE } from '@/utils/contextdbReviewSupport'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { findKnowledgeSpace, getSpaces } from '@/api/knowledgeSpaces'
const props=defineProps<{knowledgeBaseId?:string;spaceScope?:string;view?:string;embedded?:boolean}>()
const route=useRoute(), router=useRouter(), auth=useAuthStore(), ui=useUIStore()
const kbId=computed(()=>props.knowledgeBaseId || String(route.params.kbId)), editable=computed(()=>auth.hasRole('contributor'))
const base=ref<any>(null), tab=ref(props.view || (typeof route.query.tab==='string'?route.query.tab:'wiki')), baseLoading=ref(false)
const wikiRef=ref<{permitNavigation:()=>boolean}|null>(null), issuesRef=ref<{permitNavigation:()=>boolean}|null>(null)
const canRefresh=()=>wikiRef.value?.permitNavigation()!==false && issuesRef.value?.permitNavigation()!==false
defineExpose({canRefresh})
let baseRequest=0, sourceRequest=0
const bases=ref<any[]>([])
const viewTabs=computed(()=>[
  {key:'documents',label:'文档',icon:'file'}, {key:'nodes',label:'目录',icon:'folder'},
  ...(base.value?.wiki_enabled?[{key:'wiki',label:'Wiki',icon:'book-open'},{key:'history',label:'内容问题',icon:'error-circle'}]:[]),
  ...(base.value?.graph_enabled?[{key:'graph',label:'知识图谱',icon:'share'}]:[]),
])
const error=ref(''), preview=ref<any>(null), chunkPage=ref(1)
const nodePage=ref(1), nodeTotal=ref(0), nodes=ref<any[]>([]), breadcrumbs=ref<any[]>([]), parent=ref('')
const nodeDialog=ref(false), nodeName=ref(''), nodeTarget=ref(''), nodeEditing=ref<any>(null)
const folderOptions=ref<any[]>([]), folderLoading=ref(false), folderError=ref('')
async function run(fn:()=>Promise<void>) { error.value='';try {await fn()}catch(e:any){error.value=e.message;MessagePlugin.error(e.message)} }
function openWikiPage(pageId: string) {
  if(pageId)void router.push({path:props.spaceScope ? `/platform/knowledge-spaces/${encodeURIComponent(props.spaceScope)}` : `/platform/knowledge-bases/${kbId.value}`,query:{tab:'wiki',wikiPageId:pageId}})
}
async function loadNodes() {
  const res=await nativeAPI.get('knowledge/nodes',{knowledge_base_id:kbId.value,parent_node_id:parent.value||undefined,page:nodePage.value,page_size:35})
  nodes.value=res.data.items.map((node:any)=>({...node,label:node.node_type==='file'&&/^doc-[a-f\d]{64}\./i.test(node.display_name)
    ?documentDisplayName({name:node.display_name,metadata:node.metadata}):node.display_name}))
  breadcrumbs.value=res.data.breadcrumbs||[];nodeTotal.value=res.data.total
}
async function enterNode(id='') {parent.value=id;nodePage.value=1;await run(loadNodes)}
async function open(item:any) {
  const request=++sourceRequest, target=kbId.value
  await run(async()=>{
    const doc=(await getDocument(item.id)).data
    if(request!==sourceRequest||target!==kbId.value)return
    preview.value={...doc,title:doc.file_name,time:dateTime(doc.updated_at),md:[],total:0,chunkLoading:true}
    chunkPage.value=1;await loadChunks()
  })
}
async function loadChunks(){
  if(!preview.value)return
  const target=preview.value
  target.chunkLoading=true;target.chunkLoadError=''
  try{const res=await getKnowledgeDetailsCon(target.id,chunkPage.value);if(preview.value===target){target.md=res.data;target.total=res.total}}
  catch(e:any){if(preview.value===target)target.chunkLoadError=e.message}
  finally{if(preview.value===target)target.chunkLoading=false}
}
function addDocuments(){router.push({path:'/platform/collect',query:{mode:'file',...(props.spaceScope?{space:props.spaceScope}:{kb_id:kbId.value})}})}
async function loadFolders(node:any) {
  const target=kbId.value, folders:any[]=[]
  for(let page=1;;page++){
    const res=await nativeAPI.get('knowledge/nodes',{knowledge_base_id:target,parent_node_id:node.value,page,page_size:100})
    const items=res.data.items||[]
    folders.push(...items.filter((item:any)=>item.node_type==='folder'&&item.node_id!==nodeEditing.value?.node_id).map((item:any)=>({value:item.node_id,label:item.display_name,children:true})))
    if(items.length<100||page*100>=res.data.total)break
  }
  return target===kbId.value?folders:[]
}
async function editNode(node?:any){
  nodeEditing.value=node||null;nodeName.value=node?.display_name||'';nodeTarget.value='';nodeDialog.value=true
  folderOptions.value=[];folderError.value='';folderLoading.value=true
  const target=kbId.value
  try{
    const res=await nativeAPI.get('knowledge/nodes',{knowledge_base_id:target,page:1,page_size:1})
    if(target!==kbId.value)return
    const root=res.data.parent_node||res.data.breadcrumbs?.[0]
    if(!root?.node_id)throw new Error('目录位置读取失败，请重试')
    folderOptions.value=[{value:root.node_id,label:'根目录',children:true}]
  }catch(e:any){folderError.value=e.message}finally{folderLoading.value=false}
}
async function saveNode(){await run(async()=>{
  if(!nodeName.value.trim())throw new Error('请输入名称')
  if(nodeEditing.value)await nativeAPI.patch('knowledge/nodes',{node_id:nodeEditing.value.node_id,expected_tree_version:nodeEditing.value.tree_version,display_name:nodeName.value,parent_node_id:nodeTarget.value||undefined})
  else await nativeAPI.post('knowledge/nodes',{knowledge_base_id:kbId.value,parent_node_id:parent.value||undefined,display_name:nodeName.value})
  nodeDialog.value=false;await loadNodes()
})}
async function loadBase(){
  if(!canRefresh())return
  const request=++baseRequest, target=kbId.value
  baseLoading.value=true;error.value=''
  try{
    if(!props.embedded){
      const spaces=await getSpaces()
      if(request!==baseRequest||target!==kbId.value)return
      const match=findKnowledgeSpace(spaces.spaces,target)
      if(match){
        const query={...route.query}, replaced=match.space[`${match.mode}_kb_id`]!==target
        if(replaced)for(const key of ['wikiPageId','slug','document_id','knowledge_id','node_id','parent_node_id','file_path'])delete query[key]
        const hasDocument=typeof (query.document_id||query.knowledge_id)==='string'
        const defaultTab=match.mode==='graph'?'graph':'wiki'
        const requested=replaced?defaultTab:hasDocument?'documents':['documents','nodes','wiki','history','graph','progress'].includes(String(query.tab))?String(query.tab):defaultTab
        if(replaced)delete query.target
        await router.replace({path:`/platform/knowledge-spaces/${encodeURIComponent(match.space.scope)}`,query:{...query,tab:requested,...(match.mode==='graph'?{target:'graph'}:{})}})
        return
      }
    }
    const result=await getBase(target)
    if(request!==baseRequest||target!==kbId.value)return
    base.value=result.data
    const requested=props.view||(typeof route.query.tab==='string'?route.query.tab:undefined)
    tab.value=route.query.document_id||route.query.knowledge_id?'documents':viewTabs.value.some(item=>item.key===requested)?requested!:
      base.value?.wiki_enabled?'wiki':base.value?.graph_enabled?'graph':'documents'
    if(tab.value==='nodes')await loadNodes()
    const documentId=route.query.document_id||route.query.knowledge_id
    if(tab.value!=='documents'&&typeof documentId==='string')await open({id:documentId})
  }catch(e:any){if(request===baseRequest)error.value=e.message||'知识库读取失败'}
  finally{if(request===baseRequest)baseLoading.value=false}
}
watch(kbId,()=>{sourceRequest++;base.value=null;preview.value=null;parent.value='';void loadBase()},{immediate:true})
watch(()=>props.view,value=>{if(value)tab.value=value})
watch(()=>route.query.tab,value=>{if(!props.embedded&&base.value)tab.value=viewTabs.value.some(item=>item.key===value)?String(value):base.value.wiki_enabled?'wiki':base.value.graph_enabled?'graph':'documents'})
watch(tab,()=>run(async()=>{
  if(tab.value==='documents'){sourceRequest++;preview.value=null}
  if(!props.embedded&&tab.value!==route.query.tab)void router.replace({query:{...route.query,tab:tab.value}})
  if(tab.value==='nodes')await loadNodes()
}))
onMounted(()=>{if(!props.embedded)void run(async()=>{bases.value=(await listBases()).data})})
</script>
<template>
  <div class="contextdb-knowledge" :class="{'knowledge-layout':!embedded}">
    <KnowledgePageHeader v-if="!embedded" :model-value="tab" @update:model-value="value=>router.replace({query:{...route.query,tab:value}})" :title="base?.name||'加载中'" :current-id="kbId" :choices="bases" :tabs="viewTabs" :can-manage="editable" @navigate="router.push('/platform/knowledge-bases')" @select="id=>router.push(`/platform/knowledge-bases/${id}`)" @settings="ui.openKBSettings(kbId)">
      <template #actions><t-space><t-button v-if="base" variant="outline" @click="router.push({path:'/platform/governance',query:{kb_id:kbId,tab:'reviews'}})">知识评审</t-button><t-button v-if="base&&editable" variant="outline" @click="addDocuments">添加资料</t-button><t-button v-if="base" @click="router.push(`/platform/knowledge-bases/${kbId}/creatChat`)">开始对话</t-button></t-space></template>
    </KnowledgePageHeader>
    <t-alert v-if="error" theme="error" :message="error" close/>
    <t-alert v-if="tab==='documents'||tab==='nodes'" theme="info" :message="CONTEXTDB_REVIEW_FORMAT_NOTICE" />
    <EmptyState v-if="!base&&!baseLoading" icon="folder" title="暂时无法读取知识库"><p>请确认 ContextDB 中的库仍存在，且当前成员有读取权限。已有采集与提交历史不会因此删除。</p><t-space><t-button variant="outline" @click="loadBase">重新读取</t-button><t-button variant="outline" @click="router.push('/platform/knowledge-bases')">返回列表核对关联</t-button></t-space></EmptyState>
    <t-loading v-else-if="!base&&baseLoading" text="正在核对知识库" />
    <KnowledgeBase v-else-if="tab==='documents'" :knowledge-base-id="kbId" :space-scope="spaceScope" view="documents" embedded />
    <ContextDBWiki ref="wikiRef" v-else-if="tab==='wiki'" :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})">
      <template #compile><ContextDBWikiCompile :kb-id="kbId" :can-edit="editable" @open-source-doc="id=>open({id})" @open-page="openWikiPage" /></template>
    </ContextDBWiki>
    <div v-else-if="tab==='nodes'" class="native-documents">
      <t-space><t-breadcrumb><t-breadcrumb-item @click="enterNode()">根目录</t-breadcrumb-item><t-breadcrumb-item v-for="node in breadcrumbs.filter(item=>item.node_type!=='root')" :key="node.node_id" @click="enterNode(node.node_id)">{{node.display_name}}</t-breadcrumb-item></t-breadcrumb>
        <t-button v-if="editable" variant="outline" @click="editNode()">新建目录</t-button><t-button v-if="editable" variant="outline" @click="addDocuments">添加资料</t-button></t-space>
      <t-table row-key="node_id" :data="nodes" :columns="[{colKey:'display_name',title:'名称'},{colKey:'node_type',title:'类型'},{colKey:'ingest_status',title:'入库状态'},{colKey:'graph_status',title:'图谱状态'},{colKey:'actions',title:'操作'}]">
        <template #display_name="{row}"><t-link @click="row.node_type==='folder'?enterNode(row.node_id):open(documentView({...row,id:row.document_id,name:row.display_name}))"><t-icon :name="row.node_type==='folder'?'folder':'file'"/>{{row.label}}</t-link></template>
        <template #node_type="{row}">{{row.node_type==='folder'?'目录':row.node_type==='root'?'根目录':'文档'}}</template>
        <template #ingest_status="{row}">{{row.node_type==='file'?stateLabel(row.ingest_status,'ingest'):'—'}}</template>
        <template #graph_status="{row}">{{row.node_type==='file'?stateLabel(row.graph_status,'graph'):'—'}}</template>
        <template #actions="{row}"><t-button v-if="editable && row.node_type!=='root'" variant="text" @click="editNode(row)">编辑名称与位置</t-button></template>
      </t-table>
      <t-pagination :total="nodeTotal" :current="nodePage" :page-size="35" :show-page-size="false" @current-change="(v:number)=>{nodePage=v;run(loadNodes)}"/>
    </div>
    <ContextDBGraph v-else-if="tab==='graph'" :kb-id="kbId" @open-source-doc="id=>open({id})"/>
    <ContextDBWikiIssues ref="issuesRef" v-else-if="tab==='history'" :kb-id="kbId" :can-edit="editable" @open-page="openWikiPage" @open-source-doc="id=>open({id})" />
    <DocContent :visible="!!preview" :details="preview||{}" :kb-id="kbId" :can-edit-k-b="false" :can-download-k-b="true" @close-doc="preview=null" @get-doc="(value:number)=>{chunkPage=value;void loadChunks()}" />
    <t-dialog v-model:visible="nodeDialog" :header="nodeEditing?'编辑名称与位置':'新建目录'" @confirm="saveNode">
      <t-form label-align="top"><t-form-item label="名称" required><t-input v-model="nodeName" :maxlength="512" /></t-form-item>
        <t-form-item v-if="nodeEditing" label="目标目录"><t-cascader v-model="nodeTarget" :options="folderOptions" :load="loadFolders" check-strictly clearable :loading="folderLoading" placeholder="保持当前位置" /></t-form-item>
      </t-form><t-alert v-if="folderError" theme="error" :message="folderError" />
    </t-dialog>
    <KnowledgeBaseEditorModal :visible="ui.showKBEditorModal" :mode="ui.kbEditorMode" :kb-id="ui.currentKBId || undefined" @update:visible="v=>ui.showKBEditorModal=v" @success="()=>run(async()=>{base=(await getBase(kbId)).data})"/>
  </div>
</template>
<style scoped lang="less">
@import './knowledgePageLayout.less';
.contextdb-knowledge{height:100%;display:flex;flex-direction:column;min-height:0}
.native-documents{overflow:auto;flex:1}.native-toolbar{margin-bottom:20px}
.contextdb-knowledge :deep(.contextdb-wiki){flex:1;min-height:0}
</style>
