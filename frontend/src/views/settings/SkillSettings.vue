<template>
  <div class="skill-settings">
    <div class="section-header">
      <h2>{{ $t('settings.skills.title') }}</h2>
      <p class="section-description">{{ $t('settings.skills.description') }}</p>
    </div>
    <t-alert theme="info" :message="$t('settings.skills.nativeUsage')" />
    <t-alert v-if="error" theme="error" :message="error" />
    <t-button v-if="error" variant="outline" :loading="loading" @click="loadCatalog">{{ $t('common.retry') }}</t-button>
    <div v-if="loading" class="loading-container"><t-loading :text="$t('common.loading')" /></div>
    <template v-else>
      <Teleport to="#toolbox-toolbar" defer>
        <t-input v-if="catalog.length" v-model="query" class="list-search" :placeholder="$t('menu.search')" :aria-label="$t('menu.search')" clearable>
          <template #prefix-icon><t-icon name="search" size="16px" /></template>
        </t-input>
      </Teleport>
      <div v-if="!catalog.length || !filteredCatalog.length" class="empty-state">
        <t-empty :description="$t(catalog.length ? 'common.noResult' : 'settings.skills.emptyDesc')" />
        <div class="empty-actions">
          <t-button v-if="query" variant="outline" @click="query = ''">{{ $t('common.clear') }}</t-button>
          <t-button v-if="canManage" theme="primary" @click="openAdd">{{ $t('settings.skills.addSkill') }}</t-button>
        </div>
      </div>
      <div v-else class="skill-list">
        <article v-for="item in filteredCatalog" :key="item.id" class="skill-card">
          <div class="skill-card__header">
            <span class="skill-card__badge" aria-hidden="true">{{ item.name.slice(0, 1).toUpperCase() }}</span>
            <h3 class="skill-card__title" :title="item.name">{{ item.name }}</h3>
            <span v-if="item.version" class="skill-card__type">{{ item.version }}</span>
            <t-tag v-if="item.enabled === false" theme="default" size="small">{{ $t('settings.sandbox.skillDisabled') }}</t-tag>
            <button type="button" class="skill-card__icon-btn" :title="$t('settings.sandbox.skillFiles')" :aria-label="$t('settings.sandbox.skillFiles')" @click="openCatalogFiles(item)"><folder-icon size="14px" /></button>
            <button v-if="canManage" type="button" class="skill-card__icon-btn skill-card__icon-btn--danger" :disabled="deletingId === item.id" :title="$t('settings.skills.deleteCatalog')" :aria-label="$t('settings.skills.deleteCatalog')" @click="askDelete(item)"><delete-icon size="14px" /></button>
          </div>
          <p v-if="item.description" class="skill-card__desc">{{ item.description }}</p>
        </article>
        <button v-if="canManage" type="button" class="skill-card skill-card--add" @click="openAdd"><add-icon /><span>{{ $t('settings.skills.addSkill') }}</span></button>
      </div>
    </template>
    <SettingDrawer :visible="showAdd" :title="$t('settings.skills.addSkill')" :description="$t('settings.skills.addSourceDescription')" :icon="SKILL_ICON" width="680px" :min-width="560" :max-width="920" storage-key="setting-drawer:width:skill-catalog-add" :confirm-loading="addBusy" :confirm-disabled="addPrimaryDisabled" :confirm-text="$t('settings.skills.addStepRegister')" @update:visible="setAddVisible" @confirm="handleAddPrimary">
      <section class="setting-drawer__section">
        <h4>{{ $t('settings.sandbox.skillSourceSection') }}</h4>
        <p>{{ $t('settings.sandbox.skillSourceSectionHint', { size: maxSkillBundleMB }) }}</p>
        <t-input v-model="sourceInput" :placeholder="$t('settings.sandbox.skillSourcePlaceholder')" :disabled="addBusy || !!pendingFile" @enter="handleAddPrimary" />
      </section>
      <section class="setting-drawer__section">
        <h4>{{ $t('settings.sandbox.skillUploadSection') }}</h4>
        <p>{{ $t('settings.sandbox.skillUploadSectionHint', { size: maxSkillBundleMB }) }}</p>
        <input ref="fileInputRef" type="file" accept=".zip,application/zip" class="file-input-hidden" :disabled="addBusy" @change="onFileInputChange" />
        <button type="button" class="file-upload-area" :disabled="addBusy" @click="fileInputRef?.click()" @dragover.prevent @drop.prevent="onFileDrop">
          <t-icon name="cloud-upload" size="32px" />
          <span v-if="pendingFile">{{ $t('settings.skills.addFileSelected', { name: pendingFile.name }) }}</span>
          <span v-else>{{ $t('settings.sandbox.skillUploadClick') }} · {{ $t('settings.sandbox.skillUploadDrag') }}</span>
        </button>
        <t-progress v-if="uploading" :percentage="uploadPercent" size="small" />
        <t-button v-if="pendingFile" variant="text" size="small" :disabled="addBusy" @click="pendingFile = null">{{ $t('settings.skills.addClearFile') }}</t-button>
      </section>
    </SettingDrawer>
    <SkillFilesDrawer v-model:visible="filesDrawerVisible" :catalog-id="filesCatalogId" :skill-name="filesCatalogName" />
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon, DeleteIcon, FolderIcon } from 'tdesign-icons-vue-next'
import { useI18n } from 'vue-i18n'
import SkillFilesDrawer from '@/components/SkillFilesDrawer.vue'
import SettingDrawer from '@/components/settings/SettingDrawer.vue'
import { useConfirmDelete } from '@/components/settings/useConfirmDelete'
import { useAuthStore } from '@/stores/auth'
import { matchesResourceQuery } from '@/utils/resourceListSearch'
import { useAssistantDataChange } from '@/utils/assistantDataChange'
import { SKILL_ICON } from '@/types/mention'
import { MAX_SKILL_BUNDLE_SIZE_BYTES, MAX_SKILL_BUNDLE_SIZE_MB } from '@/utils'
import { deleteSkillCatalog, listSkillCatalog, registerSkillCatalogFromFile, registerSkillCatalogFromSource, type SkillCatalogItem } from '@/api/skill'

defineProps<{ initialSandboxId?: string }>()
const emit = defineEmits<{ count: [value: number] }>()
const { t } = useI18n()
const auth = useAuthStore()
const confirmDelete = useConfirmDelete()
const canManage = computed(() => auth.hasRole('admin'))
const loading = ref(false), error = ref(''), catalog = ref<SkillCatalogItem[]>([]), query = ref('')
const filteredCatalog = computed(() => catalog.value.filter(item => matchesResourceQuery(item, query.value)))
const showAdd = ref(false), pendingFile = ref<File | null>(null), sourceInput = ref(''), uploading = ref(false), addingFromSource = ref(false), uploadPercent = ref(0)
const fileInputRef = ref<HTMLInputElement | null>(null), deletingId = ref('')
const filesDrawerVisible = ref(false), filesCatalogId = ref(''), filesCatalogName = ref('')
const maxSkillBundleMB = MAX_SKILL_BUNDLE_SIZE_MB
const addBusy = computed(() => uploading.value || addingFromSource.value)
const addPrimaryDisabled = computed(() => !canManage.value || addBusy.value || (!pendingFile.value && !sourceInput.value.trim()))
let generation = 0, catalogRequest = 0

async function loadCatalog() {
  const identity = generation, request = ++catalogRequest
  loading.value = true; error.value = ''
  try {
    const res = await listSkillCatalog()
    if (identity !== generation || request !== catalogRequest) return
    catalog.value = res.data || []; emit('count', catalog.value.length)
  } catch (e: any) {
    if (identity === generation && request === catalogRequest) error.value = e.message || t('settings.skills.loadFailed')
  } finally {
    if (identity === generation && request === catalogRequest) loading.value = false
  }
}
function resetAdd() {
  pendingFile.value = null; sourceInput.value = ''; uploadPercent.value = 0
  if (fileInputRef.value) fileInputRef.value.value = ''
}
function openAdd() {
  if (!canManage.value || addBusy.value) return
  resetAdd(); showAdd.value = true
}
function setAddVisible(value: boolean) {
  if (addBusy.value) return
  showAdd.value = value
  if (!value) resetAdd()
}
function acceptPendingFile(file: File) {
  if (!canManage.value || addBusy.value) return
  if (!file.name.toLowerCase().endsWith('.zip') && file.type !== 'application/zip') {
    MessagePlugin.error(t('settings.sandbox.skillUploadFailed')); return
  }
  if (file.size > MAX_SKILL_BUNDLE_SIZE_BYTES) {
    MessagePlugin.error(t('settings.sandbox.skillBundleTooLarge', { size: maxSkillBundleMB })); return
  }
  pendingFile.value = file
}
function skillRegisterErrorMessage(err: any, fromFile: boolean) {
  const raw = String(err?.message || '')
  if (/cannot exceed \d+\s*MB/i.test(raw)) return t('settings.sandbox.skillBundleTooLarge', { size: maxSkillBundleMB })
  const files = raw.match(/(?:skill directory|archive) holds more than (\d+) files/i)
  if (files) return t('settings.sandbox.skillBundleTooManyFiles', { count: files[1] })
  const entries = raw.match(/archive has more than (\d+) zip entries/i)
  if (entries) return t('settings.sandbox.skillBundleTooManyZipEntries', { count: entries[1] })
  return raw || t(fromFile ? 'settings.sandbox.skillUploadFailed' : 'settings.sandbox.skillSourceFailed')
}
async function handleAddPrimary() {
  if (addPrimaryDisabled.value) return
  const identity = generation, file = pendingFile.value
  uploading.value = !!file; addingFromSource.value = !file; uploadPercent.value = 0
  try {
    if (file) await registerSkillCatalogFromFile(file, percent => { if (identity === generation) uploadPercent.value = percent })
    else await registerSkillCatalogFromSource(sourceInput.value.trim())
    if (identity !== generation) return
    showAdd.value = false; resetAdd()
    MessagePlugin.success(t('settings.skills.registerAccepted'))
    await loadCatalog()
  } catch (e: any) {
    if (identity === generation) MessagePlugin.error(skillRegisterErrorMessage(e, !!file))
  } finally {
    if (identity === generation) { uploading.value = false; addingFromSource.value = false; uploadPercent.value = 0 }
  }
}
function onFileInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) acceptPendingFile(input.files[0])
  input.value = ''
}
function onFileDrop(event: DragEvent) { if (event.dataTransfer?.files[0]) acceptPendingFile(event.dataTransfer.files[0]) }
function openCatalogFiles(item: SkillCatalogItem) {
  filesCatalogId.value = item.id; filesCatalogName.value = item.name; filesDrawerVisible.value = true
}
function askDelete(item: SkillCatalogItem) {
  if (!canManage.value || deletingId.value) return
  const identity = generation
  confirmDelete({ body: t('settings.skills.deleteCatalogConfirm', { name: item.name }), onConfirm: async () => {
    if (identity !== generation || !canManage.value || deletingId.value) return
    deletingId.value = item.id
    try {
      await deleteSkillCatalog(item.id)
      if (identity !== generation) return
      MessagePlugin.success(t('settings.skills.deleteSuccess')); await loadCatalog()
    } catch (e: any) {
      if (identity === generation) MessagePlugin.error(e.message || t('common.deleteFailed'))
    } finally { if (identity === generation) deletingId.value = '' }
  } })
}
watch(() => auth.user?.id, () => {
  generation++; catalog.value = []; query.value = ''; error.value = ''; deletingId.value = ''
  showAdd.value = false; filesDrawerVisible.value = false; filesCatalogId.value = ''; filesCatalogName.value = ''
  uploading.value = false; addingFromSource.value = false; resetAdd(); void loadCatalog()
}, { immediate: true })
useAssistantDataChange(() => { void loadCatalog() }, { areas: ['skill'] })
onUnmounted(() => { generation++ })
defineExpose({ openAdd })
</script>

<style lang="less" scoped>
@import (reference) '@/components/css/settings-section.less';
.skill-settings { width: 100%; display: flex; flex-direction: column; gap: 16px; }
.section-header { .settings-section-header(); }
.loading-container, .empty-state { padding: 40px 0; text-align: center; }
.empty-actions { display: flex; justify-content: center; gap: 8px; margin-top: 16px; }
.skill-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 12px; }
.skill-card { min-width: 0; padding: 14px; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); background: var(--td-bg-color-container); }
.skill-card__header { display: flex; align-items: center; gap: 8px; }
.skill-card__badge { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; flex-shrink: 0; border-radius: 7px; background: var(--td-brand-color-light); color: var(--td-brand-color); }
.skill-card__title { flex: 1; min-width: 0; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--app-text-base); }
.skill-card__type { font-size: var(--app-text-xs); color: var(--td-text-color-placeholder); }
.skill-card__desc { margin: 10px 0 0; color: var(--td-text-color-secondary); overflow-wrap: anywhere; }
.skill-card__icon-btn { display: inline-flex; align-items: center; justify-content: center; padding: 5px; border: 0; border-radius: var(--app-radius-sm); background: none; color: var(--td-text-color-secondary); cursor: pointer; }
.skill-card__icon-btn:hover { background: var(--td-bg-color-container-hover); }
.skill-card__icon-btn--danger:hover { color: var(--td-error-color); }
.skill-card__icon-btn:disabled { opacity: .4; cursor: not-allowed; }
.skill-card--add { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 88px; border-style: dashed; color: var(--td-text-color-secondary); cursor: pointer; }
.file-input-hidden { display: none; }
.file-upload-area { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; margin-top: 16px; padding: 24px; border: 1px dashed var(--td-component-stroke); border-radius: var(--app-radius-md); background: var(--td-bg-color-container); color: var(--td-text-color-secondary); cursor: pointer; }
.file-upload-area:disabled { cursor: not-allowed; opacity: .5; }
.setting-drawer__section { margin-bottom: 24px; }
.setting-drawer__section h4 { margin: 0 0 8px; }
.setting-drawer__section p { color: var(--td-text-color-secondary); }
</style>
