<!--
  知识库视图(WeKnora 排版移植):检索+知识评审(ContextDB 原生)+入库文档编辑+图谱+评审设置
-->
<script setup lang="ts">
import ContextDBTemplates from './knowledge/ContextDBTemplates.vue'
import ContextDBGraph from './knowledge/ContextDBGraph.vue'
import {useRoute, useRouter} from 'vue-router'
import {nativeAPI} from '@/api/contextdb'
import {useAuthStore} from '@/stores/auth'
import { onMounted, ref, computed, watch } from 'vue'
import api from '@/api/backend'
import DocMarkdown from '@/components/DocMarkdown.vue'
import KnowledgeChunksList from '@/components/KnowledgeChunksList.vue'
import StructuredFields from '@/components/StructuredFields.vue'
import { stateLabel as stageLabel, dateTime, reviewActionLabels } from '@/utils/platformPresentation'
import { splitKnowledgeResults } from '@/utils/contextdbSearchResults'
import { reviewEditableContent } from '@/utils/reviewContent'
import { CONTEXTDB_REVIEW_FORMAT_NOTICE, supportsOfficialReview } from '@/utils/contextdbReviewSupport'
import GraphQueryResults from './chat/components/tool-results/GraphQueryResults.vue'

const REVIEW_STATES = [
  { value: 'pending_human', label: '待人工评审' },
  { value: 'auto_accepted', label: '自动通过' },
  { value: 'approved', label: '人工通过' },
  { value: 'rejected', label: '已拒绝' },
  { value: 'failed', label: '评审失败' },
]
const BATCH_REVIEW_ACTIONS = ['confirm', 'force_accept', 'accept_rewrite', 'reject', 'retract', 'retry_review']
const CONFLICT_OPTIONS = [
  { value: 'use_new', label: '采用新文档' },
  { value: 'keep_old', label: '保留旧知识' },
  { value: 'merge', label: '合并' },
  { value: 'annotate_divergence', label: '标注分歧' },
]
const stateLabel = (value: string) => stageLabel(value,'review')

const router=useRouter()
const route=useRoute()
const auth=useAuthStore()
const extraError=ref('')
async function extra(fn:()=>Promise<void>){extraError.value='';try{await fn()}catch(e:any){extraError.value=e.message}}
const bases = ref<any[]>([])
const activeBaseId = ref('')
const question = ref('')
const searching = ref(false)
const chunks = ref<any[]>([])
const graphChunks = ref<any[]>([])
const wikiItems = ref<any[]>([])
const reviews = ref<any[]>([])
const selectedReviewIds = ref<string[]>([]), reviewsKbId = ref(''), reviewLoading = ref(false), reviewBatchActing = ref(false)
const reviewBatchResults = ref<any[]>([]), reviewBatchError = ref('')
let reviewListRequest = 0, reviewBatchRequest = 0
const reviewPage=ref(1), reviewTotal=ref(0), docPage=ref(1), docTotal=ref(0)
const reviewState = ref('pending_human')
const reviewDrawer = ref(false)
const reviewRow = ref<any>(null)
const reviewDetail = ref<any>(null)
const contentPage = ref(1)
const editing = ref(false)
const editedContent = ref('')
const resolutions = ref<Record<string, string>>({})
const reviewActing = ref(false)
const reviewError = ref('')
const reviewNotice = ref(''), conflictNotice = ref('')
const reviewDocument = ref<any>(null), reviewStatusError = ref(''), reviewStatusLoading = ref(false)
let reviewStatusRequest = 0, reviewRequest = 0
const kbDocuments = ref<any[]>([])
const docDialog = ref(false)
const docRow = ref<any>(null)
const docText = ref('')
const docLoading = ref(false)
const docError = ref('')
const docReady = ref(false), docKbId = ref('')
let docRequest = 0
const tab = ref(typeof route.query.tab === 'string' && ['reviews', 'search', 'graph', 'documents', 'templates', 'settings'].includes(route.query.tab) ? route.query.tab : 'reviews')
const graphNodes = ref<any[]>([])
const graphEdges = ref<any[]>([])
const graphLoading = ref(false)
const reviewSettings = ref<any>(null)
const reviewSettingsKbId = ref(''), reviewSettingsSaving = ref(false)
let reviewSettingsRequest = 0

const wikiBases = computed(() => bases.value.filter((b:any)=>b.name!=='_governance'))
const reviewBase = computed(() => bases.value.find(base => base.id === reviewDetail.value?.knowledge_base_id))

async function loadBases() {
  const data = await api.kbBases()
  bases.value = data.bases || []
  if (wikiBases.value.length) activeBaseId.value = wikiBases.value.find(base => base.id === route.query.kb_id)?.id || wikiBases.value[0].id
}

watch(activeBaseId, () => {reviewPage.value=1;docPage.value=1;void extra(async()=>{await Promise.all([loadReviews(),loadKbDocuments(),loadSettings()])})})
watch(reviewState, () => {reviewPage.value=1;void extra(loadReviews)})
watch([activeBaseId, reviewState, reviewPage], () => {
  reviewBatchRequest++
  selectedReviewIds.value = []; reviewBatchResults.value = []; reviewBatchError.value = ''
}, { flush: 'sync' })

async function search() {
  if (!question.value.trim() || !activeBaseId.value) return
  searching.value = true
  try {
    const data = await api.kbSearch(question.value, [activeBaseId.value], {
      view: 'auto', top_k: 10, query_rewrite: true,
    })
    const result=splitKnowledgeResults(data.chunks||[])
    chunks.value=result.documents;graphChunks.value=result.graph
    wikiItems.value = data.wiki_items || []
  } finally {
    searching.value = false
  }
}

async function loadReviews() {
  const request = ++reviewListRequest, kbId = activeBaseId.value, state = reviewState.value, page = reviewPage.value
  reviews.value = []; reviewTotal.value = 0; reviewsKbId.value = ''; selectedReviewIds.value = []
  reviewLoading.value = !!kbId
  if (!kbId) return
  try {
    const data = await api.kbReviews(kbId, { lifecycle_state: state, page })
    if (request !== reviewListRequest || activeBaseId.value !== kbId || reviewState.value !== state || reviewPage.value !== page) return
    reviews.value = data.reviews || []
    reviewTotal.value=data.total??reviews.value.length
    reviewsKbId.value = kbId
  } finally {
    if (request === reviewListRequest) reviewLoading.value = false
  }
}

function canReviewAction(row: any, action: string) {
  if (!auth.hasRole('contributor') || row?.can_approve_review === false) return false
  if (action === 'retract') return ['approved', 'auto_accepted'].includes(row?.lifecycle_state)
  if (action === 'retry_review') return row?.lifecycle_state === 'failed'
  return ['confirm', 'force_accept', 'accept_rewrite', 'reject', 'reject_reupload'].includes(action) && row?.lifecycle_state === 'pending_human'
}

function canBatchReview(action: string) {
  const rows = reviews.value.filter(row => selectedReviewIds.value.includes(row.review_id))
  return reviewsKbId.value === activeBaseId.value && !reviewBatchActing.value && !reviewLoading.value && rows.length > 0 && rows.length <= 50 &&
    rows.length === selectedReviewIds.value.length && rows.every(row => canReviewAction(row, action))
}

async function actReviews(action: string) {
  if (!canBatchReview(action)) return
  const ids = [...selectedReviewIds.value], rows = [...reviews.value]
  if (action === 'reject' && !window.confirm(`拒绝会删除本页选中的 ${ids.length} 份文档及其切片，确认继续？`)) return
  if (action === 'retract' && !window.confirm(`撤回本页选中的 ${ids.length} 份文档后，内容将退出检索并回到待人工评审，确认继续？`)) return
  const request = ++reviewBatchRequest
  reviewBatchActing.value = true; reviewBatchError.value = ''; reviewBatchResults.value = []; selectedReviewIds.value = []
  try {
    let results: any[] = []
    try {
      const result = await api.kbReviewBatch(ids, action)
      results = result.results || []
    } catch (error: any) {
      if (request === reviewBatchRequest) reviewBatchError.value = `批量请求结果待确认：${error.message}。请核对下方官方状态后再决定是否重试。`
    }
    const statuses = await Promise.allSettled(ids.map(id => api.kbReviewDetail(id)))
    if (request !== reviewBatchRequest) return
    reviewBatchResults.value = ids.map((id, index) => {
      const result = results.find(item => item.id === id), status = statuses[index]
      return { id, document_name: rows.find(row => row.review_id === id)?.document_name || id,
        success: result?.success, error: result?.error,
        lifecycle_state: status.status === 'fulfilled' ? status.value.review?.lifecycle_state : null,
        status_error: status.status === 'rejected' ? status.reason?.message || String(status.reason) : '',
      }
    })
    const refreshed = await Promise.allSettled([loadReviews(), loadKbDocuments()])
    const failed = refreshed.find(result => result.status === 'rejected')
    if (failed?.status === 'rejected' && request === reviewBatchRequest) reviewBatchError.value = `列表刷新失败：${failed.reason?.message || failed.reason}`
  } finally {
    reviewBatchActing.value = false
  }
}

function parseJson(value: any) {
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

const qualityDetails = computed(() => parseJson(reviewDetail.value?.quality_details) || {})
const conflicts = computed<any[]>(() => {
  const parsed = parseJson(reviewDetail.value?.conflicts)
  return Array.isArray(parsed) ? parsed : (parsed?.conflicts || [])
})
const contradictions = computed<any[]>(() => {
  const parsed = parseJson(reviewDetail.value?.contradictions)
  return Array.isArray(parsed) ? parsed : []
})
const activeState = computed(() => reviewDetail.value?.lifecycle_state || reviewRow.value?.lifecycle_state)

function conflictId(conflict: any) {
  return conflict.conflict_id || conflict.id
}

async function loadReviewPage(page: number) {
  if (reviewActing.value) return false
  const id = reviewRow.value.review_id
  const request = ++reviewRequest
  try {
    const data = await api.kbReviewDetail(id, page)
    if (request !== reviewRequest || reviewRow.value?.review_id !== id || !reviewDrawer.value) return false
    reviewDetail.value = data.review
    contentPage.value = page
    return true
  } catch (error: any) {
    if (request === reviewRequest) reviewError.value = error.message
    return false
  }
}

watch(reviewDrawer, visible => {
  if (visible) return
  reviewRequest++; reviewStatusRequest++
  reviewDetail.value = null; reviewDocument.value = null
  editing.value = false; editedContent.value = ''; resolutions.value = {}
  reviewActing.value = false; reviewStatusLoading.value = false
}, { flush: 'sync' })

async function openReview(row: any) {
  reviewRequest++; reviewStatusRequest++
  reviewActing.value = false
  reviewRow.value = row
  reviewDetail.value = null
  reviewError.value = ''
  reviewNotice.value = ''; conflictNotice.value = ''; reviewDocument.value = null; reviewStatusError.value = ''; reviewStatusLoading.value = false
  editedContent.value = ''
  editing.value = false
  reviewDrawer.value = true
  if (!await loadReviewPage(1)) return
  const saved = parseJson(reviewDetail.value?.human_conflict_resolutions) || []
  resolutions.value = Object.fromEntries((Array.isArray(saved) ? saved : []).map((item: any) => [item.conflict_id, item.resolution]))
  await refreshReviewStatus()
}

async function startEditing() {
  if (reviewActing.value || !canReviewAction(reviewDetail.value, 'confirm')) return
  const detail = reviewDetail.value
  const request = ++reviewRequest
  reviewError.value = ''; reviewActing.value = true
  try {
    const text = await reviewEditableContent(detail, api.kbReviewDetail)
    if (request !== reviewRequest || !reviewDrawer.value || reviewDetail.value?.review_id !== detail.review_id) return
    editedContent.value = text
    editing.value = true
  } catch (error: any) {
    if (request === reviewRequest) reviewError.value = error.message
  } finally {
    if (request === reviewRequest) reviewActing.value = false
  }
}

function selectedResolutions() {
  return Object.entries(resolutions.value)
    .filter(([, resolution]) => resolution)
    .map(([conflict_id, resolution]) => ({ conflict_id, resolution }))
}

async function saveConflictDraft() {
  if (reviewActing.value || !canReviewAction(reviewDetail.value, 'confirm')) return
  const items = selectedResolutions()
  if (!items.length) return
  const id = reviewRow.value.review_id
  const request = ++reviewRequest
  reviewActing.value = true; reviewError.value = ''; conflictNotice.value = ''
  try {
    await api.kbReviewConflicts(id, items)
    if (request === reviewRequest) conflictNotice.value = '处置草稿已保存；仍需提交评审决定，文档才会继续处理。'
  } catch (error: any) { if (request === reviewRequest) reviewError.value = error.message }
  finally { if (request === reviewRequest) reviewActing.value = false }
}

async function refreshReviewStatus() {
  const review = reviewDetail.value
  if (!review?.document_id || !review.knowledge_base_id) return
  const request = ++reviewStatusRequest, version = reviewRequest
  reviewStatusLoading.value = true; reviewStatusError.value = ''
  try {
    const result = await nativeAPI.get('knowledge/documents/detail', {
      knowledge_base_id: review.knowledge_base_id, document_id: review.document_id,
    })
    if (request !== reviewStatusRequest || version !== reviewRequest || !reviewDrawer.value || reviewDetail.value?.review_id !== review.review_id) return
    if (result.data?.id !== review.document_id || result.data?.knowledge_base_id !== review.knowledge_base_id) throw new Error('官方文档归属与当前评审不一致，请重新读取')
    reviewDocument.value = result.data
  } catch (error: any) {
    if (request === reviewStatusRequest && version === reviewRequest) reviewStatusError.value = error.message
  } finally {
    if (request === reviewStatusRequest) reviewStatusLoading.value = false
  }
}

function openReviewWiki() {
  const kbId = reviewDetail.value?.knowledge_base_id
  if (kbId && reviewBase.value?.wiki_enabled) void router.push({ path: `/platform/knowledge-bases/${kbId}`, query: { tab: 'wiki' } })
}

async function actReview(action: string) {
  if (reviewActing.value || !canReviewAction(reviewDetail.value, action)) return
  const id = reviewRow.value.review_id
  reviewError.value = ''
  if (['reject', 'reject_reupload'].includes(action) && !window.confirm('拒绝会删除该文档及其切片,确认继续?')) return
  const options: any = {}
  if (['confirm', 'force_accept', 'accept_rewrite'].includes(action)) {
    const items = selectedResolutions()
    if (items.length) options.conflictResolutions = items
  }
  if (action === 'accept_rewrite' && editing.value) {
    if (!editedContent.value.trim()) {
      reviewError.value = '编辑稿不能为空'
      return
    }
    options.editedContent = editedContent.value
  }
  const request = ++reviewRequest
  reviewStatusRequest++; reviewStatusLoading.value = false
  reviewActing.value = true
  try {
    const result = await api.kbReviewAction(id, action, options)
    if (request !== reviewRequest || reviewRow.value?.review_id !== id || !reviewDrawer.value) return
    reviewDetail.value = { ...reviewDetail.value, ...result.review }
    editing.value = false
    conflictNotice.value = ''
    reviewDocument.value = null
    const deleting = ['reject', 'reject_reupload'].includes(action)
    reviewNotice.value = deleting ? '拒绝决定已受理，官方将异步删除该文档及相关资源；这不代表资料处理失败。' : '评审决定已受理，仍需核对文档入库状态；处理结果不会回写采集原件或外部来源。'
    if (!deleting) await refreshReviewStatus()
    const refreshes = await Promise.allSettled([loadReviews(), loadKbDocuments()])
    const failed = refreshes.find(result => result.status === 'rejected')
    if (failed?.status === 'rejected' && request === reviewRequest) reviewStatusError.value = `列表刷新失败：${failed.reason?.message || failed.reason}`
  } catch (error: any) {
    if (request === reviewRequest) reviewError.value = error.message
  } finally {
    if (request === reviewRequest) reviewActing.value = false
  }
}

async function loadKbDocuments() {
  if (!activeBaseId.value) return
  const data = await api.kbDocuments(activeBaseId.value,{page:docPage.value})
  kbDocuments.value = data.documents || []
  docTotal.value=data.total??kbDocuments.value.length
}

function canEditDocument(row: any) {
  if (['text', 'memory_promotion'].includes(row.source_type)) return true
  const mime = String(row.mime_type || '').split(';')[0].trim().toLowerCase()
  return row.source_type === 'file' && /\.(md|txt|html|json)$/i.test(row.name) &&
    (!mime || mime === 'application/octet-stream' || mime.startsWith('text/') || mime === 'application/json' || mime === 'application/xhtml+xml')
}

function resetDocumentEditor() {
  docRequest++
  docRow.value = null; docKbId.value = ''; docText.value = ''
  docReady.value = false; docLoading.value = false; docError.value = ''
}

watch(docDialog, visible => { if (!visible) resetDocumentEditor() }, { flush: 'sync' })
watch(activeBaseId, () => { docDialog.value = false; reviewDrawer.value = false }, { flush: 'sync' })

function currentDocumentEditor(request: number, kbId: string, documentId: string) {
  return request === docRequest && docDialog.value && activeBaseId.value === kbId &&
    docKbId.value === kbId && docRow.value?.id === documentId
}

async function openDocumentEditor(row: any) {
  const request = ++docRequest, kbId = activeBaseId.value, documentId = row.id
  docError.value = ''
  docRow.value = { ...row }
  docKbId.value = kbId
  docText.value = ''
  docReady.value = false
  docDialog.value = true
  docLoading.value = true
  try {
    const result = await api.kbDocumentText(kbId, documentId)
    if (!currentDocumentEditor(request, kbId, documentId)) return
    if (typeof result.text !== 'string') throw new Error('未读取到完整正文，请重新打开文档')
    docText.value = result.text
    docReady.value = true
  } catch (error: any) {
    if (currentDocumentEditor(request, kbId, documentId)) docError.value = error.message
  } finally {
    if (currentDocumentEditor(request, kbId, documentId)) docLoading.value = false
  }
}

async function saveDocument() {
  if (docLoading.value) return
  const kbId = docKbId.value, documentId = docRow.value?.id
  if (!docReady.value || !currentDocumentEditor(docRequest, kbId, documentId)) {
    docError.value = '请先完整读取当前知识库的目标文档'
    return
  }
  if (!docText.value.trim()) {
    docError.value = '正文不能为空'
    return
  }
  const request = ++docRequest, text = docText.value
  docLoading.value = true
  try {
    await api.kbDocumentUpdate(documentId, text, kbId)
    if (!currentDocumentEditor(request, kbId, documentId)) return
    docDialog.value = false
    await Promise.all([loadKbDocuments(), loadReviews()])
  } catch (error: any) {
    if (currentDocumentEditor(request, kbId, documentId)) docError.value = error.message
  } finally {
    if (currentDocumentEditor(request, kbId, documentId)) docLoading.value = false
  }
}

async function loadGraph() {
  if (!activeBaseId.value) return
  graphLoading.value = true
  try {
    const data = await api.kbGraph(activeBaseId.value, { max_nodes: 500, max_edges: 2000 })
    graphNodes.value = data.nodes || data.entities || []
    graphEdges.value = data.relations || data.edges || []
  } catch {
    graphNodes.value = []
    graphEdges.value = []
  } finally {
    graphLoading.value = false
  }
}

async function loadSettings() {
  const kbId = activeBaseId.value, request = ++reviewSettingsRequest
  reviewSettings.value = null; reviewSettingsKbId.value = ''
  if (!kbId) return
  try {
    const rs = await api.kbReviewSettings(kbId)
    if (request !== reviewSettingsRequest || activeBaseId.value !== kbId) return
    reviewSettings.value = rs.settings || rs
    reviewSettingsKbId.value = kbId
  } catch {
    if (request === reviewSettingsRequest && activeBaseId.value === kbId) reviewSettings.value = null
  }
}

async function saveReviewSettings() {
  const kbId = reviewSettingsKbId.value
  if (reviewSettingsSaving.value || !kbId || kbId !== activeBaseId.value || !reviewSettings.value) return
  reviewSettingsRequest++; reviewSettingsSaving.value = true
  try {
    await api.kbReviewSettingsUpdate(kbId, {
      review_enabled: reviewSettings.value.review_enabled,
      high_threshold: reviewSettings.value.high_threshold,
      rewrite_enabled: reviewSettings.value.rewrite_enabled,
      conflict_detection_enabled: reviewSettings.value.conflict_detection_enabled,
      rewrite_auto_ingest_enabled: reviewSettings.value.rewrite_auto_ingest_enabled,
      max_rewrite_iterations: reviewSettings.value.max_rewrite_iterations,
    })
    if (activeBaseId.value === kbId) await loadSettings()
  } finally { reviewSettingsSaving.value = false }
}

function activateSettingsSwitch(event: KeyboardEvent) {
  if (![' ', 'Enter'].includes(event.key)) return
  event.preventDefault()
  const target = event.currentTarget as HTMLElement
  target.click()
}

onMounted(()=>extra(loadBases))
</script>

<template>
  <div class="knowledge-layout">
    <t-card title="知识评审" :bordered="false">
      <t-radio-group v-model="activeBaseId" variant="default-filled">
        <t-radio-button v-for="base in wikiBases" :key="base.id" :value="base.id">
          {{ base.name }}
        </t-radio-button>
      </t-radio-group>
    </t-card>

    <t-alert v-if="extraError" theme="error" :message="extraError"/>
    <t-tabs v-model="tab" class="knowledge-tabs">
      <!-- 检索 -->
      <t-tab-panel value="search" label="检索">
        <div class="search-bar">
          <t-input v-model="question" placeholder="输入问题或关键词" clearable @enter="extra(search)" />
          <t-button theme="primary" :loading="searching" aria-label="检索知识" @click="extra(search)">
            <template #icon><t-icon name="search" /></template>
          </t-button>
        </div>
        <KnowledgeChunksList :chunks="wikiItems.map((item: any) => ({ ...item, content: item.content, doc_name: item.title, similarity: item.score }))" title="Wiki 章节" />
        <KnowledgeChunksList :chunks="chunks" title="知识片段" />
        <GraphQueryResults v-if="graphChunks.length" :context-chunks="graphChunks">
          <template #sources="{chunk}"><t-space break-line v-for="entity in chunk.graph?.entities || []" :key="entity.entity_id"><t-link v-for="(id,index) in entity.source_document_ids || []" :key="String(id)" @click="router.push({path:`/platform/knowledge-bases/${entity.kb_id || chunk.kb_id || activeBaseId}`,query:{document_id:String(id)}})">来源文档 {{Number(index)+1}}</t-link></t-space></template>
        </GraphQueryResults>
        <t-empty v-if="!chunks.length && !wikiItems.length && !graphChunks.length && !searching" description="暂无检索结果" />
      </t-tab-panel>

      <!-- 知识图谱 -->
      <t-tab-panel value="graph" label="知识图谱"><ContextDBGraph v-if="bases.find(b=>b.id===activeBaseId)?.graph_enabled" :kb-id="activeBaseId" @open-source-doc="id=>router.push({path:`/platform/knowledge-bases/${activeBaseId}`,query:{document_id:id}})"/><t-empty v-else description="请选择图谱知识库"/></t-tab-panel>

      <!-- 知识评审(ContextDB 原生) -->
      <t-tab-panel value="reviews" label="知识评审">
        <t-alert theme="info" :message="CONTEXTDB_REVIEW_FORMAT_NOTICE" />
        <div class="review-toolbar">
          <t-radio-group v-model="reviewState" variant="default-filled" size="small">
            <t-radio-button v-for="item in REVIEW_STATES" :key="item.value" :value="item.value">{{ item.label }}</t-radio-button>
          </t-radio-group>
          <t-button size="small" variant="outline" @click="extra(loadReviews)">刷新</t-button>
        </div>
        <div v-if="auth.hasRole('contributor')" class="review-batch-toolbar">
          <p class="hint-text">仅操作当前页选中的 {{ selectedReviewIds.length }} 条（最多 50 条）；翻页、切换状态或知识库会清空选择。所有选中记录均适用时才可执行。</p>
          <t-space break-line>
            <t-button v-for="action in BATCH_REVIEW_ACTIONS" :key="action" size="small" variant="outline"
                      :theme="action === 'reject' ? 'danger' : 'default'" :loading="reviewBatchActing" :disabled="!canBatchReview(action)" @click="actReviews(action)">
              批量{{ reviewActionLabels[action] }}
            </t-button>
          </t-space>
          <p class="hint-text">批量采纳仅使用各记录已有的重写稿，不提交详情中的编辑稿或冲突草稿；无可用重写稿时该项会失败。</p>
        </div>
        <t-alert v-if="reviewBatchError" theme="warning" :message="reviewBatchError" />
        <div v-if="reviewBatchResults.length" class="review-batch-results">
          <p class="hint-text">批量操作结果逐条列出；操作已受理不代表文档已完成入库、删除或图谱回滚。</p>
          <t-table row-key="id" :data="reviewBatchResults" :columns="[
            { colKey: 'document_name', title: '文档', ellipsis: true },
            { colKey: 'result', title: '本次操作结果', width: 140 },
            { colKey: 'status', title: '最新官方评审状态', width: 160 },
            { colKey: 'detail', title: '说明' },
          ]">
            <template #result="{ row }">{{ row.success === true ? '已受理' : row.success === false ? '失败' : '结果待确认' }}</template>
            <template #status="{ row }">{{ stateLabel(row.lifecycle_state) }}</template>
            <template #detail="{ row }">{{ [row.error, row.status_error && `状态读取失败：${row.status_error}`].filter(Boolean).join('；') || '—' }}</template>
          </t-table>
        </div>
        <t-table row-key="review_id" :data="reviews" :loading="reviewLoading" :selected-row-keys="selectedReviewIds"
                 :reserve-selected-row-on-paginate="false" @select-change="(keys: Array<string | number>) => selectedReviewIds = keys.map(String)" :columns="[
          { colKey: 'selection', type: 'multiple', width: 48, disabled: ({ row }: any) => !auth.hasRole('contributor') || row.can_approve_review === false || reviewBatchActing || reviewLoading || row.lifecycle_state === 'rejected' },
          { colKey: 'document_name', title: '文档', ellipsis: true },
          { colKey: 'confidence_score', title: '置信度', width: 90 },
          { colKey: 'flags', title: '标记', width: 220 },
          { colKey: 'created_at', title: '评审时间', width: 180 },
          { colKey: 'operation', title: '操作', width: 90 },
        ]">
          <template #flags="{ row }">
            <t-space size="small" break-line>
              <t-tag v-if="row.has_conflicts" size="small" theme="warning">冲突</t-tag>
              <t-tag v-if="row.has_contradictions" size="small" theme="danger">矛盾</t-tag>
              <t-tag v-if="row.rewrite_needed" size="small" theme="primary">建议重写</t-tag>
              <t-tag v-if="row.human_action" size="small">{{ reviewActionLabels[row.human_action] || '人工处理' }}</t-tag>
            </t-space>
          </template>
          <template #operation="{ row }">
              <t-button size="small" variant="text" theme="primary" @click="extra(()=>openReview(row))">详情</t-button>
          </template>
        </t-table>
        <t-pagination :total="reviewTotal" :current="reviewPage" :page-size="50" :show-page-size="false" @current-change="(value:number)=>{reviewPage=value;extra(loadReviews)}"/>
        <t-empty v-if="!reviews.length" :description="`暂无「${stateLabel(reviewState)}」评审`" />
      </t-tab-panel>

      <!-- 知识库文档(入库后编辑) -->
      <t-tab-panel value="documents" label="文档">
        <t-table row-key="id" :data="kbDocuments" :columns="[
          { colKey: 'title', title: '标题', ellipsis: true },
          { colKey: 'ingest_status', title: '入库状态', width: 110 },
          { colKey: 'review_support', title: '评审格式', width: 160 },
          { colKey: 'chunk_count', title: '片段数', width: 80 },
          { colKey: 'updated_at', title: '更新时间', width: 180 },
          { colKey: 'operation', title: '操作', width: 160 },
        ]">
          <template #title="{ row }">{{ row.metadata?.title || row.name }}</template>
          <template #review_support="{ row }">{{ supportsOfficialReview(row) ? '官方支持评审' : '治理支持未确认' }}</template>
          <template #ingest_status="{ row }">
            <t-tag size="small" :theme="row.ingest_status === 'succeeded' ? 'success' : row.ingest_status === 'failed' ? 'danger' : 'warning'">
              {{ stageLabel(row.ingest_status,'ingest') }}
            </t-tag>
          </template>
          <template #operation="{ row }">
            <t-space size="small">
              <t-button v-if="auth.hasRole('contributor') && canEditDocument(row)" size="small" variant="text" theme="primary" @click="openDocumentEditor(row)">编辑正文</t-button>
              <t-button v-if="row.ingest_status === 'failed'" size="small" variant="text" @click="extra(async()=>{await api.kbDocumentRetry(row.id);await loadKbDocuments()})">重试入库</t-button>
            </t-space>
          </template>
        </t-table>
        <t-pagination :total="docTotal" :current="docPage" :page-size="50" :show-page-size="false" @current-change="(value:number)=>{docPage=value;extra(loadKbDocuments)}"/>
        <t-empty v-if="!kbDocuments.length" description="当前知识库暂无文档" />
      </t-tab-panel>

      <t-tab-panel value="templates" label="内容模板"><ContextDBTemplates v-if="activeBaseId" :kb-id="activeBaseId"/></t-tab-panel>

      <!-- 设置 -->
      <t-tab-panel v-if="auth.hasRole('contributor')" value="settings" label="处理设置">
        <h3>文档评审</h3>
        <t-form label-width="160px" v-if="reviewSettings" :disabled="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId">
          <t-form-item label="启用知识评审" help="设置后续上传文档的默认评审方式；单次上传可覆盖，不会重新评审已有文档">
            <t-switch v-model="reviewSettings.review_enabled" role="switch" aria-label="启用知识评审" :aria-checked="!!reviewSettings.review_enabled"
                      :aria-disabled="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId" :tabindex="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId ? -1 : 0" @keydown="activateSettingsSwitch" />
          </t-form-item>
          <t-form-item label="自动通过阈值（0～1）">
            <t-input-number v-model="reviewSettings.high_threshold" :min="0" :max="1" :step="0.05" theme="column" />
          </t-form-item>
          <t-form-item label="自动重写">
            <t-switch v-model="reviewSettings.rewrite_enabled" role="switch" aria-label="自动重写" :aria-checked="!!reviewSettings.rewrite_enabled"
                      :aria-disabled="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId" :tabindex="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId ? -1 : 0" @keydown="activateSettingsSwitch" />
          </t-form-item>
          <t-form-item label="冲突检测">
            <t-switch v-model="reviewSettings.conflict_detection_enabled" role="switch" aria-label="冲突检测" :aria-checked="!!reviewSettings.conflict_detection_enabled"
                      :aria-disabled="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId" :tabindex="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId ? -1 : 0" @keydown="activateSettingsSwitch" />
          </t-form-item>
          <t-form-item label="重写稿自动入库" help="仅控制重写稿，其他文档仍按阈值处理">
            <t-switch v-model="reviewSettings.rewrite_auto_ingest_enabled" role="switch" aria-label="重写稿自动入库" :aria-checked="!!reviewSettings.rewrite_auto_ingest_enabled"
                      :aria-disabled="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId" :tabindex="reviewSettingsSaving || reviewSettingsKbId !== activeBaseId ? -1 : 0" @keydown="activateSettingsSwitch" />
          </t-form-item>
          <t-form-item label="最多评审轮次" :help="`含首次评估，最多重写 ${Math.max(0, (reviewSettings.max_rewrite_iterations || 1) - 1)} 次；设为 1 时仅评估不重写`">
            <t-input-number v-model="reviewSettings.max_rewrite_iterations" :min="1" :step="1" :decimal-places="0" theme="column" />
          </t-form-item>
          <t-form-item>
            <t-button theme="primary" :loading="reviewSettingsSaving" @click="extra(saveReviewSettings)">保存评审设置</t-button>
          </t-form-item>
        </t-form>
        <t-empty v-if="!reviewSettings" description="暂无配置" />
      </t-tab-panel>
    </t-tabs>
    <t-drawer v-model:visible="reviewDrawer" size="720px" :footer="false"
              :header="reviewDetail?.document_name || '评审详情'" destroy-on-close>
      <div v-if="reviewDetail" class="review-detail">
        <t-alert theme="info" message="文档评审决定采用原文或修订稿继续入库；处理结果不会回写采集原件或外部来源。" />
        <t-alert v-if="!supportsOfficialReview(reviewDetail)" theme="warning" :message="CONTEXTDB_REVIEW_FORMAT_NOTICE" />
        <t-descriptions :column="2" bordered size="small">
          <t-descriptions-item label="状态">{{ stateLabel(activeState) }}</t-descriptions-item>
          <t-descriptions-item label="综合置信度">{{ reviewDetail.confidence_score??'未评分' }}</t-descriptions-item>
          <t-descriptions-item label="逻辑连贯性（高为佳）">{{ reviewDetail.logic_score??'未评分' }}</t-descriptions-item>
          <t-descriptions-item label="噪声比例（低为佳）">{{ reviewDetail.noise_score??'未评分' }}</t-descriptions-item>
          <t-descriptions-item label="内部矛盾度（低为佳）">{{ reviewDetail.contradiction_score??'未评分' }}</t-descriptions-item>
          <t-descriptions-item label="评审轮次">{{ reviewDetail.loop_iterations }} / {{ reviewDetail.max_iterations }}</t-descriptions-item>
          <t-descriptions-item label="判定理由" :span="2">{{ reviewDetail.decision_reason }}</t-descriptions-item>
          <t-descriptions-item v-if="reviewDetail.human_action" label="人工处理" :span="2">
            {{ reviewActionLabels[reviewDetail.human_action] || '已处理' }} · {{ dateTime(reviewDetail.human_action_at) }}
          </t-descriptions-item>
        </t-descriptions>

        <template v-if="qualityDetails.logic_issues?.length || qualityDetails.noise_segments?.length">
          <t-divider align="left">质量问题</t-divider>
          <ul class="issue-list">
            <li v-for="(item, index) in qualityDetails.logic_issues || []" :key="`l${index}`">逻辑:{{ item }}</li>
            <li v-for="(item, index) in qualityDetails.noise_segments || []" :key="`n${index}`">噪声内容：<span v-if="typeof item === 'string'">{{item}}</span><StructuredFields v-else :model-value="item" readonly/></li>
          </ul>
        </template>
        <template v-if="contradictions.length">
          <t-divider align="left">内部矛盾</t-divider>
          <ul class="issue-list">
            <li v-for="(item, index) in contradictions" :key="index"><span v-if="typeof item === 'string'">{{item}}</span><StructuredFields v-else :model-value="item" readonly/></li>
          </ul>
        </template>

        <template v-if="conflicts.length">
          <t-divider align="left">与已有知识冲突({{ conflicts.length }})</t-divider>
          <div v-for="conflict in conflicts" :key="conflictId(conflict)" class="conflict-card">
            <div v-if="conflict.description || conflict.summary" class="conflict-text">{{ conflict.description || conflict.summary }}</div><StructuredFields v-else :model-value="conflict" readonly/>
            <t-select v-model="resolutions[conflictId(conflict)]" :options="CONFLICT_OPTIONS" size="small"
                      placeholder="选择处置" clearable :disabled="!canReviewAction(reviewDetail, 'confirm')" class="conflict-select" />
          </div>
          <t-button v-if="canReviewAction(reviewDetail, 'confirm')" size="small" variant="outline" :loading="reviewActing" @click="saveConflictDraft">保存处置草稿</t-button>
          <t-alert v-if="conflictNotice" theme="info" :message="conflictNotice" />
        </template>

        <t-divider align="left">原文</t-divider>
        <pre class="review-content">{{ reviewDetail.original_content?.text }}</pre>
        <t-pagination v-if="(reviewDetail.original_content?.total_pages || 1) > 1" size="small"
                      :total="reviewDetail.original_content.total_pages" :page-size="1" :current="contentPage"
                      :show-page-size="false" :disabled="reviewActing" @current-change="loadReviewPage" />

        <template v-if="reviewDetail.rewritten_content">
          <t-divider align="left">AI 重写稿</t-divider>
          <div v-if="reviewDetail.rewrite_reason" class="hint-text">{{ reviewDetail.rewrite_reason }}</div>
          <pre class="review-content">{{ reviewDetail.rewritten_content }}</pre>
        </template>

        <template v-if="editing">
          <t-divider align="left">编辑稿(将替换文档全文)</t-divider>
          <t-textarea v-model="editedContent" :autosize="{ minRows: 10, maxRows: 24 }" />
        </template>

        <t-alert v-if="reviewError" theme="error" :message="reviewError" class="review-error" />
        <t-alert v-if="reviewNotice" theme="info" :message="reviewNotice" />
        <t-descriptions :column="2" bordered size="small">
          <t-descriptions-item label="文档入库">{{ stageLabel(reviewDocument?.ingest_status, 'ingest') }}</t-descriptions-item>
          <t-descriptions-item v-if="reviewBase?.wiki_enabled" label="Wiki 编译">{{ stageLabel(reviewDocument?.wiki_status, 'wiki') }}</t-descriptions-item>
        </t-descriptions>
        <p v-if="reviewBase?.wiki_enabled" class="hint-text">文档入库与 Wiki 编译分别推进。自动编译通常无需逐条批准；请打开同库 Wiki 核对正式正文和来源。</p>
        <p v-else class="hint-text">文档入库与图谱构建分别推进；图谱仍在处理时，已成功入库的正文可供检索。</p>
        <t-alert v-if="reviewStatusError" theme="warning" :message="`官方文档状态未能确认：${reviewStatusError}`" />
        <t-alert v-if="reviewDocument?.ingest_error_message || reviewDocument?.wiki_error_message" theme="error" :message="reviewDocument.ingest_error_message || reviewDocument.wiki_error_message" />
        <t-space><t-button variant="outline" size="small" :loading="reviewStatusLoading" @click="refreshReviewStatus">刷新官方状态</t-button><t-button v-if="reviewBase?.wiki_enabled" variant="outline" size="small" @click="openReviewWiki">打开同库 Wiki 核对</t-button></t-space>
        <t-space v-if="auth.hasRole('contributor') && reviewDetail.can_approve_review !== false" class="review-actions" break-line>
          <template v-if="activeState === 'pending_human'">
            <t-button theme="primary" :loading="reviewActing" @click="actReview('confirm')">通过原文</t-button>
            <t-button variant="outline" :loading="reviewActing" @click="actReview('force_accept')">强制通过</t-button>
            <t-button v-if="!editing" variant="outline" :loading="reviewActing" @click="startEditing">编辑后通过</t-button>
            <t-button v-if="editing || reviewDetail.rewritten_content" theme="success" :loading="reviewActing"
                      @click="actReview('accept_rewrite')">{{ editing ? '提交编辑稿' : '采纳重写稿' }}</t-button>
            <t-button theme="danger" variant="outline" :loading="reviewActing" @click="actReview('reject_reupload')">拒绝并等待重新上传</t-button>
            <t-button theme="danger" :loading="reviewActing" @click="actReview('reject')">拒绝并删除</t-button>
          </template>
          <t-button v-else-if="['approved', 'auto_accepted'].includes(activeState)" theme="warning" :loading="reviewActing"
                    @click="actReview('retract')">撤回至待人工评审</t-button>
          <t-button v-else-if="activeState === 'failed'" theme="primary" :loading="reviewActing"
                    @click="actReview('retry_review')">重新评审</t-button>
        </t-space>
      </div>
    </t-drawer>

    <t-dialog v-model:visible="docDialog" width="760px" :header="`编辑正文 · ${docRow?.metadata?.title || docRow?.name || ''}`"
              :confirm-btn="{content:'保存并重新处理',disabled:!docReady || docLoading}" :confirm-loading="docLoading" @confirm="saveDocument">
      <t-alert v-if="docError" theme="error" :message="docError" class="review-error" />
      <t-textarea v-model="docText" :disabled="docLoading" :autosize="{ minRows: 14, maxRows: 28 }" />
    </t-dialog>
  </div>
</template>

<style scoped>
.knowledge-layout { display: flex; flex-direction: column; gap: 16px; }
.knowledge-tabs :deep(.t-tabs__content) { padding-top: 12px; }
.search-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.search-bar :deep(.t-input) { flex: 1; }
.result-card { background: var(--td-bg-color-container); border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); padding: 12px 16px; margin-bottom: 12px; }
.result-meta { font-size: var(--app-text-sm); opacity: .6; margin-bottom: 8px; }

.graph-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.graph-stats { font-size: var(--app-text-sm); opacity: .6; }
.graph-canvas { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.graph-node { cursor: pointer; }
.graph-edges { width: 100%; border-top: 1px solid var(--td-component-stroke); padding-top: 10px; }
.graph-edge { display: flex; align-items: center; gap: 6px; font-size: var(--app-text-sm); padding: 3px 0; }
.edge-source, .edge-target { font-weight: 600; }
.edge-type { opacity: .6; }

.review-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.review-detail { display: flex; flex-direction: column; gap: 8px; }
.review-content {
  background: var(--td-bg-color-component); padding: 12px; border-radius: var(--app-radius-sm); margin: 0;
  font-size: var(--app-text-sm); max-height: 360px; overflow: auto; white-space: pre-wrap; word-break: break-word;
}
.issue-list { margin: 0; padding-left: 18px; font-size: var(--app-text-md); line-height: 1.8; }
.conflict-card { display: flex; gap: 10px; align-items: flex-start; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-sm); padding: 8px 10px; }
.conflict-text { flex: 1; font-size: var(--app-text-md); }
.conflict-select { width: 150px; flex: none; }
.hint-text { font-size: var(--app-text-sm); opacity: .65; }
.review-error { margin-top: 4px; }
.review-actions { margin-top: 12px; }
</style>
