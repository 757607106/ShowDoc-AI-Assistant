<script setup lang="ts">
import { ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { createBase, getBase, updateBase } from '@/api/contextdb'
const props = defineProps<{visible: boolean; mode: 'create' | 'edit'; kbId?: string | null; initialType?: string}>()
const emit = defineEmits(['update:visible', 'success'])
const name = ref(''), description = ref(''), mode = ref('wiki')
const loading = ref(false), saving = ref(false), reviewEnabled = ref(false)
const modes = [
  { value: 'search', label: '零编译', description: '不对知识库内的知识进行再编译，适合直接查找信息、检索原文的场景。' },
  { value: 'graph', label: '图谱编译', description: '提取并关联跨文档的实体、关系与事实，构建知识图谱，适合需要串联多份文档、进行多跳检索与关系分析的场景。' },
  { value: 'wiki', label: 'Wiki 编译', description: '围绕主题与概念归纳跨文档知识，生成结构化 Wiki 页面，并通过链接组织成可导航的知识网络，适合系统阅读、知识梳理以及可视化管理与编辑的场景。' },
]
function activateReviewSwitch(event: KeyboardEvent) {
  if (![' ', 'Enter'].includes(event.key)) return
  event.preventDefault(); (event.currentTarget as HTMLElement).click()
}
watch(() => [props.visible, props.kbId], async () => {
  if (!props.visible) return
  name.value = ''; description.value = ''; mode.value = 'wiki'; reviewEnabled.value = false; loading.value = true
  try {
    if (props.mode === 'edit' && props.kbId) {
      const { data } = await getBase(props.kbId)
      name.value = data.name; description.value = data.description || ''; reviewEnabled.value = !!data.review_enabled
      mode.value = data.wiki_enabled ? 'wiki' : data.graph_enabled ? 'graph' : 'search'
    }
  } catch (e: any) { MessagePlugin.error(e.message) }
  finally { loading.value = false }
}, { immediate: true })
async function save() {
  if (saving.value || loading.value) return
  if (!name.value.trim()) { MessagePlugin.warning('请输入知识库名称'); return }
  if (name.value.trim().length > 255) { MessagePlugin.warning('知识库名称最多 255 字符'); return }
  saving.value = true
  try {
    const data = { name: name.value.trim(), description: description.value, review_enabled: reviewEnabled.value,
      indexing_strategy: { wiki_enabled: mode.value === 'wiki', graph_enabled: mode.value === 'graph' } }
    const result = props.mode === 'edit' && props.kbId ? await updateBase(props.kbId, data) : await createBase(data)
    emit('success', result.data.id); emit('update:visible', false)
    MessagePlugin.success('知识库已保存')
  } catch (e: any) { MessagePlugin.error(e.message) }
  finally { saving.value = false }
}
</script>
<template>
  <t-dialog dialog-class-name="contextdb-overlay" :visible="visible" :header="props.mode === 'create' ? '新建知识库' : '知识库设置'" width="720px"
    :close-btn="!saving" :close-on-overlay-click="!saving" :close-on-esc-keydown="!saving" @close="emit('update:visible', false)">
    <t-loading :loading="loading">
    <t-form label-align="top" class="native-form" @submit.prevent="save">
      <t-form-item label="名称" required><t-input v-model="name" :maxlength="255" /></t-form-item>
      <t-form-item v-if="props.mode === 'edit'" label="知识库说明"><t-textarea v-model="description" :autosize="{minRows:3,maxRows:6}" /></t-form-item>
      <t-form-item label="知识评审"><t-switch v-model="reviewEnabled" role="switch" aria-label="知识评审" :aria-checked="reviewEnabled" :disabled="saving||loading" :tabindex="saving||loading?-1:0" @keydown="activateReviewSwitch" /></t-form-item>
      <t-form-item label="编译模式"><t-radio-group v-model="mode" class="mode-cards" :disabled="props.mode === 'edit' || saving || loading">
        <t-radio v-for="item in modes" :key="item.value" :value="item.value" class="mode-card" :class="{selected:mode===item.value}">
          <span>{{ item.label }}</span><p>{{ item.description }}</p>
        </t-radio>
      </t-radio-group></t-form-item>
      <p class="hint">创建后不可切换编译模式。</p>
    </t-form>
    </t-loading>
    <template #footer><t-button :loading="saving" :disabled="loading" @click="save">确定</t-button><t-button variant="outline" :disabled="saving" @click="emit('update:visible',false)">取消</t-button></template>
  </t-dialog>
</template>
<style scoped>
.native-form{padding:8px 0;font-family:var(--app-font-family);font-size:var(--app-text-base)}.hint{color:var(--td-text-color-secondary);line-height:1.6;margin:8px 0 0;font-size:var(--app-text-sm)}
.mode-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;width:100%}
.mode-card{display:flex;align-items:flex-start;height:auto;padding:16px;border:1px solid var(--td-component-border);border-radius:var(--td-radius-default);cursor:pointer;white-space:normal}
.mode-card :deep(.t-radio__label){white-space:normal}
.mode-card.selected{border-color:var(--app-selection-border);background:var(--app-selection-bg);color:var(--app-selection-text)}
.mode-card p{margin:12px 0 0;color:var(--td-text-color-secondary);font-size:var(--app-text-md);line-height:1.7;white-space:normal}
@media(max-width:640px){.mode-cards{grid-template-columns:1fr}}
</style>

<style scoped lang="less">
@import './knowledgePageLayout.less';
</style>
