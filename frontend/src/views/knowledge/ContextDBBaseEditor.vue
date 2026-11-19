<script setup lang="ts">
import KnowledgeOverlay from './components/KnowledgeOverlay.vue'
import { computed, onUnmounted, ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { createBase, getBase, updateBase } from '@/api/contextdb'
const props = defineProps<{visible: boolean; mode: 'create' | 'edit'; kbId?: string | null; initialType?: string}>()
const emit = defineEmits(['update:visible', 'success'])
const name = ref(''), description = ref(''), mode = ref('wiki')
const loading = ref(false), saving = ref(false), reviewEnabled = ref(false)
const loadError = ref(''), saveError = ref('')
let request = 0
const modes = [
  { value: 'search', label: '零编译', description: '不对知识库内的知识进行再编译，适合直接查找信息、检索原文的场景。' },
  { value: 'graph', label: '图谱编译', description: '提取并关联跨文档的实体、关系与事实，构建知识图谱，适合需要串联多份文档、进行多跳检索与关系分析的场景。' },
  { value: 'wiki', label: 'Wiki 编译', description: '围绕主题与概念归纳跨文档知识，生成结构化 Wiki 页面，并通过链接组织成可导航的知识网络，适合系统阅读、知识梳理以及可视化管理与编辑的场景。' },
]
const currentMode = computed(() => modes.find(item => item.value === mode.value))
function activateReviewSwitch(event: KeyboardEvent) {
  if (![' ', 'Enter'].includes(event.key)) return
  event.preventDefault(); (event.currentTarget as HTMLElement).click()
}
async function load() {
  const token = ++request
  loading.value = false
  if (!props.visible) return
  loadError.value = ''; saveError.value = ''
  name.value = ''; description.value = ''; mode.value = 'wiki'; reviewEnabled.value = false; loading.value = true
  try {
    if (props.mode === 'edit') {
      if (!props.kbId) throw new Error('缺少知识库标识，请重新打开设置。')
      const { data } = await getBase(props.kbId)
      if (token !== request) return
      name.value = data.name; description.value = data.description || ''; reviewEnabled.value = !!data.review_enabled
      mode.value = data.wiki_enabled ? 'wiki' : data.graph_enabled ? 'graph' : 'search'
    }
  } catch (e: any) { if (token === request) loadError.value = e.message || '无法读取知识库设置' }
  finally { if (token === request) loading.value = false }
}
watch(() => [props.visible, props.kbId, props.mode], load, { immediate: true })
onUnmounted(() => { request++ })
async function save() {
  if (!props.visible || saving.value || loading.value || loadError.value) return
  saveError.value = ''
  if (!name.value.trim()) { saveError.value = '请输入知识库名称'; return }
  if (name.value.trim().length > 255) { saveError.value = '知识库名称最多 255 字符'; return }
  const token = request
  saving.value = true
  try {
    const data = { name: name.value.trim(), description: description.value, review_enabled: reviewEnabled.value,
      indexing_strategy: { wiki_enabled: mode.value === 'wiki', graph_enabled: mode.value === 'graph' } }
    const result = props.mode === 'edit' && props.kbId ? await updateBase(props.kbId, data) : await createBase(data)
    if (token !== request) return
    emit('success', result.data.id); emit('update:visible', false)
    MessagePlugin.success('知识库已保存')
  } catch (e: any) { if (token === request) saveError.value = e.message || '保存失败，请重试。' }
  finally { saving.value = false }
}
</script>
<template>
  <KnowledgeOverlay dialog-class-name="contextdb-overlay" :visible="visible" :header="props.mode === 'create' ? '新建知识库' : '知识库设置'" width="720px"
    :close-btn="!saving" :close-on-overlay-click="!saving" :close-on-esc-keydown="!saving" @close="emit('update:visible', false)">
    <t-alert v-if="loadError" role="alert" theme="error" :message="loadError"><template #operation><t-button variant="text" @click="load">重试读取</t-button></template></t-alert>
    <t-loading v-if="loading" text="正在读取知识库设置…" />
    <t-form v-else-if="!loadError" :disabled="saving" label-align="top" class="native-form" @submit.prevent="save">
      <t-form-item label="名称" required><t-input v-model="name" placeholder="输入知识库名称" :maxlength="255" /></t-form-item>
      <t-form-item v-if="props.mode === 'edit'" label="知识库说明"><t-textarea v-model="description" placeholder="说明此知识库的用途" :autosize="{minRows:3,maxRows:6}" /></t-form-item>
      <t-form-item label="知识评审"><t-switch v-model="reviewEnabled" role="switch" aria-label="知识评审" :aria-checked="reviewEnabled" :disabled="saving||loading" :tabindex="saving||loading?-1:0" @keydown="activateReviewSwitch" /></t-form-item>
      <t-form-item v-if="props.mode === 'edit'" label="编译模式">
        <div><strong>{{ currentMode?.label }}</strong><p class="hint">创建后不可切换编译模式。</p></div>
      </t-form-item>
      <template v-else>
      <p class="hint">创建后不可切换编译模式。</p>
      <t-form-item label="编译模式"><t-radio-group v-model="mode" class="mode-cards" :disabled="saving || loading">
        <t-radio v-for="item in modes" :key="item.value" :value="item.value" class="mode-card" :class="{selected:mode===item.value}">
          <span>{{ item.label }}</span><p>{{ item.description }}</p>
        </t-radio>
      </t-radio-group></t-form-item>
      </template>
    </t-form>
    <t-alert v-if="saveError" role="alert" theme="error" :message="saveError" />
    <template #footer><t-button variant="outline" :disabled="saving" @click="emit('update:visible',false)">取消</t-button><t-button :loading="saving" :disabled="loading || !!loadError" @click="save">{{ props.mode==='edit'?'保存设置':'创建知识库' }}</t-button></template>
  </KnowledgeOverlay>
</template>
<style scoped>
.native-form{padding:8px 0;max-height:min(60dvh,560px);overflow:auto;font-family:var(--app-font-family);font-size:var(--app-text-base)}.hint{color:var(--td-text-color-secondary);line-height:1.6;margin:8px 0 0;font-size:var(--app-text-sm)}
.mode-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;width:100%;align-items:stretch}
.mode-card{display:flex;align-items:flex-start;height:auto;padding:16px;border:1px solid var(--td-component-border);border-radius:var(--app-radius-md);cursor:pointer;white-space:normal}
.mode-cards .mode-card{margin-right:0}
.mode-card :deep(.t-radio__label){white-space:normal}
.mode-card.selected{border-color:var(--app-selection-border);background:var(--app-selection-bg);color:var(--app-selection-text)}
.mode-card p{margin:12px 0 0;color:var(--td-text-color-secondary);font-size:var(--app-text-md);line-height:1.7;white-space:normal}
@media(max-width:640px){.mode-cards{grid-template-columns:1fr}}
</style>

<style scoped lang="less">
@import './knowledgePageLayout.less';
</style>
