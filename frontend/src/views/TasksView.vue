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
import { currentTask, foldTaskRows, taskFilter, taskSourceName, taskStatusLabel, type MaterialTask, type TaskFilter } from './materialTasks'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const tasks = ref<MaterialTask[]>([]), spaces = ref<any[]>([])
const error = ref(''), actionError = ref(''), loading = ref(false), busy = ref('')
const page = ref(1), pageSize = ref(20), total = ref(0), filter = ref<TaskFilter>('all')
const detail = ref<MaterialTask | null>(null), detailId = ref(''), detailLoading = ref(false), detailError = ref(''), submissionReadError = ref('')
const detailPending = ref(false)
const addingBusy = ref(false), releasesRef = ref<{refresh: () => void} | null>(null)
const spaceScope = computed(() => typeof route.query.space === 'string' && route.query.space ? route.query.space : undefined)
const activeView = computed(() => route.query.view === 'history' ? 'history' : 'tasks')
const adding = computed(() => route.query.add === '1')
const taskRows = computed(() => foldTaskRows(tasks.value).filter(task => filter.value === 'all' || taskFilter(task) === filter.value))
const scopeOptions = computed(() => {
  const values = new Map(spaces.value.map(space => [space.scope, space.name]))
  if (spaceScope.value && !values.has(spaceScope.value)) values.set(spaceScope.value, '当前资料范围')
  return [...values].map(([value, label]) => ({value, label}))
})
const detailSubmission = computed(() => detail.value?.kind === 'ctxdb_sync' ? detail.value : detail.value?.submission_task)
const filters: {value: TaskFilter; label: string}[] = [
  {value:'all', label:'全部'}, {value:'active', label:'进行中'}, {value:'action', label:'需处理'}, {value:'done', label:'已结束'},
]
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
    const data = await api.tasks(spaceScope.value, {page:page.value, page_size:pageSize.value})
    if (stopped || request !== requestId) return
    tasks.value = data.tasks || []; total.value = data.total ?? tasks.value.length; error.value = ''
    if (page.value > 1 && !tasks.value.length && total.value > 0) {
      page.value = Math.ceil(total.value / pageSize.value); await load()
    }
  } catch (err: any) { if (!stopped && request === requestId) error.value = err.message }
  finally { if (request === requestId) loading.value = false }
}
async function openDetails(taskId: string, background = false) {
  const request = ++detailRequest
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
  detailError.value = ''; submissionReadError.value = ''; actionError.value = ''
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
function openKnowledgeBase(row: MaterialTask) {
  void router.push({path:`/platform/knowledge-spaces/${encodeURIComponent(row.scope)}`})
}
function statusLabel(row: MaterialTask) { return taskStatusLabel(currentTask(row)) }
function canCancel(row: MaterialTask) { return ['pending', 'running', 'cancelling'].includes(row.status) }
function canRetry(row: MaterialTask) { return ['failed', 'cancelled', 'partial'].includes(row.status) }
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
const timer = window.setInterval(() => {
  if (activeView.value === 'tasks' && !loading.value && !busy.value) void load()
  if (detailId.value && !detailPending.value && !busy.value) void openDetails(detailId.value, true)
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
    <template #description>采集、提交与异常处理</template>
    <template #actions><t-space><t-button variant="outline" @click="refresh"><template #icon><t-icon name="refresh" /></template>刷新</t-button><t-button v-if="auth.hasRole('contributor')" @click="openAdd"><template #icon><t-icon name="add" /></template>添加资料</t-button></t-space></template>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="actionError && !detailId" theme="error" :message="actionError" />
    <div class="workspace-navigation">
      <t-tabs :value="activeView" @change="changeView"><t-tab-panel value="tasks" label="处理任务" /><t-tab-panel value="history" label="提交历史" /></t-tabs>
      <label class="scope-filter"><span>所属知识库</span><t-select :value="spaceScope || ''" clearable filterable placeholder="全部知识库" :options="scopeOptions" aria-label="筛选资料所属知识库" @change="changeScope" /></label>
    </div>
    <template v-if="activeView === 'tasks'">
      <div class="task-toolbar"><t-radio-group v-model="filter" variant="default-filled" aria-label="筛选当前页任务"><t-radio-button v-for="item in filters" :key="item.value" :value="item.value">{{item.label}}</t-radio-button></t-radio-group><span class="hint">当前账号 · 筛选当前页</span></div>
      <t-table row-key="task_id" :data="taskRows" :loading="loading && !tasks.length" :columns="[
        {colKey:'source',title:'资料来源',minWidth:190}, {colKey:'scope',title:'所属知识库',minWidth:120},
        {colKey:'status',title:'当前阶段',minWidth:130}, {colKey:'result',title:'处理结果',minWidth:230}, {colKey:'operation',title:'操作',width:110},
      ]">
        <template #source="{row}"><div class="source-name">{{taskSourceName(row)}}</div><small>{{row.entry_name}} · {{dateTime(row.start_time)}}</small></template>
        <template #scope="{row}"><span :title="row.scope">{{spaceName(row.scope,spaces)}}</span></template>
        <template #status="{row}"><t-tag size="small" variant="light" :theme="taskFilter(row)==='action'?'danger':taskFilter(row)==='done'?'success':'default'">{{statusLabel(row)}}</t-tag></template>
        <template #result="{row}">
          <div class="result-title">{{currentTask(row).kind==='ctxdb_sync'?'资料提交':'已处理'}} {{currentTask(row).completed_pages || 0}} / {{currentTask(row).total_pages || 0}} 份<span v-if="currentTask(row).failed_pages"> · 失败 {{currentTask(row).failed_pages}} 份</span></div>
          <p v-if="currentTask(row).message" class="task-message" :title="currentTask(row).message">{{currentTask(row).message}}</p>
          <small v-if="row.submission_task">采集已完成 · 关联全库资料提交</small>
          <t-progress v-if="taskFilter(row)==='active'" :percentage="currentTask(row).progress || 0" size="small" :label="false" class="task-progress" />
        </template>
        <template #operation="{row}"><t-button size="small" variant="text" @click="openDetails(row.task_id)">{{taskFilter(row)==='action'?'查看并处理':'详情'}}</t-button></template>
      </t-table>
      <t-empty v-if="!taskRows.length && !loading" :description="tasks.length?'当前页没有符合条件的任务':'暂无资料任务，请先添加资料'" />
      <div class="task-pagination"><span class="hint">当前页 {{taskRows.length}} 组 · 共 {{total}} 条执行记录；关联提交在详情展开</span><t-pagination :total="total" :current="page" :page-size="pageSize" :page-size-options="[20,50,100]" :total-content="false" @current-change="changePage" @page-size-change="changePageSize" /></div>
    </template>
    <ReleasesView v-else ref="releasesRef" embedded :scope="spaceScope" :spaces="spaces" @show-task="showHistoryTask" />
    <t-drawer :visible="adding" attach="body" size="min(860px, 100vw)" header="添加资料" :footer="false" :close-btn="!addingBusy" :close-on-overlay-click="!addingBusy" :close-on-esc-keydown="!addingBusy" @close="closeAdd">
      <CollectView v-if="adding" embedded @created="created" @show-tasks="showTasks" @busy-change="addingBusy=$event" />
    </t-drawer>
    <t-drawer :visible="!!detailId" attach="body" size="min(820px, 100vw)" header="任务详情" :footer="false" :close-btn="true" @close="dismissDetails">
      <t-loading :loading="detailLoading">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <t-alert v-if="actionError" theme="error" :message="actionError" />
        <template v-if="detail">
          <div class="detail-heading"><h3>{{taskSourceName(detail)}}</h3><t-tag>{{spaceName(detail.scope,spaces)}}</t-tag></div>
          <ImportDirectoryLinks :directories="detail.import_directories" />
          <div class="task-stages">
            <section><small>{{detail.kind==='ctxdb_sync'?'触发来源':detail.entry==='file'?'文件检查':'网站采集'}}</small><p>{{detail.kind==='ctxdb_sync'?(detail.source_task_id?'由采集任务触发':'独立资料提交'):detail.status==='completed'?(detail.entry==='file'?'检查完成':'采集完成'):stateLabel(detail.status,'task')}}</p><t-button v-if="detail.kind==='ctxdb_sync' && detail.source_task_id" variant="text" size="small" @click="openDetails(detail.source_task_id)">查看触发任务</t-button></section>
            <section><small>资料提交</small><p>{{detailSubmission?taskStatusLabel(detailSubmission):detail.phase==='submission_failed'?'自动提交失败':detail.phase==='submitted'?'已排队提交':'未开始'}}</p><small v-if="detailSubmission">已处理 {{detailSubmission.completed_pages || 0}} / {{detailSubmission.total_pages || 0}} 份</small></section>
            <section><small>评审 / 入库 / 生成</small><p>分别查看正式处理状态</p><t-button v-if="detail.kind==='ctxdb_sync' || detail.submission_id" variant="text" size="small" @click="openKnowledgeBase(detail)">查看正式处理结果</t-button></section>
          </div>
          <t-alert v-if="submissionReadError" theme="warning" :message="'提交任务详情暂不可用：'+submissionReadError" />
          <t-alert v-if="detail.phase==='submission_failed'" theme="warning" message="自动提交尚未成功。补交包含该知识库全部当前资料，不只本次采集内容。" />
          <t-alert v-if="detailSubmission" theme="info" message="提交处理的是该知识库的资料快照；提交完成不代表评审、入库或内容生成完成。取消只停止后续处理，不撤回已投递文档。" />
          <p class="detail-message">{{currentTask(detail).message}}</p>
          <t-space v-if="auth.hasRole('contributor')" break-line class="detail-actions">
            <t-button v-if="detail.kind!=='ctxdb_sync' && canCancel(detail)" :disabled="!!busy" variant="outline" @click="act(detail,'cancel')">取消采集 / 检查</t-button>
            <t-button v-if="detail.kind!=='ctxdb_sync' && canRetry(detail)" :disabled="!!busy" @click="act(detail,'retry')">{{detail.entry==='file'?'重新检查':'重试采集'}}</t-button>
            <t-button v-if="detail.submit_available" :loading="busy===detail.task_id" :disabled="!!busy" @click="act(detail,'submit')">补交全库当前资料</t-button>
            <t-button v-if="detailSubmission && canCancel(detailSubmission)" :disabled="!!busy" variant="outline" @click="act(detailSubmission,'cancel')">取消后续提交</t-button>
            <t-button v-if="detailSubmission && canRetry(detailSubmission)" :disabled="!!busy" @click="act(detailSubmission,'retry-sync')">重试资料提交</t-button>
          </t-space>
          <t-alert v-if="detail.metrics?.video_references" theme="warning" :message="`${detail.metrics.video_references} 条仅保存视频链接和封面，视频内容尚未采集或解析。`" />
          <t-alert v-if="detail.failure_details_error" theme="warning" :message="detail.failure_details_error" />
          <h3 v-if="detail.failure_details?.length">失败条目</h3>
          <t-table v-if="detail.failure_details?.length" row-key="id" :data="detail.failure_details" :columns="[{colKey:'title',title:'资料'},{colKey:'error',title:'失败原因'}]" />
          <p v-if="detail.failure_details_truncated" class="hint">仅显示前 20 条，其余见本次采集资料包。</p>
          <t-collapse class="task-extra">
            <t-collapse-panel value="metadata" header="编号、耗时与任务日志">
              <p class="mono">{{detail.task_id}}</p>
              <t-descriptions :column="2"><t-descriptions-item label="等待时长">{{duration(detail.queued_seconds)}}</t-descriptions-item><t-descriptions-item label="处理时长">{{duration(detail.processing_seconds)}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="已处理条数">{{detail.completed_pages}} / {{detail.total_pages}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="失败条数">{{detail.failed_pages}}</t-descriptions-item></t-descriptions>
              <p v-for="(log,index) in detail.logs || []" :key="index" class="log-line"><span>{{log.time}}</span>{{log.message}}</p>
              <template v-if="detail.kind!=='ctxdb_sync' && detailSubmission"><h4>关联提交任务</h4><p class="mono">{{detailSubmission.task_id}}</p><t-button variant="text" size="small" @click="openDetails(detailSubmission.task_id)">展开提交详情和日志</t-button></template>
            </t-collapse-panel>
            <t-collapse-panel value="downloads" header="资料包与提交快照">
              <t-space break-line><t-button v-if="detail.download_available" variant="outline" @click="downloadTask(detail)">下载本次采集资料包</t-button><t-button v-if="detail.submission_id || detail.release_id" variant="text" @click="changeView('history')">查看全库提交历史</t-button></t-space>
              <p class="hint">采集资料包保存本次来源产物及失败明细；提交快照包保存该批次的全库资料。</p>
            </t-collapse-panel>
          </t-collapse>
        </template>
      </t-loading>
    </t-drawer>
  </t-card>
</template>

<style scoped>
.material-workspace { height: 100%; overflow: auto; }
.material-workspace :deep(.t-card__title) { font-size: var(--app-text-4xl); line-height: 32px; }
.material-workspace :deep(.t-card__description) { font-size: var(--app-text-md); }
.workspace-navigation { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 20px; border-bottom: 1px solid var(--td-component-stroke); }
.workspace-navigation :deep(.t-tabs__nav-container.t-is-top::after) { display: none; }
.workspace-navigation > .t-tabs { flex: 1; min-width: 0; }
.scope-filter { display: flex; align-items: center; gap: 10px; flex: none; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.scope-filter .t-select__wrap { width: 210px; }
.task-toolbar,.task-pagination { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 18px 0; flex-wrap: wrap; }
.task-pagination { margin-bottom: 0; }
.t-table td small { display: block; line-height: 18px; }
.source-name { font-weight: 500; overflow-wrap: anywhere; }
.result-title { font-weight: 500; }
small,.hint,.log-line span { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.task-message { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); line-height: 18px; margin: 4px 0; overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.task-progress { max-width: 200px; margin-top: 8px; }
.detail-heading { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.detail-heading h3 { margin: 0; font-size: var(--app-text-xl); }
.task-stages { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 16px; margin: 24px 0; }
.task-stages section { border-top: 2px solid var(--td-component-stroke); padding-top: 12px; }
.task-stages p { margin: 6px 0; }
.detail-message { overflow-wrap: anywhere; }
.detail-actions { margin: 4px 0 20px; }
.task-extra { margin-top: 24px; }
.mono { font-family: ui-monospace, monospace; overflow-wrap: anywhere; }
.log-line { overflow-wrap: anywhere; line-height: 1.6; }
.log-line span { display: block; }
:deep(.t-alert) { margin-bottom: 16px; }
@media(max-width:760px) {
  .workspace-navigation { align-items: stretch; flex-direction: column; gap: 12px; padding-bottom: 12px; }
  .scope-filter .t-select__wrap { width: min(230px,65vw); }
  .task-stages { grid-template-columns: 1fr; }
  .task-pagination { align-items: flex-start; flex-direction: column; }
  .task-pagination :deep(.t-pagination) { max-width: 100%; flex-wrap: wrap; }
}
</style>
