<script setup lang="ts">
import { computed, ref } from 'vue'
import { contextdbToolLabel, stateLabel, permissionLabel, memberRoleLabel } from '@/utils/platformPresentation'

const props = withDefaults(defineProps<{ modelValue: any; readonly?: boolean; maxFields?: number }>(), { readonly: false })
const emit = defineEmits<{ 'update:modelValue': [value: any] }>()
const newName = ref(''), error = ref('')
const isArray = computed(() => Array.isArray(props.modelValue))
const entries = computed(() => Object.entries(props.modelValue || {}))
const types = [{value:'string',label:'文本'},{value:'number',label:'数字'},{value:'boolean',label:'是/否'},{value:'object',label:'分组'},{value:'array',label:'列表'},{value:'null',label:'空值'}]
const labels: Record<string, string> = {
  actions:'待执行操作', name:'名称', args:'操作内容', description:'说明', title:'标题', content:'内容',
  knowledge_base_id:'知识库编号', knowledge_base_ids:'知识库编号', document_id:'文档编号', document_ids:'文档编号',
  member_id:'成员编号', metadata:'附加信息', text:'正文', file_path:'来源路径', question:'问题', query:'关键词',
  topic:'主题', messages:'消息', role:'角色',
  entity_id:'实体编号', entity_name:'实体名称', relation_id:'关系编号', entity_type:'实体类型',
  source:'来源', target:'目标', relation:'关系', weight:'权重', snippet1:'矛盾片段一', snippet2:'矛盾片段二',
  kb_document_name:'已有文档', kb_fact:'已有事实', new_fact:'新增事实', conflict_type:'冲突类型',
  severity_score:'严重程度评分', ai_recommendation:'处理建议', resolvable:'可自动解决', confidence:'置信度',
  id:'编号', knowledge_base_name:'知识库名称', document_name:'文档名称', knowledge_bases:'知识库', documents:'文档',
  results:'结果', total:'总数', count:'数量', page:'当前页', page_size:'每页数量',
  created_at:'创建时间', updated_at:'更新时间', size_bytes:'文件大小（字节）',
  ingest_status:'入库状态', graph_status:'图谱状态', wiki_status:'Wiki 状态', review_status:'评审状态',
  status:'状态', event_id:'任务编号', chunk_count:'片段数', content_with_weight:'内容',
}
function displayValue(key:string,value:any){
  if(typeof value==='string'){
    if(key==='name'&&contextdbToolLabel(value))return contextdbToolLabel(value)
    if(key==='ingest_status')return stateLabel(value,'ingest')
    if(key==='graph_status')return stateLabel(value,'graph')
    if(key==='wiki_status')return stateLabel(value,'wiki')
    if(key==='review_status')return stateLabel(value,'review')
    if(key==='permission')return permissionLabel(value)
    if(key==='role'){
      const messageRole=({user:'用户',assistant:'助手',system:'系统'} as Record<string,string>)[value]
      const memberRole=memberRoleLabel(value)
      return messageRole||(memberRole==='未知角色'?value:memberRole)
    }
  }
  return value===null?'空值':typeof value==='boolean'?(value?'是':'否'):value===''?'空文本':value
}
function typeOf(value: any) { return value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value }
function update(key: string, value: any) {
  if (props.readonly) return
  emit('update:modelValue', isArray.value
    ? props.modelValue.map((item: any, index: number) => String(index) === key ? value : item)
    : Object.fromEntries(entries.value.map(([name, item]) => [name, name === key ? value : item])))
}
function remove(key: string) {
  if (props.readonly) return
  const remaining = entries.value.filter(([name]) => name !== key)
  emit('update:modelValue', isArray.value ? remaining.map(([, value]) => value) : Object.fromEntries(remaining))
}
function rename(key: string, name: string) {
  if (props.readonly || key === name) return
  if (!name.trim() || Object.hasOwn(props.modelValue, name)) { error.value = '字段名称不能为空或重复'; return }
  error.value = ''
  emit('update:modelValue', Object.fromEntries(entries.value.map(([old, value]) => [old === key ? name : old, value])))
}
function changeType(key: string, type: string) {
  update(key, ({string:'',number:0,boolean:false,object:{},array:[],null:null} as Record<string, any>)[type])
}
function add() {
  if (props.readonly) return
  if (isArray.value) { emit('update:modelValue', [...props.modelValue, '']); return }
  const name = newName.value.trim()
  if (!name || Object.hasOwn(props.modelValue, name)) { error.value = '字段名称不能为空或重复'; return }
  error.value = ''; newName.value = ''
  emit('update:modelValue', Object.fromEntries([...entries.value, [name, '']]))
}
</script>

<template>
  <div class="structured-fields">
    <div v-for="[key, value] in entries" :key="key" class="structured-field">
      <div class="field-heading">
        <span v-if="readonly || isArray" class="field-label">{{ isArray ? Number(key) + 1 : labels[key] || key }}</span>
        <t-input v-else :value="key" aria-label="字段名称" @blur="(value: string) => rename(key, value)" />
        <template v-if="!readonly">
          <t-select :value="typeOf(value)" :options="types" aria-label="字段类型" @change="(value: any) => changeType(key, String(value))" />
          <t-button variant="text" theme="danger" :aria-label="`删除字段 ${key}`" @click="remove(key)">删除</t-button>
        </template>
      </div>
      <StructuredFields v-if="value !== null && typeof value === 'object'" :model-value="value" :readonly="readonly" @update:model-value="(value: any) => update(key, value)" />
      <span v-else-if="readonly" class="field-value">{{ displayValue(key,value) }}</span>
      <t-input-number v-else-if="typeof value === 'number'" :value="value" :aria-label="key" @change="(value: any) => update(key, value ?? null)" />
      <t-switch v-else-if="typeof value === 'boolean'" :value="value" :aria-label="key" @change="(value: any) => update(key, value)" />
      <t-textarea v-else-if="value !== null" :value="String(value)" :aria-label="key" :autosize="{minRows:1,maxRows:6}" @change="(value: string) => update(key, value)" />
      <span v-else>空值</span>
    </div>
    <t-space v-if="!readonly && (maxFields == null || entries.length < maxFields)" class="field-add">
      <t-input v-if="!isArray" v-model="newName" placeholder="字段名称" aria-label="新增字段名称" @enter="add" />
      <t-button variant="outline" @click="add">{{ isArray ? '添加条目' : '添加字段' }}</t-button>
    </t-space>
    <t-alert v-if="error" theme="error" :message="error" />
    <span v-if="readonly && !entries.length">无</span>
  </div>
</template>

<style scoped>
.structured-field{padding:12px 0;border-bottom:1px solid var(--td-component-border)}
.field-heading{display:flex;align-items:center;gap:8px;margin-bottom:8px}.field-heading :deep(.t-select__wrap){max-width:110px}
.field-label{font-weight:500}.field-value{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
.structured-fields .structured-fields{padding-left:16px;border-left:2px solid var(--td-component-border)}.field-add{margin-top:12px}
</style>
