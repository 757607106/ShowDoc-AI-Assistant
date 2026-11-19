<script setup lang="ts">
import KnowledgeOverlay from './components/KnowledgeOverlay.vue'
import { computed, onUnmounted, ref, watch } from 'vue'
import { nativeAPI } from '@/api/contextdb'
import DocMarkdown from '@/components/DocMarkdown.vue'
const props=defineProps<{kbId:string;canEdit:boolean}>()
const templates=ref<any[]>([]),selected=ref<any>(null),error=ref(''),visible=ref(false)
const name=ref(''),isDefault=ref(false),sections=ref<{level:number;title:string;guidance:string}[]>([])
const loading=ref(false),detailLoading=ref(false),saving=ref(false),deleting=ref(false),templatesKbId=ref(''),editorKbId=ref('')
const deleteTarget = ref<any>(null)
const editorBaseline = ref('')
const editable=computed(()=>props.canEdit===true),busy=computed(()=>loading.value||detailLoading.value||saving.value||deleting.value)
const editorSnapshot = () => JSON.stringify([name.value, isDefault.value, sections.value])
const dirty = computed(() => editable.value && visible.value && !!editorBaseline.value && editorBaseline.value !== editorSnapshot())
const writing = computed(() => saving.value || deleting.value)
defineExpose({ dirty, saving: writing, load })
const preview=computed(()=>sections.value.map(section=>'#'.repeat([1,2,3].includes(section.level)?section.level:1)+' '+section.title+'\n'+section.guidance).join('\n\n'))
const root='knowledge/review_templates'
let listRequest=0,editorRequest=0
function query(kb:string,id?:string){return '?'+new URLSearchParams({knowledge_base_id:kb,...(id?{template_id:id}:{})})}
async function load(){
  const token=++listRequest,kb=props.kbId;templates.value=[];templatesKbId.value='';loading.value=!!kb;error.value=''
  if(!kb)return
  try{const {data}=await nativeAPI.get(root+query(kb));if(token!==listRequest||kb!==props.kbId)return
    if(!Array.isArray(data)||data.some(item=>!item||item.knowledge_base_id!==kb))throw new Error('模板列表所属知识库未确认，请刷新后重试')
    templates.value=data;templatesKbId.value=kb
  }catch(e:any){if(token===listRequest)error.value=e.message}finally{if(token===listRequest)loading.value=false}
}
async function detail(kb:string,id:string){
  const {data}=await nativeAPI.get(root+'/detail'+query(kb,id))
  if(!data)throw new Error('模板已不存在，请刷新列表')
  if(data.id!==id||data.knowledge_base_id!==kb||typeof data.name!=='string'||typeof data.is_default!=='boolean'||!Array.isArray(data.sections)||data.sections.some((section:any)=>!section||typeof section.title!=='string'||typeof section.guidance!=='string'))throw new Error('模板详情所属知识库未确认，请重新读取')
  return data
}
async function edit(item?:any){
  if(busy.value||(!item&&(!editable.value||templates.value.length>=5)))return
  const token=++editorRequest,kb=props.kbId
  selected.value=null;editorKbId.value='';editorBaseline.value='';name.value='';isDefault.value=false;sections.value=[];error.value='';visible.value=true
  if(!item){sections.value=[{level:1,title:'概述',guidance:'说明文件背景、适用范围和核心结论。'},{level:2,title:'关键信息',guidance:'按主题说明主要事实、配置或操作步骤。'},{level:2,title:'注意事项与建议',guidance:'列出风险、限制条件和后续可执行建议。'}];editorKbId.value=kb;editorBaseline.value=editorSnapshot();return}
  detailLoading.value=true
  try{const value=await detail(kb,item.id);if(token!==editorRequest||kb!==props.kbId||!visible.value)return
    selected.value=value;name.value=value.name;isDefault.value=value.is_default;sections.value=value.sections.map((section:any)=>({...section}));editorKbId.value=kb
    editorBaseline.value=editorSnapshot()
  }catch(e:any){if(token===editorRequest)error.value=e.message}finally{if(token===editorRequest)detailLoading.value=false}
}
async function save(){
  if(!editable.value||busy.value||!visible.value||editorKbId.value!==props.kbId)return
  error.value=''
  if(!name.value.trim()||name.value.trim().length>128){error.value='模板名称需为 1～128 个字符';return}
  if(!sections.value.length||sections.value.length>15||sections.value.some(s=>!Number.isInteger(s.level)||s.level<1||s.level>3||!s.title.trim()||/[\r\n]/.test(s.title)||!s.guidance.trim()||s.guidance.trim().split(/\r\n|\r|\n/).some(line=>!line.trim()))){error.value='请填写 1～15 个章节，标题为单行，撰写指引不能包含空行，标题级别为 1～3';return}
  const kb=props.kbId,token=editorRequest,original=selected.value
  const payload={name:name.value.trim(),is_default:isDefault.value,sections:sections.value.map(section=>({...section}))}
  saving.value=true
  try{
    if(original){
      const changed=(Object.keys(payload) as (keyof typeof payload)[]).filter(key=>JSON.stringify(payload[key])!==JSON.stringify(original[key]))
      if(changed.length){const current=await detail(kb,original.id);if(token!==editorRequest||kb!==props.kbId||!editable.value)return
        if(changed.some(key=>JSON.stringify(current[key])!==JSON.stringify(original[key])))throw new Error('模板已被更新，请刷新后重新编辑')
        await nativeAPI.put(root+query(kb,original.id),Object.fromEntries(changed.map(key=>[key,payload[key]])))
      }
    }else await nativeAPI.post(root+query(kb),payload)
    if(token!==editorRequest||kb!==props.kbId)return
    visible.value=false;await load()
  }catch(e:any){if(token===editorRequest)error.value=e.message}finally{saving.value=false}
}
async function remove(item:any){
  const kb=props.kbId
  if(!item||!editable.value||busy.value||templatesKbId.value!==kb||!templates.value.some(row=>row.id===item.id))return
  deleting.value=true;error.value=''
  try{const {data}=await nativeAPI.del(root+query(kb,item.id));if(kb!==props.kbId)return
    if(data?.deleted!==true)throw new Error('删除结果未确认，请刷新列表核对')
    deleteTarget.value = null
    await load()
  }catch(e:any){if(kb===props.kbId)error.value=e.message}finally{deleting.value=false}
}
function requestClose() {
  if (saving.value) return
  if (dirty.value && !window.confirm('放弃未保存的模板修改？')) return
  visible.value = false
}
watch(()=>props.kbId,()=>{editorRequest++;visible.value=false;selected.value=null;deleteTarget.value=null;editorKbId.value='';detailLoading.value=false;void load()},{immediate:true})
watch(visible,value=>{if(!value){editorRequest++;editorKbId.value='';detailLoading.value=false}})
onUnmounted(()=>{listRequest++;editorRequest++})
</script>
<template>
  <div class="rewrite-templates"><p class="template-description">为当前知识库配置文件重写的章节结构和撰写指引，AI 会按模板生成重写内容。</p><t-space><span>已使用{{templates.length}}/5个模板</span><t-button v-if="editable" :disabled="busy||templates.length>=5" @click="edit()">新建模板</t-button><t-button variant="text" :disabled="saving||deleting" :loading="loading" @click="load">刷新</t-button></t-space>
    <t-alert v-if="error && !visible && !deleteTarget" role="alert" theme="error" :message="error"/>
    <t-table row-key="id" :data="templates" :loading="loading" :columns="[{colKey:'name',title:'模板名称'},{colKey:'is_default',title:'默认模板'},{colKey:'operations',title:'操作'}]"><template #is_default="{row}">{{row.is_default?'是':'否'}}</template><template #operations="{row}"><t-button variant="text" :disabled="busy" @click="edit(row)">{{editable?'编辑':'查看'}}</t-button><t-button v-if="editable" variant="text" theme="danger" :disabled="busy" @click="error='';deleteTarget=row">删除</t-button></template><template #empty>暂无重写模板</template></t-table>
    <KnowledgeOverlay dialog-class-name="contextdb-overlay" :visible="visible" @update:visible="(value: boolean) => { if(!value) requestClose() }" :header="selected?'重写模板':'新建重写模板'" width="1160px" :close-btn="!saving" :close-on-overlay-click="!saving" :close-on-esc-keydown="!saving">
      <t-loading :loading="detailLoading"><div class="template-editor"><t-form label-align="top" :disabled="!editable||saving||detailLoading" class="template-form"><t-form-item label="模板名称" help="知识库内唯一，最多128个字符。" required><t-input v-model="name" :maxlength="128" placeholder="请输入模板名称"/></t-form-item><t-checkbox v-model="isDefault">设为默认模板</t-checkbox><div class="sections-heading"><span>章节（{{sections.length}}/15）</span><t-button v-if="editable" variant="outline" :disabled="saving||detailLoading||sections.length>=15" @click="sections.push({level:1,title:'',guidance:''})">添加章节</t-button></div><div v-for="(item,i) in sections" :key="i" class="section-row"><div class="section-heading"><strong>章节{{i+1}}</strong><t-select v-model="item.level" :options="[{value:1,label:'一级标题'},{value:2,label:'二级标题'},{value:3,label:'三级标题'}]"/><t-button v-if="editable" variant="text" :disabled="saving||detailLoading" @click="sections.splice(i,1)">删除章节</t-button></div><t-form-item label="章节标题" required><t-input v-model="item.title" placeholder="请输入章节标题"/></t-form-item><t-form-item label="撰写指引" required><t-textarea v-model="item.guidance" :autosize="{minRows:2,maxRows:6}" placeholder="请输入本章节的撰写指引"/></t-form-item></div></t-form><div class="template-preview"><h3>预览</h3><DocMarkdown :content="!editable&&selected?.content?selected.content:preview"/></div></div></t-loading><t-alert v-if="error" role="alert" :message="error" theme="error"/>
      <template #footer><t-button v-if="editable" :disabled="busy||editorKbId!==kbId" :loading="saving" @click="save">保存模板</t-button><t-button variant="outline" :disabled="saving" @click="requestClose">{{ editable ? '取消' : '关闭' }}</t-button></template>
    </KnowledgeOverlay>
    <KnowledgeOverlay :visible="!!deleteTarget" header="删除重写模板" :confirm-btn="{content:'删除模板',theme:'danger',loading:deleting}"
      :cancel-btn="{disabled:deleting}" :close-on-esc-keydown="!deleting" :close-on-overlay-click="!deleting" :close-btn="!deleting"
      @update:visible="(value: boolean) => { if(!value&&!deleting) deleteTarget=null }" @confirm="remove(deleteTarget)">
      <p>删除“{{ deleteTarget?.name }}”？此操作无法撤销。</p>
      <t-alert v-if="error" role="alert" theme="error" :message="error" />
    </KnowledgeOverlay>
  </div>
</template>
<style scoped>
.rewrite-templates,.template-editor{font-family:var(--app-font-family);font-size:var(--app-text-base)}
.template-description{font-size:var(--app-text-md);margin:0 0 16px;color:var(--td-text-color-secondary);line-height:1.7}.rewrite-templates>.t-table{margin-top:16px}.template-editor{display:grid;grid-template-columns:55fr 45fr;max-height:65vh;min-height:420px}.template-form{overflow:auto;padding:0 24px 0 0}.template-preview{overflow:auto;padding:0 0 0 24px;border-left:1px solid var(--td-component-border)}.template-preview h3{margin:0 0 16px;font-size:var(--app-text-3xl);font-weight:600}.sections-heading,.section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.sections-heading{margin:24px 0 12px}.section-heading{margin-bottom:16px}.section-heading>.t-select__wrap{width:140px;margin-left:auto}.section-row{margin:16px 0;padding:16px;border:1px solid var(--td-component-border);border-radius:var(--app-radius-md)}.section-row :deep(.t-form__item){margin-bottom:16px}.section-row :deep(.t-form__item:last-child){margin-bottom:0}@media(max-width:760px){.template-editor{display:block;min-height:0;overflow:auto}.template-preview{border-left:0;padding:20px 0 0}.template-form{padding-right:0}.section-heading{flex-wrap:wrap}.section-heading>.t-select__wrap{margin-left:0}}
.sections-heading>span{font-size:var(--app-text-3xl);font-weight:600}.section-heading strong{font-size:var(--app-text-xl);font-weight:600}
</style>

<style scoped lang="less">
@import './knowledgePageLayout.less';
</style>
