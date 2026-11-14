<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import { getSpaceProgress, retrySpaceTarget, type KnowledgeSpace } from '@/api/knowledgeSpaces'
import { stateLabel, stateTheme } from '@/utils/platformPresentation'

const props = defineProps<{ scope: string }>()
const emit = defineEmits<{ refreshSpace: []; spaceLoaded: [space: KnowledgeSpace] }>()
const auth = useAuthStore()
const data = ref<any>(null), error = ref(''), loading = ref(false), page = ref(1), retrying = ref('')
let requestId = 0
async function load() {
  const request = ++requestId, scope = props.scope
  loading.value = true
  try {
    const result = await getSpaceProgress(scope, page.value)
    if (request !== requestId || scope !== props.scope) return
    data.value = result; error.value = ''; emit('spaceLoaded', result.space)
  } catch (e: any) { if (request === requestId) error.value = e.message }
  finally { if (request === requestId) loading.value = false }
}
async function retry(body: Parameters<typeof retrySpaceTarget>[1], key: string, label = '重试') {
  if (retrying.value) return
  const scope = props.scope
  retrying.value = key
  try {
    await retrySpaceTarget(scope, body)
    if (scope !== props.scope) return
    MessagePlugin.success(`${label}已受理，请继续查看处理状态`)
    emit('refreshSpace'); await load()
  } catch (e: any) { if (scope === props.scope) MessagePlugin.error(e.message) }
  finally { retrying.value = '' }
}
function processingLabel(stage: string, row: any) {
  if (stage === 'ingest') return '重试入库'
  return row.official?.graph_status === 'failed' ? '重试图谱构建' : '构建图谱'
}
function canRetryUpload(job: any, mode: string) {
  if (!['failed', 'partial', 'cancelled'].includes(job.status)) return false
  if (mode === 'graph' && !data.value?.space.graph_enabled) return false
  if (job.params?.target_modes && !job.params.target_modes.includes(mode)) return false
  const target = job.summary?.targets?.[mode]
  return !target || ['failed', 'partial'].includes(target.status) || Number(target.errors?.length ?? target.errors ?? 0) > 0
}
function uploadState(job: any, mode: string) {
  if (job.params?.target_modes && !job.params.target_modes.includes(mode)) return '未选择'
  const target = job.summary?.targets?.[mode]
  return target ? `${stateLabel(target.status, 'upload')} · 已提交 ${target.uploaded ?? 0} / 未变化 ${target.skipped ?? 0}` : '尚无提交结果'
}
const theme = stateTheme
watch(() => props.scope, () => { requestId++; data.value = null; error.value = ''; page.value = 1; void load() }, { immediate: true })
const timer = window.setInterval(() => { if (!loading.value && !retrying.value) void load() }, 10000)
onUnmounted(() => { requestId++; window.clearInterval(timer) })
</script>

<template>
  <div class="space-progress">
    <t-space class="progress-toolbar" break-line><t-button variant="outline" :loading="loading" @click="load">刷新状态</t-button><span>每 10 秒更新</span></t-space>
    <t-alert v-if="error" theme="error" :message="`更新失败，下列为上次结果：${error}`" />
    <h3>最近 20 次提交任务</h3>
    <t-table row-key="task_id" :data="data?.jobs || []" :columns="[{colKey:'task_id',title:'任务编号',width:130},{colKey:'status',title:'提交状态',width:120},{colKey:'wiki',title:'Wiki 资料提交'},{colKey:'graph',title:'图谱资料提交'},{colKey:'actions',title:'操作',width:230}]">
      <template #task_id="{row}"><span :title="row.task_id">{{row.task_id.slice(0,8)}}</span></template>
      <template #status="{row}">{{row.phase === 'submitted' ? '提交完成' : stateLabel(row.status,'upload')}}</template>
      <template #wiki="{row}">{{uploadState(row,'wiki')}}</template><template #graph="{row}">{{uploadState(row,'graph')}}</template>
      <template #actions="{row}"><t-space v-if="auth.hasRole('contributor')" break-line><t-button v-for="mode in (['wiki','graph'] as const)" v-show="canRetryUpload(row,mode)" :key="mode" size="small" variant="text" :disabled="!!retrying" @click="retry({stage:'upload',task_id:row.task_id,target_mode:mode},row.task_id+mode)">{{mode === 'wiki' ? '重试 Wiki 上传' : '重试图谱上传'}}</t-button></t-space><p v-if="row.status==='partial' || row.status==='failed'" class="failure">{{row.message}}</p></template>
    </t-table>
    <section v-for="mode in (['wiki','graph'] as const)" :key="mode" class="target-progress">
      <h3>{{mode==='wiki' ? 'Wiki 处理进度' : '知识图谱处理进度'}}<t-tag v-if="mode==='graph' && data && !data.space.graph_enabled" variant="outline">后续提交已停用</t-tag></h3>
      <t-table row-key="source_id" :data="(data?.mappings || []).filter((row:any)=>row.target_mode===mode)" :columns="[{colKey:'source',title:'文档'},{colKey:'status',title:'最近提交回执',width:130},{colKey:'review',title:'文档评审',width:140},{colKey:'ingest',title:'文档入库',width:140},{colKey:'derived',title:mode==='wiki'?'Wiki 生成':'图谱构建',width:150},{colKey:'actions',title:'操作',width:200}]">
        <template #source="{row}"><div class="source-name" :title="row.source_id">{{row.official?.name || '文档名称未获取'}}</div></template>
        <template #status="{row}"><t-tag :theme="theme(row.status)" variant="light">{{stateLabel(row.status,'ingest')}}</t-tag></template>
        <template #review="{row}">{{stateLabel(row.official?.lifecycle_state ?? row.official?.review_status,'review')}}</template>
        <template #ingest="{row}"><t-tag v-if="row.official?.ingest_status" :theme="theme(row.official.ingest_status)" variant="light">{{stateLabel(row.official.ingest_status,'ingest')}}</t-tag><span v-else>未返回</span></template>
        <template #derived="{row}"><t-tag v-if="row.official?.[mode+'_status']" :theme="theme(row.official[mode+'_status'])" variant="light">{{stateLabel(row.official[mode+'_status'],mode)}}</t-tag><span v-else>未返回</span></template>
        <template #actions="{row}"><t-space v-if="auth.hasRole('contributor')" break-line><t-button v-for="stage in row.retry_stages || []" :key="stage" size="small" variant="text" :disabled="!!retrying || (mode==='graph' && !data.space.graph_enabled)" @click="retry({stage,source_id:row.source_id,target_mode:mode},row.source_id+mode+stage,processingLabel(stage,row))">{{processingLabel(stage,row)}}</t-button></t-space><p class="failure">{{row.official_error || row.official?.ingest_error_message || row.official?.wiki_error_message || row.official?.graph_error_message || row.error}}</p></template>
      </t-table>
    </section>
    <t-pagination :current="page" :total="data?.total || 0" :page-size="50" :show-page-size="false" @current-change="(value:number)=>{page=value;load()}" />
  </div>
</template>

<style scoped>.space-progress{padding:24px;overflow:auto;flex:1;min-height:0}.progress-toolbar{margin-bottom:16px;color:var(--td-text-color-secondary)}h3{display:flex;align-items:center;gap:10px;margin:24px 0 12px;font-size:var(--app-text-lg)}.source-name,.failure{overflow-wrap:anywhere}.failure{color:var(--td-error-color);font-size:var(--app-text-sm);margin:6px 0 0}.hint,small{color:var(--td-text-color-secondary);font-size:var(--app-text-sm)}.target-progress{margin-bottom:24px}</style>
