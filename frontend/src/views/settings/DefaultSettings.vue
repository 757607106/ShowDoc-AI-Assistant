<template>
  <div class="default-settings">
    <div class="section-header">
      <h2>{{ t('defaultSettings.title') }}</h2>
      <p class="section-description">{{ t(canEdit ? 'defaultSettings.autoSave' : 'defaultSettings.readOnly') }}</p>
    </div>

    <t-alert v-if="settingsLoadFailed" theme="error" :message="t('defaultSettings.loadFailed')">
      <template #operation>
        <t-button variant="text" @click="loadSettings">{{ t('common.retry') }}</t-button>
      </template>
    </t-alert>
    <div class="settings-group">
      <div v-for="slot in modelSlots" :key="slot.field" class="setting-row">
        <div class="setting-info">
          <label :id="`${labelsId}-${slot.field}`">{{ t(`defaultSettings.slots.${slot.key}.label`) }}</label>
          <p class="desc">{{ t(`defaultSettings.slots.${slot.key}.description`) }}</p>
          <p v-if="settingsLoaded && effective[slot.field].source !== 'workspace'" class="desc hint"
            :class="{ warn: effective[slot.field].stale || effective[slot.field].source === 'none' }">
            {{ effectiveHint(slot, effective[slot.field]) }}
          </p>
        </div>
        <div class="setting-control">
          <ModelSelector
            v-if="!settingsLoaded || effective[slot.field].source !== 'none'"
            role="group"
            :aria-labelledby="`${labelsId}-${slot.field}`"
            :model-type="slot.type"
            :selected-model-id="settings[slot.field]"
            :disabled="!canEdit || saving || !settingsLoaded"
            :all-models="models"
            :clearable="true"
            :placeholder="t('model.selectModelPlaceholder')"
            @update:selected-model-id="(id: string) => onModelChange(slot.field, id)"
            @add-model="openModels(slot.type)"
          />
          <t-button v-else-if="canEdit" variant="outline" :disabled="saving"
            :aria-label="`${t('modelSettings.actions.addModel')} · ${t(`defaultSettings.slots.${slot.key}.label`)}`"
            @click="openModels(slot.type)">
            <template #icon><t-icon name="add" aria-hidden="true" /></template>
            {{ t('modelSettings.actions.addModel') }}
          </t-button>
          <p v-if="saveFeedback?.field === slot.field" class="save-feedback" role="status"
            :class="saveFeedback.state">{{ feedbackText }}</p>
        </div>
      </div>
    </div>

    <template v-if="webSearchSupported">
      <h3 class="group-title">{{ t('defaultSettings.webSearchGroup') }}</h3>
      <div class="settings-group">
        <div class="setting-row">
          <div class="setting-info">
            <label>{{ t('defaultSettings.webSearch.label') }}</label>
            <p class="desc">{{ t('defaultSettings.webSearch.description') }}</p>
            <p v-if="!webSearchDefaultId" class="desc hint warn">{{ t('defaultSettings.webSearch.unset') }}</p>
          </div>
        <div class="setting-control">
            <t-select
              :value="webSearchDefaultId"
              :options="webSearchOptions"
              :disabled="!canEdit || saving || webSearchLoading"
              :loading="webSearchLoading"
              :placeholder="t('defaultSettings.webSearch.placeholder')"
              clearable
              style="width: 100%"
              @change="onWebSearchChange"
            />
            <p v-if="saveFeedback?.field === 'webSearch'" class="save-feedback" role="status"
              :class="saveFeedback.state">{{ feedbackText }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import ModelSelector from '@/components/ModelSelector.vue'
import type { ModelConfig } from '@/api/model'
import {
  getTenantDefaultSettings,
  updateTenantDefaultSettings,
  type DefaultSettings,
} from '@/api/default-settings'
import { patchWebSearchProvider } from '@/api/web-search-provider'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { useChatResourcesStore } from '@/stores/chatResources'
import { useDeploymentCapabilitiesStore } from '@/stores/deploymentCapabilities'
import {
  effectiveModelDefault,
  effectiveUtilityDefault,
  type DefaultModelType,
  type EffectiveDefault,
} from './defaultSettingsState'

type ModelField = keyof DefaultSettings

interface ModelSlot {
  field: ModelField
  key: string
  type: DefaultModelType
}

const modelSlots: ModelSlot[] = [
  { field: 'chat_model_id', key: 'chat', type: 'KnowledgeQA' },
  { field: 'utility_model_id', key: 'utility', type: 'KnowledgeQA' },
  { field: 'embedding_model_id', key: 'embedding', type: 'Embedding' },
  { field: 'rerank_model_id', key: 'rerank', type: 'Rerank' },
  { field: 'vlm_model_id', key: 'vlm', type: 'VLLM' },
  { field: 'asr_model_id', key: 'asr', type: 'ASR' },
]

const { t } = useI18n()
const authStore = useAuthStore()
const uiStore = useUIStore()
const chatResources = useChatResourcesStore()
const deploymentCapabilities = useDeploymentCapabilitiesStore()

const canEdit = computed(() => authStore.hasRole('admin'))
const labelsId = useId()
const saveFeedback = ref<{ field: ModelField | 'webSearch'; state: 'saving' | 'saved' | 'error'; message?: string }>()
const saving = computed(() => saveFeedback.value?.state === 'saving')
const feedbackText = computed(() => {
  const state = saveFeedback.value
  if (state?.state === 'error') return t('defaultSettings.toasts.saveFailed', { message: state.message || '' })
  return t(state?.state === 'saved' ? 'defaultSettings.toasts.saveSuccess' : 'defaultSettings.saving')
})
const settingsLoaded = ref(false)
const settingsLoadFailed = ref(false)

const settings = reactive<DefaultSettings>({
  chat_model_id: '',
  utility_model_id: '',
  embedding_model_id: '',
  rerank_model_id: '',
  vlm_model_id: '',
  asr_model_id: '',
})

const models = computed<ModelConfig[]>(() => chatResources.allModels.filter((m) => m.status === 'active'))

const effective = computed(() => {
  const out = {} as Record<ModelField, EffectiveDefault<ModelConfig>>
  for (const slot of modelSlots) {
    out[slot.field] = slot.field === 'utility_model_id'
      ? effectiveUtilityDefault(models.value, settings.utility_model_id, settings.chat_model_id)
      : effectiveModelDefault(models.value, slot.type, settings[slot.field])
  }
  return out
})

const modelName = (model: ModelConfig | null) => model?.display_name?.trim() || model?.name || ''

const effectiveHint = (slot: ModelSlot, state: EffectiveDefault<ModelConfig>) => {
  const name = modelName(state.model)
  if (state.stale) {
    return state.model
      ? t('defaultSettings.hints.staleFallback', { name })
      : t('defaultSettings.hints.staleNone')
  }
  switch (state.source) {
    case 'workspace':
      return t('defaultSettings.hints.workspace')
    case 'system':
      return t('defaultSettings.hints.system', { name })
    case 'auto':
      return t('defaultSettings.hints.auto', { name })
    case 'chat':
      return t('defaultSettings.hints.followChat', { name })
    default:
      return t(`defaultSettings.slots.${slot.key}.none`)
  }
}

const loadSettings = async () => {
  settingsLoaded.value = false
  settingsLoadFailed.value = false
  try {
    const response = await getTenantDefaultSettings()
    if (!response.data) throw new Error('Default settings response is missing data')
    for (const slot of modelSlots) {
      settings[slot.field] = response.data[slot.field] || ''
    }
    settingsLoaded.value = true
  } catch (error) {
    settingsLoadFailed.value = true
    console.error('Failed to load default settings:', error)
  }
}

const onModelChange = async (field: ModelField, id: string) => {
  if (!canEdit.value || !settingsLoaded.value || saving.value || settings[field] === (id || '')) return
  const previous = settings[field]
  settings[field] = id || ''
  saveFeedback.value = { field, state: 'saving' }
  try {
    await updateTenantDefaultSettings({ ...settings })
    // Refresh every picker. A failed refresh must not undo an already saved choice.
    await chatResources.ensureModels(true).catch((error) => {
      console.error('Failed to refresh models after saving defaults:', error)
    })
    saveFeedback.value = { field, state: 'saved' }
  } catch (error: any) {
    settings[field] = previous
    saveFeedback.value = { field, state: 'error', message: error?.message }
  }
}

const webSearchSupported = computed(() => deploymentCapabilities.isSupported('settings.websearch'))
const webSearchProviders = computed(() => chatResources.webSearchProviders)
const webSearchLoading = ref(false)

const webSearchDefaultId = computed(() => webSearchProviders.value.find((p) => p.is_default)?.id || '')
const webSearchOptions = computed(() =>
  webSearchProviders.value
    .filter((p) => p.id)
    .map((p) => ({ label: p.name, value: p.id as string })),
)

const loadWebSearchProviders = async () => {
  webSearchLoading.value = true
  try {
    await chatResources.ensureWebSearchProviders(true)
  } catch (error) {
    console.error('Failed to load web search providers:', error)
  } finally {
    webSearchLoading.value = false
  }
}

// Providers keep their own is_default flag; setting one clears the others
// on the server, so clearing is the only case that targets the old default.
const onWebSearchChange = async (value: unknown) => {
  const id = typeof value === 'string' ? value : ''
  const current = webSearchDefaultId.value
  if (!canEdit.value || saving.value || webSearchLoading.value || id === current) return
  saveFeedback.value = { field: 'webSearch', state: 'saving' }
  try {
    if (id) {
      await patchWebSearchProvider(id, { is_default: true })
    } else if (current) {
      await patchWebSearchProvider(current, { is_default: false })
    }
    for (const provider of webSearchProviders.value) {
      provider.is_default = provider.id === id
    }
    await loadWebSearchProviders()
    saveFeedback.value = { field: 'webSearch', state: 'saved' }
  } catch (error: any) {
    saveFeedback.value = { field: 'webSearch', state: 'error', message: error?.message }
  }
}

const openModels = (type: DefaultModelType) => {
  const subsection = type === 'KnowledgeQA' ? 'chat' : type === 'VLLM' ? 'vllm' : type.toLowerCase()
  uiStore.openSettings('models', subsection)
  window.dispatchEvent(
    new CustomEvent('settings-nav', { detail: { section: 'models', subsection } }),
  )
}

onMounted(() => {
  void chatResources.ensureModels(true).catch(() => {})
  void loadSettings()
  if (webSearchSupported.value) void loadWebSearchProviders()
})
</script>

<style lang="less" scoped>
@import (reference) '@/components/css/settings-section.less';

.default-settings {
  width: 100%;
  container-type: inline-size;
}

.section-header {
  .settings-section-header();
}

.group-title {
  margin: 24px 0 0;
  font-size: var(--app-text-base);
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.settings-group {
  display: flex;
  flex-direction: column;
}

.setting-row {
  .setting-row();
}

.setting-info {
  .setting-info();

  .hint {
    margin-top: 4px !important;
    color: var(--td-text-color-placeholder);

    &.warn {
      color: var(--td-warning-color);
    }
  }
}

.setting-control {
  .setting-control();
  flex-direction: column;
  align-items: flex-end;
  max-width: 45%;
}

.save-feedback {
  margin: 0;
  font-size: var(--app-text-sm);
  color: var(--td-text-color-secondary);

  &.error {
    color: var(--td-error-color);
  }
}

@container (max-width: 520px) {
  .stacked-setting-rows();
  .setting-control {
    max-width: 100%;
    align-items: flex-start;
  }
}
</style>
