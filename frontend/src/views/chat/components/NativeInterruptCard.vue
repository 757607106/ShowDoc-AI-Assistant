<template>
  <div class="native-interrupt">
    <div class="native-interrupt__title">{{ $t('nativeAgent.interruptTitle') }}</div>
    <template v-if="interactive && open">
      <pre>{{ JSON.stringify(request?.value, null, 2) }}</pre>
      <details v-if="request?.response_schema">
        <summary>{{ $t('nativeAgent.responseSchema') }}</summary>
        <pre>{{ JSON.stringify(request.response_schema, null, 2) }}</pre>
      </details>
      <t-textarea v-model="draft" :aria-label="$t('nativeAgent.responseJson')" :autosize="{ minRows: 3, maxRows: 12 }" />
      <p v-if="error" role="alert">{{ error }}</p>
      <t-button :loading="submitting" @click="submit">{{ $t('nativeAgent.submitResponse') }}</t-button>
    </template>
    <div v-else>{{ $t(open ? 'nativeAgent.waitingResponse' : 'nativeAgent.responseSubmitted') }}</div>
    <pre v-if="!open && response !== undefined">{{ JSON.stringify(response, null, 2) }}</pre>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { resolveAgentPrompt } from '@/api/mcp-service'
import { markPromptSubmitted as markDefaultPromptSubmitted, promptSubmission as defaultPromptSubmission, usePromptDock } from '@/composables/usePromptDock'
import { resumeSuspendedRunKey, promptSubmissionTransportKey } from '@/utils/suspendedRun'

const props = defineProps<{
  pendingId: string
  request?: { value?: unknown; response_schema?: Record<string, unknown> }
  variant?: 'dock' | 'inline'
  resolved?: boolean
  response?: unknown
}>()
const { t } = useI18n()
const dock = usePromptDock()
const { markPromptSubmitted, promptSubmission } = dock ?? {
  markPromptSubmitted: markDefaultPromptSubmitted, promptSubmission: defaultPromptSubmission,
}
const submitToThread = inject(promptSubmissionTransportKey, undefined)
const resume = inject(resumeSuspendedRunKey, undefined)
const draft = ref('{}')
const error = ref('')
const submitting = ref(false)
const interactive = computed(() => props.variant === 'dock' || !dock)
const open = computed(() => !props.resolved && !promptSubmission(props.pendingId))

async function submit() {
  if (!open.value || submitting.value) return
  let response: unknown
  try { response = JSON.parse(draft.value) }
  catch { error.value = t('nativeAgent.invalidJson'); return }
  submitting.value = true
  error.value = ''
  try {
    const result = await (submitToThread ? submitToThread(props.pendingId, 'native_interrupt', response)
      : resolveAgentPrompt(props.pendingId, 'native_interrupt', response))
    if ('stale' in result && result.stale) return
    markPromptSubmitted(props.pendingId, { value: response })
    if (result.resumed) resume?.(props.pendingId)
  } catch (failure: any) {
    error.value = failure?.message || t('nativeAgent.responseFailed')
  } finally { submitting.value = false }
}
</script>

<style scoped>
.native-interrupt { padding: 12px; border: 1px solid var(--td-component-border); border-radius: 8px; }
.native-interrupt__title { font-weight: 500; margin-bottom: 8px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 280px; overflow: auto; }
button { margin-top: 8px; }
</style>
