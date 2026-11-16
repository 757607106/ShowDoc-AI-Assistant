<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { nativeAPI } from '@/api/contextdb'

const props = defineProps<{ kbId: string; canEdit: boolean }>()
interface ReviewSettings {
  knowledge_base_id: string
  review_enabled: boolean
  high_threshold: number
  rewrite_enabled: boolean
  rewrite_auto_ingest_enabled: boolean
}
const fields = ['review_enabled', 'rewrite_auto_ingest_enabled', 'rewrite_enabled', 'high_threshold'] as const
const settings = ref<ReviewSettings | null>(null), baseline = ref<ReviewSettings | null>(null), settingsKbId = ref('')
const loading = ref(false), saving = ref(false), error = ref(''), notice = ref('')
const disabled = computed(() => !props.canEdit || loading.value || saving.value || settingsKbId.value !== props.kbId)
const dirty = computed(() => !!settings.value && !!baseline.value && fields.some(key => settings.value![key] !== baseline.value![key]))
let request = 0
async function readSettings(kb: string): Promise<ReviewSettings> {
  const { data } = await nativeAPI.get('knowledge/review_settings', { knowledge_base_id: kb })
  if (data?.knowledge_base_id !== kb) throw new Error('评审策略不属于当前知识库，请重新读取')
  if (typeof data.high_threshold !== 'number' || fields.slice(0, 3).some(key => typeof data[key] !== 'boolean')) {
    throw new Error('评审策略未完整返回，请重新读取')
  }
  return { knowledge_base_id: kb, review_enabled: data.review_enabled, rewrite_auto_ingest_enabled: data.rewrite_auto_ingest_enabled,
    rewrite_enabled: data.rewrite_enabled, high_threshold: data.high_threshold }
}
async function load() {
  const token = ++request, kb = props.kbId
  settings.value = null; baseline.value = null; settingsKbId.value = ''; error.value = ''; notice.value = ''
  loading.value = !!kb
  if (!kb) return
  try {
    const data = await readSettings(kb)
    if (token !== request || kb !== props.kbId) return
    settings.value = { ...data }; baseline.value = { ...data }; settingsKbId.value = kb
  } catch (e: any) { if (token === request) error.value = e.message }
  finally { if (token === request) loading.value = false }
}
async function save() {
  if (disabled.value || !dirty.value || !settings.value || !baseline.value) return
  const value = settings.value
  error.value = ''; notice.value = ''
  if (!Number.isFinite(value.high_threshold) || value.high_threshold < 0 || value.high_threshold > 1) {
    error.value = '自动入库阈值范围为 0～1'; return
  }
  if (fields.slice(0, 3).some(key => typeof value[key] !== 'boolean')) {
    error.value = '评审策略开关未完整返回，请重新读取'; return
  }
  const kb = props.kbId, token = ++request
  const original = { ...baseline.value }, changed = fields.filter(key => value[key] !== original[key])
  const changes = Object.fromEntries(changed.map(key => [key, value[key]]))
  saving.value = true
  try {
    const current = await readSettings(kb)
    if (token !== request || kb !== props.kbId || !props.canEdit) return
    if (changed.some(key => current[key] !== original[key])) throw new Error('评审策略已被更新，请刷新后重新修改')
    await nativeAPI.patch('knowledge/review_settings', { knowledge_base_id: kb, ...changes })
    if (token !== request || kb !== props.kbId) return
    await load()
    if (settings.value && settingsKbId.value === kb) notice.value = '配置已保存'
  } catch (e: any) { if (token === request) error.value = e.message }
  finally { saving.value = false }
}
watch(() => props.kbId, load, { immediate: true })
onUnmounted(() => { request++ })
</script>
<template>
  <section class="review-settings">
    <div class="strategy-notes">
      <p>自动入库的文件仍可在知识评审‘已通过’区追溯。</p>
      <p>低于自动入库阈值的文件需等待人工审核。</p>
      <p>重写后自动入库：启用后，重写后的文件若评分 ≥ 自动入库阈值，可自动入库。</p>
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="notice" theme="success" :message="notice" />
    <t-loading :loading="loading">
      <t-form v-if="settings" label-width="160px" :disabled="disabled" @submit.prevent="save">
        <t-form-item label="启用知识评审">
          <t-switch v-model="settings.review_enabled" aria-label="启用知识评审" :disabled="disabled" />
        </t-form-item>
        <t-form-item label="重写文件自动入库">
          <t-switch v-model="settings.rewrite_auto_ingest_enabled" aria-label="重写文件自动入库" :disabled="disabled" />
        </t-form-item>
        <t-form-item label="启用知识重写">
          <t-switch v-model="settings.rewrite_enabled" aria-label="启用知识重写" :disabled="disabled" />
        </t-form-item>
        <t-form-item label="自动入库阈值" help="置信度大于或等于该阈值时，文件将自动入库并可被 Agent 召回。">
          <t-input-number v-model="settings.high_threshold" :min="0" :max="1" :step="0.05" theme="column" />
        </t-form-item>
        <t-form-item><t-button v-if="canEdit" :disabled="disabled || !dirty" :loading="saving" @click="save">保存配置</t-button></t-form-item>
      </t-form>
      <t-empty v-else-if="!loading && !error" description="暂无配置" />
    </t-loading>
  </section>
</template>
<style scoped>
.review-settings{padding:16px 0;font-family:var(--app-font-family);font-size:var(--app-text-base)}.review-settings :deep(.t-alert){margin-bottom:16px}.review-settings :deep(.t-form__item){margin-bottom:24px}
.strategy-notes{margin-bottom:24px;padding:12px 16px;background:var(--td-bg-color-secondarycontainer);color:var(--td-text-color-secondary);font-size:var(--app-text-md);line-height:1.8}.strategy-notes p{margin:0}
</style>
