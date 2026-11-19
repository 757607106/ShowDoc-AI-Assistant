<script setup lang="ts">
import KnowledgeOverlay from './components/KnowledgeOverlay.vue'
import { computed, onUnmounted, ref, watch } from 'vue'
import { nativeAPI } from '@/api/contextdb'
import { useAuthStore } from '@/stores/auth'
import { graphDocumentLabel } from '@/utils/contextdbDocumentName'
import KnowledgeActionMenu from './components/KnowledgeActionMenu.vue'

const props = defineProps<{ kbId: string; active: boolean; documents: any[]; canEdit?: boolean; attach?: () => HTMLElement }>()
const emit = defineEmits<{
  (e: 'inspect', id: string, relation: boolean): void
  (e: 'expand', entity: any): void
  (e: 'changed', change: { kind: 'entity' | 'relation'; id: string; deleted: boolean }): void
}>()
const auth = useAuthStore()
const items = ref<any[]>([]), total = ref(0), page = ref(1), keyword = ref(''), mode = ref('fuzzy')
const loading = ref(false), error = ref(''), editorOpen = ref(false), editorLoading = ref(false), saving = ref(false), editError = ref('')
const kind = ref<'entity' | 'relation'>('entity'), editingId = ref(''), detailReady = ref(false)
const form = ref({ entity_name: '', entity_type: '', description: '', aliases: [] as string[], source_entity_id: '', target_entity_id: '', relation_type: '', keywords: [] as string[], weight: 1 })
const choices = ref<any[]>([]), selectedEndpoints = ref<any[]>([]), endpointLoading = ref(false), endpointError = ref('')
const deleting = ref<any>(null), deleteError = ref(''), removing = ref(false)
const writeInProgress = computed(() => saving.value || removing.value)
const editable = computed(() => props.canEdit ?? auth.hasRole('contributor'))
const rowActions = computed(() => [
  { content: '查看子图', value: 'expand' },
  ...(editable.value ? [{ content: '编辑', value: 'edit' }, { content: '删除', value: 'delete', theme: 'error' }] : []),
])
let listRequest = 0, editRequest = 0, endpointRequest = 0, deleteRequest = 0
const label = (name: string) => graphDocumentLabel(name || '', props.documents)
const endpointOptions = computed(() => [...new Map([...choices.value, ...selectedEndpoints.value].map(item => [item.entity_id, item])).values()]
  .map(item => ({ value: item.entity_id, label: label(item.entity_name) })))
const searchHint = computed(() => mode.value === 'semantic' ? '按语义查找；总数为本次候选集数量。'
  : mode.value === 'exact' ? '按实体名称精确匹配，区分大小写。' : '支持名称、ID、类型、别名的前缀匹配，以及描述分词匹配。')

async function load() {
  if (!props.active) return
  const request = ++listRequest, kb = props.kbId
  loading.value = true; error.value = ''
  try {
    const result = await nativeAPI.get('knowledge/entities', { kb_id: kb, keyword: keyword.value.trim() || undefined, mode: mode.value, page: page.value, page_size: 20 })
    if (request !== listRequest || kb !== props.kbId || !props.active) return
    items.value = result.data.entities || []; total.value = result.data.total ?? items.value.length
  } catch (e: any) { if (request === listRequest) error.value = e.message || '实体列表读取失败' }
  finally { if (request === listRequest) loading.value = false }
}
function query() { page.value = 1; void load() }
function closeEditor() {
  if (saving.value) return
  editRequest++; endpointRequest++; editorOpen.value = false; editorLoading.value = false; endpointLoading.value = false
}
async function searchEndpoints(keyword = '') {
  const request = ++endpointRequest, kb = props.kbId
  endpointLoading.value = true; endpointError.value = ''
  try {
    const result = await nativeAPI.get('knowledge/entities', { kb_id: kb, keyword: keyword.trim() || undefined, mode: 'fuzzy', page: 1, page_size: 100 })
    if (request === endpointRequest && kb === props.kbId && editorOpen.value) choices.value = result.data.entities || []
  } catch (e: any) { if (request === endpointRequest) endpointError.value = e.message || '实体搜索失败' }
  finally { if (request === endpointRequest) endpointLoading.value = false }
}
function retainEndpoint(id: any) {
  const item = choices.value.find(item => item.entity_id === id)
  if (item) selectedEndpoints.value = [...selectedEndpoints.value.filter(item => item.entity_id !== id), item]
}
async function edit(resource: 'entity' | 'relation', item?: any, sourceEntity?: any) {
  if (!(props.canEdit ?? auth.hasRole('contributor')) || saving.value) return
  const request = ++editRequest, kb = props.kbId
  endpointRequest++; kind.value = resource; editingId.value = item?.[`${resource}_id`] || ''
  form.value = { entity_name: '', entity_type: '', description: '', aliases: [], source_entity_id: sourceEntity?.entity_id || '', target_entity_id: '', relation_type: '', keywords: [], weight: 1 }
  editorOpen.value = true; editError.value = ''; endpointError.value = ''; choices.value = []
  selectedEndpoints.value = sourceEntity ? [sourceEntity] : []; editorLoading.value = !!editingId.value; detailReady.value = !editingId.value
  if (resource === 'relation' && !editingId.value) void searchEndpoints()
  if (!editingId.value) return
  try {
    const result = await nativeAPI.get(resource === 'entity' ? 'knowledge/entities/detail' : 'knowledge/entity-relations/detail',
      { knowledge_base_id: kb, [`${resource}_id`]: editingId.value })
    if (request !== editRequest || kb !== props.kbId || !editorOpen.value) return
    const detail = result.data
    if (detail?.[`${resource}_id`] !== editingId.value) throw new Error('未读取到目标完整信息，请重新打开编辑')
    detailReady.value = true
    form.value = { ...form.value, ...detail, aliases: [...(detail.aliases || [])], keywords: [...(detail.keywords || [])] }
    if (resource === 'relation') selectedEndpoints.value = [
      { entity_id: detail.source_entity_id, entity_name: detail.source_entity_name || detail.source_entity_id },
      { entity_id: detail.target_entity_id, entity_name: detail.target_entity_name || detail.target_entity_id },
    ]
  } catch (e: any) { if (request === editRequest) editError.value = e.message || '读取完整信息失败，请重新打开编辑' }
  finally { if (request === editRequest) editorLoading.value = false }
}
const editEntity = (entity?: any) => edit('entity', entity)
const editRelation = (relation?: any, sourceEntity?: any) => edit('relation', relation, sourceEntity)
function fields() {
  const value = form.value
  if (value.description.length > 8192) throw new Error('描述最多 8192 字符')
  if (kind.value === 'entity') {
    if (!value.entity_name.trim() || !value.entity_type.trim()) throw new Error('请填写实体名称和实体类型')
    if (value.entity_name.trim().length > 100 || value.entity_type.trim().length > 128) throw new Error('实体名称最多 100 字符，类型最多 128 字符')
    const aliases = [...new Set(value.aliases.map(item => item.trim()).filter(Boolean))]
    if (aliases.length > 20 || aliases.some(item => item.length > 128)) throw new Error('别名最多 20 个，每个最多 128 字符')
    return { entity_name: value.entity_name.trim(), entity_type: value.entity_type.trim(), description: value.description, aliases }
  }
  if (!value.relation_type.trim()) throw new Error('请填写关系类型')
  if (value.relation_type.trim().length > 128) throw new Error('关系类型最多 128 字符')
  const keywords = [...new Set(value.keywords.map(item => item.trim()).filter(Boolean))]
  if (keywords.length > 50 || keywords.some(item => item.length > 128)) throw new Error('关键词最多 50 个，每个最多 128 字符')
  if (!editingId.value && (!value.source_entity_id || !value.target_entity_id)) throw new Error('请选择起点实体和终点实体')
  if (typeof value.weight !== 'number' || !Number.isFinite(value.weight) || value.weight < 0 || value.weight > 1) throw new Error('关系权重必须在 0 到 1 之间')
  return { ...(!editingId.value ? { source_entity_id: value.source_entity_id, target_entity_id: value.target_entity_id } : {}),
    relation_type: value.relation_type.trim(), description: value.description, keywords, weight: value.weight }
}
async function save() {
  if (!(props.canEdit ?? auth.hasRole('contributor')) || !editorOpen.value || saving.value || editorLoading.value || !detailReady.value) return
  const request = editRequest, kb = props.kbId, resource = kind.value, id = editingId.value
  editError.value = ''
  try {
    const payload = { knowledge_base_id: kb, ...(id ? { [`${resource}_id`]: id } : {}), ...fields() }
    saving.value = true
    const path = resource === 'entity' ? 'knowledge/entities' : 'knowledge/entity-relations'
    const result = await (id ? nativeAPI.put(path, payload) : nativeAPI.post(path, payload))
    if (request !== editRequest || kb !== props.kbId) return
    const savedId = result.data?.[`${resource}_id`]
    if (!savedId || (id && savedId !== id) || result.data?.knowledge_base_id !== kb) throw new Error('未收到有效保存结果，请刷新核对后重试')
    editorOpen.value = false; endpointRequest++
    emit('changed', { kind: resource, id: savedId, deleted: false }); await load()
  } catch (e: any) { if (request === editRequest) editError.value = e.message || '保存失败' }
  finally { if (request === editRequest) saving.value = false }
}
function askDelete(resource: 'entity' | 'relation', item: any) {
  if (!(props.canEdit ?? auth.hasRole('contributor')) || removing.value || !item?.[`${resource}_id`]) return
  deleteRequest++; deleteError.value = ''; deleting.value = { kind: resource, id: item[`${resource}_id`], name: resource === 'entity' ? label(item.entity_name) : item.relation_type }
}
const deleteEntity = (entity: any) => askDelete('entity', entity)
const deleteRelation = (relation: any) => askDelete('relation', relation)
function selectRowAction(row: any, value: string) {
  if (value === 'expand') emit('expand', row)
  else if (value === 'edit') void editEntity(row)
  else if (value === 'delete') deleteEntity(row)
}
async function remove() {
  if (!(props.canEdit ?? auth.hasRole('contributor')) || !deleting.value || removing.value) return
  const request = deleteRequest, kb = props.kbId, target = deleting.value
  removing.value = true; deleteError.value = ''
  try {
    const path = target.kind === 'entity' ? 'knowledge/entities' : 'knowledge/entity-relations'
    const params = new URLSearchParams({ knowledge_base_id: kb, [`${target.kind}_id`]: target.id })
    const result = await nativeAPI.del(`${path}?${params}`)
    if (request !== deleteRequest || kb !== props.kbId) return
    if (result.data?.deleted !== true || result.data?.[`${target.kind}_id`] !== target.id || result.data?.knowledge_base_id !== kb) throw new Error('未确认删除成功，请刷新核对')
    deleting.value = null
    if (items.value.length === 1 && page.value > 1) page.value--
    emit('changed', { kind: target.kind, id: target.id, deleted: true }); await load()
  } catch (e: any) { if (request === deleteRequest) deleteError.value = e.message || '删除失败' }
  finally { if (request === deleteRequest) removing.value = false }
}
watch(() => props.kbId, () => {
  listRequest++; editRequest++; endpointRequest++; deleteRequest++
  items.value = []; total.value = 0; page.value = 1; keyword.value = ''; mode.value = 'fuzzy'; error.value = ''
  editorOpen.value = false; editorLoading.value = false; saving.value = false; deleting.value = null; removing.value = false
})
watch(() => [props.kbId, props.active], () => { if (props.active) void load(); else { listRequest++; loading.value = false } }, { immediate: true })
onUnmounted(() => { listRequest++; editRequest++; endpointRequest++; deleteRequest++ })
defineExpose({ editEntity, editRelation, deleteEntity, deleteRelation, load, writeInProgress })
</script>

<template>
  <section v-if="active" class="graph-management" aria-label="实体管理">
    <div class="management-search">
      <t-input v-model="keyword" clearable placeholder="搜索实体名称、ID、类型或别名" aria-label="搜索管理实体" @enter="query" />
      <label class="matching-mode"><span>匹配方式</span><t-select :popup-props="{ attach: attach || 'body' }" v-model="mode" :options="[{value:'fuzzy',label:'模糊匹配'},{value:'exact',label:'精确匹配'},{value:'semantic',label:'语义匹配'}]" @change="query" /></label>
      <t-button :loading="loading" @click="query">查询</t-button>
      <t-button v-if="(props.canEdit ?? auth.hasRole('contributor'))" variant="outline" @click="editEntity()">新建实体</t-button>
    </div>
    <p class="management-hint">{{ searchHint }}</p>
    <t-alert v-if="error" theme="error" :message="error"><template #operation><t-button variant="text" @click="load">重试</t-button></template></t-alert>
    <t-table row-key="entity_id" :data="items" :loading="loading" :columns="[{colKey:'entity_name',title:'实体'},{colKey:'operations',title:'操作',width:88}]">
      <template #entity_name="{row}">
        <button type="button" class="entity-name" @click="emit('inspect',row.entity_id,false)">{{ label(row.entity_name) }}</button>
        <t-tag size="small" variant="light">{{ row.entity_type || '未分类' }}</t-tag>
        <p v-if="row.description" class="entity-description">{{ row.description }}</p>
      </template>
      <template #operations="{row}"><KnowledgeActionMenu :label="'实体更多操作 '+label(row.entity_name)" :options="rowActions" @select="selectRowAction(row,$event)" /></template>
      <template #empty><span>{{ keyword.trim() ? '未找到符合条件的实体' : '暂无实体' }}</span></template>
    </t-table>
    <p v-if="!loading && !error" class="management-hint" role="status">共 {{ total }} 个实体</p>
    <t-pagination v-if="total > 20" :total="total" :current="page" :page-size="20" :total-content="false" :show-page-size="false" @current-change="(value:number)=>{page=value;load()}" />
  </section>
  <KnowledgeOverlay :attach="attach || 'body'" :visible="editorOpen" :header="`${editingId ? '编辑' : '新建'}${kind === 'entity' ? '实体' : '关系'}`" width="600px" :close-on-overlay-click="!saving" :close-on-esc-keydown="!saving" :close-btn="!saving" :cancel-btn="{disabled:saving}" :confirm-btn="{content:'保存',loading:saving,disabled:editorLoading || !detailReady}" @close="closeEditor" @confirm="save">
    <t-loading v-if="editorLoading" text="正在读取完整信息" />
    <t-form v-else label-align="top" :disabled="saving">
      <p class="management-hint">人工维护的{{ kind === 'entity' ? '名称、类型、描述和别名' : '关系类型、描述、关键词和权重' }}会在后续图谱自动构建后保留。</p>
      <template v-if="kind === 'entity'">
        <t-form-item label="实体名称" required><t-input v-model="form.entity_name" :maxlength="100" aria-label="实体名称" /></t-form-item>
        <t-form-item label="实体类型" required><t-input v-model="form.entity_type" :maxlength="128" aria-label="实体类型" /></t-form-item>
        <t-form-item label="别名" help="输入后按回车添加，最多 20 个；可留空。"><t-tag-input v-model="form.aliases" :max="20" aria-label="别名" placeholder="输入别名后按回车" /></t-form-item>
      </template>
      <template v-else>
        <t-form-item label="起点实体" required><t-select :popup-props="{ attach: attach || 'body' }" v-model="form.source_entity_id" :disabled="!!editingId" filterable :filter="() => true" :loading="endpointLoading" :options="endpointOptions" aria-label="起点实体" placeholder="搜索实体名称、ID、类型或别名" @search="searchEndpoints" @change="retainEndpoint" /></t-form-item>
        <t-form-item label="终点实体" required><t-select :popup-props="{ attach: attach || 'body' }" v-model="form.target_entity_id" :disabled="!!editingId" filterable :filter="() => true" :loading="endpointLoading" :options="endpointOptions" aria-label="终点实体" placeholder="搜索实体名称、ID、类型或别名" @search="searchEndpoints" @change="retainEndpoint" /></t-form-item>
        <t-alert v-if="endpointError" theme="warning" :message="endpointError"><template #operation><t-button variant="text" @click="searchEndpoints()">重试搜索</t-button></template></t-alert>
        <t-form-item label="关系类型" required><t-input v-model="form.relation_type" :maxlength="128" aria-label="关系类型" /></t-form-item>
        <t-form-item label="权重" required><t-input-number v-model="form.weight" :min="0" :max="1" :step="0.1" aria-label="权重" /></t-form-item>
        <t-form-item label="关键词" help="输入后按回车添加，最多 50 个；可留空。"><t-tag-input v-model="form.keywords" :max="50" aria-label="关键词" placeholder="输入关键词后按回车" /></t-form-item>
      </template>
      <t-form-item label="描述"><t-textarea v-model="form.description" :maxlength="8192" :autosize="{minRows:4,maxRows:8}" aria-label="描述" /></t-form-item>
    </t-form>
    <t-alert v-if="editError" role="alert" theme="error" :message="editError" />
  </KnowledgeOverlay>
  <KnowledgeOverlay :attach="attach || 'body'" :visible="!!deleting" header="确认删除" :close-on-overlay-click="!removing" :close-on-esc-keydown="!removing" :close-btn="!removing" :cancel-btn="{disabled:removing}" :confirm-btn="{content:'删除',theme:'danger',loading:removing}" @close="!removing && (deleting=null)" @confirm="remove">
    <p>删除“{{ deleting?.name }}”？{{ deleting?.kind === 'entity' ? '该实体及其所有入向、出向关系将被删除，无法恢复。' : '该关系将被删除，起点和终点实体保留，无法恢复。' }}</p>
    <t-alert v-if="deleteError" role="alert" theme="error" :message="deleteError" />
  </KnowledgeOverlay>
</template>

<style scoped lang="less">
.graph-management { flex: 1; min-width: 0; overflow: auto; padding: 20px; background: var(--td-bg-color-container); }
.management-search { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
.management-search :deep(.t-input__wrap) { flex: 1; min-width: 160px; max-width: 440px; }
.management-search :deep(.t-select__wrap) { width: 140px; flex: none; }
.management-hint { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); line-height: 1.6; margin: 12px 0 16px; }
.graph-management :deep(.t-pagination) { margin-top: 20px; }
 .matching-mode { display: grid; gap: 4px; font-size: var(--app-text-sm); }
.entity-name { border: 0; padding: 0; margin: 0 8px 4px 0; color: var(--td-brand-color); background: transparent; font: inherit; text-align: start; overflow-wrap: anywhere; cursor: pointer; }
.entity-name:hover { text-decoration: underline; }
.entity-description { margin: 4px 0 0; color: var(--td-text-color-secondary); overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
@media (max-width: 700px) { .graph-management { padding: 12px; } .management-search :deep(.t-input__wrap) { flex-basis: 100%; } }
</style>
