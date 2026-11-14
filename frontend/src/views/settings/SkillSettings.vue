<template>
  <div class="skill-settings">
    <div class="section-header">
      <h2>{{ $t('settings.skills.title') }}</h2>
      <p class="section-description">技能作为官方 Agent 的指令和文件加载，不执行安装脚本。</p>
    </div>
    <t-loading v-if="loading" :text="$t('common.loading')" />
    <template v-else>
      <Teleport to="#toolbox-toolbar" defer>
        <t-input v-if="catalog.length" v-model="query" class="list-search" :placeholder="$t('menu.search')" clearable>
          <template #prefix-icon><t-icon name="search" size="16px" /></template>
        </t-input>
      </Teleport>
      <t-empty v-if="!filteredCatalog.length" :description="$t('common.noResult')" />
      <div class="skill-list">
        <article v-for="item in filteredCatalog" :key="item.id" class="skill-card">
          <div class="skill-card__body">
            <h3>{{ item.name }} <small v-if="item.version">{{ item.version }}</small></h3>
            <p v-if="item.description">{{ item.description }}</p>
          </div>
          <div class="skill-card__actions">
            <t-button variant="text" :title="$t('settings.sandbox.skillFiles')" @click="openCatalogFiles(item)"><folder-icon /></t-button>
            <t-button variant="text" theme="danger" :title="$t('common.delete')" :loading="deletingId === item.id" @click="askDelete(item)"><delete-icon /></t-button>
          </div>
        </article>
      </div>
      <t-button theme="primary" variant="outline" @click="openAdd">{{ $t('settings.skills.addSkill') }}</t-button>
    </template>
    <SettingDrawer v-model:visible="showAdd" :title="$t('settings.skills.addSkill')" :icon="SKILL_ICON"
      width="560px" :confirm-loading="addBusy" :confirm-disabled="addPrimaryDisabled" :confirm-text="$t('settings.skills.addFinish')" @confirm="registerCatalog">
      <section class="setting-drawer__section">
        <h4>来源地址</h4>
        <t-input v-model="sourceInput" :disabled="addBusy || Boolean(pendingFile)" placeholder="技能仓库或文件地址" />
      </section>
      <section class="setting-drawer__section">
        <p>{{ $t('settings.sandbox.skillUploadSectionHint', { size: maxSkillBundleMB }) }}</p>
        <input ref="fileInputRef" type="file" accept=".zip,.md" hidden @change="onFileChange" />
        <div class="file-upload-area" @click="!addBusy && fileInputRef?.click()" @dragover.prevent @drop.prevent="onFileDrop">
          <t-icon name="cloud-upload" size="32px" />
          <span>{{ pendingFile?.name || $t('settings.sandbox.skillUploadClick') }}</span>
          <t-progress v-if="addBusy && pendingFile" :percentage="uploadPercent" size="small" />
        </div>
        <t-button v-if="pendingFile" variant="text" :disabled="addBusy" @click="pendingFile = null">{{ $t('settings.skills.addClearFile') }}</t-button>
      </section>
    </SettingDrawer>
    <SkillFilesDrawer v-model:visible="filesDrawerVisible" :catalog-id="filesCatalogId" :skill-name="filesCatalogName" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MessagePlugin } from 'tdesign-vue-next'
import { DeleteIcon, FolderIcon } from 'tdesign-icons-vue-next'
import SkillFilesDrawer from '@/components/SkillFilesDrawer.vue'
import SettingDrawer from '@/components/settings/SettingDrawer.vue'
import { useConfirmDelete } from '@/components/settings/useConfirmDelete'
import { matchesResourceQuery } from '@/utils/resourceListSearch'
import { useAssistantDataChange } from '@/utils/assistantDataChange'
import { MAX_SKILL_BUNDLE_SIZE_MB } from '@/utils'
import { SKILL_ICON } from '@/types/mention'
import { listSkillCatalog, registerSkillCatalogFromFile, registerSkillCatalogFromSource, deleteSkillCatalog, type SkillCatalogItem } from '@/api/skill'

defineProps<{ initialSandboxId?: string }>()
const emit = defineEmits<{ count: [value: number] }>()
const { t } = useI18n()
const confirmDelete = useConfirmDelete()
const catalog = ref<SkillCatalogItem[]>([])
const query = ref('')
const filteredCatalog = computed(() => catalog.value.filter(item => matchesResourceQuery(item, query.value)))
const loading = ref(false)
const deletingId = ref('')
const showAdd = ref(false)
const addBusy = ref(false)
const pendingFile = ref<File | null>(null)
const sourceInput = ref('')
const uploadPercent = ref(0)
const fileInputRef = ref<HTMLInputElement>()
const maxSkillBundleMB = Math.min(MAX_SKILL_BUNDLE_SIZE_MB, 99)
const addPrimaryDisabled = computed(() => addBusy.value || (!pendingFile.value && !sourceInput.value.trim()))
const filesDrawerVisible = ref(false)
const filesCatalogId = ref('')
const filesCatalogName = ref('')

async function loadCatalog(silent = false) {
  if (!silent) loading.value = true
  try {
    const result = await listSkillCatalog()
    catalog.value = result.data || []
    emit('count', catalog.value.length)
  } catch (error: any) { if (!silent) MessagePlugin.error(error?.message || t('settings.skills.loadFailed')) }
  finally { loading.value = false }
}
function openCatalogFiles(item: SkillCatalogItem) {
  filesCatalogId.value = item.id
  filesCatalogName.value = item.name
  filesDrawerVisible.value = true
}
function openAdd() {
  pendingFile.value = null
  sourceInput.value = ''
  showAdd.value = true
}
function acceptPendingFile(file: File) {
  if (addBusy.value) return
  if (!/\.(zip|md)$/i.test(file.name)) {
    MessagePlugin.error(t('settings.sandbox.skillUploadFailed'))
    return
  }
  if (file.size > maxSkillBundleMB * 1024 * 1024) {
    MessagePlugin.error(t('settings.sandbox.skillBundleTooLarge', { size: maxSkillBundleMB }))
    return
  }
  pendingFile.value = file
}
function onFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) acceptPendingFile(file)
}
function onFileDrop(event: DragEvent) {
  const file = event.dataTransfer?.files[0]
  if (file) acceptPendingFile(file)
}
async function registerCatalog() {
  if (addPrimaryDisabled.value) return
  addBusy.value = true
  try {
    if (pendingFile.value) await registerSkillCatalogFromFile(pendingFile.value, percent => { uploadPercent.value = percent })
    else await registerSkillCatalogFromSource(sourceInput.value.trim())
    showAdd.value = false
    MessagePlugin.success(t('settings.skills.registerAccepted'))
    await loadCatalog(true)
  } catch (error: any) { MessagePlugin.error(error?.message || t('settings.sandbox.skillUploadFailed')) }
  finally {
    addBusy.value = false
    uploadPercent.value = 0
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}
function askDelete(item: SkillCatalogItem) {
  confirmDelete({ body: t('settings.skills.deleteCatalogConfirm', { name: item.name }), onConfirm: async () => {
    deletingId.value = item.id
    try {
      await deleteSkillCatalog(item.id)
      await loadCatalog(true)
      MessagePlugin.success(t('settings.skills.deleteSuccess'))
    } catch (error: any) { MessagePlugin.error(error?.message || t('common.deleteFailed')) }
    finally { deletingId.value = '' }
  } })
}
onMounted(() => loadCatalog())
useAssistantDataChange(() => { void loadCatalog(true) }, { areas: ['skill'] })
defineExpose({ openAdd })
</script>

<style lang="less" scoped>
@import (reference) '@/components/css/settings-section.less';
.section-header { .settings-section-header(); }
.skill-settings { width: 100%; }
.skill-list { display: flex; flex-direction: column; gap: 12px; margin: 20px 0; }
.skill-card { display: flex; align-items: flex-start; gap: 16px; padding: 16px; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); }
.skill-card__body { flex: 1; min-width: 0; }
.skill-card h3 { margin: 0 0 6px; font-size: var(--app-text-md); }
.skill-card small, .skill-card p { color: var(--td-text-color-secondary); }
.skill-card p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.skill-card__actions { display: flex; }
.file-upload-area { border: 1px dashed var(--td-component-border); padding: 28px; display: flex; flex-direction: column; align-items: center; gap: 12px; cursor: pointer; }
</style>
