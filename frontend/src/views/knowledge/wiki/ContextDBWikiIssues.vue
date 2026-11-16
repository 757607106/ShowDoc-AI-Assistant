<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import {
  listWikiIssues, getWikiIssue, actOnWikiIssue, createWikiIssueTask, getWikiIssueTask, getWikiPage,
  type WikiIssue, type WikiIssueDetail, type WikiIssueChoice, type WikiIssueTask,
} from '@/api/contextdbWiki'
import { dateTime } from '@/utils/platformPresentation'

const props = withDefaults(defineProps<{ kbId: string; pageId?: string; canEdit?: boolean }>(), { canEdit: undefined })
const emit = defineEmits<{ 'open-page': [pageId: string]; 'open-source-doc': [documentId: string] }>()
const auth = useAuthStore(), editable = computed(() => props.canEdit ?? auth.hasRole('contributor'))
const rows = ref<WikiIssue[]>([]), cursor = ref(''), total = ref<number | undefined>()
const status = ref(''), severity = ref(''), issueType = ref(''), loading = ref(false), error = ref('')
const drawer = ref(false), detail = ref<WikiIssueDetail | null>(null), detailLoading = ref(false), detailError = ref('')
const choice = ref<WikiIssueChoice>('keep_both'), manualContent = ref(''), note = ref(''), busy = ref(false)
const initialChoice = ref<WikiIssueChoice>('keep_both')
const task = ref<WikiIssueTask | null>(null), taskError = ref(''), notice = ref(''), pageCheck = ref('')
const states: Record<string, string> = { pending: '待处理', queued: '等待处理', applying: '正在处理', resolved: '已解决', ignored: '已忽略', failed: '处理失败', reopened: '已重新打开', review_required: '需人工复核', succeeded: '处理成功', running: '处理中', partial: '部分失败', cancelled: '已取消' }
const types: Record<string, string> = { contradictory_facts: '来源陈述冲突', out_of_date: '内容过时', mixed_entities: '实体混淆', broken_link: '链接失效', merge_conflict: '合并冲突', other: '其他问题' }
const choices: Record<WikiIssueChoice, string> = { use_old: '采用原有陈述', use_new: '采用新增陈述', keep_both: '保留双方适用范围', fix: '按建议修复', manual_edit: '手动填写修订正文', rerun_merge: '重新合并' }
const bodyLabels: Record<string, string> = { old: '原有陈述', new: '新增陈述', old_claim: '原有陈述', new_claim: '新增陈述', old_statement: '原有陈述', new_statement: '新增陈述', description: '问题说明', summary: '问题概述', scope: '适用范围', reason: '原因', claims: '相关陈述' }
const uncertain = computed(() => detail.value?.body?.recheck_uncertain === true)
const choiceOptions = computed(() => Object.entries(choices).filter(([value]) => !uncertain.value || value === 'manual_edit').map(([value, label]) => ({ value, label })))
const evidenceGroups = computed(() => Object.entries(detail.value?.evidence || {}).filter(([, items]) => Array.isArray(items)))
const bodyFields = computed(() => Object.entries(detail.value?.body || {}).filter(([key]) => key !== 'recheck_uncertain'))
const taskPending = computed(() => !!task.value?.event_id && !['succeeded', 'failed', 'partial', 'cancelled', 'canceled'].includes(String(task.value.status || '').toLowerCase()))
const draftDirty = computed(() => !!manualContent.value || !!note.value || choice.value !== initialChoice.value)
const formSignature = computed(() => JSON.stringify([choice.value, manualContent.value, note.value]))
let alive = true, active = false, timer: ReturnType<typeof setTimeout> | undefined, request = 0, detailRequest = 0, pollStarted = 0
let attempt: { fingerprint: string; key: string } | undefined
let acceptedDraft = ''
function permitNavigation() {
  if (busy.value || taskPending.value) { MessagePlugin.warning('问题处理仍在进行，请先核对处理结果'); return false }
  if (draftDirty.value) { MessagePlugin.warning('问题处理草稿已保留，请先提交或明确取消草稿'); return false }
  return true
}
defineExpose({ permitNavigation })
function closeDrawer(value: boolean) { if (value || permitNavigation()) drawer.value = value }
function clearDraft() { choice.value = initialChoice.value; manualContent.value = ''; note.value = '' }
function cancelDraft() { if (!busy.value && !taskPending.value) { clearDraft(); detailError.value = '' } }
function beforeUnload(event: BeforeUnloadEvent) {
  if (draftDirty.value || busy.value || taskPending.value) { event.preventDefault(); event.returnValue = '' }
}
onBeforeRouteLeave(permitNavigation)
onBeforeRouteUpdate((to, from) => to.fullPath === from.fullPath || permitNavigation())
function stopPolling() { if (timer) clearTimeout(timer); timer = undefined }
function schedulePolling() {
  stopPolling()
  if (!alive || !active || !taskPending.value || document.visibilityState === 'hidden') return
  if (Date.now() - pollStarted >= 120000) { notice.value = '处理仍在进行，自动刷新已暂停，可手动查看进度。'; return }
  timer = setTimeout(() => { void checkTask() }, 3000)
}
function scopeText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(scopeText).join('、')
  if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}：${scopeText(item)}`).join('；')
  return String(value)
}
async function load(append = false) {
  if (!props.kbId || (append && !cursor.value)) return
  const current = ++request, kb = props.kbId
  loading.value = true; error.value = ''
  try {
    const data = await listWikiIssues(kb, { page_id: props.pageId || undefined, status: status.value || undefined, severity: severity.value || undefined, issue_type: issueType.value || undefined, limit: 50, cursor: append ? cursor.value : undefined })
    if (!alive || current !== request || kb !== props.kbId) return
    rows.value = append ? [...rows.value, ...(data.items || [])] : data.items || []; cursor.value = data.next_cursor || ''; total.value = data.total
  } catch (e: any) { if (alive && current === request) error.value = e.message || '问题列表读取失败' }
  finally { if (alive && current === request) loading.value = false }
}
async function openIssue(issue: Pick<WikiIssue, 'issue_id'>) {
  const same = detail.value?.issue_id === issue.issue_id
  if (!same && !permitNavigation()) return
  const current = ++detailRequest, kb = props.kbId
  drawer.value = true; if (!same) detail.value = null
  detailError.value = ''; detailLoading.value = true
  if (!same) { initialChoice.value = 'keep_both'; clearDraft() }
  try {
    const data = await getWikiIssue(kb, issue.issue_id)
    if (!alive || current !== detailRequest || kb !== props.kbId) return
    detail.value = data
    if (!same) { initialChoice.value = data.body?.recheck_uncertain ? 'manual_edit' : 'keep_both'; clearDraft() }
    else if (data.body?.recheck_uncertain) choice.value = 'manual_edit'
  } catch (e: any) { if (alive && current === detailRequest) detailError.value = e.message || '问题证据读取失败' }
  finally { if (alive && current === detailRequest) detailLoading.value = false }
}
async function rereadIssue(issueId: string) {
  const kb = props.kbId, current = detailRequest
  const data = await getWikiIssue(kb, issueId)
  if (alive && current === detailRequest && kb === props.kbId && detail.value?.issue_id === issueId) detail.value = data
  return data
}
async function changeStatus(action: 'ignore' | 'reopen') {
  if (!editable.value || !detail.value || busy.value || taskPending.value) return
  const target = detail.value, kb = props.kbId
  busy.value = true; detailError.value = ''; notice.value = ''
  try {
    await actOnWikiIssue(kb, { issue_id: target.issue_id, expected_version: target.version, action, reason: note.value.trim() || undefined })
    if (!alive || kb !== props.kbId) return
    await rereadIssue(target.issue_id); await load(); clearDraft(); notice.value = action === 'ignore' ? '已关闭该问题，主题正文没有改变。' : '已重新打开该问题。'
  } catch (e: any) { if (alive && kb === props.kbId) detailError.value = `${e.message || '处理未完成'}；请重新读取问题证据后再决定。` }
  finally { if (alive && kb === props.kbId) busy.value = false }
}
async function submitTask() {
  if (!editable.value || !detail.value || busy.value || taskPending.value) return
  if (uncertain.value && choice.value !== 'manual_edit') { detailError.value = '当前证据需要人工复核，请手动填写修订正文。'; return }
  if (choice.value === 'manual_edit' && !manualContent.value.trim()) { detailError.value = '请填写修订正文。'; return }
  const target = detail.value, kb = props.kbId
  const item = { issue_id: target.issue_id, expected_version: target.version, choice: choice.value, ...(note.value.trim() ? { note: note.value.trim() } : {}), ...(choice.value === 'manual_edit' ? { manual_content: manualContent.value } : {}) }
  const fingerprint = JSON.stringify({ kb, item })
  if (attempt?.fingerprint !== fingerprint) attempt = { fingerprint, key: crypto.randomUUID() }
  busy.value = true; detailError.value = ''; taskError.value = ''; notice.value = ''; pageCheck.value = ''
  try {
    const result = await createWikiIssueTask(kb, { idempotency_key: attempt.key, items: [item] })
    if (!alive || kb !== props.kbId) return
    task.value = result; acceptedDraft = formSignature.value; pollStarted = Date.now(); notice.value = '处理决定已提交，请等待逐项结果并核对正式正文。'; await checkTask()
  } catch (e: any) { if (alive && kb === props.kbId) detailError.value = `${e.message || '提交结果待确认'}；相同决定重试会使用原请求编号。` }
  finally { if (alive && kb === props.kbId) busy.value = false }
}
async function checkTask() {
  const id = task.value?.event_id, kb = props.kbId
  if (!id) return
  taskError.value = ''
  try {
    const data = await getWikiIssueTask(kb, id)
    if (!alive || !active || kb !== props.kbId || task.value?.event_id !== id) return
    task.value = data
    if (!taskPending.value) {
      await load()
      if (!alive || !active || kb !== props.kbId || task.value?.event_id !== id) return
      for (const item of data.items || []) {
        const issue = await rereadIssue(item.issue_id)
        if (!alive || kb !== props.kbId || task.value?.event_id !== id) return
        if (item.status.toLowerCase() === 'succeeded' && issue.page_id) {
          const page = await getWikiPage(kb, issue.page_id)
          if (!alive || kb !== props.kbId || task.value?.event_id !== id) return
          const revisionMatches = !!item.resolution_revision_id && page.head_revision_id === item.resolution_revision_id
          pageCheck.value = page.published && revisionMatches ? '处理修订已在正式正文可读，请打开主题页核对内容。' : page.published ? '任务已完成，当前正式修订尚未与处理结果核对一致，草稿已保留，请打开主题页核对。' : '当前页面尚无可读的正式正文，请稍后重新核对。'
          if (page.published && revisionMatches && detail.value?.issue_id === item.issue_id && formSignature.value === acceptedDraft) clearDraft()
        }
      }
    }
  } catch (e: any) { if (alive && kb === props.kbId && task.value?.event_id === id) taskError.value = e.message || '处理进度读取失败，请保留任务编号并刷新核对' }
  finally { schedulePolling() }
}
async function refreshTask() { pollStarted = Date.now(); await checkTask() }
function visibilityChanged() { if (document.visibilityState === 'hidden') stopPolling(); else { pollStarted = Date.now(); schedulePolling() } }
watch([() => props.kbId, () => props.pageId], () => {
  request++; detailRequest++; stopPolling(); rows.value = []; cursor.value = ''; total.value = undefined; drawer.value = false; detail.value = null; task.value = null; taskError.value = ''; notice.value = ''; pageCheck.value = ''; busy.value = false; attempt = undefined; acceptedDraft = ''; initialChoice.value = 'keep_both'; clearDraft()
  if (active) void load()
})
watch([status, severity, issueType], () => { rows.value = []; cursor.value = ''; if (active) void load() })
onMounted(() => { active = true; document.addEventListener('visibilitychange', visibilityChanged); window.addEventListener('beforeunload', beforeUnload); void load() })
onActivated(() => { active = true; pollStarted = Date.now(); if (!loading.value) void load(); schedulePolling() })
onDeactivated(() => { active = false; request++; detailRequest++; loading.value = false; detailLoading.value = false; drawer.value = false; stopPolling() })
onUnmounted(() => { alive = false; active = false; request++; detailRequest++; stopPolling(); document.removeEventListener('visibilitychange', visibilityChanged); window.removeEventListener('beforeunload', beforeUnload) })
</script>

<template>
  <section class="wiki-issues">
    <div class="toolbar">
      <t-select v-model="status" style="width:170px" :options="[{ value: '', label: '全部处理状态' }, ...Object.entries(states).filter(([key]) => !['succeeded', 'running', 'partial', 'cancelled'].includes(key)).map(([value, label]) => ({ value, label }))]" />
      <t-select v-model="severity" style="width:150px" :options="[{ value: '', label: '全部严重程度' }, { value: 'high', label: '高' }, { value: 'medium', label: '中' }, { value: 'low', label: '低' }]" />
      <t-select v-model="issueType" style="width:180px" :options="[{ value: '', label: '全部问题类型' }, ...Object.entries(types).map(([value, label]) => ({ value, label }))]" />
      <t-button variant="outline" :loading="loading" @click="load()">刷新</t-button><span v-if="total != null" class="hint">共 {{ total }} 个问题</span>
    </div>
    <p class="hint">先核对双方陈述与来源，再提交处理决定。关闭问题不会修改主题正文；处理任务完成后仍需核对正式正文。</p>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="notice" theme="info" :message="notice" />
    <t-alert v-if="taskError" theme="warning" :message="taskError" />
    <t-alert v-if="pageCheck" theme="info" :message="pageCheck" />
    <div v-if="task" class="task-results">
      <div class="toolbar"><strong>最近处理：{{ states[String(task.status || '').toLowerCase()] || '等待处理' }}</strong><span v-if="task.total_items != null">共 {{ task.total_items }} 项，成功 {{ task.succeeded_items || 0 }} 项，失败 {{ task.failed_items || 0 }} 项</span><t-button size="small" variant="outline" @click="refreshTask">查看最新进度</t-button></div>
      <p v-for="item in task.items" :key="item.issue_id" class="result">{{ states[item.status.toLowerCase()] || '状态待确认' }}<span v-if="item.error_message">：{{ item.error_message }}</span><t-button variant="text" size="small" @click="openIssue({ issue_id: item.issue_id })">查看问题</t-button></p>
      <details><summary>任务诊断信息</summary>任务编号：{{ task.event_id }}</details>
    </div>
    <t-table row-key="issue_id" :data="rows" :loading="loading" :columns="[{ colKey: 'description', title: '问题' }, { colKey: 'issue_type', title: '类型' }, { colKey: 'severity', title: '严重程度' }, { colKey: 'status', title: '状态' }, { colKey: 'updated_at', title: '更新时间' }, { colKey: 'actions', title: '操作' }]">
      <template #description="{ row }"><t-link @click="openIssue(row)">{{ row.title || row.description || types[row.issue_type] || '查看问题证据' }}</t-link></template>
      <template #issue_type="{ row }">{{ types[row.issue_type] || '其他问题' }}</template>
      <template #severity="{ row }">{{ ({ high: '高', medium: '中', low: '低' } as Record<string, string>)[row.severity] || '未返回' }}</template>
      <template #status="{ row }">{{ states[row.status] || '状态待确认' }}</template>
      <template #updated_at="{ row }">{{ dateTime(row.updated_at || row.created_at) }}</template>
      <template #actions="{ row }"><t-space><t-button variant="text" @click="openIssue(row)">核对证据</t-button><t-button v-if="row.page_id" variant="text" @click="emit('open-page', row.page_id)">打开主题页</t-button></t-space></template>
    </t-table>
    <t-button v-if="cursor" variant="outline" :loading="loading" @click="load(true)">加载更多问题</t-button>
    <t-drawer :visible="drawer" header="核对问题与来源" size="min(760px, 94vw)" :footer="false" :close-btn="true" @update:visible="closeDrawer">
      <t-loading :loading="detailLoading" size="small">
        <t-alert v-if="detailError" theme="error" :message="detailError" />
        <div v-if="detail" class="detail">
          <div class="toolbar"><t-tag>{{ states[detail.status] || '状态待确认' }}</t-tag><strong>{{ detail.title || detail.description || types[detail.issue_type || ''] || '内容问题' }}</strong></div>
          <t-alert v-if="uncertain" theme="warning" message="来源复核存在不确定性，只能人工核对后填写修订正文。" />
          <p v-if="detail.recommended_action && choices[detail.recommended_action as WikiIssueChoice]" class="hint">建议：{{ choices[detail.recommended_action as WikiIssueChoice] }}。请结合来源自行判断。</p>
          <div v-for="[side, evidence] in evidenceGroups" :key="side" class="evidence-group">
            <h4>{{ ({ old: '原有陈述与来源', new: '新增陈述与来源', both: '双方来源' } as Record<string, string>)[side] || '来源证据' }}</h4>
            <t-empty v-if="!evidence.length" description="未返回可读证据" />
            <article v-for="(item, index) in evidence" :key="index" class="evidence">
              <blockquote>{{ item.quote || '未返回引用原文' }}</blockquote>
              <p v-if="item.scope" class="hint">适用范围：{{ scopeText(item.scope) }}</p>
              <t-button v-if="item.document_id" variant="text" size="small" @click="emit('open-source-doc', item.document_id)">查看来源文档</t-button>
            </article>
          </div>
          <t-empty v-if="!evidenceGroups.length" description="未返回来源证据，请先打开主题及原文核对" />
          <details v-if="bodyFields.length"><summary>完整问题说明</summary><p v-for="[key, value] in bodyFields" :key="key">{{ bodyLabels[key] || '说明' }}：{{ scopeText(value) }}</p></details>
          <t-form v-if="editable" label-align="top">
            <t-form-item label="处理决定"><t-select v-model="choice" :options="choiceOptions" :disabled="busy || taskPending" /></t-form-item>
            <t-form-item v-if="choice === 'manual_edit'" label="修订正文" required><t-textarea v-model="manualContent" :maxlength="200000" :autosize="{ minRows: 8, maxRows: 18 }" :disabled="busy || taskPending" placeholder="填写核对后的完整修订正文" /></t-form-item>
            <t-form-item label="处理说明"><t-textarea v-model="note" :maxlength="4000" :disabled="busy || taskPending" placeholder="记录依据或适用范围（可选）" /></t-form-item>
            <t-space break-line>
              <t-button :loading="busy" :disabled="taskPending || ['resolved', 'ignored', 'queued', 'applying'].includes(detail.status)" @click="submitTask">提交处理决定</t-button>
              <t-button v-if="['resolved', 'ignored'].includes(detail.status)" variant="outline" :disabled="busy || taskPending" @click="changeStatus('reopen')">重新打开问题</t-button>
              <t-button v-else variant="outline" :disabled="busy || taskPending || ['queued', 'applying'].includes(detail.status)" @click="changeStatus('ignore')">关闭问题，不修改正文</t-button>
              <t-button v-if="draftDirty" variant="text" :disabled="busy || taskPending" @click="cancelDraft">取消处理草稿</t-button>
            </t-space>
          </t-form>
          <t-space><t-button variant="outline" :disabled="busy" @click="openIssue(detail)">重新读取证据</t-button><t-button v-if="detail.page_id" variant="outline" @click="emit('open-page', detail.page_id)">打开主题页核对</t-button></t-space>
        </div>
      </t-loading>
    </t-drawer>
  </section>
</template>

<style scoped lang="less">
.wiki-issues { font-family:var(--app-font-family);font-size:var(--app-text-base); display:flex; flex-direction:column; gap:16px; padding:24px; overflow:auto; min-height:0; }
.toolbar { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }.hint { font-size:var(--app-text-md);color:var(--td-text-color-secondary); line-height:1.7; margin:0; }
.detail h3,.detail h4,.task-results h4{font-weight:600}.detail { display:flex; flex-direction:column; gap:20px; }.evidence-group h4 { font-size:var(--app-text-xl);font-weight:600;margin:0 0 12px; }.evidence { padding:12px 16px; background:var(--td-bg-color-secondarycontainer); border-radius:var(--app-radius-md); margin-bottom:8px; }
blockquote { margin:0 0 8px; white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.7; }.task-results { border:1px solid var(--td-component-border); border-radius:var(--app-radius-md); padding:16px; }.result { margin:8px 0; }
details { font-size:var(--app-text-sm); color:var(--td-text-color-secondary); overflow-wrap:anywhere; }summary { cursor:pointer; }pre { font-family:var(--app-font-family-mono);font-size:var(--app-text-base);white-space:pre-wrap; overflow-wrap:anywhere; }
</style>
