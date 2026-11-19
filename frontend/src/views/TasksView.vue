<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { dateTime, stateLabel, spaceName } from '@/utils/platformPresentation'
import CollectView from './CollectView.vue'
import ReleasesView from './ReleasesView.vue'
import ImportDirectoryLinks from './ImportDirectoryLinks.vue'
import { currentTask, taskFilter, taskSourceName, taskStatusLabel, type MaterialTask, type TaskFilter } from './materialTasks'

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
  if (spaceScope.value && !values.has(spaceScope.value)) values.set(spaceScope.value, '当前资料范围')
  return [...values].map(([value, label]) => ({value, label}))
})
const detailSubmission = computed(() => detail.value?.kind === 'ctxdb_sync' ? detail.value : detail.value?.submission_task)
const detailStage = computed(() => detail.value && currentTask(detail.value))
const detailFailure = computed(() => detailStage.value && taskFilter(detailStage.value) === 'action' ? detailStage.value : null)
const failureReport = computed(() => detailFailure.value?.failure_details?.length || detailFailure.value?.failure_details_error ? detailFailure.value : detail.value)
const detailFailureReason = computed(() => {
  const task = detailFailure.value
  if (!task) return ''
  const firstReason = task.failure_details?.[0]?.error
  if (firstReason) return (task.failed_pages ?? task.failure_details.length) > 1 ? `其中一条失败原因是${firstReason}` : firstReason
  return task.message || '请查看任务日志了解失败原因。'
})
const detailSubmissionDone = computed(() => detailSubmission.value?.status === 'completed')
function stageStatus(status?: string): 'default' | 'process' | 'finish' | 'error' {
  if (status === 'completed') return 'finish'
  if (status && ['failed', 'partial'].includes(status)) return 'error'
  if (status && ['pending', 'running', 'cancelling'].includes(status)) return 'process'
  return 'default'
}
const stage1Status = computed(() => detail.value?.kind === 'ctxdb_sync' ? 'finish' as const : stageStatus(detail.value?.status))
const stage2Status = computed(() => {
  if (!detail.value) return 'default' as const
  if (detailSubmission.value) return stageStatus(detailSubmission.value.status)
  if (detail.value.phase === 'submission_failed') return 'error' as const
  if (detail.value.phase === 'submitted') return 'process' as const
  return 'default' as const
})
const filters: {value: TaskFilter; label: string}[] = [
  {value:'all', label:'全部'}, {value:'active', label:'进行中'}, {value:'action', label:'需处理'}, {value:'done', label:'已结束'},
]
const narrowViewport = window.matchMedia?.('(max-width: 760px)')
const narrowTasks = ref(narrowViewport?.matches ?? false)
function updateTaskLayout(event: MediaQueryListEvent) { narrowTasks.value = event.matches }
narrowViewport?.addEventListener('change', updateTaskLayout)
onUnmounted(() => narrowViewport?.removeEventListener('change', updateTaskLayout))

const taskColumns = [
  {colKey:'source', title:'资料来源', minWidth:190}, {colKey:'scope', title:'所属知识库', minWidth:120},
  {colKey:'status', title:'当前阶段', minWidth:160}, {colKey:'result', title:'处理结果', minWidth:230}, {colKey:'operation', title:'操作', width:150},
]
const narrowTaskColumns = [{colKey:'source', title:'任务'}, {colKey:'operation', title:'操作', width:120}]
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
function duration(seconds = 0) {
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
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
function taskProgressLabel(row: MaterialTask) {
  const task = currentTask(row)
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
  } catch (err: any) { if (!stopped && detailId.value === opened) actionError.value = err.message }
  finally { busy.value = '' }
}
async function downloadTask(row: MaterialTask) {
  const opened = detailId.value
  try { await api.downloadFile(api.taskDownloadUrl(row.task_id), row.task_id + '.zip') }
  catch (err: any) { if (!stopped && detailId.value === opened) actionError.value = err.message }
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
  <t-card title="资料任务" :bordered="false" class="material-workspace">
    <template #actions><t-space><t-button variant="outline" @click="refresh"><template #icon><t-icon name="refresh" /></template>刷新</t-button><t-button v-if="auth.hasRole('contributor')" @click="openAdd"><template #icon><t-icon name="add" /></template>添加资料</t-button></t-space></template>
    <t-alert v-if="error" theme="error" :message="error"><template #operation><t-button size="small" variant="text" @click="refresh">重试</t-button></template></t-alert>
    <t-alert v-if="actionError && !detailId" theme="error" :message="actionError" />
    <div class="workspace-navigation">
      <t-tabs :value="activeView" @change="changeView"><t-tab-panel value="tasks" label="处理任务" /><t-tab-panel value="history" label="提交历史" /></t-tabs>
      <label class="scope-filter"><span>所属知识库</span><t-select :value="spaceScope || ''" clearable filterable placeholder="全部知识库" :options="scopeOptions" aria-label="筛选资料所属知识库" @change="changeScope" /></label>
    </div>
    <template v-if="activeView === 'tasks'">
      <div class="task-toolbar"><t-radio-group :value="filter" variant="default-filled" aria-label="按状态筛选任务" @change="changeFilter"><t-radio-button v-for="item in filters" :key="item.value" :value="item.value">{{item.label}}</t-radio-button></t-radio-group></div>
      <t-table class="task-list-table" row-key="task_id" :data="tasks" :loading="loading && !tasks.length" :row-attributes="rowAttrs" :row-class-name="({row}:any)=>taskFilter(row)==='action'?'task-row-needs-action':''" @row-click="onRowActivate" @keydown.enter="onRowEnter" :columns="narrowTasks ? narrowTaskColumns : taskColumns">
        <template #source="{row}">
          <div class="source-name">{{taskSourceName(row)}}</div>
          <small>{{row.entry_name}} · {{dateTime(row.start_time)}}</small>
          <div v-if="narrowTasks" class="task-source-summary">
            <small :title="row.scope">{{spaceName(row.scope,spaces)}}</small>
            <t-tag size="small" variant="light" :theme="statusTheme(row)">{{statusLabel(row)}}</t-tag>
          </div>
        </template>
        <template #scope="{row}"><span :title="row.scope">{{spaceName(row.scope,spaces)}}</span></template>
        <template #status="{row}"><t-tag size="small" variant="light" :theme="statusTheme(row)">{{statusLabel(row)}}</t-tag></template>
        <template #result="{row}">
          <div v-if="taskProgressLabel(row)" class="result-title">{{taskProgressLabel(row)}}</div>
          <p v-if="currentTask(row).status!=='pending' && currentTask(row).message" class="task-message" :title="currentTask(row).message">{{currentTask(row).message}}</p>
          <small v-if="row.submission_task">采集已完成 · 关联全库资料提交</small>
          <t-progress v-if="taskFilter(row)==='active' && currentTask(row).progress" :percentage="currentTask(row).progress" size="small" :label="false" class="task-progress" />
        </template>
        <template #operation="{row}"><div class="row-operations" @click.stop><t-button size="small" variant="text" @click="openDetails(row.task_id)">{{taskDetailsLabel(row)}}</t-button><template v-if="auth.hasRole('contributor') && row.kind!=='ctxdb_sync'"><t-button v-if="canRetry(row)" size="small" variant="text" :loading="busy===row.task_id" :disabled="!!busy" @click="act(row,'retry')">重试</t-button><t-popconfirm v-if="canCancel(row)" content="确认取消该任务？仅停止后续处理，不撤回已投递文档。" @confirm="act(row,'cancel')"><t-button size="small" variant="text" theme="danger" :disabled="!!busy">取消</t-button></t-popconfirm></template></div></template>
      </t-table>
      <t-empty v-if="!tasks.length && !loading && !error" :description="filter==='all'?'暂无资料任务，请先添加资料':'没有符合条件的任务'"><t-button v-if="filter==='all' && auth.hasRole('contributor')" @click="openAdd">添加资料</t-button></t-empty>
      <div class="task-pagination"><t-pagination :total="total" :current="page" :page-size="pageSize" :page-size-options="[20,50,100]" @current-change="changePage" @page-size-change="changePageSize" /></div>
    </template>
    <ReleasesView v-else ref="releasesRef" embedded :scope="spaceScope" :spaces="spaces" @show-task="showHistoryTask" />
    <t-drawer :visible="adding" attach="body" size="min(860px, 100vw)" header="添加资料" :close-btn="!addingBusy" :close-on-overlay-click="!addingBusy" :close-on-esc-keydown="!addingBusy" @close="closeAdd">
      <CollectView v-if="adding" embedded @created="created" @show-tasks="showTasks" @busy-change="addingBusy=$event" />
      <template #footer><div id="collect-view-drawer-footer" /></template>
    </t-drawer>
    <t-drawer :visible="!!detailId" attach="body" size="min(820px, 100vw)" header="任务详情" :footer="false" :close-btn="true" @close="dismissDetails">
      <t-loading :loading="detailLoading">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <t-alert v-if="actionError" theme="error" :message="actionError" />
        <template v-if="detail">
          <div v-if="detailHistory.length" class="detail-back"><t-button variant="text" size="small" @click="goBackDetail"><t-icon name="chevron-left" />返回上一任务</t-button></div>
          <div class="detail-heading"><h3>{{taskSourceName(detail)}}</h3><t-tag>{{spaceName(detail.scope,spaces)}}</t-tag></div>
          <t-alert v-if="submissionReadError" theme="warning" :message="'提交任务详情暂不可用：'+submissionReadError" />
          <t-alert v-if="detailFailure" theme="warning" :title="taskFailureLabel(detail)" class="task-recovery">
            <template #message>
              <div>{{detailFailureReason}}</div>
              <div v-if="detailFailure.phase==='submission_failed' && detail.submit_available && auth.hasRole('contributor')">补交会将该知识库的全部当前资料加入提交队列。</div>
            </template>
          </t-alert>
          <t-alert v-else-if="detailSubmissionDone" theme="success" title="资料提交完成" message="评审、入库和生成进度以知识库中的状态为准。" />
          <p v-else-if="detailStage?.message" class="detail-message">{{detailStage.message}}</p>
          <t-space v-if="detailSubmissionDone || auth.hasRole('contributor')" break-line class="detail-actions">
            <t-button v-if="detailSubmissionDone" @click="openKnowledgeBase(detail)">查看知识库处理结果</t-button>
            <template v-if="auth.hasRole('contributor')">
              <t-tooltip v-if="detailSubmission && canRetry(detailSubmission)" content="重新提交该知识库的资料快照"><t-button :theme="detailStage?.task_id===detailSubmission.task_id?'primary':'default'" :disabled="!!busy" @click="act(detailSubmission,'retry-sync')">重试资料提交</t-button></t-tooltip>
              <t-tooltip v-if="detail.kind!=='ctxdb_sync' && canRetry(detail)" content="以来源当前内容重新执行，会生成新的任务批次"><t-button :theme="detailStage?.task_id===detail.task_id?'primary':'default'" :disabled="!!busy" @click="act(detail,'retry')">{{detail.entry==='file'?'重新检查':'重试采集'}}</t-button></t-tooltip>
              <t-popconfirm v-if="detail.kind!=='ctxdb_sync' && canCancel(detail)" content="确认取消采集 / 检查？仅停止后续处理，不撤回已投递文档。" @confirm="act(detail,'cancel')"><t-button :disabled="!!busy" variant="outline">取消采集 / 检查</t-button></t-popconfirm>
              <t-popconfirm v-if="detailSubmission && canCancel(detailSubmission)" content="确认取消后续提交？仅停止后续处理，不撤回已投递文档。" @confirm="act(detailSubmission,'cancel')"><t-button :disabled="!!busy" variant="outline">取消后续提交</t-button></t-popconfirm>
              <t-button v-if="detail.submit_available" variant="text" :loading="busy===detail.task_id" :disabled="!!busy" @click="requestSubmit(detail)">补交全库当前资料</t-button>
            </template>
          </t-space>
          <t-alert v-if="failureReport?.failure_details_error" theme="warning" :message="failureReport.failure_details_error" />
          <section v-if="failureReport?.failure_details?.length" class="failure-details">
            <h3>失败条目</h3>
            <t-table row-key="id" :data="failureReport.failure_details" :columns="[{colKey:'title',title:'资料'},{colKey:'error',title:'失败原因'}]" />
            <p v-if="failureReport.failure_details_truncated" class="hint">仅显示前 20 条，其余请查看任务日志或本次采集资料包。</p>
          </section>
          <ImportDirectoryLinks :directories="detail.import_directories" />
          <t-steps class="task-stages" layout="horizontal">
            <t-step-item :title="detail.kind==='ctxdb_sync'?'触发来源':detail.entry==='file'?'文件检查':'网站采集'" :status="stage1Status">
              <template #default><p>{{detail.kind==='ctxdb_sync'?(detail.source_task_id?'由采集任务触发':'独立资料提交'):detail.status==='completed'?(detail.entry==='file'?'检查完成':'采集完成'):stateLabel(detail.status,'task')}}</p><t-button v-if="detail.kind==='ctxdb_sync' && detail.source_task_id" variant="text" size="small" @click="openDetails(detail.source_task_id)">查看触发任务</t-button></template>
            </t-step-item>
            <t-step-item title="资料提交" :status="stage2Status">
              <template #default><p>{{detailSubmission?taskStatusLabel(detailSubmission):detail.phase==='submission_failed'?'自动提交失败':detail.phase==='submitted'?'已排队提交':'未开始'}}</p><small v-if="detailSubmission?.total_pages">已处理 {{detailSubmission.completed_pages || 0}} / {{detailSubmission.total_pages}} 份</small></template>
            </t-step-item>
            <t-step-item title="评审 / 入库 / 生成" status="default">
              <template #default><t-button v-if="!detailSubmissionDone && (detail.kind==='ctxdb_sync' || detail.submission_id)" variant="text" size="small" @click="openKnowledgeBase(detail)">查看知识库</t-button></template>
            </t-step-item>
          </t-steps>
          <t-alert v-if="detail.metrics?.video_references" theme="warning" :message="`${detail.metrics.video_references} 条仅保存视频链接和封面，视频内容尚未采集或解析。`" />
          <t-collapse class="task-extra">
            <t-collapse-panel value="metadata" header="编号、耗时与任务日志">
              <p class="mono">{{detail.task_id}}</p>
              <t-descriptions :column="2"><t-descriptions-item label="等待时长">{{duration(detail.queued_seconds)}}</t-descriptions-item><t-descriptions-item label="处理时长">{{duration(detail.processing_seconds)}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="已处理条数">{{detail.completed_pages}} / {{detail.total_pages}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="失败条数">{{detail.failed_pages}}</t-descriptions-item></t-descriptions>
              <p v-for="(log,index) in detail.logs || []" :key="index" class="log-line"><span>{{log.time}}</span>{{log.message}}</p>
              <template v-if="detail.kind!=='ctxdb_sync' && detailSubmission"><h4>关联提交任务</h4><p class="mono">{{detailSubmission.task_id}}</p><t-button variant="text" size="small" @click="openDetails(detailSubmission.task_id)">展开提交详情和日志</t-button></template>
            </t-collapse-panel>
            <t-collapse-panel value="downloads" header="资料包与提交快照">
              <t-space break-line><t-button v-if="detail.download_available" variant="outline" @click="downloadTask(detail)">下载本次采集资料包</t-button><t-button v-if="detail.submission_id || detail.release_id" variant="text" @click="changeView('history')">查看全库提交历史</t-button></t-space>
            </t-collapse-panel>
          </t-collapse>
        </template>
      </t-loading>
    </t-drawer>
    <t-dialog :visible="!!submitTarget" attach="body" header="确认补交全库当前资料" theme="warning"
      width="min(480px, calc(100vw - 32px))" :confirm-btn="{content:'确认补交'}" :close-on-overlay-click="false"
      :confirm-on-enter="false" @close="closeSubmitConfirmation" @confirm="confirmSubmit">
      <template v-if="submitTarget">
        <p>目标知识库 <strong>{{spaceName(submitTarget.scope,spaces)}}</strong><span v-if="spaceName(submitTarget.scope,spaces)==='名称未获取'">（标识 {{submitTarget.scope}}）</span></p>
        <p>确认后会将该知识库当前全部资料加入提交队列，范围包含本次采集以外的资料。</p>
      </template>
    </t-dialog>
  </t-card>
</template>

<style scoped>
.material-workspace { height: 100%; overflow: auto; }
.material-workspace :deep(.t-card__title) { font-size: var(--app-text-4xl); line-height: 32px; }
.workspace-navigation { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 20px; border-bottom: 1px solid var(--td-component-stroke); }
.workspace-navigation :deep(.t-tabs__nav-container.t-is-top::after) { display: none; }
.workspace-navigation > .t-tabs { flex: 1; min-width: 0; }
.scope-filter { display: flex; align-items: center; gap: 10px; flex: none; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.scope-filter .t-select__wrap { width: 210px; }
.task-toolbar,.task-pagination { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 18px 0; flex-wrap: wrap; }
.task-pagination { margin-bottom: 0; justify-content: flex-end; }
.t-table td small { display: block; line-height: 18px; }
.source-name { font-weight: 500; overflow-wrap: anywhere; }
.result-title { font-weight: 500; }
small,.hint,.log-line span { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.task-message { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); line-height: 18px; margin: 4px 0; overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.task-progress { max-width: 200px; margin-top: 8px; }
.detail-heading { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.detail-heading h3 { margin: 0; font-size: var(--app-text-xl); }
.task-stages { margin: 24px 0; }
.task-stages p { margin: 6px 0; }
.task-stages :deep(.t-steps-item) { flex: 1; }
.row-operations { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.detail-back { margin-bottom: 8px; }
.material-workspace :deep(.t-table tbody tr) { cursor: pointer; }
.material-workspace :deep(.t-table tbody tr:focus-visible) { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
.material-workspace :deep(.task-row-needs-action) { background: color-mix(in srgb, var(--td-error-color) 5%, transparent); }
.detail-message { overflow-wrap: anywhere; }
.task-recovery,.failure-details { overflow-wrap: anywhere; }
.failure-details { margin-bottom: 20px; }
.detail-actions { margin: 4px 0 20px; }
.task-extra { margin-top: 24px; }
.mono { font-family: ui-monospace, monospace; overflow-wrap: anywhere; }
.log-line { overflow-wrap: anywhere; line-height: 1.6; }
.log-line span { display: block; }
:deep(.t-alert) { margin-bottom: 16px; }
@media(max-width:760px) {
  .workspace-navigation { align-items: stretch; flex-direction: column; gap: 12px; padding-bottom: 12px; }
  .scope-filter .t-select__wrap { width: min(230px,65vw); }
  .task-source-summary { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; margin-top: 6px; overflow-wrap: anywhere; }
  .task-list-table .row-operations { flex-direction: column; align-items: flex-start; }
  .task-pagination { align-items: flex-start; flex-direction: column; }
  .task-pagination :deep(.t-pagination) { max-width: 100%; flex-wrap: wrap; }
}
</style>
