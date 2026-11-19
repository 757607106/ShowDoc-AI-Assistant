<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { getDocument, nativeAPI, uploadDocumentFile, updateDocumentMetadata, retryDocument } from '@/api/contextdb'
import api from '@/api/backend'
import { batchDownloadKnowledge, getKnowledgeDetailsCon } from '@/api/knowledge-base'
import ContextDBSourcePreview from '@/components/ContextDBSourcePreview.vue'
import DocMarkdown from '@/components/DocMarkdown.vue'
import { chunkAttachments } from '@/utils/contextdbResources'
import PanelResizeHandle from '@/components/PanelResizeHandle.vue'
import ContextDBMetadata from './ContextDBMetadata.vue'
import { formatFileSize, getFileIcon } from '@/utils/files'
import { documentDisplayName, documentDownloadName } from '@/utils/contextdbDocumentName'

const props=defineProps<{kbId:string;canEdit:boolean;wikiEnabled?:boolean;graphEnabled?:boolean;reviewEnabled?:boolean;documentId?:string;folderId?:string;baseName?:string;syncLocation?:boolean}>()
const emit = defineEmits<{ navigate: [folderId: string, documentId?: string] }>()
const rows=ref<any[]>([]),tree=ref<any[]>([]),breadcrumbs=ref<any[]>([]),parent=ref(''),rootId=ref(''),page=ref(1),pageSize=ref(20),total=ref(0),loading=ref(false),error=ref(''),selected=ref<string[]>([])
const sortBy=ref('created_at'),sortOrder=ref('desc'),width=ref(260);let startWidth=260,request=0,previewRequest=0,uploadRequest=0,chunkRequest=0,writeEpoch=0,metadataRequest=0
const preview=ref<any>(null),previewLoading=ref(false),previewError=ref(''),previewMode=ref('original'),chunks=ref<any[]>([]),chunkPage=ref(1),chunkTotal=ref(0),chunkLoading=ref(false)
const nodeDialog=ref(''),node=ref<any>(null),nodeName=ref(''),target=ref(''),folderOptions=ref<any[]>([]),saving=ref(false)
const removing=ref<any[]>([]),recursiveDelete=ref(false),metadata=ref<any>(null),metadataText=ref(''),mutating=ref(false)
const uploadOpen=ref(false),files=ref<File[]>([]),uploading=ref(false),review=ref(false),fileInput=ref<HTMLInputElement|null>(null)
const selection=computed(()=>rows.value.filter(row=>selected.value.includes(row.node_id)))
const statusLabels:Record<string,string>={succeeded:'成功',failed:'失败',pending:'等待处理',uploading:'上传中',processing:'处理中',ai_reviewing:'评审中',pending_review:'待人工评审',deleting:'删除中',deleted:'已删除',building:'处理中',skipped:'已跳过',disabled:'未启用',compiled:'已编译'}
const state=(value:any)=>value?statusLabels[String(value).toLowerCase()]||String(value):'-'
const time=(value:any)=>value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'-'
const title=(row:any)=>row?.node_type==='file'&&/^doc-[a-f\d]{64}\./i.test(row.display_name||'')?documentDisplayName({...row,name:row.display_name,display_name:undefined}):row?.display_name||documentDisplayName(row)||''
async function readNodes(id:string,p=1,size=pageSize.value){return (await nativeAPI.get('knowledge/nodes',{knowledge_base_id:props.kbId,parent_node_id:id||undefined,page:p,page_size:size,sort_by:sortBy.value,sort_order:sortOrder.value})).data}
async function children(id:string){
  const kb=props.kbId,items:any[]=[]
  for(let p=1;;p++){const res=await readNodes(id,p,100);if(kb!==props.kbId)return [];items.push(...res.items);if(res.items.length<100||items.length>=res.total)break}
  return items.map(item=>({...item,label:title(item),children:item.has_children?true:undefined}))
}
async function loadChildren(item:any){try{return await children(item.value||item.node_id)}catch(e:any){error.value=e.message;throw e}}
async function load(){
  const token=++request,kb=props.kbId;loading.value=true;error.value='';selected.value=[]
  try{
    const res=await readNodes(parent.value,page.value)
    if(parent.value&&parent.value===props.folderId){
      const current=res.parent_node||res.breadcrumbs?.at(-1)
      if(current?.node_id!==props.folderId||!['folder','root'].includes(current?.node_type)||(current.knowledge_base_id&&current.knowledge_base_id!==kb)||(res.knowledge_base_id&&res.knowledge_base_id!==kb))throw new Error('导入目录不存在或无权访问，请核对知识库和目录链接')
    }
    const items=res.items.map((item:any)=>item.document_id?{...item,id:item.document_id}:item)
    if(token!==request||kb!==props.kbId)return
    rows.value=items;total.value=res.total;breadcrumbs.value=res.breadcrumbs||[];rootId.value=res.breadcrumbs?.[0]?.node_id||res.parent_node?.node_id||''
    return items
  }catch(e:any){if(token===request)error.value=e.message}finally{if(token===request)loading.value=false}
}
async function refresh(){const kb=props.kbId,items=await load();if(kb!==props.kbId)return;try{const nodes=await children('');if(kb===props.kbId)tree.value=nodes}catch(e:any){if(kb===props.kbId)error.value=e.message}return items}
async function enterNode(id=''){
  if (props.syncLocation) { emit('navigate', id); return }
  await clearPreview(false)
  parent.value=id;page.value=1;await load()
}
async function open(row:any){
  if(!row.document_id&&!row.id)return enterNode(row.node_id)
  const token=++previewRequest,kb=props.kbId;error.value='';previewError.value='';previewLoading.value=true
  try{const data=(await getDocument(row.document_id||row.id)).data;if(token!==previewRequest||kb!==props.kbId)return;preview.value={...row,...data,display_name:row.display_name||data.name,node_id:row.node_id||data.node_id,tree_version:row.tree_version??data.tree_version,wiki_status:row.node_id?row.wiki_status:data.wiki_status,id:data.id};previewMode.value='original';chunkPage.value=1;chunkRequest++;chunks.value=[];chunkTotal.value=0}
  catch(e:any){if(token===previewRequest)previewError.value=e.message}
  finally{if(token===previewRequest)previewLoading.value=false}
}
const documentMain = ref<HTMLElement | null>(null)
let openedFromTable = ''
let pendingFile: { row: any; fromTable: boolean } | undefined
async function openFile(row: any, fromTable = false) {
  const id = row.document_id || row.id
  if (!id) return enterNode(row.node_id)
  if (props.syncLocation) {
    pendingFile = { row, fromTable }
    emit('navigate', parent.value, id)
    return
  }
  await showFile(row, fromTable)
}
async function showFile(row: any, fromTable: boolean) {
  const loadingFile = open(row)
  const token = previewRequest
  if (fromTable && props.syncLocation) openedFromTable = row.node_id
  await loadingFile
  if (!fromTable || token !== previewRequest || (!props.syncLocation && !preview.value)) return
  openedFromTable = row.node_id
  await nextTick()
  documentMain.value?.querySelector<HTMLElement>('.preview-heading button')?.focus()
}
async function closePreview() {
  if (props.syncLocation) { emit('navigate', parent.value); return }
  await clearPreview()
}
async function clearPreview(restoreFocus = true) {
  const trigger = restoreFocus ? openedFromTable : ''
  openedFromTable = ''
  previewRequest++
  preview.value = null
  previewLoading.value = false
  previewError.value = ''
  await nextTick()
  if (trigger) {
    documentMain.value?.querySelector<HTMLElement>('[data-node-open="' + CSS.escape(trigger) + '"]')?.focus()
  }
}
async function loadChunks(){
  if(!preview.value)return
  const id=preview.value.id,token=++chunkRequest,previewToken=previewRequest;chunkLoading.value=true;error.value=''
  try{const res=await getKnowledgeDetailsCon(id,chunkPage.value);if(token===chunkRequest&&previewToken===previewRequest){chunks.value=res.data;chunkTotal.value=res.total}}
  catch(e:any){if(token===chunkRequest&&previewToken===previewRequest)error.value=e.message}
  finally{if(token===chunkRequest&&previewToken===previewRequest)chunkLoading.value=false}
}
watch(previewMode,value=>{if(value==='chunks')void loadChunks()})
function menu(row:any){return [{content:'进入下级',value:'enter'},...(props.canEdit?[{content:'新建子目录',value:'folder'},{content:'重命名',value:'rename'},{content:'移动到…',value:'move'},{content:'删除',value:'delete',theme:'error' as const}]:[]),...(props.canEdit&&row.ingest_status==='failed'?[{content:'重试',value:'retry'}]:[])]}
async function act(row:any,value:string){if(value==='enter')return enterNode(row.node_id);if(!props.canEdit)return;if(value==='delete'){removing.value=[row];recursiveDelete.value=false;return}if(value==='retry'){try{await retryDocument(row.document_id||row.id);await refresh()}catch(e:any){error.value=e.message}return}await editNode(value,row)}
async function editNode(kind:string,row?:any){
  if(!props.canEdit||saving.value)return
  node.value=row||null;nodeDialog.value=kind;nodeName.value=kind==='rename'?title(row):'';target.value='';error.value='';folderOptions.value=[]
  if(kind==='move'){try{folderOptions.value=[{node_id:rootId.value,display_name:'主页',children:true}]}catch(e:any){error.value=e.message}}
}
async function saveNode(){
  if(!props.canEdit||saving.value)return
  const kind=nodeDialog.value,current=node.value,destination=target.value,label=nodeName.value.trim(),kb=props.kbId,epoch=writeEpoch
  if(kind==='move'&&!destination){error.value='请选择目标目录';return}
  if(kind!=='move'&&!label){error.value='请输入名称';return}
  saving.value=true;error.value=''
  try{
    if(kind==='folder')await nativeAPI.post('knowledge/nodes',{knowledge_base_id:kb,parent_node_id:current?.node_id||parent.value||undefined,display_name:label})
    else if(kind==='move'&&Array.isArray(current)){
      const ids=current.map((n:any)=>n.node_id),versions=Object.fromEntries(current.map((n:any)=>[n.node_id,n.tree_version]))
      const res=await nativeAPI.post('knowledge/nodes/batch?knowledge_base_id='+encodeURIComponent(kb),{action:'move',ids,expected_tree_versions:versions,parent_node_id:destination})
      if(epoch!==writeEpoch)return
      const results=res.data.results||[],failures=current.filter((n:any)=>!results.find((r:any)=>r.id===n.node_id)?.success)
      if(failures.length){node.value=failures;throw new Error(failures.map((n:any)=>results.find((r:any)=>r.id===n.node_id)?.error||'移动结果未确认，请刷新后核对').join('；'))}
    }else await nativeAPI.patch('knowledge/nodes?knowledge_base_id='+encodeURIComponent(kb),{node_id:current.node_id,expected_tree_version:current.tree_version,...(kind==='move'?{parent_node_id:destination}:{display_name:label})})
    if(epoch!==writeEpoch)return
    nodeDialog.value='';await refresh()
  }catch(e:any){if(epoch===writeEpoch)error.value=e.message}finally{if(epoch===writeEpoch)saving.value=false}
}
async function remove(){
  if(!props.canEdit||mutating.value||!removing.value.length)return
  mutating.value=true;error.value=''
  const items=[...removing.value],kb=props.kbId,epoch=writeEpoch,recursive=recursiveDelete.value
  try{
    if(items.some(item=>!Number.isInteger(item.tree_version)))throw new Error('目录版本未返回，请刷新后核对再删除')
    if(items.length===1){const item=items[0],query=new URLSearchParams({knowledge_base_id:kb,node_id:item.node_id,expected_tree_version:String(item.tree_version),recursive:String(recursive)});const res=await nativeAPI.del('knowledge/nodes?'+query);if(epoch!==writeEpoch)return;if(res.data.deleted!==true)throw new Error('删除结果未确认，请刷新后核对')}
    else{const res=await nativeAPI.del('knowledge/nodes/batch?knowledge_base_id='+encodeURIComponent(kb),{ids:items.map(item=>item.node_id),expected_tree_versions:Object.fromEntries(items.map(item=>[item.node_id,item.tree_version])),recursive});if(epoch!==writeEpoch)return;const failures=items.filter(item=>!res.data.results?.find((r:any)=>r.id===item.node_id)?.success);removing.value=failures;if(failures.length)throw new Error(failures.map((n:any)=>res.data.results?.find((r:any)=>r.id===n.node_id)?.error||'删除结果未确认，请刷新后核对').join('；'))}
    if(epoch!==writeEpoch)return
    removing.value=[];if(preview.value)await closePreview();await refresh()
  }catch(e:any){
    if(epoch!==writeEpoch)return
    const pending=[...removing.value]
    rows.value=[];tree.value=[];total.value=0
    if(preview.value)await closePreview()
    const fresh=await refresh()
    if(epoch!==writeEpoch)return
    removing.value=pending.filter(item=>fresh?.some((row:any)=>row.node_id===item.node_id&&row.tree_version===item.tree_version))
    error.value=[e.message,error.value].filter(Boolean).join('；')
  }finally{if(epoch===writeEpoch)mutating.value=false}
}
async function editMetadata(row:any){
  if(saving.value)return
  const token=++metadataRequest,epoch=writeEpoch;error.value=''
  try{const data=(await getDocument(row.document_id||row.id)).data;if(token!==metadataRequest||epoch!==writeEpoch)return;metadata.value={...row,...data};metadataText.value=JSON.stringify(data.metadata||data.custom_metadata||{},null,2)}
  catch(e:any){if(token===metadataRequest&&epoch===writeEpoch)error.value=e.message}
}
function closeMetadata(){if(!saving.value){metadataRequest++;metadata.value=null;error.value=''}}

async function saveMetadata(){
  if(!props.canEdit||saving.value)return
  const current=metadata.value,kb=props.kbId,epoch=writeEpoch
  if(!current)return
  saving.value=true;error.value=''
  try{const value=JSON.parse(metadataText.value);if(!value||Array.isArray(value)||typeof value!=='object')throw new Error('元数据必须是 JSON 对象');await updateDocumentMetadata(current.document_id||current.id,value);if(epoch!==writeEpoch||metadata.value!==current)return;metadata.value=null;await refresh()}
  catch(e:any){if(epoch===writeEpoch)error.value=e.message}finally{if(epoch===writeEpoch)saving.value=false}
}
function add(){if(!props.canEdit)return;files.value=[];review.value=!!props.reviewEnabled;uploadOpen.value=true;error.value=''}
function chooseFiles(event:Event){const input=event.target as HTMLInputElement;files.value=[...files.value,...Array.from(input.files||[])];input.value=''}
function dropped(event:DragEvent){if(!uploading.value)files.value=[...files.value,...Array.from(event.dataTransfer?.files||[])]}
async function upload(){
  if(!props.canEdit||uploading.value||!files.value.length)return
  if(files.value.some(file=>!file.size||file.size>2*1024*1024)){error.value='所有格式统一限制单文件为 1 B 至 2 MB，超过限制无法上传。';return}
  uploading.value=true;error.value='';const kb=props.kbId,folder=parent.value,queue=[...files.value],reviewEnabled=review.value,token=++uploadRequest
  try{for(const file of queue){if(token!==uploadRequest)return;await uploadDocumentFile(kb,file,{parent_node_id:folder||undefined,review_enabled:reviewEnabled});if(token!==uploadRequest)return;files.value.shift()}uploadOpen.value=false;await refresh()}
  catch(e:any){if(token===uploadRequest)error.value=e.message}finally{if(token===uploadRequest)uploading.value=false}
}
async function download(row:any){try{const id=row.document_id||row.id,doc=row.name?row:(await getDocument(id)).data;await api.downloadFile('/api/contextdb/documents/'+encodeURIComponent(id)+'/download',documentDownloadName({...doc,document_display_name:title(row)}))}catch(e:any){error.value=e.message}}
async function downloadSelected(){try{const ids=selection.value.filter(row=>row.document_id).map(row=>row.document_id);if(!ids.length)return;const blob=await batchDownloadKnowledge(props.kbId,ids),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='knowledge-documents.zip';link.click();URL.revokeObjectURL(url)}catch(e:any){error.value=e.message}}
watch(()=>[props.kbId,props.folderId] as const,([kb,folder],previous)=>{
  request++;uploadRequest++;writeEpoch++;metadataRequest++;chunkRequest++
  saving.value=false;mutating.value=false;uploading.value=false;rows.value=[];breadcrumbs.value=[];total.value=0
  parent.value=folder||'';page.value=1;removing.value=[];nodeDialog.value='';metadata.value=null;uploadOpen.value=false
  if(kb!==previous?.[0]||!props.syncLocation){tree.value=[];rootId.value='';void refresh()}
  else void load()
},{immediate:true})
watch(()=>[props.kbId,props.folderId,props.documentId] as const,([kb,folder,id],previous)=>{
  const requested=pendingFile
  pendingFile=undefined
  void clearPreview(!id && kb===previous?.[0] && folder===previous?.[1])
  if(!id)return
  if(requested&&(requested.row.document_id||requested.row.id)===id)void showFile(requested.row,requested.fromTable)
  else void open(rows.value.find(row=>row.document_id===id)||{id})
},{immediate:true})
onUnmounted(()=>{request++;previewRequest++;uploadRequest++;chunkRequest++;writeEpoch++;metadataRequest++})
</script>
<template>
  <section class="document-workspace"><aside class="document-tree" :style="{width:width+'px'}"><button class="tree-home" :class="{active:!parent&&!preview}" @click="enterNode()"><t-icon name="view-module" size="var(--app-text-xl)" />主页</button><div class="tree-heading"><span><t-icon name="view-list" />目录</span><t-dropdown v-if="canEdit" :options="[{content:'新建目录',value:'folder'}]" @click="editNode('folder')"><t-button variant="text" shape="square" aria-label="目录 更多操作"><t-icon name="more" /></t-button></t-dropdown></div>
    <t-tree :data="tree" :keys="{value:'node_id',label:'label',children:'children'}" :load="loadChildren" activable :expand-on-click-node="false" @click="({node}:any)=>node.data.node_type==='file'?openFile(node.data):enterNode(node.value)"><template #icon="{node}"><t-icon :name="node.data.node_type==='file'?getFileIcon(node.label):'folder'" /></template><template #operations="{node}"><t-dropdown :options="menu(node.data)" @click="(item:any)=>act(node.data,item.value)"><t-button variant="text" shape="square" :aria-label="'更多操作 '+node.label" @click.stop><t-icon name="more" /></t-button></t-dropdown></template></t-tree>
    <PanelResizeHandle edge="right" label="拖拽调整文档列表宽度" :value="width" :min="200" :max="480" @start="startWidth=width" @resize="delta=>width=Math.max(200,Math.min(480,startWidth+delta))" />
  </aside><main ref="documentMain" class="document-main"><t-alert v-if="error || previewError" theme="error" :message="previewError || error" close />
    <template v-if="!preview && !(syncLocation && documentId)"><t-breadcrumb class="document-location">
      <t-breadcrumb-item><button type="button" class="document-text-button" @click="enterNode()">主页</button></t-breadcrumb-item>
      <t-breadcrumb-item v-for="crumb in breadcrumbs.filter(item=>item.node_type!=='root')" :key="crumb.node_id">
        <button type="button" class="document-text-button" @click="enterNode(crumb.node_id)">{{crumb.display_name}}</button>
      </t-breadcrumb-item>
    </t-breadcrumb>
      <div class="document-toolbar"><t-select v-model="sortBy" aria-label="排序" :options="[{value:'created_at',label:'创建时间'},{value:'updated_at',label:'更新时间'}]" @change="page=1;load()" /><t-button variant="outline" aria-label="排序方向" @click="sortOrder=sortOrder==='asc'?'desc':'asc';page=1;load()"><t-icon :name="sortOrder==='asc'?'arrow-up':'arrow-down'" /></t-button><div class="toolbar-actions"><t-button v-if="canEdit" variant="outline" @click="editNode('folder')">新建目录</t-button><t-button v-if="canEdit" @click="add"><t-icon name="upload" />上传文件</t-button><t-button variant="outline" :loading="loading" @click="refresh"><t-icon name="refresh" />刷新</t-button></div></div>
      <div v-if="selected.length" class="selection-actions"><span>已选择 {{selected.length}} 项</span><t-button variant="text" @click="downloadSelected">下载</t-button><t-button v-if="canEdit" variant="text" :disabled="selected.length>50" @click="editNode('move',selection)">移动到…</t-button><t-button v-if="canEdit" variant="text" theme="danger" :disabled="selected.length>50" @click="removing=[...selection];recursiveDelete=false">删除</t-button></div>
      <t-table row-key="node_id" :data="rows" :loading="loading" :selected-row-keys="selected" @select-change="(keys:(string|number)[])=>selected=keys.map(String)" :columns="[{colKey:'selection',type:'multiple' as const,width:44},{colKey:'name',title:'文件名称',minWidth:200},{colKey:'metadata',title:'元数据',width:150},{colKey:'ingest_status',title:'入库状态',width:100},...(wikiEnabled?[{colKey:'wiki_status',title:'WIKI 状态',width:100}]:[]),...(graphEnabled?[{colKey:'graph_status',title:'图谱状态',width:100}]:[]),{colKey:'size_bytes',title:'文件大小',width:100},{colKey:'updated_at',title:'最后一次更新时间',width:170},{colKey:'actions',title:'操作',width:160}]">
        <template #name="{row}">
          <button type="button" class="document-text-button document-file-open" :data-node-open="row.node_id"
            @click="row.node_type==='file'?openFile(row, true):enterNode(row.node_id)">
            <t-icon :name="row.node_type==='file'?getFileIcon(title(row)):'folder'" aria-hidden="true" />{{title(row)}}
          </button>
        </template><template #metadata="{row}"><span v-if="!Object.keys(row.metadata||{}).length">-</span><t-link v-else @click="editMetadata(row)">{{Object.entries(row.metadata).slice(0,2).map(([key,value])=>key+' '+value).join(' ')}}</t-link></template><template #ingest_status="{row}"><span :class="{'status-success':row.ingest_status==='succeeded','status-failure':row.ingest_status==='failed'}">{{state(row.ingest_status)}}</span></template><template #wiki_status="{row}">{{state(row.wiki_status)}}</template><template #graph_status="{row}"><span :class="{'status-success':row.graph_status==='succeeded'}">{{state(row.graph_status)}}</span></template><template #size_bytes="{row}">{{formatFileSize(row.size_bytes)||'-'}}</template><template #updated_at="{row}">{{time(row.updated_at)}}</template><template #actions="{row}"><t-space><t-button v-if="row.node_type==='file'" variant="text" @click="editMetadata(row)">元数据</t-button><t-dropdown :options="menu(row)" @click="(item:any)=>act(row,item.value)"><t-button variant="text">更多<t-icon name="chevron-down" /></t-button></t-dropdown></t-space></template>
      </t-table><div class="document-pagination"><span>当前层共 {{total}} 项</span><t-pagination :current="page" :total="total" :page-size="pageSize" :page-size-options="[20,50,100]" :total-content="false" @current-change="(value:number)=>{page=value;load()}" @page-size-change="(value:number)=>{pageSize=value;page=1;load()}" /></div>
    </template><template v-else><div class="preview-heading"><t-button variant="text" shape="square" aria-label="返回文件列表" @click="closePreview"><t-icon name="chevron-left" /></t-button><h2>{{preview ? title(preview) : '文件预览'}}</h2><t-space v-if="preview"><t-button variant="outline" @click="editMetadata(preview)">元数据</t-button><t-button v-if="canEdit&&preview.node_id" variant="outline" @click="removing=[preview];recursiveDelete=false">删除</t-button><t-button variant="outline" @click="download(preview)">下载原文</t-button><t-button variant="outline" @click="open(preview)">刷新</t-button></t-space></div><t-loading v-if="!preview && previewLoading" text="正在加载文件" /><template v-if="preview"><p class="preview-status">入库状态：{{state(preview.ingest_status)}} <span v-if="wikiEnabled">WIKI 状态：{{state(preview.wiki_status)}}</span><span v-if="graphEnabled">图谱状态：{{state(preview.graph_status)}}</span>文件大小：{{formatFileSize(preview.size_bytes)||'-'}}　最后一次更新时间：{{time(preview.updated_at)}}</p><t-radio-group v-model="previewMode" variant="default-filled"><t-radio-button value="original">原文</t-radio-button><t-radio-button value="chunks">Chunks</t-radio-button></t-radio-group><ContextDBSourcePreview v-if="previewMode==='original'" :key="`${preview.id}:${preview.current_snapshot_id || preview.updated_at || ''}`" :document-id="preview.id" :kb-id="kbId" :title="title(preview)" /><t-loading v-else :loading="chunkLoading"><section v-for="chunk in chunks" :key="chunk.id" class="document-chunk"><DocMarkdown :content="chunk.content||''" :source-name="preview.name" :source-display-name="title(preview)" :attachments="chunkAttachments([chunk], preview.id)" :kb-id="kbId" /></section><t-pagination :current="chunkPage" :total="chunkTotal" :page-size="25" :show-page-size="false" @current-change="(value:number)=>{chunkPage=value;loadChunks()}" /></t-loading></template></template>
  </main>
  <t-dialog dialog-class-name="contextdb-overlay" :visible="!!nodeDialog" :header="nodeDialog==='rename'?'重命名':nodeDialog==='move'?'移动到…':'新建目录'" :confirm-btn="{content:'确定',loading:saving}" :close-on-overlay-click="!saving" @update:visible="(value:boolean)=>{if(!value&&!saving)nodeDialog=''}" @confirm="saveNode"><t-input v-if="nodeDialog!=='move'" v-model="nodeName" :maxlength="512" placeholder="名称" @enter="saveNode" /><t-cascader v-else v-model="target" :options="folderOptions" :keys="{value:'node_id',label:'display_name',children:'children'}" :load="loadChildren" check-strictly placeholder="选择目标目录" /><t-alert v-if="error" theme="error" :message="error" /></t-dialog>
  <t-dialog dialog-class-name="contextdb-overlay" :visible="!!removing.length" header="删除" :confirm-btn="{content:'确定',theme:'danger',loading:mutating}" :close-on-overlay-click="!mutating" @update:visible="(value:boolean)=>{if(!value&&!mutating)removing=[]}" @confirm="remove"><p>确定删除所选的 {{removing.length}} 项吗？</p><t-checkbox v-model="recursiveDelete">同时删除子目录及其中的文件</t-checkbox><t-alert v-if="error" theme="error" :message="error" /></t-dialog>
  <ContextDBMetadata :document="metadata" :visible="!!metadata" :can-edit="canEdit" :saving="saving" :error="error" v-model:text="metadataText" @save="saveMetadata" @close="closeMetadata" />
  <t-dialog dialog-class-name="contextdb-overlay" v-model:visible="uploadOpen" header="上传文件" width="720px" :close-on-overlay-click="!uploading" :close-btn="!uploading" :cancel-btn="{content:'取消',disabled:uploading}" :confirm-btn="{content:'确定',loading:uploading,disabled:!files.length}" @confirm="upload"><p>当前位置：{{baseName}}<span v-for="crumb in breadcrumbs.filter(item=>item.node_type!=='root')" :key="crumb.node_id"> / {{crumb.display_name}}</span></p><input ref="fileInput" type="file" multiple hidden aria-label="选择上传文件" @change="chooseFiles" /><button class="file-drop" type="button" :disabled="uploading" @click="fileInput?.click()" @dragover.prevent @drop.prevent="dropped"><t-icon name="upload" size="32px" /><strong>点击选择或将文件拖到这里</strong><span>支持文本、Office、表格、网页、EPUB 与常见代码文件格式</span></button><p>所有格式统一限制单文件为 1 B 至 2 MB，超过限制无法上传。</p><div v-for="(file,index) in files" :key="index" class="upload-file"><span>{{file.name}}　{{formatFileSize(file.size)}}</span><t-button variant="text" :disabled="uploading" @click="files.splice(index,1)">删除</t-button></div><t-checkbox v-model="review" :disabled="uploading">上传后进行知识评审</t-checkbox><t-alert v-if="error" theme="error" :message="error" /></t-dialog>
  </section>
</template>
<style scoped lang="less">
.document-text-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;

  &:hover { text-decoration: underline; }
  &:focus-visible {
    outline: 2px solid var(--td-brand-color);
    outline-offset: 2px;
  }
}
.document-file-open {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--td-brand-color);
}

.document-workspace{display:flex;flex:1;min-height:440px;overflow:hidden;border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-lg) var(--app-radius-lg) 0 0}.document-tree{flex:none;position:relative;padding:16px 10px;box-sizing:border-box;border-right:1px solid var(--td-component-stroke);background:var(--td-bg-color-sidebar);overflow-y:auto;overflow-x:hidden;min-width:200px}.tree-home{width:100%;height:36px;display:flex;align-items:center;gap:4px;padding:0 12px;border:0;border-radius:var(--app-radius-md);font:inherit;font-size:var(--app-text-base);background:transparent;cursor:pointer;color:var(--td-text-color-primary)}.tree-home.active{background:var(--app-selection-bg);color:var(--app-selection-text)}.tree-heading{display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding:8px 12px}.tree-heading>span{display:flex;align-items:center;gap:10px}.document-tree :deep(.t-tree__label){font-size:var(--app-text-base);overflow:hidden;text-overflow:ellipsis}.document-tree :deep(.t-tree__item){height:36px;min-width:0;padding-left:calc(12px + var(--td-comp-margin-xxl)*var(--level))}.document-tree :deep(.panel-resize-handle__grip){display:none}.document-main{flex:1;min-width:0;padding:16px 20px;overflow:auto}.document-location{margin-bottom:16px}.document-toolbar{display:flex;gap:8px;align-items:center;margin-bottom:16px}.document-toolbar>.t-select__wrap{width:144px}.toolbar-actions{margin-left:auto;display:flex;gap:8px}.document-pagination{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:16px;font-size:var(--app-text-md);color:var(--td-text-color-secondary)}.document-pagination>span{flex:none;white-space:nowrap}.document-pagination :deep(.t-pagination){justify-content:flex-end}.document-main :deep(.t-table td){height:64px}.document-main :deep(.t-table__header th){height:44px}.selection-actions{display:flex;align-items:center;gap:12px;margin-bottom:16px}.status-success{color:var(--td-success-color)}.status-failure{color:var(--td-error-color)}.preview-heading{display:flex;align-items:center;gap:8px}.preview-heading h2{flex:1;margin:0;font-size:var(--app-text-3xl);font-weight:600}.preview-status{display:flex;gap:24px;flex-wrap:wrap;font-size:var(--app-text-md);color:var(--td-text-color-secondary);margin:20px 0}.document-chunk{padding:16px;border-bottom:1px solid var(--td-component-stroke)}.document-main :deep(.doc-markdown-toggle){display:none}.file-drop{display:flex;align-items:center;flex-direction:column;justify-content:center;gap:12px;padding:32px;width:100%;border:1px dashed var(--td-component-stroke);border-radius:var(--app-radius-lg);background:var(--td-bg-color-secondarycontainer);font:inherit;cursor:pointer}.file-drop span{font-size:var(--app-text-md);color:var(--td-text-color-secondary)}.upload-file{display:flex;align-items:center;justify-content:space-between}.document-main>.t-alert{margin-bottom:12px}@media(max-width:900px){.document-tree{display:none}.document-main{padding:16px 10px}.document-toolbar{flex-wrap:wrap}.toolbar-actions{margin-left:0}.preview-heading{flex-wrap:wrap}}
.document-toolbar,.toolbar-actions,.document-pagination { flex-wrap: wrap; }
.document-pagination :deep(.t-pagination) { width: auto; }
.document-pagination :deep(.t-pagination),.preview-heading :deep(.t-space) { max-width: 100%; flex-wrap: wrap; }
</style>

<style scoped lang="less">
@import './knowledgePageLayout.less';
</style>
