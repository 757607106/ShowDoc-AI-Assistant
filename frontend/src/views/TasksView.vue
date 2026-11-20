<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { dateTime, stateLabel, stateTheme, spaceName } from '@/utils/platformPresentation'
import CollectView from './CollectView.vue'
import ReleasesView from './ReleasesView.vue'
import ImportDirectoryLinks from './ImportDirectoryLinks.vue'
import { currentTask, materialErrorLabel, taskFilter, taskSourceName, taskStatusLabel, type MaterialTask, type TaskFilter } from './materialTasks'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const tasks = ref<MaterialTask[]>([]), spaces = ref<any[]>([])
const error = ref(''), actionError = ref(''), loading = ref(false), busy = ref('')
const page = ref(1), pageSize = ref(20), total = ref(0), filter = ref<TaskFilter>('all')
const detail = ref<MaterialTask | null>(null), detailId = ref(''), detailLoading = ref(false), detailError = ref(''), submissionReadError = ref('')
const detailPending = ref(false)
const detailHistory = ref<string[]>([])
const submitTarget = ref<MaterialTask | null>(null)
const addingBusy = ref(false), releasesRef = ref<{refresh: () => void} | null>(null)
const spaceScope = computed(() => typeof route.query.space === 'string' && route.query.space ? route.query.space : undefined)
const activeView = computed(() => route.query.view === 'history' ? 'history' : 'tasks')
const adding = computed(() => route.query.add === '1')
const scopeOptions = computed(() => {
  const values = new Map(spaces.value.map(space => [space.scope, space.name]))
  if (spaceScope.value && !values.has(spaceScope.value)) values.set(spaceScope.value, '当前知识库')
  return [...values].map(([value, label]) => ({value, label}))
})
const detailSubmission = computed(() => detail.value?.kind === 'ctxdb_sync' ? detail.value : detail.value?.submission_task)
const detailStage = computed(() => detail.value && currentTask(detail.value))
const detailFailure = computed(() => detailStage.value && taskFilter(detailStage.value) === 'action' ? detailStage.value : null)
const failureReport = computed(() => detailFailure.value?.failure_details?.length || detailFailure.value?.failure_details_error ? detailFailure.value : detail.value)
const detailFailureReason = computed(() => failureReport.value?.failure_details?.length ? '' : materialErrorLabel(detailFailure.value?.message))
const detailSubmissionDone = computed(() => detailSubmission.value?.status === 'completed')
const submissionStatus = computed(() => detailSubmission.value?.status ??
  (detail.value?.phase === 'submission_failed' ? 'failed' : detail.value?.phase === 'submitted' ? 'pending' : undefined))
const canOpenKnowledgeBase = computed(() => detailSubmissionDone.value || detail.value?.kind === 'ctxdb_sync' || !!detail.value?.submission_id)
const filters: {value: TaskFilter; label: string}[] = [
  {value:'all', label:'全部'}, {value:'active', label:'进行中'}, {value:'action', label:'需处理'}, {value:'done', label:'已结束'},
]
const narrowViewport = window.matchMedia?.('(max-width: 760px)')
const narrowTasks = ref(narrowViewport?.matches ?? false)
function updateTaskLayout(event: MediaQueryListEvent) { narrowTasks.value = event.matches }
narrowViewport?.addEventListener('change', updateTaskLayout)
onUnmounted(() => narrowViewport?.removeEventListener('change', updateTaskLayout))

const taskColumns = [
  {colKey:'source', title:'任务'}, {colKey:'scope', title:'知识库', width:'20%'},
  {colKey:'status', title:'状态', width:'27%'}, {colKey:'operation', title:'操作', width:168},
]
const narrowTaskColumns = [{colKey:'source', title:'任务'}, {colKey:'operation', title:'操作', width:108}]
let requestId = 0, spaceRequest = 0, detailRequest = 0, stopped = false

async function loadSpaces() {
  const request = ++spaceRequest
  try { const result = await getSpaces(); if (!stopped && request === spaceRequest) spaces.value = result.spaces || [] }
  catch { if (!stopped && request === spaceRequest) spaces.value = [] }
}
async function load() {
  const request = ++requestId
  loading.value = true
  try {
    const data = await api.tasks(spaceScope.value, {page:page.value, page_size:pageSize.value, status_group:filter.value})
    if (stopped || request !== requestId) return
    tasks.value = data.tasks || []; total.value = data.total ?? tasks.value.length; error.value = ''
    const lastPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (!tasks.value.length && page.value > lastPage) {
      page.value = lastPage
      if (total.value > 0) await load()
    }
  } catch (err: any) { if (!stopped && request === requestId) error.value = err.message }
  finally { if (request === requestId) loading.value = false }
}
async function openDetails(taskId: string, background = false) {
  const request = ++detailRequest
  if (!background && detailId.value && detailId.value !== taskId) detailHistory.value.push(detailId.value)
  detailId.value = taskId
  detailPending.value = true
  if (!background) { detail.value = null; detailLoading.value = true; actionError.value = '' }
  detailError.value = ''; submissionReadError.value = ''
  try {
    const result: MaterialTask = await api.taskStatus(taskId)
    if (request !== detailRequest || stopped) return
    detail.value = result
    if (result.kind !== 'ctxdb_sync' && result.sync_task_id) {
      try {
        const submission: MaterialTask = await api.taskStatus(result.sync_task_id)
        if (request === detailRequest && !stopped) detail.value = {...result, submission_task:submission}
      } catch (err: any) { if (request === detailRequest && !stopped) submissionReadError.value = err.message }
    }
  } catch (err: any) { if (request === detailRequest && !stopped) detailError.value = err.message }
  finally { if (request === detailRequest) { detailLoading.value = false; detailPending.value = false } }
}
function closeDetails() {
  detailRequest++; detailId.value = ''; detail.value = null; detailLoading.value = false; detailPending.value = false
  submitTarget.value = null
  detailError.value = ''; submissionReadError.value = ''; actionError.value = ''; detailHistory.value = []
}
function goBackDetail() {
  const previous = detailHistory.value.pop()
  if (!previous) return
  detailId.value = ''
  void openDetails(previous)
}
function taskQuery() {
  const query = {...route.query}
  delete query.kb_id; delete query.mode; delete query.url
  return query
}
function dismissDetails() {
  closeDetails()
  if (route.query.task) void router.replace({query:{...route.query, task:undefined}})
}
async function changeScope(value: string | number) {
  await router.replace({query:{...taskQuery(), space:String(value || '') || undefined, task:undefined}})
}
function changeView(value: string | number) {
  closeDetails()
  void router.replace({query:{...route.query, view:String(value), task:undefined}})
}
function openAdd() { void router.replace({query:{...route.query, add:'1'}}) }
function closeAdd() {
  if (!addingBusy.value) void router.replace({query:{...taskQuery(), add:undefined}})
}
function created() { if (activeView.value === 'tasks') void load(); else releasesRef.value?.refresh() }
async function showTasks(receipt: {scope: string; task_id?: string}) {
  if (addingBusy.value) return
  await router.replace({query:{...taskQuery(), view:'tasks', add:undefined, space:receipt.scope || undefined, task:receipt.task_id}})
  page.value = 1; filter.value = 'all'; await load()
  if (receipt.task_id && detailId.value !== receipt.task_id) await openDetails(receipt.task_id)
}
async function showHistoryTask(taskId: string) {
  await router.replace({query:{...route.query, view:'tasks', task:taskId}})
  if (detailId.value !== taskId) await openDetails(taskId)
}
function refresh() {
  if (activeView.value === 'history') releasesRef.value?.refresh()
  else void load()
  if (detailId.value) void openDetails(detailId.value, true)
}
function changePage(value: number) { page.value = value; void load() }
function changePageSize(value: number) { pageSize.value = value; page.value = 1; void load() }
function changeFilter(value: TaskFilter) {
  if (filter.value === value) return
  filter.value = value; page.value = 1; tasks.value = []; total.value = 0; error.value = ''
  void load()
}
function rowAttrs() { return { tabindex: 0 } }
function onRowActivate({ row }: { row: MaterialTask }) { void openDetails(row.task_id) }
function onRowEnter(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.closest('button,a,input,textarea,select')) return
  const tr = target.closest('tr')
  if (!tr?.parentElement) return
  const row = tasks.value[Array.from(tr.parentElement.children).indexOf(tr)]
  if (row) { event.preventDefault(); void openDetails(row.task_id) }
}
function openKnowledgeBase(row: MaterialTask) {
  void router.push({path:`/platform/knowledge-spaces/${encodeURIComponent(row.scope)}`})
}
function taskCountUnit(task: MaterialTask) { return task.kind === 'ctxdb_sync' || task.entry === 'file' ? '份' : '页' }
function taskFailureLabel(row: MaterialTask) {
  const task = currentTask(row)
  if (task.phase === 'submission_failed') return '自动提交失败'
  if (task.status !== 'failed' && task.status !== 'partial') return ''
  const stage = task.kind === 'ctxdb_sync' ? '资料提交' : task.entry === 'file' ? '文件检查' : '采集'
  const failure = task.status === 'partial' ? '部分失败' : '失败'
  return `${stage}${failure}${task.failed_pages ? ` · ${task.failed_pages} ${taskCountUnit(task)}` : ''}`
}
function statusLabel(row: MaterialTask) {
  const task = currentTask(row)
  if (task.status === 'pending') return '等待执行'
  return taskFailureLabel(row) || taskStatusLabel(task)
}
function statusTheme(row: MaterialTask) {
  const group = taskFilter(row)
  if (group === 'action') return 'danger'
  return group === 'done' && currentTask(row).status === 'completed' ? 'success' : 'default'
}
function taskProgressLabel(task: MaterialTask) {
  if (task.total_pages) return `已处理 ${task.completed_pages || 0} / ${task.total_pages} ${taskCountUnit(task)}`
  if (task.completed_pages) return `已处理 ${task.completed_pages} ${taskCountUnit(task)}`
  return ''
}
function taskDetailsLabel(row: MaterialTask) {
  if (taskFilter(row) !== 'action') return '详情'
  const task = currentTask(row)
  if (task.kind !== 'ctxdb_sync' && task.phase !== 'submission_failed' && task.failed_pages) return '查看失败条目'
  return '查看并处理'
}
function canCancel(row: MaterialTask) { return ['pending', 'running', 'cancelling'].includes(row.status) }
function canRetry(row: MaterialTask) { return ['failed', 'cancelled', 'partial'].includes(row.status) }
function requestSubmit(row: MaterialTask) {
  if (!busy.value && auth.hasRole('contributor') && row.submit_available) submitTarget.value = row
}
function closeSubmitConfirmation() { submitTarget.value = null }
async function confirmSubmit() {
  const target = submitTarget.value
  closeSubmitConfirmation()
  if (!target || detailId.value !== target.task_id) return
  if (detail.value?.task_id !== target.task_id || !detail.value.submit_available) {
    actionError.value = '此任务已不能补交，请刷新详情。'
    return
  }
  await act(target, 'submit')
}
async function act(row: MaterialTask, action: 'cancel' | 'retry' | 'submit' | 'retry-sync') {
  if (busy.value || !auth.hasRole('contributor')) return
  const opened = detailId.value
  busy.value = row.task_id; actionError.value = ''
  try {
    let result: any
    if (action === 'cancel') result = await api.cancelTask(row.task_id)
    else if (action === 'retry') result = await api.retryTask(row.task_id)
    else if (action === 'retry-sync') result = await api.retrySubmission(row.scope, row.task_id)
    else { result = await api.submitTask(row.task_id); MessagePlugin.success('该知识库全部当前资料已加入提交队列') }
    await load()
    if (detailId.value === opened && opened) await openDetails(result?.task_id || result?.result?.task_id || opened)
  } catch (err: any) {
    if (!stopped && detailId.value === opened) actionError.value = materialErrorLabel(err.message) || '操作失败，请重试。'
  }
  finally { busy.value = '' }
}
async function downloadTask(row: MaterialTask) {
  const opened = detailId.value
  try { await api.downloadFile(api.taskDownloadUrl(row.task_id), row.task_id + '.zip') }
  catch (err: any) { if (!stopped && detailId.value === opened) actionError.value = materialErrorLabel(err.message) || '暂时无法下载资料包。' }
}

watch(spaceScope, () => { page.value = 1; tasks.value = []; total.value = 0; filter.value = 'all'; closeDetails(); void load(); void loadSpaces() }, {immediate:true})
watch([spaceScope, () => route.query.task], ([, value]) => {
  if (typeof value === 'string' && value) void openDetails(value)
  else if (detailId.value) closeDetails()
}, {immediate:true})
let pollTick = 0
const timer = window.setInterval(() => {
  pollTick++
  if (document.hidden) return
  const active = tasks.value.some(row => taskFilter(row) === 'active')
  const due = active || pollTick % 6 === 0
  const detailActive = !!detail.value && taskFilter(detail.value) === 'active'
  if (activeView.value === 'tasks' && !loading.value && !busy.value && due) void load()
  if (detailId.value && !detailPending.value && !busy.value && (due || detailActive)) void openDetails(detailId.value, true)
}, 4000)
function allowNavigation() {
  if (!addingBusy.value) return true
  MessagePlugin.warning('资料正在提交，请等待完成后再离开')
  return false
}
onBeforeRouteLeave(allowNavigation)
onBeforeRouteUpdate(allowNavigation)
onUnmounted(() => { stopped = true; requestId++; spaceRequest++; closeDetails(); window.clearInterval(timer) })
</script>

<template>
  <t-card :bordered="false" class="material-workspace">
    <template #title><h1 class="workspace-title">资料任务</h1></template>
    <template #actions><t-space><t-button variant="outline" @click="refresh"><template #icon><t-icon name="refresh" /></template>刷新</t-button><t-button v-if="auth.hasRole('contributor')" @click="openAdd"><template #icon><t-icon name="add" /></template>添加资料</t-button></t-space></template>
    <t-alert v-if="activeView === 'tasks' && error" theme="error" :message="materialErrorLabel(error) || '暂时无法加载任务。'"><template #operation><t-button size="small" variant="text" @click="refresh">重试</t-button></template></t-alert>
    <t-alert v-if="actionError && !detailId" theme="error" :message="actionError" />
    <nav class="workspace-navigation" aria-label="资料任务视图">
      <t-button variant="text" :aria-pressed="activeView === 'tasks'" @click="changeView('tasks')">处理任务</t-button>
      <t-button variant="text" :aria-pressed="activeView === 'history'" @click="changeView('history')">提交历史</t-button>
    </nav>
    <div class="task-toolbar">
      <t-radio-group v-if="activeView === 'tasks'" :value="filter" variant="default-filled" role="group" aria-label="按状态筛选任务" @change="changeFilter">
        <t-radio-button v-for="item in filters" :key="item.value" :value="item.value">{{item.label}}</t-radio-button>
      </t-radio-group>
      <label class="scope-filter">
        <span class="scope-filter-label">按知识库筛选</span>
        <t-select :value="spaceScope || ''" clearable filterable placeholder="全部知识库" :options="scopeOptions" @change="changeScope" />
      </label>
    </div>
    <template v-if="activeView === 'tasks'">
      <t-table class="task-list-table" row-key="task_id" :data="tasks" :loading="loading && !tasks.length" :row-attributes="rowAttrs" @row-click="onRowActivate" @keydown.enter="onRowEnter" :columns="narrowTasks ? narrowTaskColumns : taskColumns">
        <template #source="{row}">
          <div class="source-name">{{taskSourceName(row)}}</div>
          <time v-if="row.start_time" :datetime="row.start_time" class="task-meta">{{dateTime(row.start_time)}}</time>
          <template v-if="narrowTasks">
            <span class="task-meta">{{spaceName(row.scope,spaces)}}</span>
            <div class="task-status task-status--narrow">
              <t-tag size="small" variant="light" :theme="statusTheme(row)">{{statusLabel(row)}}</t-tag>
              <span v-if="taskProgressLabel(currentTask(row))" class="task-meta">{{taskProgressLabel(currentTask(row))}}</span>
              <t-progress v-else-if="taskFilter(row)==='active' && currentTask(row).progress" :percentage="currentTask(row).progress" size="small" />
            </div>
          </template>
        </template>
        <template #scope="{row}"><span class="task-library">{{spaceName(row.scope,spaces)}}</span></template>
        <template #status="{row}">
          <div class="task-status">
            <t-tag size="small" variant="light" :theme="statusTheme(row)">{{statusLabel(row)}}</t-tag>
            <span v-if="taskProgressLabel(currentTask(row))" class="task-meta">{{taskProgressLabel(currentTask(row))}}</span>
            <t-progress v-else-if="taskFilter(row)==='active' && currentTask(row).progress" :percentage="currentTask(row).progress" size="small" />
          </div>
        </template>
        <template #operation="{row}">
          <div class="row-operations" @click.stop>
            <t-button size="small" variant="text" :aria-label="`${taskDetailsLabel(row)} · ${taskSourceName(row)}`" @click="openDetails(row.task_id)">{{taskDetailsLabel(row)}}</t-button>
            <t-button v-if="row.kind!=='ctxdb_sync' && row.download_available" size="small" variant="text" :aria-label="`下载资料包 · ${taskSourceName(row)}`" @click="downloadTask(row)">下载资料包</t-button>
            <template v-if="auth.hasRole('contributor') && row.kind!=='ctxdb_sync'">
              <t-button v-if="canRetry(row)" size="small" variant="text" :loading="busy===row.task_id" :disabled="!!busy" @click="act(row,'retry')">重试</t-button>
              <t-popconfirm v-if="canCancel(row)" content="确认取消该任务？已投递的文档会保留。" @confirm="act(row,'cancel')"><t-button size="small" variant="text" theme="danger" :disabled="!!busy">取消</t-button></t-popconfirm>
            </template>
          </div>
        </template>
        <template #empty><t-empty v-if="!loading && !error" :description="filter==='all' ? '暂无资料任务' : '暂无符合条件的任务'" /></template>
      </t-table>
      <div v-if="total" class="task-pagination"><t-pagination :total="total" :current="page" :page-size="pageSize" :page-size-options="[20,50,100]" @current-change="changePage" @page-size-change="changePageSize" /></div>
    </template>
    <ReleasesView v-else ref="releasesRef" embedded :scope="spaceScope" :spaces="spaces" @show-task="showHistoryTask" />
    <t-drawer :visible="adding" attach="body" size="min(860px, 100vw)" header="添加资料" role="dialog" :aria-modal="adding" :aria-hidden="!adding" :inert="!adding" aria-label="添加资料" :close-btn="!addingBusy" :close-on-overlay-click="!addingBusy" :close-on-esc-keydown="!addingBusy" @close="closeAdd">
      <template #close-btn><t-button size="small" variant="text" shape="square" aria-label="关闭添加资料"><t-icon name="close" /></t-button></template>
      <CollectView v-if="adding" embedded @created="created" @show-tasks="showTasks" @busy-change="addingBusy=$event" />
      <template #footer><div id="collect-view-drawer-footer" /></template>
    </t-drawer>
    <t-drawer :visible="!!detailId" attach="body" size="min(820px, 100vw)" header="任务详情" role="dialog" :aria-modal="!!detailId" :aria-hidden="!detailId" :inert="!detailId" aria-label="任务详情" :footer="false" :close-btn="true" @close="dismissDetails">
      <template #close-btn><t-button size="small" variant="text" shape="square" aria-label="关闭任务详情"><t-icon name="close" /></t-button></template>
      <t-loading :loading="detailLoading">
        <t-alert v-if="detailError" theme="error" :message="materialErrorLabel(detailError) || '暂时无法加载任务详情。'">
          <template #operation><t-button size="small" variant="text" @click="openDetails(detailId)">重试</t-button></template>
        </t-alert>
        <t-alert v-if="actionError" theme="error" :message="actionError" />
        <template v-if="detail">
          <div v-if="detailHistory.length" class="detail-back"><t-button variant="text" size="small" @click="goBackDetail"><t-icon name="chevron-left" />返回上一任务</t-button></div>
          <header class="detail-heading">
            <h2>{{taskSourceName(detail)}}</h2>
            <p class="task-meta">{{spaceName(detail.scope,spaces)}}<template v-if="detail.start_time"> · <time :datetime="detail.start_time">{{dateTime(detail.start_time)}}</time></template></p>
          </header>
          <dl class="task-stages" aria-label="处理进度">
            <div v-if="detail.kind!=='ctxdb_sync'">
              <dt>{{detail.entry==='file' ? '文件检查' : '资料采集'}}</dt>
              <dd>
                <t-tag size="small" variant="light" :theme="stateTheme(detail.status)">{{detail.status==='completed' ? '已完成' : stateLabel(detail.status,'task')}}</t-tag>
                <span v-if="taskProgressLabel(detail)" class="task-meta">{{taskProgressLabel(detail)}}</span>
                <span v-if="detail.failed_pages" class="task-meta">{{detail.failed_pages}} {{taskCountUnit(detail)}}失败</span>
              </dd>
            </div>
            <div>
              <dt>资料提交</dt>
              <dd>
                <t-tag size="small" variant="light" :theme="stateTheme(submissionStatus)">{{submissionStatus ? stateLabel(submissionStatus,'upload') : '未开始'}}</t-tag>
                <template v-if="detailSubmission">
                  <span v-if="taskProgressLabel(detailSubmission)" class="task-meta">{{taskProgressLabel(detailSubmission)}}</span>
                  <span v-if="detailSubmission.failed_pages" class="task-meta">{{detailSubmission.failed_pages}} 份失败</span>
                </template>
              </dd>
            </div>
          </dl>
          <t-alert v-if="submissionReadError" theme="warning" message="暂时无法加载提交任务详情。" />
          <t-alert v-if="detailFailureReason" theme="warning" :message="detailFailureReason" />
          <div class="detail-actions">
            <t-button v-if="canOpenKnowledgeBase" :variant="detailSubmissionDone ? 'base' : 'outline'" @click="openKnowledgeBase(detail)">查看知识库</t-button>
            <template v-if="auth.hasRole('contributor')">
              <t-button v-if="detailSubmission && canRetry(detailSubmission)" :theme="detailStage?.task_id===detailSubmission.task_id?'primary':'default'" :disabled="!!busy" @click="act(detailSubmission,'retry-sync')">重试资料提交</t-button>
              <t-button v-if="detail.kind!=='ctxdb_sync' && canRetry(detail)" :theme="detailStage?.task_id===detail.task_id?'primary':'default'" :disabled="!!busy" @click="act(detail,'retry')">{{detail.entry==='file'?'重新检查':'重试采集'}}</t-button>
              <t-popconfirm v-if="detail.kind!=='ctxdb_sync' && canCancel(detail)" content="确认取消该任务？已投递的文档会保留。" @confirm="act(detail,'cancel')"><t-button :disabled="!!busy" variant="outline">{{detail.entry==='file'?'取消检查':'取消采集'}}</t-button></t-popconfirm>
              <t-popconfirm v-if="detailSubmission && canCancel(detailSubmission)" content="确认取消后续提交？已投递的文档会保留。" @confirm="act(detailSubmission,'cancel')"><t-button :disabled="!!busy" variant="outline">取消后续提交</t-button></t-popconfirm>
              <t-button v-if="detail.submit_available" variant="text" :loading="busy===detail.task_id" :disabled="!!busy" @click="requestSubmit(detail)">补交全库当前资料</t-button>
            </template>
          </div>
          <t-alert v-if="failureReport?.failure_details_error && !detailFailureReason" theme="warning"
            :message="failureReport.failure_details?.length ? '失败条目读取不完整。' : '暂时无法读取失败条目。'" />
          <section v-if="failureReport?.failure_details?.length" class="failure-details">
            <h3>失败条目<template v-if="failureReport.failure_details_truncated">（前 {{failureReport.failure_details.length}} 条）</template></h3>
            <t-table row-key="id" :data="failureReport.failure_details" :columns="[{colKey:'title',title:'资料'},{colKey:'error',title:'失败原因'}]">
              <template #title="{row}">{{row.title || '未命名资料'}}</template>
              <template #error="{row}">{{materialErrorLabel(row.error) || '无法读取资料'}}</template>
            </t-table>
          </section>
          <t-alert v-if="detail.metrics?.video_references" theme="warning" :message="`${detail.metrics.video_references} 条仅保存视频链接和封面，视频内容尚未采集或解析。`" />
          <div class="detail-links">
            <ImportDirectoryLinks :directories="detail.import_directories" />
            <t-button v-if="detail.kind==='ctxdb_sync' && detail.source_task_id" variant="text" size="small" @click="openDetails(detail.source_task_id)">查看来源任务</t-button>
            <t-button v-if="detail.kind!=='ctxdb_sync' && detailSubmission" variant="text" size="small" @click="openDetails(detailSubmission.task_id)">查看提交任务</t-button>
            <t-button v-if="detail.download_available" variant="text" size="small" @click="downloadTask(detail)">下载资料包</t-button>
            <t-button v-if="detail.submission_id || detail.release_id" variant="text" size="small" @click="changeView('history')">查看提交历史</t-button>
          </div>
        </template>
      </t-loading>
    </t-drawer>
    <t-dialog :visible="!!submitTarget" attach="body" header="确认补交全库当前资料" theme="warning"
      width="min(480px, calc(100vw - 32px))" :confirm-btn="{content:'确认补交'}" :close-on-overlay-click="false"
      :confirm-on-enter="false" @close="closeSubmitConfirmation" @confirm="confirmSubmit">
      <template v-if="submitTarget">
        <p>将 <strong>{{spaceName(submitTarget.scope,spaces)}}</strong> 的全部当前资料加入提交队列，包含其他来源的资料。</p>
      </template>
    </t-dialog>
  </t-card>
</template>

<style scoped>
.material-workspace { height: 100%; overflow: auto; }
.workspace-title { margin: 0; font-size: var(--app-text-4xl); line-height: 32px; text-wrap: balance; }
.workspace-navigation { display: flex; gap: 8px; border-bottom: 1px solid var(--td-component-stroke); }
.workspace-navigation :deep(.t-button) { height: 44px; border-bottom: 2px solid transparent; border-radius: 0; }
.workspace-navigation :deep(.t-button[aria-pressed='true']) { color: var(--td-brand-color); border-bottom-color: var(--td-brand-color); font-weight: 600; }
.task-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 16px 0; }
.scope-filter { width: min(100%, 210px); margin-inline-start: auto; }
.scope-filter-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.task-pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.source-name { font-weight: 600; }
.source-name,.task-library,.task-meta { overflow-wrap: anywhere; }
.task-meta { display: block; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); font-variant-numeric: tabular-nums; }
.task-status { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.task-status :deep(.t-tag) { height: auto; white-space: normal; overflow-wrap: anywhere; }
.task-status :deep(.t-progress) { width: min(160px, 100%); }
.detail-heading { margin-bottom: 20px; overflow-wrap: anywhere; }
.detail-heading h2 { margin: 0 0 4px; font-size: var(--app-text-xl); text-wrap: balance; }
.detail-heading p { margin: 0; }
.task-stages { margin: 0 0 16px; border-top: 1px solid var(--td-component-stroke); }
.task-stages > div { display: grid; grid-template-columns: 96px minmax(0, 1fr); align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--td-component-stroke); }
.task-stages dt { font-weight: 500; }
.task-stages dd { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; margin: 0; }
.row-operations { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.detail-back { margin-bottom: 8px; }
.task-list-table :deep(tbody tr[tabindex]) { cursor: pointer; }
.task-list-table :deep(tbody tr:focus-visible) { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
.failure-details { margin-bottom: 16px; overflow-wrap: anywhere; }
.failure-details h3 { margin: 0 0 8px; }
.detail-actions,.detail-links { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.detail-actions:not(:empty) { margin-bottom: 16px; }
:deep(.t-alert) { margin-bottom: 16px; }
@media(max-width:760px) {
  .material-workspace :deep(.t-card__header) { flex-wrap: wrap; gap: 8px 12px; }
  .material-workspace :deep(.t-card__header-wrapper) { min-width: max-content; }
  .scope-filter { margin-inline-start: 0; }
  .task-status--narrow { margin-top: 6px; }
  .task-list-table .row-operations { flex-direction: column; align-items: flex-start; }
  .task-pagination :deep(.t-pagination) { max-width: 100%; flex-wrap: wrap; }
}
</style>
