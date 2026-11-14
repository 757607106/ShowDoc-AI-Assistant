<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listWikiCompileRuns, controlWikiCompileRuns, getWikiEvent } from '@/api/contextdbWiki'
import { getDocument } from '@/api/contextdb'
import { dateTime } from '@/utils/platformPresentation'

const props = withDefaults(defineProps<{ kbId: string; canEdit?: boolean }>(), { canEdit: undefined })
const emit = defineEmits<{ 'open-page': [pageId: string]; 'open-source-doc': [documentId: string] }>()
const auth = useAuthStore()
const editable = computed(() => props.canEdit ?? auth.hasRole('contributor'))
const rows = ref<any[]>([]), summary = ref<Record<string, any>>({}), cursor = ref(''), status = ref('')
const loading = ref(false), busy = ref(false), paused = ref(false), error = ref(''), notice = ref('')
const event = ref<any>(null), eventError = ref('')
const states: Record<string, string> = {
  compiled: '已编译', pending: '待编译', blocked_oversize: '文件超出编译限制',
  waiting_budget: '等待预算或计量检查', revoked: '来源已撤回',
}
const summaryLabels: Record<string, string> = {
  total: '来源总数', total_documents: '来源总数', compiled: '已编译', compiled_count: '已编译',
  pending: '待编译', pending_count: '待编译', blocked_oversize: '超出限制',
  waiting_budget: '等待预算检查', revoked: '已撤回',
}
const eventLabels: Record<string, string> = { PENDING: '等待执行', RUNNING: '处理中', SUCCEEDED: '执行成功', FAILED: '执行失败', CANCELLED: '已取消' }
const eventPending = computed(() => ['PENDING', 'RUNNING'].includes(String(event.value?.status || '').toUpperCase()))
const hasPending = computed(() => rows.value.some(row => row.run_state === 'pending') || Object.entries(summary.value).some(([key, value]) => key.includes('pending') && Number(value) > 0))
let alive = true, active = false, timer: ReturnType<typeof setTimeout> | undefined, request = 0, pollStarted = 0
let nameGeneration = 0
const documentNames = new Map<string, string>(), namesLoading = new Set<string>()
async function resolveNames(kb: string, items: any[]) {
  const generation = nameGeneration
  const pending = items.filter(row => !documentNames.has(row.document_id) && !namesLoading.has(row.document_id))
  for (const row of pending) namesLoading.add(row.document_id)
  for (let offset = 0; offset < pending.length; offset += 4) {
    if (!alive || !active || kb !== props.kbId || generation !== nameGeneration) break
    await Promise.allSettled(pending.slice(offset, offset + 4).map(async row => {
      let name = ''
      try { const data = await getDocument(row.document_id); name = data.data?.file_name || data.data?.name || '' } catch { /* The source remains openable when its name cannot be read. */ }
      if (!alive || kb !== props.kbId || generation !== nameGeneration) return
      documentNames.set(row.document_id, name); namesLoading.delete(row.document_id)
      rows.value = rows.value.map(item => item.document_id === row.document_id ? { ...item, document_name: name } : item)
    }))
  }
  if (generation === nameGeneration) for (const row of pending) namesLoading.delete(row.document_id)
}
function stopPolling() { if (timer) clearTimeout(timer); timer = undefined }
function schedulePolling() {
  stopPolling()
  if (!alive || !active || document.visibilityState === 'hidden' || (!eventPending.value && !hasPending.value)) return
  if (Date.now() - pollStarted >= 120000) { notice.value = '自动刷新已暂停，请刷新以查看最新结果。'; return }
  timer = setTimeout(async () => { await checkEvent(); if (alive && active && document.visibilityState !== 'hidden') await load(); }, 4000)
}
async function load(append = false) {
  if (!props.kbId || (append && !cursor.value)) return
  const current = ++request, kb = props.kbId
  loading.value = true; error.value = ''
  try {
    const data = await listWikiCompileRuns(kb, { status: status.value || undefined, limit: 50, cursor: append ? cursor.value : undefined })
    if (!alive || current !== request || kb !== props.kbId) return
    const items = (data.items || []).map(row => ({ ...row, document_name: row.document_name || documentNames.get(row.document_id) }))
    rows.value = append ? [...rows.value, ...items] : items
    cursor.value = data.next_cursor || ''; summary.value = data.summary || {}; paused.value = !!data.wiki_compile_paused
    void resolveNames(kb, items)
  } catch (e: any) { if (alive && current === request) error.value = e.message || '编译记录读取失败' }
  finally { if (alive && current === request) { loading.value = false; schedulePolling() } }
}
async function checkEvent(force = false) {
  const id = event.value?.id, kb = props.kbId
  if (!id || (!force && !eventPending.value)) return
  try {
    const data = await getWikiEvent(id)
    if (!alive || !active || kb !== props.kbId || event.value?.id !== id) return
    event.value = { ...data, id }; eventError.value = ''
    if (String(data.status).toUpperCase() === 'FAILED') eventError.value = '编译操作失败，请核对来源状态后重试。'
  } catch (e: any) {
    if (alive && kb === props.kbId && event.value?.id === id) { eventError.value = e.message || '操作进度读取失败'; event.value = { ...event.value, status: 'UNKNOWN' } }
  }
}
async function refresh() {
  pollStarted = Date.now(); notice.value = ''
  for (const [id, name] of documentNames) if (!name) documentNames.delete(id)
  await checkEvent(true); await load()
}
async function control(action: 'pause' | 'resume' | 'recompile_affected' | 'retry_failed', row?: any) {
  if (!editable.value || busy.value) return
  const kb = props.kbId
  busy.value = true; error.value = ''; eventError.value = ''; notice.value = ''
  try {
    const result = await controlWikiCompileRuns(kb, { action, ...(action === 'recompile_affected' ? { document_id: row.document_id } : {}), ...(action === 'retry_failed' && row?.event_id ? { event_id: row.event_id } : {}) })
    if (!alive || kb !== props.kbId) return
    event.value = result.event_id ? { id: result.event_id, status: 'PENDING' } : null
    notice.value = action === 'pause' ? '已提交暂停新编译，在途任务会继续执行。' : action === 'resume' ? '已提交恢复，暂停期间的积压来源需单独重新编译。' : '已提交编译操作，请核对来源状态和页面正文。'
    pollStarted = Date.now(); await checkEvent(); await load()
  } catch (e: any) { if (alive && kb === props.kbId) error.value = e.message || '编译操作未完成' }
  finally { if (alive && kb === props.kbId) busy.value = false }
}
function visibilityChanged() { if (document.visibilityState === 'hidden') stopPolling(); else { pollStarted = Date.now(); schedulePolling() } }
watch(() => props.kbId, () => {
  request++; stopPolling(); rows.value = []; cursor.value = ''; summary.value = {}; event.value = null; eventError.value = ''; notice.value = ''; busy.value = false
  pollStarted = Date.now(); if (active) void load()
})
watch(status, () => {
  request++; stopPolling(); rows.value = []; cursor.value = ''; summary.value = {}
  pollStarted = Date.now(); if (active) void load()
})
watch(() => props.kbId, () => { nameGeneration++; documentNames.clear(); namesLoading.clear() }, { flush: 'sync' })
onMounted(() => { active = true; pollStarted = Date.now(); document.addEventListener('visibilitychange', visibilityChanged); void load() })
onActivated(() => { active = true; pollStarted = Date.now(); if (!loading.value && !rows.value.length) void load(); else schedulePolling() })
onDeactivated(() => { active = false; request++; loading.value = false; stopPolling() })
onUnmounted(() => { alive = false; active = false; request++; stopPolling(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<template>
  <section class="wiki-compile">
    <div class="toolbar">
      <t-select v-model="status" :options="[{ value: '', label: '全部编译状态' }, ...Object.entries(states).map(([value, label]) => ({ value, label }))]" style="width:220px" />
      <t-button variant="outline" :loading="loading" @click="refresh">刷新</t-button>
      <span class="spacer" />
      <t-tag :theme="paused ? 'warning' : 'success'">{{ paused ? '新编译已暂停' : '自动编译开启' }}</t-tag>
      <t-button v-if="editable" variant="outline" :loading="busy" @click="control(paused ? 'resume' : 'pause')">{{ paused ? '恢复新编译' : '暂停新编译' }}</t-button>
      <t-button v-if="editable" variant="outline" :disabled="paused || busy" @click="control('retry_failed')">重试失败任务</t-button>
    </div>
    <p class="hint">暂停不会取消在途编译；恢复后不会自动补派积压来源。来源编译完成后，请打开相关主题核对正式正文。</p>
    <div v-if="Object.keys(summary).length" class="summary">
      <span v-for="(value, key) in summary" :key="key">{{ summaryLabels[key] || states[key] || key }} <strong>{{ value }}</strong></span>
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="notice" theme="info" :message="notice" />
    <t-alert v-if="eventError" theme="warning" :message="eventError" />
    <details v-if="event" class="event"><summary>最近操作：{{ eventLabels[String(event.status).toUpperCase()] || '进度待确认' }}</summary><span>任务编号：{{ event.id }}</span></details>
    <t-table row-key="document_id" :data="rows" :loading="loading" :columns="[{ colKey: 'source', title: '来源文档' }, { colKey: 'run_state', title: '编译状态' }, { colKey: 'updated_at', title: '更新时间' }, { colKey: 'actions', title: '操作' }]">
      <template #source="{ row }"><t-link @click="emit('open-source-doc', row.document_id)">{{ row.document_name || row.name || row.title || '查看来源文档' }}</t-link></template>
      <template #run_state="{ row }"><t-tag :theme="row.run_state === 'compiled' ? 'success' : 'default'">{{ states[row.run_state] || '状态待确认' }}</t-tag></template>
      <template #updated_at="{ row }">{{ dateTime(row.updated_at || row.compiled_at || row.last_compiled_at) }}</template>
      <template #actions="{ row }">
        <t-space break-line>
          <t-button v-if="row.page_id" variant="text" @click="emit('open-page', row.page_id)">核对主题页</t-button>
          <t-button v-if="editable" variant="text" :disabled="paused || busy || ['revoked', 'blocked_oversize'].includes(row.run_state)" @click="control('recompile_affected', row)">重新编译</t-button>
        </t-space>
      </template>
    </t-table>
    <t-button v-if="cursor" variant="outline" :loading="loading" @click="load(true)">加载更多来源</t-button>
  </section>
</template>

<style scoped lang="less">
.wiki-compile { display:flex; flex-direction:column; gap:16px; padding:24px; overflow:auto; min-height:0; }
.toolbar { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }.spacer { flex:1; }
.hint { margin:0; color:var(--td-text-color-secondary); line-height:1.7; }.summary { display:flex; gap:24px; flex-wrap:wrap; }
.summary span { color:var(--td-text-color-secondary); }.summary strong { margin-left:8px; color:var(--td-text-color-primary); }
.event { color:var(--td-text-color-secondary); font-size:var(--app-text-sm); overflow-wrap:anywhere; }.event summary { cursor:pointer; margin-bottom:8px; }
</style>
