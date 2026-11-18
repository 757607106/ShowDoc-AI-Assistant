<template>
  <div class="retrieval-settings">
    <h2 class="settings-title">{{ t('retrievalSettings.title') }}</h2>
    <p class="section-description">{{ t('retrievalSettings.description') }}</p>
    <div class="settings-group">
      <!-- Top K -->
      <div class="setting-item">
        <div class="setting-label-row">
          <span>{{ t('retrievalSettings.topKLabel') }}</span>
          <span class="value-display">{{ localConfig.top_k }}</span>
        </div>
        <p class="setting-desc">{{ t('retrievalSettings.topKDescription') }}</p>
        <t-slider
          v-model="localConfig.top_k"
          :min="1"
          :max="10"
          :step="1"
          :disabled="!canEdit"
          @change="handleParamChange"
        />
      </div>

      <!-- Similarity Threshold -->
      <div class="setting-item">
        <div class="setting-label-row">
          <span>{{ t('retrievalSettings.similarityThresholdLabel') }}</span>
          <span class="value-display">{{ localConfig.similarity_threshold.toFixed(2) }}</span>
        </div>
        <p class="setting-desc">{{ t('retrievalSettings.similarityThresholdDescription') }}</p>
        <t-slider
          v-model="localConfig.similarity_threshold"
          :min="0"
          :max="1"
          :step="0.05"
          :disabled="!canEdit"
          @change="handleParamChange"
        />
      </div>

      <!-- Vector Weight -->
      <div class="setting-item">
        <div class="setting-label-row">
          <span>{{ t('retrievalSettings.vectorWeightLabel') }}</span>
          <span class="value-display">{{ localConfig.vector_weight.toFixed(2) }}</span>
        </div>
        <p class="setting-desc">{{ t('retrievalSettings.vectorWeightDescription') }}</p>
        <t-slider
          v-model="localConfig.vector_weight"
          :min="0"
          :max="1"
          :step="0.05"
          :disabled="!canEdit"
          @change="handleParamChange"
        />
      </div>

      <!-- Query Rewrite -->
      <div class="setting-item">
        <div class="setting-label-row">
          <span>{{ t('retrievalSettings.queryRewriteLabel') }}</span>
          <t-switch v-model="localConfig.query_rewrite" :disabled="!canEdit" @change="handleParamChange" />
        </div>
        <p class="setting-desc">{{ t('retrievalSettings.queryRewriteDescription') }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// 关闭搜索框不会撤销已发送的写入；重开时先等同一空间的保存结束，再读取配置。
const pendingRetrievalSaves = new Map<number | null, Promise<unknown>>()
</script>

<script setup lang="ts">
import { reactive, computed, onMounted, onUnmounted, nextTick, ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { useI18n } from 'vue-i18n'
import {
  getTenantRetrievalConfig,
  updateTenantRetrievalConfig,
  type RetrievalConfig,
} from '@/api/retrieval'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()
const configTenantId = authStore.effectiveTenantId
const isInitializing = ref(true)
const viewInvalidated = ref(false)
const isCurrentView = () => !viewInvalidated.value && authStore.effectiveTenantId === configTenantId
// 加载完成前保持只读，避免用默认值覆盖尚未读回的空间配置。
const canEdit = computed(() => authStore.hasRole('admin') && !isInitializing.value && isCurrentView())

// 平台现行默认：未保存前 kb_search 用 top_k=10、query_rewrite=true；
// similarity_threshold/vector_weight 留空时由 ContextDB 使用官方默认 0.6/0.7。
const defaultConfig: RetrievalConfig = {
  top_k: 10,
  similarity_threshold: 0.6,
  vector_weight: 0.7,
  query_rewrite: true,
}

const localConfig = reactive<RetrievalConfig>({ ...defaultConfig })
let initialConfig: RetrievalConfig = { ...defaultConfig }
const SAVE_DEBOUNCE_MS = 500
const INITIALIZATION_DELAY_MS = 100
let initializationTimer: number | null = null
let saveTimer: number | null = null
let isSaving = false
let saveRequested = false

// 切空间可能先于页面销毁；一旦失效，即使切回原空间也不复用这次编辑会话。
const invalidateView = () => {
  viewInvalidated.value = true
  if (initializationTimer !== null) clearTimeout(initializationTimer)
  if (saveTimer !== null) clearTimeout(saveTimer)
  initializationTimer = null
  saveTimer = null
  saveRequested = false
}

const loadConfig = async () => {
  try {
    while (pendingRetrievalSaves.has(configTenantId)) {
      // 旧请求失败也要重新读取；它的错误不属于新打开的设置页面。
      await pendingRetrievalSaves.get(configTenantId)?.catch(() => {})
      if (!isCurrentView()) return
    }
    const response = await getTenantRetrievalConfig()
    if (!isCurrentView() || !response.data) return
    const cfg = response.data
    Object.assign(localConfig, {
      top_k: cfg.top_k ?? defaultConfig.top_k,
      similarity_threshold: cfg.similarity_threshold ?? defaultConfig.similarity_threshold,
      vector_weight: cfg.vector_weight ?? defaultConfig.vector_weight,
      query_rewrite: cfg.query_rewrite ?? defaultConfig.query_rewrite,
    })
    initialConfig = { ...localConfig }
    await nextTick()
    await nextTick()
    if (!isCurrentView()) return
    initializationTimer = window.setTimeout(() => {
      initializationTimer = null
      if (isCurrentView()) isInitializing.value = false
    }, INITIALIZATION_DELAY_MS)
  } catch (error: any) {
    if (isCurrentView()) console.error('Failed to load retrieval config:', error)
  }
}

const hasConfigChanged = (): boolean => {
  return JSON.stringify(localConfig) !== JSON.stringify(initialConfig)
}

const saveConfig = async () => {
  if (isSaving || !saveRequested || !canEdit.value) return
  saveRequested = false
  if (!hasConfigChanged()) return

  const submittedConfig = { ...localConfig }
  isSaving = true
  let request: ReturnType<typeof updateTenantRetrievalConfig> | undefined
  try {
    request = updateTenantRetrievalConfig(submittedConfig)
    pendingRetrievalSaves.set(configTenantId, request)
    const response = await request
    if (!isCurrentView()) return
    if (!response.data) throw new Error('Missing retrieval configuration in save response')
    // 只能确认本次提交的快照，不能把请求期间的新编辑也标记为已保存。
    initialConfig = submittedConfig
    if (!hasConfigChanged()) MessagePlugin.success(t('retrievalSettings.toasts.saveSuccess'))
  } catch (error: any) {
    if (!isCurrentView()) return
    console.error('Failed to save retrieval config:', error)
    const errorMessage = error?.message || 'Unknown error'
    MessagePlugin.error(t('retrievalSettings.toasts.saveFailed', { message: errorMessage }))
  } finally {
    if (request && pendingRetrievalSaves.get(configTenantId) === request) {
      pendingRetrievalSaves.delete(configTenantId)
    }
    isSaving = false
    // 只接续已到期的新编辑；失败本身不产生重试，新的防抖也不能被提前执行。
    if (saveRequested && saveTimer === null) void saveConfig()
  }
}

const debouncedSave = () => {
  if (!canEdit.value) return
  if (saveTimer !== null) clearTimeout(saveTimer)
  saveRequested = false
  saveTimer = window.setTimeout(() => {
    saveTimer = null
    saveRequested = true
    void saveConfig()
  }, SAVE_DEBOUNCE_MS)
}

const handleParamChange = () => debouncedSave()

watch(() => authStore.effectiveTenantId, invalidateView, { flush: 'sync' })
onUnmounted(invalidateView)
onMounted(loadConfig)
</script>

<style lang="less" scoped>
@import (reference) '@/components/css/settings-section.less';

.retrieval-settings {
  width: 100%;
}

.settings-title {
  margin: 0 28px 12px 0;
  font-size: var(--app-text-lg);
  font-weight: 600;
  line-height: 24px;
  color: var(--td-text-color-primary);
}

.section-description {
  margin: 0 0 4px 0;
  font-size: var(--app-text-sm);
  color: var(--td-text-color-secondary);
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-top: 4px;
  :deep(.t-input) { border-radius: var(--app-radius-md); }
}

.setting-item {
  padding: 16px 0;
  border-bottom: 1px solid var(--td-component-stroke);

  &:last-child {
    border-bottom: none;
  }
}

.setting-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--app-text-md);
  font-weight: 500;
  color: var(--td-text-color-primary);
  margin-bottom: 10px;
}

.setting-desc {
  font-size: var(--app-text-sm);
  color: var(--td-text-color-secondary);
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.value-display {
  font-size: var(--app-text-md);
  font-weight: 500;
  color: var(--td-text-color-primary);
  font-variant-numeric: tabular-nums;
}
</style>
