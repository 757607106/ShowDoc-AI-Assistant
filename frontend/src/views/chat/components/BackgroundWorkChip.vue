<template>
  <t-popup
    v-if="items.length"
    v-model:visible="open"
    trigger="click"
    placement="top-left"
    :overlay-inner-style="{ padding: '6px' }"
  >
    <button
      type="button"
      class="chip-count"
      :aria-expanded="open"
      :aria-label="$t('chat.backgroundWork.count', { count: items.length }, items.length)"
    >
      <span class="chip-badge" aria-hidden="true" />
      <span>{{ $t('chat.backgroundWork.count', { count: items.length }, items.length) }}</span>
    </button>
    <template #content>
      <div class="work-card" role="list">
        <div v-for="item in items" :key="item.work_id" class="work-row" role="listitem">
          <button type="button" class="work-main" @click="openOutput(item.work_id)">
            <span class="work-title">{{ item.title || item.work_id }}</span>
            <span class="work-state">{{ $t(`chat.backgroundWork.states.${item.state}`) }}</span>
            <span v-if="elapsed(item)" class="work-duration">{{ elapsed(item) }}</span>
          </button>
          <button
            v-if="canCancel(item)"
            type="button"
            class="work-stop"
            :disabled="cancelling.has(item.work_id)"
            @click="onCancel(item.work_id)"
          >{{ $t('chat.backgroundWork.stop') }}</button>
        </div>
        <p v-if="cancelError" role="alert">{{ cancelError }}</p>
      </div>
    </template>
  </t-popup>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BackgroundWorkItem } from '@/api/chat/background-work'
import { isBackgroundWorkActive } from '@/utils/backgroundWork'

const props = defineProps<{
  items: BackgroundWorkItem[]
  cancelWork: (workId: string) => Promise<void>
  scopeKey?: string
}>()
const { t } = useI18n()
const emit = defineEmits<{ view: [workId: string] }>()
const cancelling = ref(new Set<string>())
const open = ref(false)
const cancelError = ref('')
const now = ref(Date.now())
let clock: ReturnType<typeof setInterval> | undefined
let generation = 0

const active = computed(() => props.items.filter((item) => isBackgroundWorkActive(item.state)))

function syncClock() {
  const live = active.value.some((item) => item.started_at)
  if (live && !clock) {
    clock = setInterval(() => { now.value = Date.now() }, 1000)
  } else if (!live && clock) {
    clearInterval(clock)
    clock = undefined
  }
}

watch(() => props.items, (items) => {
  syncClock()
  if (!items.length) open.value = false
  const ids = new Set(items.map((item) => item.work_id))
  const next = new Set([...cancelling.value].filter((id) => ids.has(id)))
  if (next.size !== cancelling.value.size) cancelling.value = next
}, { deep: true, immediate: true })

watch(() => props.scopeKey, () => {
  generation++
  cancelling.value = new Set()
  cancelError.value = ''
  open.value = false
}, { flush: 'sync' })

onUnmounted(() => {
  generation++
  if (clock) clearInterval(clock)
})

function canCancel(item: BackgroundWorkItem): boolean {
  return item.kind === 'async_subagent' && item.read_only === false && item.can_cancel === true
    && isBackgroundWorkActive(item.state)
}

function openOutput(workId: string) {
  open.value = false
  emit('view', workId)
}

async function onCancel(workId: string) {
  const item = props.items.find(item => item.work_id === workId)
  if (!item || !canCancel(item) || cancelling.value.has(workId)) return
  const current = generation
  cancelError.value = ''
  const next = new Set(cancelling.value)
  next.add(workId)
  cancelling.value = next
  try {
    await props.cancelWork(workId)
  } catch (failure: any) {
    if (current === generation) cancelError.value = failure?.message || t('chat.backgroundWork.cancelFailed')
  } finally {
    if (current !== generation) return
    // The request may fail while the job remains running. Always permit retry
    // after it settles; only an in-flight request should disable the button.
    const remaining = new Set(cancelling.value)
    remaining.delete(workId)
    cancelling.value = remaining
  }
}

function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

function elapsed(item: BackgroundWorkItem): string {
  const start = Date.parse(item.started_at ?? '')
  if (!Number.isFinite(start)) return ''
  const finish = isBackgroundWorkActive(item.state) ? now.value : Date.parse(item.finished_at ?? '')
  return Number.isFinite(finish) ? formatDuration(finish - start) : ''
}
</script>

<style lang="less" scoped>
.chip-count {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  height: 28px;
  margin: 0;
  padding: 0 10px;
  border: 0;
  border-radius: var(--app-radius-sm);
  background: transparent;
  color: var(--td-text-color-secondary);
  font: inherit;
  font-size: var(--app-text-md);
  font-weight: 500;
  line-height: 18px;
  cursor: pointer;
  transition: background var(--app-motion-instant), color var(--app-motion-instant);

  &:hover,
  &[aria-expanded='true'] {
    background: var(--td-bg-color-secondarycontainer-hover);
    color: var(--td-text-color-primary);
  }
}

.chip-badge {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.work-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: min(320px, 72vw);
  max-height: 280px;
  overflow: auto;
}

.work-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.work-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex: 1;
  min-width: 0;
  margin: 0;
  padding: 6px 8px;
  border: 0;
  border-radius: var(--td-radius-medium);
  background: transparent;
  color: var(--td-text-color-primary);
  font: inherit;
  font-size: var(--app-text-sm);
  line-height: 18px;
  text-align: left;
  cursor: pointer;

  &:hover {
    background: var(--td-bg-color-secondarycontainer-hover);
  }
}

.work-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-duration {
  flex-shrink: 0;
  color: var(--td-text-color-placeholder);
  font-variant-numeric: tabular-nums;
}

.work-state { flex-shrink: 0; color: var(--td-text-color-secondary); font-size: var(--app-text-xs); }
[role='alert'] { margin: 4px 8px; color: var(--td-error-color); font-size: var(--app-text-sm); }

.work-stop {
  flex-shrink: 0;
  margin: 0;
  padding: 4px 8px;
  border: 0;
  border-radius: var(--td-radius-medium);
  background: transparent;
  color: var(--td-text-color-secondary);
  font: inherit;
  font-size: var(--app-text-sm);
  line-height: 18px;
  cursor: pointer;

  &:hover {
    background: var(--td-bg-color-secondarycontainer-hover);
  }

  &:disabled {
    cursor: default;
    opacity: 0.45;
  }
}
</style>
