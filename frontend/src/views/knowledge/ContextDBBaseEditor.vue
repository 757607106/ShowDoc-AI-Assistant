<script setup lang="ts">
import { ref, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import SettingsModalShell from '@/components/SettingsModalShell.vue'
import { createBase, getBase, updateBase } from '@/api/contextdb'
const props = defineProps<{visible: boolean; mode: 'create' | 'edit'; kbId?: string | null; initialType?: string}>()
const emit = defineEmits(['update:visible', 'success'])
const name = ref(''), description = ref(''), mode = ref('wiki'), section = ref('basic')
const loading = ref(false), saving = ref(false)
watch(() => [props.visible, props.kbId], async () => {
  if (!props.visible) return
  name.value = ''; description.value = ''; mode.value = 'wiki'; loading.value = true
  try {
    if (props.mode === 'edit' && props.kbId) {
      const { data } = await getBase(props.kbId)
      name.value = data.space_name || data.name; description.value = data.description || ''
      mode.value = data.wiki_enabled ? 'wiki' : data.graph_enabled ? 'graph' : 'search'
    }
  } catch (e: any) { MessagePlugin.error(e.message) }
  finally { loading.value = false }
}, { immediate: true })
async function save() {
  if (!name.value.trim()) { MessagePlugin.warning('请输入知识库名称'); return }
  saving.value = true
  try {
    const data = { name: name.value.trim(), description: description.value,
      indexing_strategy: { wiki_enabled: mode.value === 'wiki', graph_enabled: mode.value === 'graph' } }
    const result = props.mode === 'edit' && props.kbId ? await updateBase(props.kbId, data) : await createBase(data)
    emit('success', result.data.id); emit('update:visible', false)
    MessagePlugin.success('知识库已保存')
  } catch (e: any) { MessagePlugin.error(e.message) }
  finally { saving.value = false }
}
</script>
<template>
  <SettingsModalShell :visible="visible" :title="props.mode === 'create' ? '创建知识库' : '知识库设置'"
    v-model="section" :loading="loading" :nav-groups="[{key:'basic',label:'知识库',items:[{key:'basic',icon:'folder',label:'基本信息'}]}]"
    @close="emit('update:visible', false)">
    <t-form label-align="top" class="native-form" @submit.prevent="save">
      <t-form-item label="知识库名称" required><t-input v-model="name" :maxlength="200" /></t-form-item>
      <t-form-item label="知识库说明"><t-textarea v-model="description" :autosize="{minRows:3,maxRows:6}" /></t-form-item>
      <t-form-item label="知识库类型"><t-radio-group v-model="mode" :disabled="props.mode === 'edit'">
        <t-radio-button value="search">文档检索</t-radio-button><t-radio-button value="wiki">Wiki</t-radio-button>
        <t-radio-button value="graph">知识图谱</t-radio-button>
      </t-radio-group></t-form-item>
    </t-form>
    <template #footer><t-button variant="outline" @click="emit('update:visible',false)">取消</t-button><t-button :loading="saving" @click="save">保存</t-button></template>
  </SettingsModalShell>
</template>
<style scoped>.native-form{padding:24px;max-width:720px}</style>
