<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { getDocument, downloadDocument } from '@/api/contextdb'
import { getKnowledgeDetailsCon } from '@/api/knowledge-base'
import { resolvePreviewKind } from '@/utils/filePreview'
import { documentDisplayName, documentDownloadName } from '@/utils/contextdbDocumentName'
import DocumentPreview from './document-preview.vue'
import DocMarkdown from './DocMarkdown.vue'
import ContextDBSourceResources from './ContextDBSourceResources.vue'

const props = defineProps<{ documentId: string; kbId?: string; title?: string }>()
const doc = ref<any>(null), loading = ref(false), error = ref(''), fileType = ref(''), chunks = ref<any[]>([])
let generation = 0
async function load() {
  const token = ++generation, id = props.documentId, kb = props.kbId
  doc.value = null; chunks.value = []; loading.value = true; error.value = ''
  try {
    const { data } = await getDocument(id)
    if (data.id !== id || (kb && data.knowledge_base_id !== kb)) throw new Error('原件不属于当前知识库')
    if (token !== generation) return
    doc.value = data
    fileType.value = String(data.name || '').split('.').pop()?.toLowerCase() || ''
    if (resolvePreviewKind(fileType.value) === 'unsupported') {
      for (let page = 1; ; page++) {
        const response = await getKnowledgeDetailsCon(id, page)
        if (token !== generation) return
        const batch = response.data || []
        chunks.value.push(...batch)
        if (!batch.length || chunks.value.length >= response.total) break
      }
    }
  } catch (e: any) { if (token === generation) error.value = e?.message || '原件读取失败' }
  finally { if (token === generation) loading.value = false }
}
async function download() {
  const token = generation, id = props.documentId, name = documentDownloadName(doc.value)
  try {
    const blob = await downloadDocument(id)
    if (token !== generation) return
    const url = URL.createObjectURL(blob), anchor = document.createElement('a')
    anchor.href = url; anchor.download = name; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e: any) { if (token === generation) error.value = e?.message || '原件下载失败' }
}
watch(() => [props.documentId, props.kbId], load, { immediate: true })
onUnmounted(() => { generation++ })
</script>

<template>
  <section class="contextdb-source-preview" aria-label="原件预览">
    <t-loading v-if="loading" text="正在读取原件" />
    <p v-if="error" role="alert">{{ error }} <t-button size="small" variant="text" @click="load">重试</t-button></p>
    <template v-if="doc">
      <template v-if="resolvePreviewKind(fileType) === 'unsupported'">
        <p>此格式显示解析预览，可下载原件查看完整格式。<t-button size="small" variant="text" @click="download">下载原件</t-button></p>
        <DocMarkdown v-for="chunk in chunks" :key="chunk.id" :content="chunk.content || ''" :source-name="doc.name" :source-display-name="title || documentDisplayName(doc)" />
      </template>
      <DocumentPreview v-else :key="documentId" :knowledge-id="documentId" :file-type="fileType" :file-name="doc.name" :display-name="title || documentDisplayName(doc)" active />
      <ContextDBSourceResources :document-ids="[documentId]" :kb-id="kbId" />
    </template>
  </section>
</template>

<style scoped>
.contextdb-source-preview { min-width: 0; }
.contextdb-source-preview :deep(.document-preview) { min-height: 320px; }
</style>
