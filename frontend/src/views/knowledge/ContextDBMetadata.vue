<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatFileSize } from '@/utils/files'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { contextdbDateTime } from '@/utils/platformPresentation'

const props = defineProps<{ document: any; canEdit: boolean; saving: boolean; error: string; text: string; visible: boolean }>()
const emit = defineEmits<{ 'update:text': [value: string]; 'update:visible': [value: boolean]; save: []; close: [] }>()
type FieldType = 'string' | 'number' | 'boolean' | 'string[]' | 'number[]' | 'boolean[]'
type Field = { id: number; key: string; type: FieldType | 'invalid'; value: string }
const types = [{ value: 'string', label: '字符串' }, { value: 'number', label: '数字' }, { value: 'boolean', label: '布尔值' }, { value: 'string[]', label: '字符串数组' }, { value: 'number[]', label: '数字数组' }, { value: 'boolean[]', label: '布尔数组' }]
const reserved = new Set(['source_type', 'content_hash', 'snapshot_id', 'toc_path'])
const draftText = ref(props.text), originalText = ref(props.text), fields = ref<Field[]>([])
const editing = ref(false), view = ref<'table' | 'json'>('table'), fieldsError = ref('')
let fieldId = 0
function object(text: string): Record<string, any> {
  const value = JSON.parse(text)
  if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('元数据必须是 JSON 对象')
  return value
}
function validate(value: Record<string, any>) {
  const keys = Object.keys(value)
  if (keys.length > 32) return '元数据最多包含 32 个字段'
  for (const key of keys) {
    if (!key.trim() || key.length > 64) return '键名不能为空白且不能超过 64 个字符'
    if (reserved.has(key)) return `“${key}”是系统保留键，不能用作自定义字段`
    const item = value[key], values = Array.isArray(item) ? item : [item]
    if (Array.isArray(item) && item.length > 100) return `“${key}”的数组最多包含 100 项`
    const kind = values.length ? typeof values[0] : 'string'
    if (!['string', 'number', 'boolean'].includes(kind) || values.some(part => typeof part !== kind || (typeof part === 'number' && !Number.isFinite(part)))) return `“${key}”仅支持字符串、数字、布尔值及其同类数组`
    if (values.some(part => typeof part === 'string' && part.length > 4096)) return `“${key}”的字符串值不能超过 4096 个字符`
  }
  return ''
}
const jsonError = computed(() => {
  try { return validate(object(draftText.value)) } catch (error: any) { return error.message || 'JSON 格式不正确' }
})
const validationError = computed(() => fieldsError.value || jsonError.value)
function fieldType(value: any): Field['type'] {
  if (['string', 'number', 'boolean'].includes(typeof value)) return typeof value as FieldType
  if (Array.isArray(value) && (!value.length || ['string', 'number', 'boolean'].includes(typeof value[0]))) return `${typeof value[0] === 'undefined' ? 'string' : typeof value[0]}[]` as FieldType
  return 'invalid'
}
function readFields(text: string) {
  try { fields.value = Object.entries(object(text)).map(([key, value]) => ({ id: ++fieldId, key, type: fieldType(value), value: typeof value === 'string' ? value : JSON.stringify(value) })) } catch { /* Invalid JSON stays in the code editor until corrected. */ }
}
function reset() {
  originalText.value = props.text; draftText.value = props.text; editing.value = false; fieldsError.value = ''; view.value = 'table'; fields.value = []
  readFields(props.text)
  if (jsonError.value) view.value = 'json'
}
function startEditing() {
  if (!props.canEdit || props.saving) return
  editing.value = true; fieldsError.value = ''
  if (jsonError.value) view.value = 'json'
}
function syncFields() {
  if (!editing.value || !props.canEdit || props.saving) return false
  fieldsError.value = ''
  try {
    if (new Set(fields.value.map(field => field.key)).size !== fields.value.length) throw new Error('键名不能重复')
    const entries = fields.value.map(field => {
      if (field.type === 'string') return [field.key, field.value]
      const value = JSON.parse(field.value)
      const kind = field.type.replace('[]', '')
      if (field.type.endsWith('[]') ? !Array.isArray(value) || value.some(part => typeof part !== kind) : typeof value !== kind) throw new Error(`“${field.key}”的值与所选数据类型不一致`)
      return [field.key, value]
    })
    const value = Object.fromEntries(entries)
    draftText.value = JSON.stringify(value, null, 2); emit('update:text', draftText.value)
    fieldsError.value = validate(value)
    return !fieldsError.value
  } catch (error: any) { fieldsError.value = error.message || '请检查字段值'; return false }
}
function updateJson(value: string) {
  if (!editing.value || !props.canEdit || props.saving) return
  draftText.value = value; fieldsError.value = ''; emit('update:text', value)
  if (!jsonError.value) readFields(value)
}
function setView(value: 'table' | 'json') {
  if (props.saving || value === view.value) return
  if (editing.value && (view.value === 'table' ? !syncFields() : !!jsonError.value)) return
  view.value = value
}
function addField() {
  if (!editing.value || !props.canEdit || props.saving || fields.value.length >= 32) return
  fields.value.push({ id: ++fieldId, key: '', type: 'string', value: '' }); syncFields()
}
function removeField(index: number) {
  if (!editing.value || !props.canEdit || props.saving) return
  fields.value.splice(index, 1); syncFields()
}
function clearFields() {
  if (!editing.value || !props.canEdit || props.saving) return
  fields.value = []; syncFields()
}
function resetFields() {
  if (!editing.value || !props.canEdit || props.saving) return
  draftText.value = originalText.value; fieldsError.value = ''; readFields(originalText.value); emit('update:text', originalText.value)
}
function cancelEditing() {
  if (props.saving || !editing.value) return
  draftText.value = originalText.value; fieldsError.value = ''; readFields(originalText.value); emit('update:text', originalText.value); editing.value = false
}
const changes = computed(() => {
  try {
    const before = object(originalText.value), after = object(draftText.value)
    return { added: Object.keys(after).filter(key => !Object.hasOwn(before, key)).length, modified: Object.keys(after).filter(key => Object.hasOwn(before, key) && JSON.stringify(before[key]) !== JSON.stringify(after[key])).length, deleted: Object.keys(before).filter(key => !Object.hasOwn(after, key)).length }
  } catch { return { added: 0, modified: 0, deleted: 0 } }
})
const dirty = computed(() => validationError.value ? draftText.value !== originalText.value || !!fieldsError.value : changes.value.added + changes.value.modified + changes.value.deleted > 0)
function save() {
  if (!editing.value || !props.canEdit || props.saving || !dirty.value || validationError.value) return
  emit('update:text', draftText.value); emit('save')
}
function close() {
  if (props.saving) return
  emit('update:visible', false); emit('close')
}
const fileName = computed(() => props.document?.file_name || documentDisplayName(props.document) || props.document?.display_name || props.document?.name || '')
const details = computed(() => [
  ['文件ID', props.document?.document_id || props.document?.id || '-'],
  ['文件类型', props.document?.source_type || '-'],
  ['切片数', props.document?.chunk_count ?? '-'], ['Token 数', props.document?.token_count ?? '-'],
  ['待处理分块变更数', props.document?.pending_chunk_change_count ?? '-'], ['文件大小', formatFileSize(props.document?.size_bytes ?? props.document?.file_size) || '-'],
  ['召回次数', props.document?.recall_count ?? '-'], ['最后召回时间', props.document?.last_recalled_at ? contextdbDateTime(props.document.last_recalled_at) : '从未召回'],
  ['创建时间', contextdbDateTime(props.document?.created_at)],
])
watch(() => [props.visible, props.document?.document_id || props.document?.id], () => { if (props.visible) reset() }, { immediate: true })
watch(() => props.text, value => {
  if (value === draftText.value) return
  draftText.value = value; fieldsError.value = ''; readFields(value)
  if (!editing.value) originalText.value = value
  if (jsonError.value) view.value = 'json'
})
</script>

<template>
  <t-drawer :visible="visible" :header="`文件详情 · ${fileName}`" size="min(800px, 96vw)" :close-btn="!saving" :close-on-overlay-click="false" @update:visible="(value:boolean)=>{if(!value)close()}">
    <div class="file-details">
      <dl class="details-grid"><div v-for="([label,value]) in details" :key="label"><dt>{{label}}</dt><dd>{{value}}</dd></div></dl>
      <section class="metadata-section">
        <div class="metadata-heading"><h3>元数据</h3><div class="metadata-views"><t-button variant="text" shape="square" aria-label="表格视图" :class="{selected:view==='table'}" :disabled="saving" @click="setView('table')"><t-icon name="table" /></t-button><t-button variant="text" shape="square" aria-label="代码视图" :class="{selected:view==='json'}" :disabled="saving" @click="setView('json')"><t-icon name="code" /></t-button><t-button v-if="editing" variant="text" :disabled="!canEdit||saving||!dirty" @click="resetFields">重置</t-button></div></div>
        <p v-if="editing" class="metadata-hint">保存将使用当前全部字段替换该文件的元数据。未改动的字段会保留，已删除的字段将被移除。</p>
        <t-textarea v-if="view==='json'" :model-value="draftText" :readonly="!editing||!canEdit||saving" :autosize="{minRows:12,maxRows:24}" aria-label="JSON 元数据" @change="updateJson" />
        <t-table v-else-if="fields.length||editing" empty="草稿中没有字段。保存后将清空这份文件的元数据。" row-key="id" :data="fields" :columns="editing?[{colKey:'key',title:'键',width:170},{colKey:'type',title:'数据类型',width:150},{colKey:'value',title:'值'},{colKey:'actions',title:'操作',width:60}]:[{colKey:'key',title:'键',width:190},{colKey:'value',title:'值'}]">
          <template #key="{row}"><t-input v-if="editing" v-model="row.key" :disabled="!canEdit||saving" :maxlength="64" aria-label="键" @change="syncFields" /><span v-else>{{row.key}}</span></template>
          <template #type="{row}"><t-select v-model="row.type" :disabled="!canEdit||saving" :options="types" aria-label="数据类型" @change="syncFields" /></template>
          <template #value="{row}"><template v-if="editing"><t-select v-if="row.type==='boolean'" v-model="row.value" :disabled="!canEdit||saving" :options="[{label:'true',value:'true'},{label:'false',value:'false'}]" aria-label="值" @change="syncFields" /><t-input v-else v-model="row.value" :disabled="!canEdit||saving" aria-label="值" @change="syncFields" /></template><span v-else class="metadata-value">{{row.value}}</span></template>
          <template #actions="{rowIndex}"><t-button theme="danger" variant="text" shape="square" aria-label="删除字段" :disabled="!canEdit||saving" @click="removeField(rowIndex)"><t-icon name="delete" /></t-button></template>
        </t-table>
        <p v-else class="metadata-empty">尚未设置元数据。可添加字段，为文件分类和筛选。</p>
        <div class="metadata-tools"><span v-if="!editing">共 {{fields.length}} 个字段</span><t-space v-if="editing"><t-button variant="outline" :disabled="!canEdit||saving||fields.length>=32" @click="addField">新增字段</t-button><t-button variant="text" :disabled="!canEdit||saving||!fields.length" @click="clearFields">清空全部字段</t-button></t-space></div>
        <p v-if="editing" class="metadata-hint metadata-limits">最多 32 个字段；键名最多 64 个字符，单值最多 4096 个字符，数组最多 100 项。支持字符串、数字、布尔值及其数组。</p>
        <t-alert v-if="editing&&validationError" theme="error" :message="validationError" /><t-alert v-if="error" theme="error" :message="error" />
      </section>
    </div>
    <template #footer><div class="metadata-footer"><template v-if="editing"><span class="metadata-change-count">新增 {{changes.added}}　修改 {{changes.modified}}　删除 {{changes.deleted}}</span><t-button variant="outline" :disabled="saving" @click="cancelEditing">取消</t-button><t-button :loading="saving" :disabled="!canEdit||!dirty||!!validationError" @click="save">保存全部修改</t-button></template><template v-else><t-button v-if="canEdit" :disabled="saving" @click="startEditing">编辑元数据</t-button><t-button variant="outline" :disabled="saving" @click="close">关闭</t-button></template></div></template>
  </t-drawer>
</template>

<style scoped lang="less">
.file-details{font-family:var(--app-font-family);font-size:var(--app-text-base)}.details-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 32px;margin:0 0 28px}.details-grid>div{display:flex;flex-direction:column;gap:8px;min-width:0}.details-grid dt{color:var(--td-text-color-placeholder);line-height:20px}.details-grid dd{margin:0;color:var(--td-text-color-primary);line-height:20px;overflow-wrap:anywhere}.metadata-section{border-top:1px solid var(--td-component-stroke);padding-top:20px}.metadata-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.metadata-heading h3{font-size:var(--app-text-xl);line-height:24px;font-weight:600;margin:0}.metadata-views{display:flex;gap:4px}.metadata-views .selected{color:var(--app-selection-text);background:var(--app-selection-bg);border-color:var(--app-selection-border)}.metadata-hint{margin:0 0 16px;font-size:var(--app-text-md);line-height:20px;color:var(--td-text-color-secondary)}.metadata-limits{margin-top:12px}.metadata-empty{font-size:var(--app-text-md);padding:24px 16px;margin:0;border:1px dashed var(--td-component-stroke);border-radius:var(--app-radius-md);color:var(--td-text-color-placeholder);line-height:20px}.metadata-value{white-space:pre-wrap;overflow-wrap:anywhere}.metadata-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:16px;color:var(--td-text-color-secondary);font-size:var(--app-text-sm)}.metadata-tools :deep(.t-button){font-size:var(--app-text-base)}.metadata-section :deep(.t-table){border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-md);overflow:hidden}.metadata-section :deep(.t-table th){font-size:var(--app-text-base);font-weight:400;background:var(--td-bg-color-secondarycontainer)}.metadata-section :deep(.t-table td){font-size:var(--app-text-base);vertical-align:top}.metadata-section :deep(.t-alert){margin-top:16px}.metadata-section :deep(.t-input),.metadata-section :deep(.t-textarea__inner){font-size:var(--app-text-base)}.metadata-section :deep(textarea){font-family:var(--app-font-family-mono);line-height:1.7}.metadata-footer{display:flex;align-items:center;justify-content:flex-end;gap:8px}.metadata-footer :deep(.t-button){font-size:var(--app-text-base)}.metadata-change-count{margin-right:auto;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}
@media(max-width:600px){.details-grid{grid-template-columns:1fr}.metadata-tools{align-items:flex-start;flex-direction:column}.metadata-footer{flex-wrap:wrap}}
</style>
