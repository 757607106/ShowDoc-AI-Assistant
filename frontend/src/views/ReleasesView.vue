<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/utils/request'
import api from '@/api/backend'
import { useAuthStore } from '@/stores/auth'
import { getSpaces } from '@/api/knowledgeSpaces'
import { stateLabel, spaceName, dateTime } from '@/utils/platformPresentation'

const props = defineProps<{ embedded?: boolean; scope?: string; spaces?: any[] }>()
const emit = defineEmits<{ 'show-task': [taskId: string] }>()
const router = useRouter(), auth = useAuthStore()
const releases = ref<any[]>([]), mappings = ref<any[]>([]), ownSpaces = ref<any[]>([])
const spaces = computed(() => props.spaces ?? ownSpaces.value)
const scope = computed(() => props.scope || undefined)
const error = ref(''), loading = ref(false), detail = ref<any>(null), detailError = ref(''), busy = ref(''), downloading = ref('')
const expanded = ref<string[]>([]), mappingPage = ref(1), mappingTotal = ref(0), mappingLoading = ref(false), mappingError = ref('')
let request = 0, mappingRequest = 0, stopped = false

async function load() {
  const token = ++request, selectedScope = scope.value
  loading.value = true; error.value = ''
  try {
    const data = await api.releases(selectedScope)
    if (stopped || token !== request || selectedScope !== scope.value) return
    releases.value = data.releases || []
    if (detail.value) detail.value = releases.value.find(item => item.id === detail.value.id) || detail.value
  } catch (err: any) { if (!stopped && token === request) error.value = err.message }
  finally { if (!stopped && token === request) loading.value = false }
}

async function loadMappings() {
  const token = ++mappingRequest, selectedScope = scope.value
  mappingLoading.value = true; mappingError.value = ''
  try {
    const sync = await get('/api/kb/sync-mappings', { params: { space_scope: selectedScope, page: mappingPage.value, page_size: 20 } })
    if (stopped || token !== mappingRequest || selectedScope !== scope.value) return
    mappings.value = (sync.mappings || []).map((item: any) => ({ ...item, row_key: `${item.scope}:${item.source_id}:${item.target_mode}` }))
    mappingTotal.value = sync.total ?? mappings.value.length
  } catch (err: any) { if (!stopped && token === mappingRequest) mappingError.value = err.message }
  finally { if (!stopped && token === mappingRequest) mappingLoading.value = false }
}

function refresh() { void load(); if (expanded.value.includes('documents')) void loadMappings() }
function changeMappingPage(page: number) { mappingPage.value = page; void loadMappings() }
function openDetails(release: any) { detail.value = release; detailError.value = '' }
function closeDetails() { detail.value = null; detailError.value = '' }
function showTask(release: any) {
  if (!release.job_id) return
  closeDetails()
  if (props.embedded) emit('show-task', release.job_id)
  else void router.push({ path: '/platform/tasks', query: { task: release.job_id, space: release.scope } })
}

async function activate(releaseId: string) {
  const release = releases.value.find(item => item.id === releaseId), selectedScope = scope.value
  if (busy.value || !auth.hasRole('contributor') || !release || release.active) return
  if (!window.confirm('重新提交此历史快照，可能用旧内容覆盖知识库中的同名文档，且不会撤回之后新增的资料。是否继续？')) return
  busy.value = releaseId; detailError.value = ''
  try {
    await api.activateRelease(releaseId)
    if (!stopped && selectedScope === scope.value) await load()
  } catch (err: any) { if (!stopped && detail.value?.id === releaseId && selectedScope === scope.value) detailError.value = err.message }
  finally { if (!stopped) busy.value = '' }
}

async function download(releaseId: string) {
  if (downloading.value) return
  downloading.value = releaseId; detailError.value = ''
  try { await api.downloadFile(api.releaseDownloadUrl(releaseId), releaseId + '.zip') }
  catch (err: any) { if (!stopped && detail.value?.id === releaseId) detailError.value = err.message }
  finally { if (!stopped) downloading.value = '' }
}

watch(scope, () => {
  request++; mappingRequest++; releases.value = []; mappings.value = []; mappingTotal.value = 0; mappingPage.value = 1
  closeDetails(); mappingError.value = ''; mappingLoading.value = false
  refresh()
}, { immediate: true })
watch(() => expanded.value.includes('documents'), visible => { if (visible) void loadMappings() })
onMounted(async () => {
  if (props.spaces !== undefined) return
  try { const data = await getSpaces(); if (!stopped) ownSpaces.value = data.spaces || [] }
  catch { if (!stopped) ownSpaces.value = [] }
})
onUnmounted(() => { stopped = true; request++; mappingRequest++ })
defineExpose({ refresh })
</script>

<template>
  <section class="release-history" :class="{ 'release-history--standalone': !embedded }">
    <h2 v-if="!embedded">提交记录</h2>
    <div class="snapshot-heading">
      <div><h3>知识库资料快照</h3><p class="hint">每个批次包含该知识库当时全部当前资料；不是本次新增文件清单。</p></div>
      <t-button variant="outline" :loading="loading" @click="refresh"><template #icon><t-icon name="refresh" /></template>刷新历史</t-button>
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-loading :loading="loading">
      <ul class="snapshot-list">
        <li v-for="release in releases" :key="release.id" class="snapshot-row">
          <div><div class="snapshot-title">{{spaceName(release.scope,spaces)}} · {{dateTime(release.created_at)}}</div><p class="hint">{{Array.isArray(release.version_ids) ? release.version_ids.length + ' 份资料的全库快照' : '资料数量未记录'}} · {{release.active ? '当前提交批次' : '历史批次'}}</p></div>
          <t-button variant="text" @click="openDetails(release)">快照详情</t-button>
        </li>
      </ul>
      <t-empty v-if="!releases.length && !loading && !error" description="暂无提交快照" />
    </t-loading>
    <p class="history-limit hint">最近 50 个提交批次 · 当前账号</p>

    <t-collapse v-model="expanded" class="document-status">
      <t-collapse-panel value="documents" header="文档处理状态">
        <div class="document-status-heading"><p class="hint">评审、入库与生成分别推进；快照已提交不代表文档处理完成。</p><t-button variant="outline" :loading="mappingLoading" @click="loadMappings"><template #icon><t-icon name="refresh" /></template>刷新状态</t-button></div>
        <t-alert v-if="mappingError" theme="error" :message="mappingError" />
        <t-table row-key="row_key" :data="mappings" :loading="mappingLoading" :columns="[{colKey:'scope',title:'知识库'},{colKey:'document',title:'文档'},{colKey:'target_mode',title:'处理目标'},{colKey:'review',title:'文档评审'},{colKey:'ingest',title:'文档入库'},{colKey:'derived',title:'生成状态'},{colKey:'error',title:'失败原因'}]">
          <template #scope="{row}">{{spaceName(row.scope,spaces)}}</template>
          <template #document="{row}"><span :title="row.source_id">{{row.official?.name || '名称未获取'}}</span></template>
          <template #target_mode="{row}">{{row.target_mode==='wiki'?'Wiki':'知识图谱'}}</template>
          <template #review="{row}">{{stateLabel(row.official?.lifecycle_state ?? row.official?.review_status,'review')}}</template>
          <template #ingest="{row}">{{stateLabel(row.official?.ingest_status,'ingest')}}</template>
          <template #derived="{row}">{{stateLabel(row.official?.[row.target_mode+'_status'],row.target_mode==='wiki'?'wiki':'graph')}}</template>
          <template #error="{row}">{{row.official_error || row.official?.ingest_error_message || row.official?.wiki_error_message || row.official?.graph_error_message || row.error || '—'}}</template>
        </t-table>
        <t-pagination :total="mappingTotal" :current="mappingPage" :page-size="20" :show-page-size="false" @current-change="changeMappingPage" />
      </t-collapse-panel>
    </t-collapse>

    <t-drawer :visible="!!detail" attach="body" size="min(760px, 100vw)" header="快照详情" :footer="false" :close-btn="true" @close="closeDetails">
      <template v-if="detail">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <h3>{{spaceName(detail.scope,spaces)}} · {{dateTime(detail.created_at)}}</h3>
        <p class="snapshot-scope hint">快照包含该知识库当时全部当前资料；快照状态与正式文档处理状态分别记录。</p>
        <t-descriptions bordered :column="1">
          <t-descriptions-item label="批次编号"><span class="mono">{{detail.id}}</span></t-descriptions-item>
          <t-descriptions-item label="状态">{{detail.active ? '当前提交批次' : '历史批次'}}</t-descriptions-item>
          <t-descriptions-item label="资料数量">{{Array.isArray(detail.version_ids) ? detail.version_ids.length : '未记录'}}</t-descriptions-item>
          <t-descriptions-item v-if="detail.job_id" label="触发任务"><span class="mono">{{detail.job_id}}</span><t-button variant="text" @click="showTask(detail)">查看触发任务</t-button></t-descriptions-item>
        </t-descriptions>
        <div class="snapshot-actions"><t-button variant="outline" :loading="downloading===detail.id" :disabled="!!downloading && downloading!==detail.id" @click="download(detail.id)">下载全库快照包</t-button></div>
        <details v-if="!detail.active && auth.hasRole('contributor')" class="snapshot-advanced">
          <summary>高级操作</summary>
          <t-alert theme="warning" message="重新提交历史快照可能用旧内容覆盖同名文档；不会自动撤回该快照之后新增的资料。" />
          <t-button variant="outline" :loading="busy===detail.id" :disabled="!!busy && busy!==detail.id" @click="activate(detail.id)">重新提交这个历史快照</t-button>
        </details>
      </template>
    </t-drawer>
  </section>
</template>

<style scoped>
.release-history { min-width: 0; }
.release-history--standalone { padding: 24px; background: var(--td-bg-color-container); }
h2,h3,p { margin: 0; }
.release-history--standalone h2 { margin-bottom: 24px; }
h3 { font-size: var(--app-text-lg); font-weight: 600; }
.snapshot-heading,.document-status-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 20px 0 12px; }
.hint { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); line-height: 1.6; }
.snapshot-heading .hint,.snapshot-row .hint { margin-top: 6px; }
.snapshot-list { margin: 0; padding: 0; list-style: none; }
.snapshot-row { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 20px 0; border-bottom: 1px solid var(--td-component-stroke); }
.snapshot-title { font-weight: 500; overflow-wrap: anywhere; }
.history-limit { margin: 16px 0 24px; }
.document-status { border-radius: var(--app-radius-md); }
.document-status-heading { margin-top: 0; }
.snapshot-scope { margin: 12px 0 20px; }
.snapshot-actions { margin-top: 20px; }
.snapshot-advanced { margin-top: 24px; }
.snapshot-advanced summary { margin-bottom: 12px; }
.snapshot-advanced :deep(.t-alert) { margin-bottom: 12px; }
.mono { font-family: ui-monospace, monospace; overflow-wrap: anywhere; }
@media (max-width: 640px) {
  .snapshot-heading,.document-status-heading { align-items: flex-start; flex-wrap: wrap; }
  .snapshot-row { align-items: flex-start; flex-direction: column; gap: 6px; }
}
</style>
