<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { getBasePermissions, knowledgeAccess, listBases, nativeAPI, type BasePermissionProfile } from '@/api/contextdb'
import { useAuthStore } from '@/stores/auth'
import DocMarkdown from '@/components/DocMarkdown.vue'
import ContextDBSourcePreview from '@/components/ContextDBSourcePreview.vue'
import ContextDBSourceResources from '@/components/ContextDBSourceResources.vue'
import StructuredFields from '@/components/StructuredFields.vue'
import { contextdbDateTime as dateTime } from '@/utils/platformPresentation'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { reviewEditableContent } from '@/utils/reviewContent'

const route = useRoute(), auth = useAuthStore()
const REVIEW_STATES = [
  { value: 'pending_human', label: '待人工评审' },
  { value: 'auto_accepted', label: '自动接受' }, { value: 'approved', label: '人工通过' },
  { value: 'rejected', label: '已拒绝' }, { value: 'failed', label: '评审失败' }, { value: '', label: '全部' },
]
const actionLabels: Record<string, string> = { confirm: '原样入库', force_accept: '强制接纳原文', accept_rewrite: '采纳重写', reject: '拒绝', reject_reupload: '要求重新上传', retract: '撤回', retry_review: '重新评审' }
const decisionLabels: Record<string, string> = { auto_accept: '自动接受', pending_review: '等待人工评审', reject: '拒绝' }
const conflictOptions = [{ value: 'use_new', label: '采用新文档' }, { value: 'keep_old', label: '保留旧知识' }, { value: 'merge', label: '合并' }, { value: 'annotate_divergence', label: '标注分歧' }]
const bases = ref<any[]>([]), permissionProfile = ref<BasePermissionProfile | null>(null)
const viewMode = ref(route.query.kb_id ? 'knowledge_base' : 'mine'), activeBaseId = ref(typeof route.query.kb_id === 'string' ? route.query.kb_id : '')
const reviewState = ref('pending_human'), sortBy = ref(''), sortOrder = ref('desc')
const contextLoading = ref(false), contextError = ref(''), contextReady = ref(false)
const writableBases = computed(() => bases.value.filter(base => knowledgeAccess(base, permissionProfile.value, auth.hasRole('contributor')).write))
const reviews = ref<any[]>([]), reviewPage = ref(1), reviewPageSize = ref(10), reviewTotal = ref(0), reviewLoading = ref(false), listError = ref('')
const selectedReviewIds = ref<string[]>([]), reviewBatchActing = ref(false), reviewBatchResults = ref<any[]>([]), reviewBatchError = ref('')
const selectableRows = computed(() => reviews.value.filter(row => row.can_approve_review !== false && row.lifecycle_state !== 'rejected' && knowledgeAccess({ id: row.knowledge_base_id }, permissionProfile.value, auth.hasRole('contributor')).write))
const allSelected = computed(() => selectableRows.value.length > 0 && selectableRows.value.every(row => selectedReviewIds.value.includes(row.review_id)))
const reviewRow = ref<any>(null), reviewDetail = ref<any>(null), detailLoading = ref(false), contentPage = ref(1)
const reviewActing = ref(false), reviewError = ref(''), reviewNotice = ref(''), conflictNotice = ref('')
const reviewDocument = ref<any>(null), reviewStatusError = ref(''), reviewStatusLoading = ref(false)
const editing = ref(false), showRewriteEditor = ref(false), editedContent = ref(''), resolutions = ref<Record<string, string>>({})
const originalMode = ref('original')
const rejectTarget = ref<'single' | 'batch' | ''>('')
let alive = true, reviewListRequest = 0, reviewBatchRequest = 0, reviewRequest = 0, reviewStatusRequest = 0
const stateLabel = (state: string) => REVIEW_STATES.find(item => item.value === state)?.label || '—'
const decisionLabel = (decision: string) => decisionLabels[decision] || '—'
const score = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—'
const activeState = computed(() => reviewDetail.value?.lifecycle_state || reviewRow.value?.lifecycle_state)
const reviewBase = computed(() => bases.value.find(base => base.id === reviewDetail.value?.knowledge_base_id))
function parseJson(value: any) { if (typeof value !== 'string') return value; try { return JSON.parse(value) } catch { return value } }
const qualityDetails = computed(() => parseJson(reviewDetail.value?.quality_details) || {})
const conflicts = computed<any[]>(() => { const value = parseJson(reviewDetail.value?.conflicts); return Array.isArray(value) ? value : value?.conflicts || [] })
const contradictions = computed<any[]>(() => { const value = parseJson(reviewDetail.value?.contradictions); return Array.isArray(value) ? value : [] })
const rewriteInfo = computed(() => parseJson(reviewDetail.value?.rewrite_info_check) || {})
const batchActions = computed(() => {
  const rows = reviews.value.filter(row => selectedReviewIds.value.includes(row.review_id))
  const actions = rows.every(row => row.lifecycle_state === 'pending_human') ? ['confirm', 'accept_rewrite', 'reject']
    : rows.every(row => ['approved', 'auto_accepted'].includes(row.lifecycle_state)) ? ['retract']
    : rows.every(row => row.lifecycle_state === 'failed') ? ['retry_review'] : []
  return actions.map(action => ({ value: action, content: actionLabels[action], disabled: !canBatchReview(action) }))
})
async function readReview(id: string, page = 1) { return { review: (await nativeAPI.get('knowledge/reviews/detail', { review_id: id, content_page: page })).data } }
async function loadContext() {
  contextLoading.value = true; contextError.value = ''; permissionProfile.value = null
  const [libraries, permissions] = await Promise.allSettled([listBases(), getBasePermissions()])
  if (!alive) return
  if (libraries.status === 'fulfilled') bases.value = libraries.value.data
  else contextError.value = libraries.reason?.message || '知识库读取失败'
  if (permissions.status === 'fulfilled') permissionProfile.value = permissions.value
  else contextError.value = permissions.reason?.message || '权限读取失败'
  if (viewMode.value === 'knowledge_base' && !writableBases.value.some(base => base.id === activeBaseId.value)) activeBaseId.value = ''
  contextReady.value = true; contextLoading.value = false
  await loadReviews()
}
function clearReview() {
  reviewRequest++; reviewStatusRequest++
  reviewRow.value = null; reviewDetail.value = null; reviewDocument.value = null; detailLoading.value = false
  editing.value = false; showRewriteEditor.value = false; editedContent.value = ''; originalMode.value = 'original'; resolutions.value = {}; reviewError.value = ''; reviewNotice.value = ''; conflictNotice.value = ''
  reviewStatusError.value = ''; reviewStatusLoading.value = false; rejectTarget.value = ''
}
function canLeaveReview() { return !editing.value || window.confirm('当前修改尚未提交，确定要离开吗？') }
function closeReview() { if (!reviewActing.value && !reviewBatchActing.value && canLeaveReview()) clearReview() }
async function loadReviews(selectFirst = true) {
  const request = ++reviewListRequest, kbId = viewMode.value === 'knowledge_base' ? activeBaseId.value : ''
  selectedReviewIds.value = []; listError.value = ''; reviewLoading.value = true
  if (viewMode.value === 'knowledge_base' && !kbId) { reviews.value = []; reviewTotal.value = 0; reviewLoading.value = false; return }
  try {
    const result = await nativeAPI.get('knowledge/reviews', {
      knowledge_base_id: kbId || undefined, lifecycle_state: reviewState.value || undefined, page: reviewPage.value, page_size: reviewPageSize.value,
      sort_by: sortBy.value || undefined, sort_order: sortBy.value ? sortOrder.value : undefined,
    })
    if (!alive || request !== reviewListRequest) return
    reviews.value = result.data.reviews || []; reviewTotal.value = result.data.total ?? reviews.value.length
    if (selectFirst && !reviewRow.value && reviews.value.length) await openReview(reviews.value[0])
  } catch (error: any) { if (alive && request === reviewListRequest) listError.value = error.message || '评审列表读取失败' }
  finally { if (alive && request === reviewListRequest) reviewLoading.value = false }
}
function canReviewAction(row: any, action: string) {
  if (!row || row.can_approve_review === false || !knowledgeAccess({ id: row.knowledge_base_id }, permissionProfile.value, auth.hasRole('contributor')).write) return false
  if (action === 'retract') return ['approved', 'auto_accepted'].includes(row.lifecycle_state)
  if (action === 'retry_review') return row.lifecycle_state === 'failed'
  return ['confirm', 'force_accept', 'accept_rewrite', 'reject', 'reject_reupload'].includes(action) && row.lifecycle_state === 'pending_human'
}
function canBatchReview(action: string) {
  const rows = reviews.value.filter(row => selectedReviewIds.value.includes(row.review_id))
  return !editing.value && !reviewLoading.value && !reviewBatchActing.value && !reviewActing.value && rows.length > 0 && rows.length <= 50 && rows.length === selectedReviewIds.value.length && rows.every(row => canReviewAction(row, action))
}
function toggleAll(checked: boolean) { selectedReviewIds.value = checked ? selectableRows.value.map(row => row.review_id) : [] }
function toggleSelection(id: string, checked: boolean) { selectedReviewIds.value = checked ? [...selectedReviewIds.value, id] : selectedReviewIds.value.filter(value => value !== id) }
async function actReviews(action: string, confirmed = false) {
  if (!canBatchReview(action)) return
  if (action === 'reject' && !confirmed) { rejectTarget.value = 'batch'; return }
  const ids = [...selectedReviewIds.value], rows = [...reviews.value], request = ++reviewBatchRequest
  reviewBatchActing.value = true; reviewBatchError.value = ''; reviewBatchResults.value = []
  try {
    if (action === 'accept_rewrite') {
      const details = await Promise.all(ids.map(id => readReview(id)))
      if (!alive || request !== reviewBatchRequest) return
      if (details.some((value, index) => value.review?.review_id !== ids[index] || !canReviewAction(value.review, action) || !value.review.rewritten_content?.trim())) { reviewBatchError.value = '所选评审包含无可采纳重写稿或状态已变化的文件'; return }
    }
    let results: any[] = []
    try { results = (await nativeAPI.post('knowledge/reviews/batch', { ids, action })).data.results || [] }
    catch (error: any) { if (request === reviewBatchRequest) reviewBatchError.value = error.message }
    const statuses = await Promise.allSettled(ids.map(id => readReview(id)))
    if (!alive || request !== reviewBatchRequest) return
    reviewBatchResults.value = ids.map((id, index) => {
      const result = results.find(item => (item.id || item.review_id) === id), status = statuses[index]!
      return { id, name: documentDisplayName(rows.find(row => row.review_id === id)), success: result?.success,
        state: status.status === 'fulfilled' ? status.value.review?.lifecycle_state : '',
        error: [result?.error, status.status === 'rejected' ? status.reason?.message : ''].filter(Boolean).join('；') }
    })
    selectedReviewIds.value = []; await loadReviews(false)
    if (reviewRow.value && ids.includes(reviewRow.value.review_id)) await loadReviewPage(1)
  } catch (error: any) { if (alive && request === reviewBatchRequest) reviewBatchError.value = error.message }
  finally { if (alive && request === reviewBatchRequest) reviewBatchActing.value = false }
}
async function loadReviewPage(page: number) {
  if (!reviewRow.value || reviewActing.value) return false
  const id = reviewRow.value.review_id, request = ++reviewRequest
  detailLoading.value = true; reviewError.value = ''
  try {
    const result = await readReview(id, page)
    if (!alive || request !== reviewRequest || reviewRow.value?.review_id !== id) return false
    if (result.review?.review_id !== id || ['document_id', 'knowledge_base_id'].some(key => reviewRow.value[key] && result.review?.[key] !== reviewRow.value[key])) throw new Error('评审记录不一致，请重新读取')
    if (result.review.original_content && result.review.original_content.page !== page) throw new Error('评审原文分页不一致，请重新读取')
    reviewDetail.value = result.review; contentPage.value = page
    return true
  } catch (error: any) { if (alive && request === reviewRequest) reviewError.value = error.message; return false }
  finally { if (alive && request === reviewRequest) detailLoading.value = false }
}
async function openReview(row: any) {
  if (reviewActing.value || reviewBatchActing.value || reviewRow.value?.review_id === row.review_id || !canLeaveReview()) return
  clearReview(); reviewRow.value = row
  if (!await loadReviewPage(1)) return
  editedContent.value = reviewDetail.value.rewritten_content || ''
  const saved = parseJson(reviewDetail.value.human_conflict_resolutions) || []
  resolutions.value = Object.fromEntries((Array.isArray(saved) ? saved : []).map((item: any) => [item.conflict_id, item.resolution]))
}
async function startEditing() {
  if (reviewActing.value || !canReviewAction(reviewDetail.value, 'confirm')) return
  if (editing.value) { showRewriteEditor.value = true; return }
  const detail = reviewDetail.value, request = ++reviewRequest
  reviewError.value = ''; reviewActing.value = true
  try {
    const text = await reviewEditableContent(detail, readReview)
    if (!alive || request !== reviewRequest || reviewDetail.value?.review_id !== detail.review_id) return
    editedContent.value = text; editing.value = true; showRewriteEditor.value = true
  } catch (error: any) { if (alive && request === reviewRequest) reviewError.value = error.message }
  finally { if (alive && request === reviewRequest) reviewActing.value = false }
}
function selectedResolutions() { return Object.entries(resolutions.value).filter(([, resolution]) => resolution).map(([conflict_id, resolution]) => ({ conflict_id, resolution })) }
async function saveConflictDraft() {
  if (reviewActing.value || !canReviewAction(reviewDetail.value, 'confirm')) return
  const items = selectedResolutions(), id = reviewDetail.value.review_id
  if (!items.length) return
  const request = ++reviewRequest
  reviewActing.value = true; reviewError.value = ''; conflictNotice.value = ''
  try { await nativeAPI.post('knowledge/reviews/resolve-conflicts', { review_id: id, resolutions: items }); if (alive && request === reviewRequest) conflictNotice.value = '处理记录已保存' }
  catch (error: any) { if (alive && request === reviewRequest) reviewError.value = error.message }
  finally { if (alive && request === reviewRequest) reviewActing.value = false }
}
async function refreshReviewStatus() {
  const review = reviewDetail.value
  if (!review?.document_id || !review.knowledge_base_id) return
  const request = ++reviewStatusRequest, version = reviewRequest
  reviewStatusLoading.value = true; reviewStatusError.value = ''
  try {
    const result = await nativeAPI.get('knowledge/documents/detail', { document_id: review.document_id })
    if (!alive || request !== reviewStatusRequest || version !== reviewRequest || reviewDetail.value?.review_id !== review.review_id) return
    if (result.data?.id !== review.document_id || result.data?.knowledge_base_id !== review.knowledge_base_id) throw new Error('文档归属与当前评审不一致，请重新读取')
    reviewDocument.value = result.data
  } catch (error: any) { if (alive && request === reviewStatusRequest && version === reviewRequest) reviewStatusError.value = error.message }
  finally { if (alive && request === reviewStatusRequest) reviewStatusLoading.value = false }
}
async function actReview(action: string, confirmed = false) {
  if (reviewActing.value || reviewBatchActing.value || !canReviewAction(reviewDetail.value, action)) return
  if (['reject', 'reject_reupload'].includes(action) && !confirmed) { rejectTarget.value = 'single'; return }
  const id = reviewDetail.value.review_id, body: Record<string, any> = { review_id: id, action }
  if (action === 'accept_rewrite') {
    if (editing.value && !editedContent.value.trim()) { reviewError.value = '文件内容不能为空'; return }
    if (!editing.value && !reviewDetail.value.rewritten_content?.trim()) { reviewError.value = '暂无重写建议'; return }
    if (editing.value) body.edited_content = editedContent.value
  }
  if (['confirm', 'force_accept', 'accept_rewrite'].includes(action) && selectedResolutions().length) body.conflict_resolutions = selectedResolutions()
  const request = ++reviewRequest
  reviewStatusRequest++; reviewActing.value = true; reviewError.value = ''; reviewNotice.value = ''
  try {
    const result = await nativeAPI.post('knowledge/reviews/action', body)
    if (!alive || request !== reviewRequest || reviewRow.value?.review_id !== id) return
    if (result.data?.review_id !== id) throw new Error('评审操作结果未确认，请刷新后核对')
    reviewDetail.value = { ...reviewDetail.value, ...result.data }; reviewRow.value = { ...reviewRow.value, ...result.data }
    editing.value = false; showRewriteEditor.value = false; conflictNotice.value = ''; reviewDocument.value = null; reviewNotice.value = '操作成功'
    await loadReviews(false)
    if (!['reject', 'reject_reupload'].includes(action)) await refreshReviewStatus()
  } catch (error: any) { if (alive && request === reviewRequest) reviewError.value = error.message }
  finally { if (alive && request === reviewRequest) reviewActing.value = false }
}
async function confirmReject() { const target = rejectTarget.value; rejectTarget.value = ''; if (target === 'batch') await actReviews('reject', true); else if (target === 'single') await actReview('reject', true) }
watch([viewMode, activeBaseId, reviewState, sortBy, sortOrder, reviewPageSize], () => {
  reviewListRequest++; reviewBatchRequest++; selectedReviewIds.value = []; reviewBatchResults.value = []; reviewBatchError.value = ''; reviewPage.value = 1
  clearReview(); reviews.value = []; reviewTotal.value = 0; if (contextReady.value) void loadReviews()
})
function changePage(page: number) { if (reviewActing.value || reviewBatchActing.value || !canLeaveReview()) return; reviewBatchRequest++; reviewPage.value = page; clearReview(); void loadReviews() }
onMounted(loadContext)
onBeforeRouteLeave(() => !reviewActing.value && !reviewBatchActing.value && canLeaveReview())
function beforeUnload(event: BeforeUnloadEvent) { if (editing.value || reviewActing.value || reviewBatchActing.value) { event.preventDefault(); event.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeUnmount(() => { alive = false; reviewListRequest++; reviewBatchRequest++; reviewRequest++; reviewStatusRequest++; window.removeEventListener('beforeunload', beforeUnload) })
</script>

<template>
  <div class="knowledge-review-page">
    <header class="review-page-header"><h2>知识评审</h2><p>整理记忆、提炼知识，并管理演进策略与模板。</p></header>
    <div class="review-scope-bar"><label><t-select v-model="viewMode" :disabled="editing || reviewActing || reviewBatchActing" :options="[{value:'mine',label:'我的评审'},{value:'knowledge_base',label:'按知识库查看'}]" aria-label="评审范围" class="scope-select" /></label><t-select v-if="viewMode === 'knowledge_base'" v-model="activeBaseId" :disabled="editing || reviewActing || reviewBatchActing" filterable clearable placeholder="请选择知识库" aria-label="知识库" :options="writableBases.map(base => ({ value: base.id, label: base.name }))" class="base-select" /></div>
    <t-collapse class="review-explanation" :default-value="[]"><t-collapse-panel value="knowledge-review" header="知识入库评审"><p>当文件上传到知识库时，系统会自动进行质量评估、自矛盾检测、计算综合置信度，并做出入库决策：自动通过（置信度高于阈值且无幻觉，直接入库）；待人工审核（置信度低于阈值，支持拒绝入库、原样入库或智能重写后入库；智能重写会针对文件进行降噪、结构化、幻觉去重等操作）。</p><t-space><t-tag variant="light">支持 txt / md / pdf / doc / docx</t-tag><t-tag variant="light">质量评估</t-tag><t-tag variant="light">重写建议</t-tag></t-space></t-collapse-panel></t-collapse>
    <t-alert v-if="contextError" theme="error" :message="contextError" />
    <div class="review-filter-bar">
      <label>评审状态 <t-select v-model="reviewState" :disabled="editing || reviewActing || reviewBatchActing" :options="REVIEW_STATES" aria-label="评审状态" /></label>
      <label><t-select v-model="sortBy" clearable placeholder="排序字段" :disabled="editing || reviewActing || reviewBatchActing" :options="[{ value: 'confidence_score', label: '质量分数' }]" aria-label="排序字段" /></label>
      <t-button variant="outline" :disabled="!sortBy || editing || reviewActing || reviewBatchActing" :aria-label="sortOrder === 'desc' ? '切换升序' : '切换降序'" @click="sortOrder = sortOrder === 'desc' ? 'asc' : 'desc'"><t-icon :name="sortOrder === 'desc' ? 'order-descending' : 'order-ascending'" /></t-button>
      <span class="toolbar-spacer" /><t-button variant="outline" :loading="reviewLoading" @click="loadReviews(false)"><t-icon name="refresh" />刷新</t-button>
    </div>
    <t-alert v-if="listError" theme="error" :message="listError" />
    <t-alert v-if="reviewState === 'failed'" theme="info" message="这里只显示已生成评审记录的失败项。更早阶段的处理失败请在知识库文档列表查看。" />
    <div v-if="reviews.length" class="review-workspace">
      <aside class="review-list" aria-label="评审列表">
        <div class="review-list-heading"><t-checkbox :checked="allSelected" :indeterminate="!!selectedReviewIds.length && !allSelected" :disabled="reviewLoading || reviewBatchActing || !reviews.length" @change="(value: boolean) => toggleAll(value)">{{ selectedReviewIds.length ? `已选择 ${selectedReviewIds.length} 条` : '全选本页' }}</t-checkbox><t-dropdown v-if="selectedReviewIds.length" :options="batchActions" @click="(item: any) => actReviews(String(item.value))"><t-button size="small" variant="outline" :loading="reviewBatchActing">批量操作<t-icon name="chevron-down" /></t-button></t-dropdown></div>
        <t-alert v-if="reviewBatchError" theme="error" :message="reviewBatchError" />
        <div v-if="reviewBatchResults.length" class="batch-results" aria-live="polite"><div v-for="result in reviewBatchResults" :key="result.id"><strong>{{ result.name }}</strong><span>{{ result.success === true ? '操作成功' : result.success === false ? '操作失败' : '结果待确认' }} · {{ stateLabel(result.state) }}</span><p v-if="result.error">{{ result.error }}</p></div></div>
        <div class="review-list-scroll">
          <t-loading v-if="reviewLoading && !reviews.length" class="review-empty" text="加载中" />
          <div v-for="row in reviews" :key="row.review_id" class="review-list-card" :class="{ selected: reviewRow?.review_id === row.review_id }" role="button" tabindex="0" @click="openReview(row)" @keydown.enter.prevent="openReview(row)" @keydown.space.prevent="openReview(row)">
            <div class="review-card-title"><span @click.stop @keydown.stop><t-checkbox :checked="selectedReviewIds.includes(row.review_id)" :disabled="reviewActing || reviewBatchActing || row.lifecycle_state === 'rejected' || row.can_approve_review === false || !knowledgeAccess({ id: row.knowledge_base_id }, permissionProfile, auth.hasRole('contributor')).write" :aria-label="`选择${documentDisplayName(row)}`" @change="(value: boolean) => toggleSelection(row.review_id, value)" /></span><strong>{{ documentDisplayName(row) || '—' }}</strong><t-tag size="small" :theme="row.lifecycle_state === 'pending_human' ? 'warning' : ['approved', 'auto_accepted'].includes(row.lifecycle_state) ? 'success' : row.lifecycle_state === 'failed' ? 'danger' : 'default'" variant="light">{{ stateLabel(row.lifecycle_state) }}</t-tag></div>
            <div class="review-card-meta"><span>AI评审结论：{{ decisionLabel(row.decision) }}</span><span>质量分数：<b>{{ score(row.confidence_score) }}</b></span><span>人工操作：{{ actionLabels[row.human_action] || '—' }}</span><span>{{ dateTime(row.created_at) }}</span></div>
          </div>
          <t-empty v-if="!reviewLoading && !reviews.length" class="review-empty" :description="viewMode === 'knowledge_base' && !activeBaseId ? '请选择知识库' : '暂无评审记录'" />
        </div>

      </aside>
      <section class="review-detail-panel" aria-label="评审详情">
        <div class="review-detail-heading"><h3>评审详情</h3><t-button v-if="reviewRow" variant="text" shape="square" aria-label="关闭评审详情" :disabled="reviewActing" @click="closeReview"><t-icon name="close" /></t-button></div>
        <div v-if="detailLoading && !reviewDetail" class="review-empty"><t-loading text="加载中" /></div>
        <div v-else-if="!reviewRow" class="review-empty"><t-empty description="请选择一条评审记录查看详情" /></div>
        <div v-if="reviewRow" class="review-detail-scroll">
          <t-alert v-if="reviewError" theme="error" :message="reviewError"><template #operation><t-button variant="text" @click="loadReviewPage(contentPage)">重试</t-button></template></t-alert>
          <t-alert v-if="reviewNotice" theme="success" :message="reviewNotice" />
          <template v-if="reviewDetail">
            <dl class="review-metadata"><dt>文件名称</dt><dd>{{ documentDisplayName(reviewDetail) || '—' }}</dd><dt>所属知识库</dt><dd>{{ reviewBase?.name || reviewDetail.knowledge_base_name || reviewDetail.knowledge_base_id || '—' }}</dd><dt>AI评审结论</dt><dd>{{ decisionLabel(reviewDetail.decision) }}</dd><dt>评审状态</dt><dd>{{ stateLabel(activeState) }}</dd><dt>创建时间</dt><dd>{{ dateTime(reviewDetail.created_at) }}</dd><dt>更新时间</dt><dd>{{ dateTime(reviewDetail.updated_at) }}</dd></dl>
            <section class="review-section"><h4>质量评分</h4><div class="quality-score-grid"><t-card v-for="item in [{ key: 'logic_score', label: '逻辑度' }, { key: 'noise_score', label: '噪音度' }, { key: 'contradiction_score', label: '自矛盾度' }, { key: 'confidence_score', label: '综合分数' }]" :key="item.key" :bordered="true" class="quality-score-card"><span>{{ item.label }}</span><strong :style="{color:['noise_score','contradiction_score'].includes(item.key)?'var(--td-error-color)':'var(--td-success-color)'}">{{ score(reviewDetail[item.key]) }}</strong></t-card></div></section>
            <section class="review-section"><h4>决策原因</h4><p>{{ reviewDetail.decision_reason || '—' }}</p><ul v-if="qualityDetails.logic_issues?.length"><li v-for="(issue, index) in qualityDetails.logic_issues" :key="index">{{ issue }}</li></ul><StructuredFields v-if="qualityDetails.noise_segments?.length" :model-value="qualityDetails.noise_segments" readonly /></section>
            <section class="review-section"><h4>冲突与处理记录</h4><p v-if="!conflicts.length" class="section-empty">-</p><div v-for="(conflict, index) in conflicts" :key="conflict.id || conflict.conflict_id || index" class="conflict-record"><StructuredFields :model-value="conflict" readonly /><t-select v-if="canReviewAction(reviewDetail, 'confirm')" v-model="resolutions[conflict.id || conflict.conflict_id]" :options="conflictOptions" clearable placeholder="选择处理方式" :disabled="reviewActing" /></div><t-button v-if="conflicts.length && canReviewAction(reviewDetail, 'confirm')" size="small" variant="outline" :loading="reviewActing" @click="saveConflictDraft">保存处理记录</t-button><p v-if="conflictNotice">{{ conflictNotice }}</p><p v-if="reviewDetail.human_action">{{ actionLabels[reviewDetail.human_action] || reviewDetail.human_action }} · {{ dateTime(reviewDetail.human_action_at) }}</p></section>
            <section class="review-section"><h4>自矛盾详情</h4><p v-if="!contradictions.length" class="section-empty">-</p><StructuredFields v-else :model-value="contradictions" readonly /></section>
            <section class="review-section"><h4>原文与重写对比</h4><div class="review-comparison">
              <section class="comparison-column"><h5>原文</h5><div class="comparison-body">
                <h6>原始评分</h6><div class="inline-scores"><span>逻辑度 {{ score(reviewDetail.original_logic_score) }}</span><span>噪音度 {{ score(reviewDetail.original_noise_score) }}</span><span>自矛盾度 {{ score(reviewDetail.original_contradiction_score) }}</span></div>
                <div class="content-label"><h6>文件内容</h6><t-radio-group v-model="originalMode" size="small" aria-label="原文显示方式"><t-radio-button value="original">当前原件</t-radio-button><t-radio-button value="parsed">本次评审文本</t-radio-button></t-radio-group></div>
                <p class="section-empty">原件展示当前可下载版本；本次评审内容请核对评审文本。</p>
                <ContextDBSourcePreview v-if="originalMode === 'original'" :key="`${reviewDetail.review_id}:${reviewDetail.updated_at || ''}`" :document-id="reviewDetail.document_id" :kb-id="reviewDetail.knowledge_base_id" :title="documentDisplayName(reviewDetail)" />
                <template v-else><p class="section-empty">以下为评审使用的解析文本；原始链接、图片及排版请在原件中核对。</p><DocMarkdown :content="reviewDetail.original_content?.text || '暂无解析内容'" :source-name="reviewDetail.document_name" :source-display-name="documentDisplayName(reviewDetail)" /><t-pagination v-if="reviewDetail.original_content?.total_pages > 1" size="small" :total="reviewDetail.original_content.total_pages" :page-size="1" :current="contentPage" :show-page-size="false" :disabled="reviewActing || editing" @current-change="loadReviewPage" /></template>
              </div></section>
              <section class="comparison-column"><h5>重写建议</h5><div class="comparison-body">
                <h6>重写后评分</h6><div class="inline-scores"><span>逻辑度 {{ score(reviewDetail.logic_score) }}</span><span>噪音度 {{ score(reviewDetail.noise_score) }}</span><span>自矛盾度 {{ score(reviewDetail.contradiction_score) }}</span></div>
                <div class="content-label"><h6>文件内容</h6><t-button v-if="canReviewAction(reviewDetail, 'accept_rewrite')" size="small" variant="text" :loading="reviewActing" @click="showRewriteEditor ? showRewriteEditor = false : startEditing()">{{ showRewriteEditor ? '预览' : '编辑' }}</t-button></div>
                <t-textarea v-if="showRewriteEditor && canReviewAction(reviewDetail, 'accept_rewrite')" v-model="editedContent" :autosize="{ minRows: 12, maxRows: 40 }" :disabled="reviewActing" aria-label="重写文件内容" />
                <DocMarkdown v-else :content="(editing ? editedContent : reviewDetail.rewritten_content) || '暂无重写建议'" :source-name="reviewDetail.document_name" :source-display-name="documentDisplayName(reviewDetail)" />
                <ContextDBSourceResources :key="`${reviewDetail.review_id}:${reviewDetail.updated_at || ''}`" :document-ids="[reviewDetail.document_id]" :kb-id="reviewDetail.knowledge_base_id" />
                <h6>重写原因</h6><p>{{ reviewDetail.rewrite_reason || '—' }}</p><h6>信息完整性校验</h6><StructuredFields v-if="Object.keys(rewriteInfo).length" :model-value="rewriteInfo" readonly /><p v-else class="section-empty">暂无校验结果</p>
              </div></section>
            </div></section>
            <t-alert v-if="reviewStatusError" theme="warning" :message="reviewStatusError" /><t-alert v-if="reviewDocument?.ingest_error_message" theme="error" :message="reviewDocument.ingest_error_message" />
          </template>
        </div>
        <footer v-if="reviewDetail && canReviewAction(reviewDetail, activeState === 'pending_human' ? 'confirm' : activeState === 'failed' ? 'retry_review' : 'retract')" class="review-detail-footer"><template v-if="activeState === 'pending_human'"><t-button :loading="reviewActing" @click="actReview('confirm')">原样入库</t-button><t-button variant="outline" :loading="reviewActing" :disabled="!editing && !reviewDetail.rewritten_content" @click="actReview('accept_rewrite')">采纳重写</t-button><t-button theme="danger" variant="outline" :loading="reviewActing" @click="actReview('reject')">拒绝</t-button></template><t-button v-else-if="activeState === 'failed'" :loading="reviewActing" @click="actReview('retry_review')">重新评审</t-button><t-button v-else-if="['approved', 'auto_accepted'].includes(activeState)" theme="warning" variant="outline" :loading="reviewActing" @click="actReview('retract')">撤回</t-button></footer>
      </section>
    </div>
    <div v-else class="review-no-records"><t-loading v-if="reviewLoading || contextLoading" text="加载中" /><span v-else-if="!listError">暂无评审记录</span></div>
    <div class="review-page-pagination"><label>每页显示 <t-select v-model="reviewPageSize" :options="[{value:10,label:'10'}]" :disabled="editing || reviewActing || reviewBatchActing" aria-label="每页显示" /></label><span>共 {{ reviewTotal }} 条评审记录</span><span class="toolbar-spacer" /><t-pagination theme="simple" size="small" :total="reviewTotal" :current="reviewPage" :page-size="reviewPageSize" :show-page-size="false" :total-content="false" :show-jumper="false" @current-change="changePage" /></div>
    <t-dialog :visible="!!rejectTarget" header="拒绝" :confirm-btn="{ content: '确定', theme: 'danger' }" cancel-btn="取消" @update:visible="(value: boolean) => { if (!value) rejectTarget = '' }" @confirm="confirmReject"><p>确定要拒绝该文件入库吗？</p></t-dialog>
  </div>
</template>

<style scoped lang="less">
.knowledge-review-page{font-family:var(--app-font-family);font-size:var(--app-text-base);height:100%;min-height:0;display:flex;flex-direction:column;gap:16px;padding:0 36px;box-sizing:border-box;color:var(--td-text-color-primary)}
.review-page-header{margin:0 -36px;padding:20px 36px;min-height:104px;box-sizing:border-box;background:var(--td-bg-color-container)}.review-page-header h2{margin:0 0 12px;font-size:var(--app-text-4xl);font-weight:600;line-height:32px}.review-page-header p{margin:0;color:var(--td-text-color-secondary);font-size:var(--app-text-md);line-height:22px}
.review-scope-bar,.review-filter-bar{display:flex;align-items:center;gap:12px;flex:none}.review-scope-bar label,.review-filter-bar label{display:flex;align-items:center;gap:8px;white-space:nowrap;font-size:var(--app-text-base)}.scope-select{width:220px}.base-select{width:300px}.review-filter-bar :deep(.t-select__wrap){width:160px}.toolbar-spacer{flex:1}.review-explanation{flex:none;border-radius:var(--app-radius-md);overflow:hidden}.review-explanation :deep(.t-collapse-panel__header){padding:12px 16px;min-height:44px;background:var(--td-bg-color-secondarycontainer);font-size:var(--app-text-base)}.review-explanation p{font-size:var(--app-text-md);line-height:1.8;margin:0 0 12px}.review-workspace{display:flex;flex:1;min-height:0;border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-md);overflow:hidden}
.review-list,.review-detail-panel{background:var(--td-bg-color-container);display:flex;flex-direction:column;min-height:0}.review-list{border-right:1px solid var(--td-component-stroke);width:30%;min-width:300px;flex:none}.review-list-heading,.review-detail-heading{height:56px;box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:1px solid var(--td-component-stroke);flex:none}.review-detail-heading h3{margin:0;font-size:var(--app-text-3xl);font-weight:600}.review-list-scroll{flex:1;min-height:0;overflow:auto;padding:12px}.review-list-card{padding:16px;margin-bottom:12px;border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-sm);cursor:pointer;background:var(--td-bg-color-container);outline-offset:2px}.review-list-card:last-child{margin-bottom:0}.review-list-card.selected{border-color:var(--app-selection-border);background:var(--app-selection-bg);color:var(--app-selection-text)}.review-list-card:focus-visible{outline:2px solid var(--td-brand-color)}.review-card-title{display:flex;align-items:flex-start;gap:8px;margin-bottom:14px}.review-card-title strong{font-size:var(--app-text-base);font-weight:500;line-height:22px;overflow-wrap:anywhere;flex:1;min-width:0}.review-card-title :deep(.t-tag){flex:none}.review-card-meta{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;font-size:var(--app-text-sm);line-height:20px;color:var(--td-text-color-secondary)}.review-card-meta b{font-weight:500;color:var(--td-brand-color)}.review-list-pagination{padding:12px;border-top:1px solid var(--td-component-stroke);box-sizing:border-box}.review-list-pagination :deep(.t-pagination__total){margin:0 8px 0 0;font-size:var(--app-text-sm)}.review-list-pagination :deep(.t-pagination__btn){min-width:24px;width:24px}.review-empty{display:flex;flex:1;min-height:160px;align-items:center;justify-content:center;padding:24px}.review-detail-panel{flex:1;min-width:0}.review-detail-scroll{flex:1;min-height:0;overflow:auto;padding:20px 24px}.review-detail-scroll>.t-alert{margin-bottom:16px}.review-metadata{display:grid;grid-template-columns:100px minmax(0,1fr) 100px minmax(0,1fr);column-gap:12px;row-gap:16px;font-size:var(--app-text-base);line-height:22px;margin:0 0 24px}.review-metadata dt{color:var(--td-text-color-secondary)}.review-metadata dd{margin:0;overflow-wrap:anywhere}.review-section{margin-top:24px}.review-section h4{margin:0 0 16px;font-size:var(--app-text-xl);font-weight:600;line-height:24px}.review-section p,.review-section li{font-size:var(--app-text-base);line-height:1.7}.review-section p{margin:8px 0}.section-empty{color:var(--td-text-color-placeholder)}
.quality-score-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.quality-score-card{background:var(--td-bg-color-secondarycontainer);box-shadow:none}.quality-score-card :deep(.t-card__body){padding:16px;text-align:left}.quality-score-card span{display:block;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}.quality-score-card strong{display:block;margin:8px 0 0;font-size:var(--app-text-3xl);font-weight:600;line-height:24px;color:var(--td-brand-color)}.conflict-record{border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-sm);padding:12px;margin-bottom:12px}.conflict-record>.t-select__wrap{margin-top:12px;max-width:240px}.review-comparison{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.comparison-column{border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-sm);overflow:hidden}.comparison-column h5{margin:0;padding:12px 16px;background:var(--td-bg-color-secondarycontainer);border-bottom:1px solid var(--td-component-stroke);font-size:var(--app-text-xl);font-weight:600}.comparison-body{padding:16px;overflow-wrap:anywhere}.comparison-body h6{margin:20px 0 12px;font-size:var(--app-text-base);font-weight:500}.comparison-body>h6:first-child{margin-top:0}.inline-scores{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}.comparison-body :deep(.doc-markdown-body){font-size:var(--app-text-base);line-height:1.8}.comparison-body :deep(textarea){font-size:var(--app-text-base);line-height:1.8}.content-label{display:flex;align-items:center;justify-content:space-between}.review-detail-footer{flex:none;display:flex;justify-content:flex-end;gap:8px;padding:16px 24px;border-top:1px solid var(--td-component-stroke);background:var(--td-bg-color-container)}.batch-results{padding:12px 16px;border-bottom:1px solid var(--td-component-stroke);max-height:180px;overflow:auto;font-size:var(--app-text-sm);line-height:20px}.batch-results>div+div{margin-top:8px}.batch-results strong,.batch-results span{display:block}.batch-results p{color:var(--td-error-color);margin:2px 0}
.review-no-records{flex:1;display:flex;align-items:center;justify-content:center;min-height:180px;color:var(--td-text-color-placeholder);font-size:var(--app-text-base)}.review-page-pagination{display:flex;align-items:center;gap:24px;flex:none;padding:0 0 20px;color:var(--td-text-color-secondary);font-size:var(--app-text-md)}.review-page-pagination label{display:flex;align-items:center;gap:8px;white-space:nowrap}.review-page-pagination :deep(.t-select__wrap){width:72px}.review-page-pagination :deep(.t-pagination){width:auto}.review-page-pagination :deep(.t-pagination__total){display:none}
@media(max-width:1100px){.knowledge-review-page{padding:20px 20px 0}.review-list{min-width:280px}.review-card-meta{grid-template-columns:1fr}.review-metadata{grid-template-columns:92px minmax(0,1fr)}.quality-score-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.review-comparison{grid-template-columns:1fr}.review-detail-scroll{padding:20px}.review-scope-bar{flex-wrap:wrap}}
@media(max-width:700px){.knowledge-review-page{padding:16px 12px 0}.review-filter-bar{flex-wrap:wrap}.review-filter-bar :deep(.t-select__wrap){width:130px}.review-workspace{flex-direction:column;overflow:auto}.review-list{width:100%;min-height:240px;max-height:350px}.review-detail-panel{min-height:520px;flex:none}.review-detail-scroll{max-height:700px}.review-card-meta{grid-template-columns:1fr 1fr}}
.knowledge-review-page :deep(.t-button.t-size-s){font-size:var(--app-text-md)}
</style>
