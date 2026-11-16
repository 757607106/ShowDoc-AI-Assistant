<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { stateLabel, spaceName } from '@/utils/platformPresentation'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const tasks = ref<any[]>([]), error = ref(''), loading = ref(false), busy = ref('')
const detail = ref<any>(null), detailId = ref(''), detailLoading = ref(false), detailError = ref('')
const spaceScope = computed(() => typeof route.query.space === 'string' ? route.query.space : undefined)
const spaces = ref<any[]>([])
async function loadSpaces() { try { spaces.value=(await getSpaces()).spaces || [] } catch { spaces.value=[] } }
let requestId = 0, stopped = false
let detailRequest = 0
async function openDetails(taskId: string) {
  const request = ++detailRequest
  detailId.value = taskId; detail.value = null; detailError.value = ''; detailLoading.value = true
  try {
    const result = await api.taskStatus(taskId)
    if (request === detailRequest) detail.value = result
  } catch (err: any) { if (request === detailRequest) detailError.value = err.message }
  finally { if (request === detailRequest) detailLoading.value = false }
}
function closeDetails() { detailRequest++; detailId.value = ''; detail.value = null; detailLoading.value = false }
function duration(seconds = 0) {
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}
async function load() {
  const request = ++requestId
  loading.value = true
  try {
    const data = await api.tasks(spaceScope.value)
    if (!stopped && request === requestId) { tasks.value = data.tasks || []; error.value = '' }
  } catch (err: any) { if (!stopped && request === requestId) error.value = err.message }
  finally { if (request === requestId) loading.value = false }
}
async function act(taskId: string, action: 'cancel'|'retry'|'submit') {
  if (busy.value) return
  busy.value = taskId; error.value = ''
  try {
    if (action === 'cancel') await api.cancelTask(taskId)
    else if (action === 'retry') await api.retryTask(taskId)
    else { await api.submitTask(taskId); MessagePlugin.success('知识库资料已加入提交队列') }
    await load()
  } catch (err: any) { error.value = err.message }
  finally { busy.value = '' }
}
function openKnowledgeBase(row: any) {
  router.push({path:`/platform/knowledge-spaces/${encodeURIComponent(row.scope)}`})
}
function statusLabel(row: any) {
  if (row.kind === 'ctxdb_sync') return row.phase === 'submitted' ? '提交完成' : stateLabel(row.status, 'upload')
  if (row.phase === 'submission_failed') return '提交失败'
  if (row.phase === 'submitted') return '已排队提交'
  return stateLabel(row.status, 'task')
}
watch(spaceScope, () => { closeDetails(); void load(); void loadSpaces() }, { immediate: true })
const timer = window.setInterval(() => { if (!loading.value && !busy.value) void load() }, 4000)
onUnmounted(() => { stopped = true; requestId++; closeDetails(); window.clearInterval(timer) })
</script>

<template>
  <t-card title="资料任务" :bordered="false">
    <template #actions><t-space><t-button variant="text" @click="load">刷新</t-button><t-button @click="router.push({path:'/platform/collect',query:spaceScope?{space:spaceScope}:{}})">添加资料</t-button></t-space></template>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-space v-if="spaceScope" class="task-filter"><t-tag closable @close="router.push('/platform/tasks')">{{spaceName(spaceScope,spaces)}}</t-tag><t-link @click="openKnowledgeBase({scope:spaceScope})">查看知识库</t-link></t-space>
    <t-table row-key="task_id" :data="tasks" :loading="loading && !tasks.length" :columns="[
      {colKey:'task_id',title:'任务编号',width:120},{colKey:'scope',title:'知识库',ellipsis:true},
      {colKey:'entry_name',title:'来源'},{colKey:'status',title:'状态',width:130},
      {colKey:'progress',title:'任务进度',width:190},{colKey:'timing',title:'耗时',width:150},{colKey:'message',title:'处理信息',ellipsis:true},
      {colKey:'operation',title:'操作',width:280},
    ]">
      <template #task_id="{row}"><span class="mono">{{row.task_id.slice(0,8)}}</span></template>
      <template #scope="{row}"><span :title="row.scope">{{spaceName(row.scope,spaces)}}</span></template>
      <template #status="{row}"><t-tag size="small" :theme="row.phase==='submission_failed'||['failed','partial'].includes(row.status)?'danger':row.status==='completed'?'success':'default'">{{statusLabel(row)}}</t-tag></template>
      <template #progress="{row}"><small>{{row.kind==='ctxdb_sync'?'资料提交':row.entry==='file'?'文件检查':'网站采集'}}</small><t-progress :percentage="row.progress || 0" size="small" /><small v-if="row.kind!=='ctxdb_sync'">已处理 {{row.completed_pages || 0}} / {{row.total_pages || 0}} 条 · 失败 {{row.failed_pages || 0}} 条</small></template>
      <template #timing="{row}"><div>等待 {{duration(row.queued_seconds)}}</div><div>处理 {{duration(row.processing_seconds)}}</div></template>
      <template #operation="{row}"><t-space size="small" break-line>
        <t-button size="small" variant="text" @click="openDetails(row.task_id)">详情</t-button>
        <t-button v-if="auth.hasRole('contributor') && ['pending','running','cancelling'].includes(row.status)" size="small" variant="outline" :disabled="!!busy" @click="act(row.task_id,'cancel')">取消</t-button>
        <t-button v-if="auth.hasRole('contributor') && row.kind!=='ctxdb_sync' && ['failed','cancelled','partial'].includes(row.status)" size="small" variant="outline" :disabled="!!busy" @click="act(row.task_id,'retry')">{{row.entry==='file'?'重新检查':'重试采集'}}</t-button>
        <t-tooltip v-if="auth.hasRole('contributor') && row.submit_available" content="自动提交未完成或历史任务尚未提交时使用；包含该知识库全部当前资料"><t-button size="small" :loading="busy===row.task_id" :disabled="!!busy && busy!==row.task_id" @click="act(row.task_id,'submit')">补交知识库资料</t-button></t-tooltip>
        <t-button v-if="row.kind==='ctxdb_sync' || row.submission_id" size="small" variant="text" @click="openKnowledgeBase(row)">知识库</t-button>
        <t-button v-if="row.download_available" size="small" variant="text" @click="api.downloadFile(api.taskDownloadUrl(row.task_id),row.task_id+'.zip').catch(e=>error=e.message)">下载资料包</t-button>
      </t-space></template>
    </t-table>
    <t-empty v-if="!tasks.length && !loading" description="暂无资料任务，请先添加资料" />
    <t-drawer :visible="!!detailId" size="760px" header="任务详情" :footer="false" :close-btn="true" @close="closeDetails">
      <t-loading :loading="detailLoading">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <template v-if="detail">
          <p class="mono">{{detail.task_id}}</p>
          <t-descriptions bordered :column="2"><t-descriptions-item label="任务状态">{{statusLabel(detail)}}</t-descriptions-item><t-descriptions-item label="知识库">{{spaceName(detail.scope,spaces)}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="已处理条数">{{detail.completed_pages}} / {{detail.total_pages}}</t-descriptions-item><t-descriptions-item v-if="detail.kind!=='ctxdb_sync'" label="失败条数">{{detail.failed_pages}}</t-descriptions-item><t-descriptions-item label="等待时长">{{duration(detail.queued_seconds)}}</t-descriptions-item><t-descriptions-item label="处理时长">{{duration(detail.processing_seconds)}}</t-descriptions-item></t-descriptions>
          <t-alert v-if="detail.metrics?.video_references" theme="warning" :message="`${detail.metrics.video_references} 条仅保存视频链接和封面，视频内容尚未采集或解析。`" />
          <t-alert v-if="detail.failure_details_error" theme="warning" :message="detail.failure_details_error" />
          <h3 v-if="detail.failure_details?.length">失败条目</h3>
          <t-table v-if="detail.failure_details?.length" row-key="id" :data="detail.failure_details" :columns="[{colKey:'title',title:'资料'},{colKey:'error',title:'失败原因'}]" />
          <p v-if="detail.failure_details_truncated">仅显示前 20 条，其余见资料包。</p>
          <h3>任务日志</h3><p v-for="(log,index) in detail.logs || []" :key="index" class="log-line"><span>{{log.time}}</span>{{log.message}}</p>
        </template>
      </t-loading>
    </t-drawer>
  </t-card>
</template>

<style scoped>
.mono { font-family: ui-monospace, monospace; }
.task-filter { margin: 16px 0; }
small,.log-line span { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.log-line { overflow-wrap: anywhere; line-height: 1.6; }
.log-line span { display: block; }
:deep(.t-alert) { margin-bottom: 16px; }
</style>
