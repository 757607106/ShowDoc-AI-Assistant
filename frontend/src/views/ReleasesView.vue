<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/utils/request'
import api from '@/api/backend'
import { useAuthStore } from '@/stores/auth'
import { getSpaces } from '@/api/knowledgeSpaces'
import { stateLabel, spaceName, dateTime } from '@/utils/platformPresentation'
import { materialErrorLabel } from './materialTasks'

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
function documentIssue(row: any) {
  if (row.official_error) return materialErrorLabel(row.official_error) || '状态暂不可用'
  const reason = row.official?.ingest_error_message || row.official?.wiki_error_message || row.official?.graph_error_message || row.error
  return reason ? materialErrorLabel(reason) || '处理失败' : '—'
}

async function activate(releaseId: string) {
  const release = releases.value.find(item => item.id === releaseId), selectedScope = scope.value
  if (busy.value || !auth.hasRole('contributor') || !release || release.active) return
  if (!window.confirm('重新提交这批资料可能用旧内容覆盖知识库中的同名文档。之后新增的资料会保留。是否继续？')) return
  busy.value = releaseId; detailError.value = ''
  try {
    await api.activateRelease(releaseId)
    if (!stopped && selectedScope === scope.value) await load()
  } catch (err: any) {
    if (!stopped && detail.value?.id === releaseId && selectedScope === scope.value) detailError.value = materialErrorLabel(err.message) || '重新提交失败，请重试。'
  }
  finally { if (!stopped) busy.value = '' }
}

async function download(releaseId: string) {
  if (downloading.value) return
  downloading.value = releaseId; detailError.value = ''
  try { await api.downloadFile(api.releaseDownloadUrl(releaseId), releaseId + '.zip') }
  catch (err: any) { if (!stopped && detail.value?.id === releaseId) detailError.value = materialErrorLabel(err.message) || '暂时无法下载资料包。' }
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
    <header v-if="!embedded" class="snapshot-heading">
      <h2>提交历史</h2>
      <t-button variant="outline" :loading="loading" @click="refresh"><template #icon><t-icon name="refresh" /></template>刷新</t-button>
    </header>
    <t-alert v-if="error" theme="error" :message="materialErrorLabel(error) || '暂时无法加载提交历史。'" />
    <t-loading :loading="loading">
      <ul class="snapshot-list" role="list" aria-label="提交记录">
        <li v-for="release in releases" :key="release.id" class="snapshot-row">
          <div>
            <div class="snapshot-title">{{spaceName(release.scope,spaces)}}<t-tag v-if="release.active" size="small" theme="primary" variant="light">当前提交</t-tag></div>
            <p class="snapshot-meta">
              <time v-if="release.created_at" :datetime="release.created_at">{{dateTime(release.created_at)}}</time>
              <span v-if="Array.isArray(release.version_ids)">{{release.version_ids.length}} 份资料</span>
            </p>
          </div>
          <t-button variant="text" :aria-label="`详情 · ${spaceName(release.scope,spaces)} · ${dateTime(release.created_at)}`" @click="openDetails(release)">详情</t-button>
        </li>
      </ul>
      <t-empty v-if="!releases.length && !loading && !error" description="暂无提交记录" />
    </t-loading>
    <p v-if="releases.length === 50" class="snapshot-meta">最近 50 次提交</p>

    <t-collapse v-model="expanded" class="document-status">
      <t-collapse-panel value="documents" header="文档处理状态">
        <div class="document-status-heading"><t-button variant="outline" :loading="mappingLoading" @click="loadMappings"><template #icon><t-icon name="refresh" /></template>刷新状态</t-button></div>
        <t-alert v-if="mappingError" theme="error" :message="materialErrorLabel(mappingError) || '暂时无法加载文档处理状态。'" />
        <t-table row-key="row_key" :data="mappings" :loading="mappingLoading" :columns="[{colKey:'scope',title:'知识库'},{colKey:'document',title:'文档'},{colKey:'review',title:'评审'},{colKey:'ingest',title:'入库'},{colKey:'derived',title:'生成'},{colKey:'error',title:'问题'}]">
          <template #scope="{row}">{{spaceName(row.scope,spaces)}}</template>
          <template #document="{row}">{{row.official?.name || '名称未获取'}}</template>
          <template #review="{row}">{{stateLabel(row.official?.lifecycle_state ?? row.official?.review_status,'review')}}</template>
          <template #ingest="{row}">{{stateLabel(row.official?.ingest_status,'ingest')}}</template>
          <template #derived="{row}">
            <template v-if="row.target_mode==='wiki'">Wiki · {{stateLabel(row.official?.wiki_status,'wiki')}}</template>
            <template v-else-if="row.target_mode==='graph'">知识图谱 · {{stateLabel(row.official?.graph_status,'graph')}}</template>
            <template v-else>—</template>
          </template>
          <template #error="{row}">{{documentIssue(row)}}</template>
        </t-table>
        <t-pagination :total="mappingTotal" :current="mappingPage" :page-size="20" :show-page-size="false" @current-change="changeMappingPage" />
      </t-collapse-panel>
    </t-collapse>

    <t-drawer :visible="!!detail" attach="body" size="min(760px, 100vw)" header="提交详情" role="dialog" :aria-modal="!!detail" :aria-hidden="!detail" :inert="!detail" aria-label="提交详情" :footer="false" :close-btn="true" @close="closeDetails">
      <template #close-btn><t-button size="small" variant="text" shape="square" aria-label="关闭提交详情"><t-icon name="close" /></t-button></template>
      <template v-if="detail">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <h2 class="snapshot-detail-title">{{spaceName(detail.scope,spaces)}}</h2>
        <p class="snapshot-meta">
          <time v-if="detail.created_at" :datetime="detail.created_at">{{dateTime(detail.created_at)}}</time>
          <span v-if="Array.isArray(detail.version_ids)">{{detail.version_ids.length}} 份资料</span>
        </p>
        <div class="snapshot-actions">
          <t-button variant="outline" :loading="downloading===detail.id" :disabled="!!downloading && downloading!==detail.id" @click="download(detail.id)">下载全库资料包</t-button>
          <t-button v-if="detail.job_id" variant="text" @click="showTask(detail)">查看来源任务</t-button>
          <t-button v-if="!detail.active && auth.hasRole('contributor')" variant="outline" theme="danger" :loading="busy===detail.id" :disabled="!!busy && busy!==detail.id" @click="activate(detail.id)">重新提交</t-button>
        </div>
      </template>
    </t-drawer>
  </section>
</template>

<style scoped>
.release-history { min-width: 0; }
.release-history--standalone { padding: 24px; background: var(--td-bg-color-container); }
h2,p { margin: 0; }
.snapshot-heading,.document-status-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.snapshot-meta { display: flex; flex-wrap: wrap; gap: 0 12px; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); font-variant-numeric: tabular-nums; line-height: 1.6; }
.snapshot-list { margin: 0; padding: 0; list-style: none; }
.snapshot-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--td-component-stroke); }
.snapshot-title { margin-bottom: 4px; font-weight: 600; overflow-wrap: anywhere; }
.snapshot-title :deep(.t-tag) { margin-left: 8px; vertical-align: middle; }
.release-history > .snapshot-meta { margin-top: 8px; }
.document-status { margin-top: 16px; border-radius: var(--app-radius-md); }
.document-status-heading { justify-content: flex-end; }
.document-status :deep(td) { overflow-wrap: anywhere; }
.document-status :deep(.t-pagination) { flex-wrap: wrap; }
.snapshot-detail-title { margin: 12px 0 4px; font-size: var(--app-text-xl); text-wrap: balance; overflow-wrap: anywhere; }
.snapshot-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
@media (max-width: 640px) {
  .snapshot-heading,.document-status-heading { align-items: flex-start; flex-wrap: wrap; }
  .document-status :deep(.t-table__content) { overflow-x: auto; }
  .document-status :deep(table) { min-width: 520px; }
}
</style>
