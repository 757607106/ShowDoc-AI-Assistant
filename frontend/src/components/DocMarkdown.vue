<script setup lang="ts">
import { watch, ref, nextTick } from 'vue'
import { renderDocumentPreviewMarkdown } from '@/utils/documentPreviewMarkdown'
import { hydrateProtectedFileImages } from '@/utils/security'
import ContextDBAttachment from './ContextDBAttachment.vue'
import type { KnowledgeAttachment } from '@/utils/contextdbResources'

const props = defineProps<{ content: string; title?: string; sourceName?: string; sourceDisplayName?: string;
  attachments?: KnowledgeAttachment[]; kbId?: string; sourceBaseUrl?: string }>()
const html = ref('')
const showSource = ref(false)
const body = ref<HTMLElement | null>(null)

function render() {
  let content = props.content || ''
  if (props.sourceDisplayName && /^doc-[a-f\d]{64}\.[a-z\d]+$/i.test(props.sourceName || '')) {
    // Only the parser's standalone filename labels are presentation aliases.
    content = content.split('\n').map(line => line.trim().replace(/^#{1,6}\s+/, '') === props.sourceName ? props.sourceDisplayName : line).join('\n')
  }
  html.value = renderDocumentPreviewMarkdown(content, undefined, { titles: [props.title], sourceBaseUrl: props.sourceBaseUrl })
  void nextTick(() => hydrateProtectedFileImages(body.value))
}
watch(() => [props.content, props.title, props.sourceName, props.sourceDisplayName, props.sourceBaseUrl, showSource.value], render, {immediate:true})
</script>

<template>
  <div class="doc-markdown">
    <div class="doc-markdown-toggle">
      <t-button size="small" variant="text" @click="showSource = !showSource">
        {{ showSource ? '渲染视图' : '源码' }}
      </t-button>
    </div>
    <pre v-if="showSource" class="doc-markdown-source">{{ content }}</pre>
    <div v-else ref="body" class="doc-markdown-body" v-html="html"></div>
    <ContextDBAttachment v-for="(attachment, index) in attachments || []" :key="attachment.asset_id || `${attachment.chunk_index}:${attachment.attachment_index}`" :attachment="attachment" :kb-id="kbId" :label="`来源${attachment.type === 'image' ? '图片' : '音视频'} ${index + 1}`" />
  </div>
</template>

<style scoped>
.doc-markdown { position: relative; }
.doc-markdown-toggle { position: absolute; top: 0; right: 0; z-index: 1; }
.doc-markdown-source {
  background: var(--td-bg-color-component); padding: 12px; border-radius: 6px;
  font-family: ui-monospace, monospace; font-size: 12px; overflow: auto; max-height: 400px;
  white-space: pre-wrap; word-break: break-word;
}
.doc-markdown-body { font-size: 13px; line-height: 1.6; }
.doc-markdown-body :deep(img) { max-width: 100%; height: auto; }
.doc-markdown-body :deep(a) { color: var(--td-brand-color); overflow-wrap: anywhere; }
.doc-markdown-body :deep(pre) {
  background: var(--td-bg-color-component); padding: 10px; border-radius: 6px; overflow: auto;
}
.doc-markdown-body :deep(code) { font-family: ui-monospace, monospace; }
.doc-markdown-body :deep(table) { border-collapse: collapse; margin: 8px 0; }
.doc-markdown-body :deep(th), .doc-markdown-body :deep(td) {
  border: 1px solid var(--td-component-stroke); padding: 4px 8px;
}
</style>
