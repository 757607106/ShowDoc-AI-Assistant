<script setup lang="ts">
import KnowledgeOverlay from '../components/KnowledgeOverlay.vue'
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listWikiCompileRuns, controlWikiCompileRuns, getWikiEvent } from '@/api/contextdbWiki'
import { getDocument } from '@/api/contextdb'
import { contextdbDateTime as dateTime } from '@/utils/platformPresentation'
import { documentDisplayName } from '@/utils/contextdbDocumentName'

const props = withDefaults(defineProps<{ kbId: string; canEdit?: boolean }>(), { canEdit: undefined })
const emit = defineEmits<{ 'open-source-doc': [documentId: string] }>()
const auth = useAuthStore()
const editable = computed(() => props.canEdit ?? auth.hasRole('contributor'))
const rows = ref<any[]>([]), summary = ref<Record<string, any>>({}), cursor = ref(''), status = ref('')
const loading = ref(false), busy = ref(false), paused = ref(false), error = ref(''), notice = ref('')
const event = ref<any>(null), eventError = ref('')
type CompileAction = 'pause' | 'resume' | 'recompile_affected' | 'retry_failed'
const confirming = ref<{ action: CompileAction; row?: any } | null>(null)
const actionLabels = { pause: '暂停新编译', resume: '恢复新编译', recompile_affected: '重新编译', retry_failed: '重试失败来源' }
const actionDescription = computed(() => {
  switch (confirming.value?.action) {
    case 'pause': return '暂停后将停止接收新编译，在途任务会继续执行。'
    case 'resume': return '恢复后可接收新编译。暂停期间登记的文件需要单独重新编译。'
    case 'recompile_affected': return `重新编译“${documentDisplayName(confirming.value.row) || '所选来源'}”？完成后可在阅读页核对正式正文。`
    case 'retry_failed': return '重新提交当前知识库中可重试的编译来源。'
    default: return ''
  }
})
const states: Record<string, string> = {
  compiled: '已编译', pending: '等待编译', waiting_budget: '等待重试',
  blocked_oversize: '超过容量限制', revoked: '已撤销',
}
const summaryCards = computed(() => [
  ...Object.entries(states).map(([key, label]) => ({ key, label, value: summary.value[key] ?? summary.value[`${key}_count`] ?? 0 })),
  { key: 'total', label: '来源总数', value: summary.value.total ?? summary.value.total_documents ?? 0 },
])
const retryAvailable = computed(() => Number(summary.value.waiting_budget ?? summary.value.waiting_budget_count ?? 0) > 0)
const eventPending = computed(() => ['PENDING', 'RUNNING'].includes(String(event.value?.status || '').toUpperCase()))
const hasPending = computed(() => rows.value.some(row => row.run_state === 'pending') || Object.entries(summary.value).some(([key, value]) => key.includes('pending') && Number(value) > 0))
let alive = true, active = false, timer: ReturnType<typeof setTimeout> | undefined, request = 0, pollStarted = 0
let nameGeneration = 0
const documentNames = new Map<string, string>(), namesLoading = new Set<string>()
async function resolveNames(kb: string, items: any[]) {
  const generation = nameGeneration
  const pending = items.filter(row => !row.document_display_name && !documentNames.has(row.document_id) && !namesLoading.has(row.document_id))
  for (const row of pending) namesLoading.add(row.document_id)
  for (let offset = 0; offset < pending.length; offset += 4) {
    if (!alive || !active || kb !== props.kbId || generation !== nameGeneration) break
    await Promise.allSettled(pending.slice(offset, offset + 4).map(async row => {
      let name = ''
      try { const data = await getDocument(row.document_id); name = data.data?.file_name || data.data?.name || '' } catch { /* The source remains openable when its name cannot be read. */ }
      if (!alive || kb !== props.kbId || generation !== nameGeneration) return
      documentNames.set(row.document_id, name); namesLoading.delete(row.document_id)
      rows.value = rows.value.map(item => item.document_id === row.document_id ? { ...item, document_display_name: name } : item)
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
    const items = (data.items || []).map(row => ({ ...row, document_display_name: row.document_display_name || documentNames.get(row.document_id) }))
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
async function control(action: CompileAction, row?: any) {
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
function confirmControl() {
  if (!confirming.value) return
  const { action, row } = confirming.value
  confirming.value = null
  void control(action, row)
}
function visibilityChanged() { if (document.visibilityState === 'hidden') stopPolling(); else { pollStarted = Date.now(); schedulePolling() } }
watch(() => props.kbId, () => {
  confirming.value = null
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
    <div class="summary" aria-label="编译统计">
      <t-card v-for="item in summaryCards" :key="item.key" class="summary-card" :bordered="true">
        <strong>{{ item.value }}</strong><span>{{ item.label }}</span>
      </t-card>
    </div>
    <div class="compile-control"><span>新编译入口：{{ paused ? '已暂停' : '已允许' }}</span><t-space v-if="editable" break-line><t-button variant="outline" :loading="busy" @click="confirming={action:paused?'resume':'pause'}">{{ paused ? '恢复新编译' : '暂停新编译' }}</t-button><t-button variant="outline" :disabled="paused || busy || !retryAvailable" @click="confirming={action:'retry_failed'}">重试失败</t-button></t-space></div>
    <p class="hint">这个开关不取消在途任务，也不会自动补跑暂停期间登记的文件。</p>
    <t-alert theme="info" message="文件已编译，不代表所有知识页面已发布。" />
    <t-alert v-if="error" role="alert" theme="error" :message="error"><template #operation><t-button variant="text" @click="refresh">刷新核对</t-button></template></t-alert>
    <t-alert v-if="notice" role="status" theme="info" :message="notice" />
    <t-alert v-if="eventError" theme="warning" :message="eventError" />
    <div class="toolbar"><t-select v-model="status" aria-label="编译状态" :options="[{ value: '', label: '全部状态' }, ...Object.entries(states).map(([value, label]) => ({ value, label }))]" /><t-button variant="text" shape="square" aria-label="刷新进度" :loading="loading" @click="refresh"><t-icon name="refresh" /></t-button></div>
    <t-table row-key="document_id" :data="rows" :loading="loading" :columns="[{ colKey: 'source', title: '编译来源' }, { colKey: 'actions', title: '操作', width:112 }]">
      <template #source="{ row }">
        <button type="button" class="source-name" @click="emit('open-source-doc', row.document_id)">{{ documentDisplayName(row) || row.title || '打开来源文件' }}</button>
        <div class="source-meta">
          <t-tag size="small" variant="light" :theme="row.run_state === 'compiled' ? 'success' : 'default'">{{ states[row.run_state] || '状态待确认' }}</t-tag>
          <span>{{ dateTime(row.updated_at || row.compiled_at || row.last_compiled_at) }}</span>
        </div>
      </template>
      <template #actions="{ row }">
        <t-button v-if="editable" size="small" variant="text" :disabled="paused || busy || ['revoked', 'blocked_oversize'].includes(row.run_state)" @click="confirming={action:'recompile_affected', row}">重新编译</t-button>
      </template>
      <template #empty>{{ status ? '当前状态暂无来源' : '暂无编译来源' }}</template>
    </t-table>
    <KnowledgeOverlay :visible="!!confirming" :header="confirming ? actionLabels[confirming.action] : ''"
      :confirm-btn="{content:confirming ? actionLabels[confirming.action] : '确认'}"
      @update:visible="(value: boolean) => { if(!value) confirming=null }" @confirm="confirmControl">
      <p>{{ actionDescription }}</p>
    </KnowledgeOverlay>
    <t-button v-if="cursor" variant="outline" :loading="loading" @click="load(true)">加载更多来源</t-button>
  </section>
</template>

<style scoped lang="less">
.wiki-compile { display:flex; flex-direction:column; gap:12px; padding:12px 0 24px; overflow:auto; min-height:0; font-family:var(--app-font-family); font-size:var(--app-text-base); }
.summary { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,110px),1fr)); gap:12px; margin-bottom:4px; }
.summary-card { border-radius:var(--app-space-4); box-shadow:none; }.summary-card :deep(.t-card__body){display:flex;flex-direction:column;gap:12px;padding:18px 16px;}
.summary-card strong{font-size:var(--app-text-4xl);line-height:28px;font-weight:600;color:var(--td-text-color-primary)}.summary-card span{color:var(--td-text-color-placeholder);font-size:var(--app-text-sm);line-height:18px}
.compile-control {display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 16px;border:1px solid var(--td-component-stroke);border-radius:var(--app-space-4);background:var(--td-bg-color-secondarycontainer)}
.toolbar { display:flex; align-items:center; gap:10px; }.toolbar :deep(.t-select__wrap){width:144px}.toolbar :deep(.t-button){width:32px;height:32px}
.source-name { border: 0; padding: 0; color: var(--td-brand-color); background: transparent; font: inherit; text-align: start; overflow-wrap: anywhere; cursor: pointer; }
.source-name:hover { text-decoration: underline; }
.source-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin-top: 6px; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.hint { margin:-10px 0 0; color:var(--td-text-color-placeholder); font-size:var(--app-text-sm);line-height:20px; }
.wiki-compile :deep(.t-alert){padding:10px 14px;border-radius:var(--app-radius-lg);font-size:var(--app-text-md)}.wiki-compile :deep(.t-table){border-radius:var(--app-space-4) 16px 0 0;overflow:hidden}.wiki-compile :deep(.t-table th){height:60px;background:var(--td-bg-color-secondarycontainer);font-size:var(--app-text-base);font-weight:400}.wiki-compile :deep(.t-table td){height:80px;font-size:var(--app-text-base)}.wiki-compile :deep(.t-button){font-size:var(--app-text-base)}
@media(max-width:900px){.compile-control{align-items:flex-start;flex-direction:column}}
</style>
