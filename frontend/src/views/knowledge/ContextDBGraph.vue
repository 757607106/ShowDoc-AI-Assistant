<script setup lang="ts">
import { ref, computed, nextTick, useId, watch, onMounted, onUnmounted } from 'vue'
import { nativeAPI } from '@/api/contextdb'
import { useAuthStore } from '@/stores/auth'
import ContextDBGraphCanvas from './ContextDBGraphCanvas.vue'
import { graphTypeColor as typeColor } from './contextdbGraphPresentation'
import { documentDisplayName, graphDocumentLabel } from '@/utils/contextdbDocumentName'
import ContextDBGraphManagement from './ContextDBGraphManagement.vue'
import DocMarkdown from '@/components/DocMarkdown.vue'
import { chunkAttachments } from '@/utils/contextdbResources'
import { dateTime } from '@/utils/platformPresentation'
import { navigateKnowledgeTabs } from './components/knowledgeTabNavigation'

const props = defineProps<{ kbId: string; canEdit?: boolean }>()
const emit = defineEmits<{ (e: 'open-source-doc', id: string): void }>()
const auth = useAuthStore()
const modeId = useId()
const graph = ref<any>(null), root = ref(''), hops = ref(2), documentId = ref('')
const view = ref('graph'), settingsOpen = ref(false), maxNodes = ref(100), maxEdges = ref(200)
const appliedHops = ref(2)
const settingsError = ref(''), locatedId = ref(''), graphScale = ref(1)
const manager = ref<InstanceType<typeof ContextDBGraphManagement> | null>(null)
const writeInProgress = computed(() => !!manager.value?.writeInProgress)
const inspectorClose = ref<HTMLButtonElement | null>(null)
let detailTrigger: HTMLElement | null = null
defineExpose({ writeInProgress })
const container = ref<HTMLElement | null>(null), fullscreen = ref(false)
const dialogAttach = () => container.value || document.body
const relations = ref<any[]>([]), relationTotal = ref(0), relationPage = ref(1), relationType = ref('')
const relationLoading = ref(false), relationError = ref('')
const error = ref(''), busy = ref(false), entities = ref<any[]>([]), entityLoading = ref(false), entityError = ref('')
const documents = ref<any[]>([]), documentPage = ref(0), documentTotal = ref(0), documentLoading = ref(false), documentError = ref('')
const detail = ref<any>(null), detailOpen = ref(false), detailLoading = ref(false), detailError = ref(''), selectedId = ref(''), isRelation = ref(false)
const sources = ref<any[]>([]), sourceLoading = ref(false), sourceError = ref(''), sourceResult = ref<any>(null)
const graphCanvas = ref<InstanceType<typeof ContextDBGraphCanvas> | null>(null)
let entityRequest = 0, graphRequest = 0, detailRequest = 0, documentRequest = 0, sourceRequest = 0, relationRequest = 0
async function searchEntities(keyword = '') {
  const request = ++entityRequest, kb = props.kbId
  entityLoading.value = true; entityError.value = ''; entities.value = []
  try {
    const result = await nativeAPI.get('knowledge/entities', { kb_id: kb,
      keyword: keyword.trim() || undefined, mode: 'fuzzy', page: 1, page_size: 100 })
    if (request === entityRequest && kb === props.kbId) { entities.value = result.data.entities || []; resolveDocumentNames() }
  } catch (e: any) { if (request === entityRequest) entityError.value = e.message }
  finally { if (request === entityRequest) entityLoading.value = false }
}
async function loadDocuments(append = false) {
  const request = ++documentRequest, kb = props.kbId, page = append ? documentPage.value + 1 : 1
  documentLoading.value = true; documentError.value = ''
  try {
    const pages = append ? [page] : Array.from({ length: Math.max(1, documentPage.value) }, (_, index) => index + 1)
    const results = await Promise.all(pages.map(page => nativeAPI.get('knowledge/documents', { knowledge_base_id: kb, page, page_size: 100 })))
    if (request !== documentRequest || kb !== props.kbId) return
    const items = results.flatMap(result => result.data.documents || [])
    documents.value = append ? [...documents.value, ...items] : items
    documentPage.value = pages[pages.length - 1]!; documentTotal.value = results[0]!.data.total ?? documents.value.length
  } catch (e: any) { if (request === documentRequest) documentError.value = e.message }
  finally { if (request === documentRequest) { documentLoading.value = false; resolveDocumentNames() } }
}
function resolveDocumentNames() {
  if (documentLoading.value || documentError.value || !documentPage.value || documentPage.value * 100 >= documentTotal.value) return
  const names = new Set(documents.value.map(item => item.name))
  if (view.value === 'entities' || [...(graph.value?.nodes || []).map((node: any) => node.label), ...entities.value.map(item => item.entity_name), ...sources.value.map(item => item.document_name)].some(name => /^doc-[a-f\d]{64}\./i.test(name || '') && !names.has(name))) void loadDocuments(true)
}
function closeDetail() {
  detailRequest++; sourceRequest++; relationRequest++; detailOpen.value = false; detail.value = null; sources.value = []
  selectedId.value = ''; locatedId.value = ''; relations.value = []; relationError.value = ''; relationLoading.value = false
  detailLoading.value = false; sourceLoading.value = false; detailError.value = ''; sourceError.value = ''; sourceResult.value = null
}
function dismissDetail() {
  closeDetail()
  const trigger = detailTrigger?.isConnected && detailTrigger.tagName !== 'BODY'
    ? detailTrigger : container.value?.querySelector<HTMLElement>('.graph-canvas [role="application"], .graph-canvas[role="application"]')
  detailTrigger = null
  trigger?.focus({ preventScroll: true })
}
function selectGraphView(value: 'graph' | 'entities') {
  if (view.value === value || writeInProgress.value) return
  closeDetail()
  view.value = value
}
async function load() {
  const request = ++graphRequest, kb = props.kbId, requestedHops = hops.value
  busy.value = true; error.value = ''; graph.value = null; closeDetail()
  try {
    const result = await nativeAPI.get('knowledge/graph-visual', { knowledge_base_id: kb,
      document_id: root.value ? undefined : documentId.value || undefined, entity_id: root.value || undefined,
      max_hops: requestedHops, max_nodes: maxNodes.value, max_edges: maxEdges.value })
    if (request !== graphRequest || kb !== props.kbId) return
    graph.value = result.data; appliedHops.value = requestedHops; resolveDocumentNames()
  } catch (e: any) { if (request === graphRequest) error.value = e.message }
  finally { if (request === graphRequest) busy.value = false }
}
function changeDocument() { root.value = ''; void searchEntities(); void load() }
function displayName(label: string) { return graphDocumentLabel(label || '', documents.value) }
const nodes = computed(() => (graph.value?.nodes || []).map((node: any) => ({ ...node, label: displayName(node.label) })))
const edges = computed(() => {
  const ids = new Set(nodes.value.map((node: any) => node.id))
  return (graph.value?.edges || []).filter((edge: any) => ids.has(edge.from) && ids.has(edge.to))
})
const types = computed<string[]>(() => [...new Set<string>(nodes.value.map((node: any) => node.group || ''))])
function fit() { graphCanvas.value?.fit() }
function zoom(factor: number) { graphCanvas.value?.zoom(factor) }
const scopeLabel = computed(() => {
  const document = documents.value.find(item => item.id === documentId.value)
  const entity = entities.value.find(item => item.entity_id === root.value)
  if (root.value) return `知识库内 · 以“${displayName(entity?.entity_name || root.value)}”为中心展开 ${appliedHops.value} 跳（不受文件范围限制）`
  return documentId.value ? `文档：${document ? documentDisplayName(document) : documentId.value}` : '当前知识库图谱'
})
const graphNotice = computed(() => {
  if (!graph.value) return ''
  if (documentId.value && !root.value && !graph.value.truncated) return '当前展示该文档的抽取结果，可能与全库合并后的实体数量不同。'
  return graph.value.note || (graph.value.truncated ? '当前范围仅返回部分图谱，请选择实体或来源文档缩小范围。' : '')
})
function applySettings() {
  settingsError.value = ''
  if (![1, 2].includes(hops.value) || !Number.isInteger(maxNodes.value) || maxNodes.value < 1 || maxNodes.value > 8000 || !Number.isInteger(maxEdges.value) || maxEdges.value < 1 || maxEdges.value > 20000) {
    settingsError.value = '请输入有效的展示上限'; return
  }
  void load()
}
function locate(id: string) {
  if (!id) { closeDetail(); return }
  const node = nodes.value.find((node: any) => node.id === id)
  if (!node) return
  graphCanvas.value?.focus(id)
  void inspect(id)
}
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement === container.value) await document.exitFullscreen()
    else await container.value?.requestFullscreen()
  } catch { error.value = '浏览器未能进入全屏，请重试。' }
}
function fullscreenChanged() { fullscreen.value = document.fullscreenElement === container.value }
async function loadDetail() {
  const request = ++detailRequest, kb = props.kbId, id = selectedId.value, relation = isRelation.value
  detailLoading.value = true; detailError.value = ''
  try {
    const result = await nativeAPI.get(relation ? 'knowledge/entity-relations/detail' : 'knowledge/entities/detail',
      { knowledge_base_id: kb, [relation ? 'relation_id' : 'entity_id']: id })
    if (request === detailRequest && kb === props.kbId && detailOpen.value) detail.value = result.data
  } catch (e: any) { if (request === detailRequest) detailError.value = e.message }
  finally { if (request === detailRequest) detailLoading.value = false }
}
async function loadSources() {
  const request = ++sourceRequest, kb = props.kbId, id = selectedId.value
  sourceLoading.value = true; sourceError.value = ''
  try {
    const result = await nativeAPI.get('knowledge/entities/chunks', { knowledge_base_id: kb, entity_ids: id, limit: 20 })
    if (request !== sourceRequest || kb !== props.kbId || !detailOpen.value) return
    sourceResult.value = result.data; sources.value = result.data.chunks || []; resolveDocumentNames()
  } catch (e: any) { if (request === sourceRequest) sourceError.value = e.message }
  finally { if (request === sourceRequest) sourceLoading.value = false }
}
async function loadRelations(page = 1) {
  const request = ++relationRequest, kb = props.kbId, id = selectedId.value
  relationLoading.value = true; relationError.value = ''
  relations.value = []
  try {
    const result = await nativeAPI.get('knowledge/entity-relations', { kb_id: kb, entity_id: id, relation_type: relationType.value.trim() || undefined, page, page_size: 10 })
    if (request !== relationRequest || kb !== props.kbId || id !== selectedId.value || !detailOpen.value) return
    relations.value = result.data.relations || []
    relationTotal.value = result.data.total ?? relations.value.length; relationPage.value = page
  } catch (e: any) { if (request === relationRequest) relationError.value = e.message }
  finally { if (request === relationRequest) relationLoading.value = false }
}
function changeRelationPage(page: number) { void loadRelations(page) }
async function inspect(id: string, relation = false) {
  if (!detailOpen.value) detailTrigger = document.activeElement as HTMLElement | null
  closeDetail(); selectedId.value = id; isRelation.value = relation; detailOpen.value = true
  if (!relation) locatedId.value = nodes.value.some((node: any) => node.id === id) ? id : ''
  relationType.value = ''; relationTotal.value = 0
  void nextTick(() => inspectorClose.value?.focus({ preventScroll: true }))
  await Promise.all([loadDetail(), ...(!relation ? [loadSources(), loadRelations()] : [])])
}
function expandEntity(entity = detail.value) {
  if (!entity?.entity_id) return
  if (!entities.value.some(item => item.entity_id === entity.entity_id)) entities.value.push(entity)
  root.value = entity.entity_id; view.value = 'graph'; void load()
}
async function changed(change: { kind: string; id: string; deleted: boolean }) {
  if (change.deleted && change.kind === 'entity' && change.id === root.value) root.value = ''
  await Promise.all([load(), searchEntities()])
}
watch(view, () => { if (view.value === 'entities') resolveDocumentNames() })
watch(() => props.kbId, () => {
  root.value = ''; documentId.value = ''; hops.value = 2; documents.value = []; documentPage.value = 0; documentTotal.value = 0
  void load(); void searchEntities(); void loadDocuments()
}, { immediate: true })
onMounted(() => { document.addEventListener('fullscreenchange', fullscreenChanged) })
onUnmounted(() => { entityRequest++; graphRequest++; documentRequest++; closeDetail(); document.removeEventListener('fullscreenchange', fullscreenChanged) })
</script>

<template>
  <div ref="container" class="native-graph" :class="{ 'is-fullscreen': fullscreen }">
    <div class="graph-tabs" role="tablist" aria-label="图谱视图" @keydown="navigateKnowledgeTabs">
      <button :id="modeId+'-graph'" type="button" role="tab" :aria-selected="view === 'graph'" :tabindex="view === 'graph'?0:-1" :aria-controls="modeId" @click="selectGraphView('graph')">查看图谱</button>
      <button :id="modeId+'-entities'" type="button" role="tab" :aria-selected="view === 'entities'" :tabindex="view === 'entities'?0:-1" :aria-controls="modeId" @click="selectGraphView('entities')">实体管理</button>
    </div>
    <div v-show="view === 'graph'" class="graph-toolbar">
      <div class="graph-search-row">
        <label class="graph-field"><span>以实体展开</span><t-select v-model="root" :filter="() => true" filterable clearable placeholder="搜索实体名称、ID、类型或别名" aria-label="以实体展开" :popup-props="{ attach: dialogAttach }" :loading="entityLoading" :options="entities.map(item => ({ value: item.entity_id, label: displayName(item.entity_name) }))" @search="searchEntities" @change="load" /></label>
        <label class="graph-field"><span>文件范围</span><t-select v-model="documentId" filterable clearable placeholder="全部文件" aria-label="文件范围" :disabled="!!root" :popup-props="{ attach: dialogAttach }" :loading="documentLoading" :options="documents.map(item => ({ value: item.id, label: documentDisplayName(item) }))" @change="changeDocument"><template #panelBottomContent><t-button v-if="documents.length < documentTotal" variant="text" block :loading="documentLoading" @click.stop="loadDocuments(true)">加载更多文档（{{ documents.length }} / {{ documentTotal }}）</t-button></template></t-select></label>
        <t-button variant="outline" :aria-expanded="settingsOpen" @click="settingsOpen = !settingsOpen"><t-icon name="setting" />展示设置</t-button>
        <t-button variant="outline" aria-label="刷新图谱" :loading="busy" @click="load"><t-icon name="refresh" />刷新</t-button>
      </div>
      <div v-if="settingsOpen" class="graph-settings">
        <label><span>展开层数</span><t-radio-group v-model="hops" aria-label="展开层数"><t-radio-button :value="1">1 跳</t-radio-button><t-radio-button :value="2">2 跳</t-radio-button></t-radio-group></label>
        <label><span>实体上限</span><t-input-number v-model="maxNodes" :min="1" :max="8000" :decimal-places="0" :input-props="{ 'aria-label': '实体上限' }" /></label>
        <label><span>关系上限</span><t-input-number v-model="maxEdges" :min="1" :max="20000" :decimal-places="0" :input-props="{ 'aria-label': '关系上限' }" /></label>
        <t-button @click="applySettings">应用</t-button><span v-if="settingsError" role="alert">{{ settingsError }}</span>
      </div>
      <div class="graph-summary" role="status"><span>{{ scopeLabel }}</span><t-button v-if="root" variant="text" size="small" @click="root = ''; load()">清除实体展开</t-button><span v-if="graph" class="graph-count">已展示 <strong>{{ nodes.length }}</strong> 个实体 / <strong>{{ edges.length }}</strong> 条关系<span class="graph-total">当前查询范围共 {{ graph.entity_total ?? '—' }} 个实体 / {{ graph.relation_total ?? '—' }} 条关系</span></span></div>
      <t-alert v-if="error" theme="error" :message="error"><template #operation><t-button variant="text" @click="load">重试</t-button></template></t-alert>
      <t-alert v-if="entityError" theme="warning" :message="`实体搜索失败：${entityError}`"><template #operation><t-button variant="text" @click="searchEntities()">重试</t-button></template></t-alert>
      <t-alert v-if="documentError" theme="warning" :message="`文档列表读取失败：${documentError}`"><template #operation><t-button variant="text" @click="loadDocuments()">重试</t-button></template></t-alert>
      <p v-if="graphNotice" class="graph-notice"><t-icon name="info-circle" />{{ graph?.truncated ? '已达到展示上限，可缩小查询范围或调整展示上限。' : graphNotice }}</p>
    </div>
    <div :id="modeId" class="graph-workspace" :class="{ 'graph-workspace-view': view === 'graph' }" role="tabpanel" :aria-labelledby="modeId+'-'+view" :aria-busy="view==='graph'&&busy">
      <div v-show="view === 'graph'" class="graph-stage">
        <div class="graph-canvas-tools">
          <t-select v-model="locatedId" filterable clearable placeholder="定位当前画布中的实体" aria-label="定位当前画布中的实体" :popup-props="{ attach: dialogAttach }" :options="nodes.map((node: any) => ({ value: node.id, label: node.label }))" @change="(id: any) => locate(String(id || ''))" />
          <t-button variant="outline" @click="fit"><t-icon name="focus" />适应画布</t-button>
          <t-button variant="outline" @click="toggleFullscreen"><t-icon :name="fullscreen ? 'fullscreen-exit' : 'fullscreen'" />{{ fullscreen ? '退出全屏' : '全屏' }}</t-button>
        </div>
        <ContextDBGraphCanvas ref="graphCanvas" class="graph-canvas" :nodes="nodes" :edges="edges" :root-id="root" :selected-id="selectedId" :is-relation="isRelation" @select="inspect" @zoom="graphScale = $event" />
        <div v-if="busy" class="graph-overlay"><t-loading text="正在读取图谱…" role="status" /></div>
        <t-empty v-else-if="!nodes.length && !error" class="graph-overlay" description="当前范围暂无实体与关系" />
        <div class="graph-zoom"><span>{{ Math.round(graphScale * 100) }}%</span><t-button variant="text" aria-label="缩小图谱" @click="zoom(1 / 1.25)"><t-icon name="zoom-out" /></t-button><t-button variant="text" aria-label="放大图谱" @click="zoom(1.25)"><t-icon name="zoom-in" /></t-button></div>
        <div class="graph-footer"><div class="graph-types"><span v-for="type in types" :key="type"><i :style="{ background: typeColor(type) }" />{{ type || '未分类' }}</span></div><p>拖动画布移动，滚轮缩放；拖动节点调整位置，点击实体或关系查看详情。也可通过实体定位框选择节点。</p></div>
      </div>
      <ContextDBGraphManagement ref="manager" :attach="dialogAttach" :kb-id="kbId" :active="view === 'entities'" :can-edit="props.canEdit" :documents="documents" @inspect="inspect" @expand="expandEntity" @changed="changed" />
      <aside v-if="detailOpen" class="graph-inspector" :aria-label="isRelation ? '关系详情' : '实体详情'"
        @keydown.esc.stop.prevent="dismissDetail">
        <div class="inspector-heading"><div><span class="inspector-kicker">{{ isRelation ? '关系详情' : '实体详情' }}</span><h3>{{ isRelation ? detail?.relation_type || edges.find((edge: any) => edge.id === selectedId)?.label || '加载中' : selectedId ? displayName(detail?.entity_name || nodes.find((node: any) => node.id === selectedId)?.label || '加载中') : '实体详情' }}</h3><t-tag v-if="!isRelation && detail?.entity_type" variant="light">{{ detail.entity_type }}</t-tag></div><button ref="inspectorClose" type="button" class="inspector-close" aria-label="关闭详情" @click="dismissDetail"><t-icon name="close" /></button></div>
        <div class="inspector-body">
          <t-loading v-if="detailLoading" text="正在读取详情…" role="status" />
          <t-alert v-if="detailError" theme="error" :message="detailError"><template #operation><t-button variant="text" @click="loadDetail">重试详情</t-button></template></t-alert>
          <template v-if="detail">
            <template v-if="isRelation"><dl class="relation-endpoints"><dt>起点实体</dt><dd><button type="button" class="graph-text-action" @click="inspect(detail.source_entity_id)">{{ displayName(detail.source_entity_name || detail.source_entity_id) }}</button></dd><dt>终点实体</dt><dd><button type="button" class="graph-text-action" @click="inspect(detail.target_entity_id)">{{ displayName(detail.target_entity_name || detail.target_entity_id) }}</button></dd><dt>权重</dt><dd>{{ detail.weight ?? '—' }}</dd><dt>关键词</dt><dd>{{ detail.keywords?.join('、') || '—' }}</dd></dl></template>
            <div v-else-if="detail.aliases?.length" class="detail-aliases"><span>别名</span><t-tag v-for="alias in detail.aliases" :key="alias" variant="light">{{ displayName(alias) }}</t-tag></div>
            <h4>描述</h4><DocMarkdown :content="detail.description || '暂无描述'" /><p class="graph-scope">更新时间：{{ dateTime(detail.updated_at) }}</p>
            <div class="detail-actions"><t-button v-if="!isRelation" @click="expandEntity()">查看子图</t-button><template v-if="(props.canEdit ?? auth.hasRole('contributor'))"><t-button variant="outline" @click="isRelation ? manager?.editRelation(detail) : manager?.editEntity(detail)">编辑</t-button><t-button variant="outline" theme="danger" @click="isRelation ? manager?.deleteRelation(detail) : manager?.deleteEntity(detail)">删除</t-button></template></div>
          </template>
          <template v-if="!isRelation">
            <section class="detail-section"><div class="section-heading"><h4>关联关系 <span>{{ relationTotal }}</span></h4><t-button v-if="(props.canEdit ?? auth.hasRole('contributor')) && detail" variant="text" size="small" @click="manager?.editRelation(undefined, detail)">新建关系</t-button></div>
              <div class="relation-search"><t-input v-model="relationType" placeholder="按关系类型精确查询" aria-label="按关系类型精确查询" clearable @enter="loadRelations()" /><t-button variant="outline" @click="loadRelations()">查询</t-button></div>
              <t-alert v-if="relationError" theme="error" :message="relationError"><template #operation><t-button variant="text" @click="loadRelations()">重试</t-button></template></t-alert>
              <ul class="relation-list"><li v-for="relation in relations" :key="relation.relation_id"><div><t-tag size="small" variant="light">{{ relation.source_entity_id === selectedId ? '出向' : '入向' }}</t-tag><button type="button" class="graph-text-action" @click="inspect(relation.relation_id, true)">{{ relation.relation_type }}</button><button type="button" class="graph-text-action" @click="inspect(relation.source_entity_id === selectedId ? relation.target_entity_id : relation.source_entity_id)">{{ displayName(relation.source_entity_id === selectedId ? relation.target_entity_name || relation.target_entity_id : relation.source_entity_name || relation.source_entity_id) }}</button></div><p>{{ relation.description }}</p></li></ul>
              <t-loading v-if="relationLoading" text="正在读取关联关系" /><t-empty v-else-if="!relations.length && !relationError" description="暂无关联关系" />
              <t-pagination v-if="relationTotal > 10" size="small" :current="relationPage" :total="relationTotal" :page-size="10" :show-page-size="false" :show-page-number="false" @current-change="changeRelationPage" />
            </section>
            <section class="detail-section"><h4>来源片段</h4><t-loading v-if="sourceLoading" text="正在读取来源片段" />
              <p v-if="documentId" class="graph-scope">来源片段可能包含该实体在其他文档中的出处。</p>
              <t-alert v-if="sourceError" theme="warning" :message="sourceError"><template #operation><t-button variant="text" @click="loadSources">重试来源</t-button></template></t-alert>
              <p v-if="sourceResult" class="graph-scope">本次返回 {{ sources.length }} 个片段<span v-if="sourceResult.truncated">；仅显示部分候选来源，可打开来源文档核对</span>。</p>
              <t-empty v-if="!sourceLoading && !sourceError && !sources.length" description="当前实体没有可读取的来源片段" />
              <div v-for="item in sources" :key="item.chunk_id" class="graph-source"><button type="button" class="graph-text-action" v-if="item.document_id" @click="emit('open-source-doc', item.document_id)">{{ displayName(item.document_name) || '来源文档' }}</button><p v-if="item.toc_path" class="graph-scope">{{ displayName(item.toc_path) }}</p><DocMarkdown :content="item.content || ''" :source-name="item.document_name" :source-display-name="displayName(item.document_name)" :attachments="chunkAttachments([item], item.document_id)" :kb-id="kbId" /></div>
            </section>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped lang="less">
.native-graph { display: flex; flex-direction: column; flex: 1; width: 100%; height: 100%; min-height: 0; overflow: auto; color: var(--td-text-color-primary); background: var(--td-bg-color-container); container-type: inline-size; }
.native-graph:fullscreen { padding: 24px; box-sizing: border-box; }
.native-graph:fullscreen .graph-workspace-view { flex: 1; min-height: 440px; height: auto; }
.graph-tabs { display: flex; gap: 24px; padding: 0; border-bottom: 1px solid var(--td-component-stroke); }
.graph-tabs button { padding: 10px 2px; font: inherit; color: var(--td-text-color-secondary); background: none; border: 0; border-bottom: 2px solid transparent; cursor: pointer; }
.graph-tabs button[aria-selected='true'] { color: var(--td-brand-color); border-bottom-color: var(--td-brand-color); font-weight: 600; }
.graph-toolbar { padding: 16px; display: flex; flex-direction: column; gap: 8px; margin: 16px 0; border-radius:var(--app-radius-lg); background: var(--td-bg-color-secondarycontainer); }
.graph-search-row { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 10px; }
.graph-field { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 200px; font-size: var(--app-text-sm); color: var(--td-text-color-secondary); }
.graph-field :deep(.t-select__wrap) { width: 100%; }
.graph-settings { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; padding: 12px; background: var(--td-bg-color-secondarycontainer); border-radius: var(--app-radius-sm); }
.graph-settings label { display: flex; align-items: center; gap: 10px; font-size: var(--app-text-sm); }
.graph-settings :deep(.t-input-number) { width: 126px; }
.graph-summary { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: var(--app-text-sm); color: var(--td-text-color-secondary); }
.graph-count { margin-left: auto; }.graph-count strong { color: var(--td-text-color-primary); }.graph-total { margin-left: 16px; color: var(--td-text-color-placeholder); }
.graph-notice { margin: 0; display: flex; gap: 6px; align-items: center; color: var(--td-warning-color); font-size: var(--app-text-sm); }
.graph-scope { margin: 12px 0; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); line-height: 1.6; overflow-wrap: anywhere; }
.graph-workspace { display: flex; flex: 1; min-height: 0; overflow: hidden; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); }
.graph-workspace-view { flex: none; height: clamp(540px, 68vh, 760px); }
.graph-stage { flex: 1; min-width: 0; min-height: 0; position: relative; display: flex; flex-direction: column; background: var(--td-bg-color-sidebar); }
.graph-canvas-tools { flex: none; padding: 12px 16px; display: flex; gap: 8px; align-items: center; background: var(--td-bg-color-container); border-bottom: 1px solid var(--td-component-stroke); }
.graph-canvas-tools :deep(.t-select__wrap) { width: min(280px, 45%); }
.graph-canvas { flex: 1; min-height: 240px; width: 100%; }
.graph-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none; }
.graph-zoom { position: absolute; bottom: 72px; right: 12px; display: flex; align-items: center; padding-left: 10px; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-sm); background: var(--td-bg-color-container); font-size: var(--app-text-sm); color: var(--td-text-color-secondary); }
.graph-footer { flex: none; padding: 10px 16px; border-top: 1px solid var(--td-component-stroke); background: var(--td-bg-color-container); }
.graph-footer p { margin: 8px 0 0; font-size: var(--app-text-xs); color: var(--td-text-color-placeholder); }
.graph-types { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: var(--app-text-xs); color: var(--td-text-color-secondary); }
.graph-types span { display: inline-flex; align-items: center; gap: 5px; }.graph-types i { width: 8px; height: 8px; border-radius: 50%; }
.graph-inspector { width: 32%; flex: 0 0 32%; min-width: 300px; min-height: 0; display: flex; flex-direction: column; border-left: 1px solid var(--td-component-stroke); background: var(--td-bg-color-container); }
.inspector-heading { padding: 18px 16px; display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; border-bottom: 1px solid var(--td-component-stroke); }
.inspector-close { display: inline-grid; place-items: center; flex: none; width: 36px; height: 36px; border: 0; border-radius: var(--app-radius-sm); background: transparent; color: var(--td-text-color-primary); cursor: pointer; }
.inspector-close:hover { background: var(--td-bg-color-container-hover); }
.graph-text-action { border: 0; padding: 0; font: inherit; color: var(--td-brand-color); background: transparent; text-align: start; overflow-wrap: anywhere; cursor: pointer; }
.graph-text-action:hover { text-decoration: underline; }
.inspector-body :deep(.doc-markdown-toggle) { display: none; }
.inspector-heading h3 { margin: 4px 0 10px; font-size: var(--app-text-xl); font-weight: 600; line-height: 1.5; overflow-wrap: anywhere; }.inspector-kicker { font-size: var(--app-text-xs); color: var(--td-text-color-placeholder); }
.inspector-body { overflow: auto; min-height: 0; padding: 16px; font-size: var(--app-text-base); line-height: 1.65; }.inspector-body h4 { margin: 0 0 12px; font-size: var(--app-text-base); font-weight: 600; }
.detail-aliases { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }.detail-aliases > span:first-child { color: var(--td-text-color-secondary); }
.detail-actions { display: flex; gap: 8px; margin: 18px 0; }.detail-section { border-top: 1px solid var(--td-component-stroke); padding-top: 20px; margin-top: 20px; }
.section-heading { display: flex; justify-content: space-between; align-items: baseline; }.section-heading h4 span { color: var(--td-text-color-placeholder); font-weight: 400; margin-left: 4px; }
.relation-search { display: flex; gap: 8px; }.relation-list { list-style: none; padding: 0; margin: 8px 0; }.relation-list li { padding: 12px 0; border-bottom: 1px solid var(--td-component-stroke); }.relation-list li > div { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }.relation-list p { margin: 6px 0 0; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.relation-endpoints { display: grid; grid-template-columns: 64px 1fr; gap: 10px; margin: 0 0 20px; }.relation-endpoints dt { color: var(--td-text-color-secondary); }.relation-endpoints dd { margin: 0; overflow-wrap: anywhere; }
.graph-source { margin-top: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--td-component-stroke); }
@media (max-width: 900px) { .graph-total { display: none; }.graph-canvas-tools { flex-wrap: wrap; }.graph-canvas-tools :deep(.t-select__wrap) { flex: 1; min-width: 140px; } }
@media (max-width: 640px) { .graph-toolbar { padding: 10px; }.graph-field { flex-basis: 100%; }.graph-count { margin-left: 0; }.graph-footer p { display: none; } }
@container (max-width: 760px) {
  .graph-inspector {
    position: fixed;
    inset: auto 0 0;
    z-index: 100;
    width: auto;
    min-width: 0;
    max-height: min(55dvh, 440px);
    padding-bottom: env(safe-area-inset-bottom);
    border: 1px solid var(--td-component-stroke);
    border-radius: var(--app-radius-lg) var(--app-radius-lg) 0 0;
    box-shadow: var(--td-shadow-2);
  }
  .inspector-heading { flex: none; padding: 12px 16px; }
  .inspector-body { overscroll-behavior: contain; }
  .detail-actions { flex-wrap: wrap; }
}
</style>
