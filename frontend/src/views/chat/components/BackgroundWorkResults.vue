<template>
  <div class="background-work-results">
    <div class="results-actions">
      <span v-if="detail">{{ $t(`chat.backgroundWork.states.${detail.state}`) }}</span>
      <t-button variant="text" :loading="loading" :disabled="!!busy" @click="refreshDetail">{{ $t('chat.backgroundWork.refresh') }}</t-button>
      <t-button v-if="canCancel" theme="danger" variant="outline" :loading="busy === 'cancel'" :disabled="!!busy" @click="act('cancel')">{{ $t('chat.backgroundWork.stop') }}</t-button>
    </div>
    <div v-if="loading && !detail" class="results-loading">{{ $t('chat.backgroundWork.loading') }}</div>
    <template v-else-if="nativeResult">
      <PendingPromptDock v-if="nativeResult.view_session_id" />
      <div v-if="viewerTask" class="async-conversation">
        <ChildAgentStream :key="viewerTask.sessionId" :task="viewerTask" :refresh-key="viewerRefresh" />
      </div>
      <pre v-else-if="nativeResult.output">{{ nativeResult.output }}</pre>
      <section v-if="Object.hasOwn(nativeResult, 'structured_response')">
        <h4>{{ $t('chat.backgroundWork.structuredResult') }}</h4>
        <pre>{{ JSON.stringify(nativeResult.structured_response, null, 2) }}</pre>
      </section>
      <pre v-if="nativeResult.error" class="results-error">{{ nativeResult.error }}</pre>
      <section v-for="interrupt in nativeResult.view_session_id ? [] : nativeResult.interrupts" :key="interrupt.id" class="interrupt-request">
        <h4>{{ $t('nativeAgent.interruptTitle') }} <code>{{ interrupt.id }}</code></h4>
        <pre>{{ JSON.stringify(interrupt.value, null, 2) }}</pre>
        <details v-if="interrupt.response_schema">
          <summary>{{ $t('nativeAgent.responseSchema') }}</summary>
          <pre>{{ JSON.stringify(interrupt.response_schema, null, 2) }}</pre>
        </details>
        <t-textarea v-if="interactive && detail?.state === 'waiting'" v-model="responseDrafts[interrupt.id]"
          :disabled="!!busy || !canResume" :aria-label="$t('nativeAgent.responseJson')" :autosize="{ minRows: 3, maxRows: 12 }" />
      </section>
      <t-button v-if="!nativeResult.view_session_id && interactive && detail?.state === 'waiting' && nativeResult.interrupts.length"
        :loading="busy === 'resume'" :disabled="!!busy || !canResume" @click="act('resume')">{{ $t('nativeAgent.submitResponse') }}</t-button>
      <section v-if="canUpdate" class="update-task">
        <label>{{ $t('chat.backgroundWork.updateMessage') }}</label>
        <t-textarea v-model="messageDraft" :disabled="!!busy" :aria-label="$t('chat.backgroundWork.updateMessage')" :autosize="{ minRows: 3, maxRows: 12 }" />
        <t-button :loading="busy === 'update'" :disabled="!!busy || !messageDraft.trim()" @click="act('update')">{{ $t('chat.backgroundWork.sendUpdate') }}</t-button>
      </section>
    </template>
    <ShellExecResult v-else-if="detail?.result" :data="detail.result" />
    <div v-else-if="!loading" class="results-error">{{ $t('chat.backgroundWork.unavailable') }}</div>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="actionError || loadError" class="results-error" role="alert">{{ actionError || loadError }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, provide, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { cancelBackgroundWork, getBackgroundWork, resumeBackgroundWork, updateBackgroundWork,
  type AsyncSubagentPayload, type BackgroundWorkDetail } from '@/api/chat/background-work'
import { asyncPromptResponses, isBackgroundWorkActive } from '@/utils/backgroundWork'
import { promptSubmissionTransportKey, resumeSuspendedRunKey } from '@/utils/suspendedRun'
import { providePromptDock } from '@/composables/usePromptDock'
import type { CollaborationTaskView } from '@/utils/collaborationDisplay'
import ChildAgentStream from './ChildAgentStream.vue'
import PendingPromptDock from './PendingPromptDock.vue'
import ShellExecResult from './tool-results/ShellExecResult.vue'

const props = defineProps<{ sessionId: string; workId: string; ownerKey?: string }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const detail = ref<BackgroundWorkDetail | null>(null)
const loading = ref(false)
const messageDraft = ref('')
const responseDrafts = ref<Record<string, string>>(Object.create(null))
const submittedInterrupts = ref(new Set<string>())
const busy = ref('')
const actionError = ref('')
const loadError = ref('')
const notice = ref('')
const promptMessages = reactive<Record<string, unknown>[]>([])
const promptSubmissions = reactive(new Map<string, Record<string, unknown>>())
providePromptDock(promptMessages, promptSubmissions)
const promptResponses = ref<Record<string, unknown>>(Object.create(null))
const viewerRefresh = ref(0)
const nativeResult = computed(() => detail.value?.result?.display_type === 'async_subagent'
  ? detail.value.result as AsyncSubagentPayload : null)
const interactive = computed(() => !!nativeResult.value && detail.value?.read_only === false)
const active = computed(() => !!detail.value && isBackgroundWorkActive(detail.value.state))
const canUpdate = computed(() => interactive.value && !!detail.value
  && ['pending', 'running', 'waiting', 'succeeded', 'failed'].includes(detail.value.state))
const canCancel = computed(() => interactive.value && active.value && detail.value?.can_cancel === true)
const canResume = computed(() => interactive.value && detail.value?.state === 'waiting'
  && !!nativeResult.value?.interrupts.length
  && nativeResult.value.interrupts.every(item => !submittedInterrupts.value.has(item.id)))
const viewerTask = computed<CollaborationTaskView | null>(() => nativeResult.value?.view_session_id ? {
  id: props.workId, name: detail.value?.title || '', displayName: detail.value?.title || '',
  sessionId: nativeResult.value.view_session_id, runId: '', latestMessage: '',
  status: detail.value?.state === 'pending' ? 'queued' : detail.value?.state || 'unknown',
} : null)
watch([nativeResult, interactive, canResume], () => {
  const events = (nativeResult.value?.prompts ?? []).map(prompt => ({
    ...prompt, type: prompt.kind === 'tool_approval' ? 'tool_approval_required' : 'agent_prompt_required',
  }))
  promptMessages.splice(0, promptMessages.length, { role: 'assistant',
    is_completed: !interactive.value || !canResume.value, agentEventStream: events })
})
provide(promptSubmissionTransportKey, submitPrompt)
provide(resumeSuspendedRunKey, () => { viewerRefresh.value++; void loadDetail(generation) })
let generation = 0
let request = 0
let timer: ReturnType<typeof setTimeout> | undefined

function stopTimer() {
  if (timer) clearTimeout(timer)
  timer = undefined
}

function schedule(current: number) {
  stopTimer()
  if (current === generation && active.value && !busy.value) {
    timer = setTimeout(() => { void loadDetail(current) }, 5000)
  }
}

async function loadDetail(current: number) {
  if (current !== generation || !props.sessionId || !props.workId) return
  const latest = ++request
  loading.value = true
  try {
    const next = await getBackgroundWork(props.sessionId, props.workId)
    if (current !== generation || latest !== request) return
    detail.value = next
    loadError.value = ''
    for (const interrupt of nativeResult.value?.interrupts ?? []) {
      if (!Object.hasOwn(responseDrafts.value, interrupt.id)) responseDrafts.value[interrupt.id] = '{}'
    }
  } catch (failure: any) {
    if (current === generation && latest === request) loadError.value = failure?.message || t('chat.backgroundWork.unavailable')
  } finally {
    if (current === generation && latest === request) {
      loading.value = false
      schedule(current)
    }
  }
}

async function refreshDetail() {
  if (!busy.value) await loadDetail(generation)
}

watch(() => [props.ownerKey, props.sessionId, props.workId], () => {
  const current = ++generation
  request++
  stopTimer()
  detail.value = null
  loading.value = false
  messageDraft.value = ''
  responseDrafts.value = Object.create(null)
  submittedInterrupts.value = new Set()
  promptResponses.value = Object.create(null)
  promptSubmissions.clear()
  promptMessages.splice(0)
  viewerRefresh.value++
  busy.value = ''
  actionError.value = ''
  loadError.value = ''
  notice.value = ''
  void loadDetail(current)
}, { immediate: true, flush: 'sync' })

onUnmounted(() => { generation++; request++; stopTimer() })

async function submitPrompt(pendingId: string, kind: 'tool_approval' | 'ask_user' | 'native_interrupt', response: unknown) {
  const prompts = nativeResult.value?.prompts ?? []
  if (!canResume.value || busy.value || !prompts.some(prompt => prompt.pending_id === pendingId && prompt.kind === kind)) {
    throw new Error(t('chat.backgroundWork.actionFailed'))
  }
  promptResponses.value[pendingId] = response
  const responses = asyncPromptResponses(prompts, promptResponses.value)
  if (responses === null) return { resumed: false }
  const current = generation
  const sessionId = props.sessionId, workId = props.workId
  busy.value = 'resume'
  actionError.value = ''
  request++
  loading.value = false
  stopTimer()
  try {
    await resumeBackgroundWork(sessionId, workId, responses)
    if (current !== generation) return { resumed: false, stale: true }
    for (const item of nativeResult.value?.interrupts ?? []) submittedInterrupts.value.add(item.id)
    emit('changed')
    await loadDetail(current)
    viewerRefresh.value++
    return { resumed: false }
  } catch (failure: any) {
    if (current !== generation) return { resumed: false, stale: true }
    actionError.value = failure?.message || t('chat.backgroundWork.actionFailed')
    throw failure
  } finally {
    if (current === generation) { busy.value = ''; schedule(current) }
  }
}

async function act(action: 'update' | 'resume' | 'cancel') {
  if (busy.value || action === 'update' && !canUpdate.value || action === 'resume' && !canResume.value
    || action === 'cancel' && !canCancel.value) return
  const message = messageDraft.value
  const interrupts = nativeResult.value?.interrupts ?? []
  const responses: Record<string, unknown> = Object.create(null)
  actionError.value = ''
  notice.value = ''
  if (action === 'update' && !message.trim()) return
  if (action === 'resume') {
    try {
      for (const item of interrupts) responses[item.id] = JSON.parse(responseDrafts.value[item.id] ?? '')
    } catch { actionError.value = t('nativeAgent.invalidJson'); return }
  }
  const current = generation
  const sessionId = props.sessionId, workId = props.workId
  busy.value = action
  request++
  loading.value = false
  stopTimer()
  try {
    if (action === 'update') await updateBackgroundWork(sessionId, workId, message)
    else if (action === 'resume') await resumeBackgroundWork(sessionId, workId, responses)
    else await cancelBackgroundWork(sessionId, workId)
    if (current !== generation) return
    if (action === 'update' && messageDraft.value === message) messageDraft.value = ''
    if (action === 'resume') for (const item of interrupts) submittedInterrupts.value.add(item.id)
    notice.value = t(action === 'resume' ? 'nativeAgent.responseSubmitted'
      : action === 'update' ? 'chat.backgroundWork.updateSent' : 'chat.backgroundWork.stopRequested')
    emit('changed')
    await loadDetail(current)
    viewerRefresh.value++
  } catch (failure: any) {
    if (current === generation) actionError.value = failure?.message || t('chat.backgroundWork.actionFailed')
  } finally {
    if (current === generation) { busy.value = ''; schedule(current) }
  }
}
</script>

<style lang="less" scoped>
.background-work-results { min-width: 0; }
.async-conversation { height: min(65vh, 640px); min-height: 200px; overflow: hidden; }
.results-actions { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.results-actions > span { margin-right: auto; }
.results-loading { font-size: var(--app-text-sm); color: var(--td-text-color-placeholder); }
.results-error { color: var(--td-error-color); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 320px; overflow: auto; font-family: var(--app-font-family-mono); }
h4 { margin: 12px 0 8px; font-weight: 500; }
.interrupt-request { margin: 12px 0; padding: 12px; border: 1px solid var(--td-component-border); border-radius: var(--app-radius-sm); }
.update-task { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin-top: 16px; }
.update-task :deep(.t-textarea) { width: 100%; }
</style>
