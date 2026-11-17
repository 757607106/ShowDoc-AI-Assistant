<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { loadDocumentResources, type DocumentResources } from '@/api/contextdbResources'
import ContextDBAttachment from './ContextDBAttachment.vue'
import DocumentPreview from './document-preview.vue'
import type { KnowledgeAttachment } from '@/utils/contextdbResources'

const props = defineProps<{ documentIds: string[]; kbId?: string }>()
const items = ref<Array<{ id: string; loading: boolean; error: string; originalOpen: boolean; resources?: DocumentResources }>>([])
let generation = 0
const isOriginalImage = (item: KnowledgeAttachment) => !!(item.source_image_hash || item.source_blob)
function additionalImages(resources: DocumentResources) {
  return resources.attachments.some(item => item.type === 'image' && !isOriginalImage(item))
    ? resources.attachments.filter(isOriginalImage) : []
}
function primaryAttachments(resources: DocumentResources) {
  const additional = additionalImages(resources)
  return resources.attachments.filter(item => !additional.includes(item))
}
async function load(id: string) {
  const row = items.value.find(item => item.id === id)
  if (!row || row.loading || row.resources) return
  const token = generation
  row.loading = true; row.error = ''; row.originalOpen = false
  try {
    const resources = await loadDocumentResources(id, props.kbId)
    if (token === generation) row.resources = resources
  } catch (e: any) { if (token === generation) row.error = e?.message || '来源资料读取失败' }
  finally { if (token === generation) row.loading = false }
}
watch(() => JSON.stringify([props.kbId, ...props.documentIds]), () => {
  generation++
  items.value = [...new Set(props.documentIds.filter(Boolean))].map(id => ({ id, loading: false, error: '', originalOpen: false }))
  if (items.value[0]) void load(items.value[0].id)
}, { immediate: true })
onUnmounted(() => { generation++ })
</script>

<template>
  <section v-if="items.length" class="source-resources" aria-label="来源图片与链接">
    <h4>来源图片与链接</h4>
    <details v-for="(item, index) in items" :key="item.id" :open="index === 0" @toggle="(event: Event) => { if ((event.target as HTMLDetailsElement).open) load(item.id) }">
      <summary>{{ item.resources?.name || '查看来源资料' }}</summary>
      <t-loading v-if="item.loading" text="正在读取来源资料" />
      <p v-if="item.error" role="alert">{{ item.error }} <t-button size="small" variant="text" @click="load(item.id)">重试</t-button></p>
      <template v-if="item.resources">
        <p v-if="item.resources.warning" role="status">{{ item.resources.warning }} <t-button size="small" variant="text" @click="item.resources=undefined;load(item.id)">重试</t-button></p>
        <ContextDBAttachment v-for="(attachment, position) in primaryAttachments(item.resources)" :key="attachment.asset_id || attachment.source_image_hash || attachment.embedded_key || `${attachment.chunk_index}:${attachment.attachment_index}`" :attachment="attachment" :kb-id="kbId" :label="`${item.resources.name} · ${attachment.type === 'image' ? '图片' : '音视频'} ${position + 1}`" />
        <details v-if="additionalImages(item.resources).length"><summary>查看原件中的图片（{{ additionalImages(item.resources).length }}）</summary><ContextDBAttachment v-for="(attachment, position) in additionalImages(item.resources)" :key="attachment.source_image_hash || attachment.embedded_key" :attachment="attachment" :kb-id="kbId" :label="`${item.resources.name} · 原件图片 ${position + 1}`" /></details>
        <details v-if="item.resources.sourceFile" @toggle="(event: Event) => { item.originalOpen = (event.target as HTMLDetailsElement).open }"><summary>查看来源原件</summary><DocumentPreview v-if="item.originalOpen" :source-blob="item.resources.sourceFile.blob" :file-name="item.resources.sourceFile.name" :file-type="item.resources.sourceFile.fileType" :display-name="item.resources.name" active /></details>
        <ul v-if="item.resources.links.length"><li v-for="link in item.resources.links" :key="link.url"><a :href="link.url" target="_blank" rel="noopener noreferrer">{{ link.text }}</a></li></ul>
        <p v-if="!item.resources.warning && !item.resources.attachments.length && !item.resources.links.length" class="source-empty">此来源没有独立的图片、音视频或外部链接。</p>
      </template>
    </details>
  </section>
</template>

<style scoped>
.source-resources { margin-top: 20px; border-top: 1px solid var(--td-component-stroke); padding-top: 12px; overflow-wrap: anywhere; }
.source-resources h4 { font-size: 14px; font-weight: 500; margin: 0 0 12px; }
.source-resources summary { cursor: pointer; color: var(--td-text-color-secondary); margin: 8px 0; }
.source-resources a { color: var(--td-brand-color); }
.source-resources ul { padding-left: 20px; }
.source-resources li { margin: 8px 0; }
.source-empty { color: var(--td-text-color-placeholder); font-size: 12px; }
</style>
