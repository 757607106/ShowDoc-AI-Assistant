<script setup lang="ts">
import { watch, ref } from 'vue'
import { renderDocumentPreviewMarkdown } from '@/utils/documentPreviewMarkdown'

const props = defineProps<{ content: string; title?: string }>()
const html = ref('')
const showSource = ref(false)

function render() {
  html.value = renderDocumentPreviewMarkdown(props.content || '', undefined, { titles: [props.title] })
}
watch(() => [props.content, props.title], render, {immediate:true})
</script>

<template>
  <div class="doc-markdown">
    <div class="doc-markdown-toggle">
      <t-button size="small" variant="text" @click="showSource = !showSource">
        {{ showSource ? '渲染视图' : '源码' }}
      </t-button>
    </div>
    <pre v-if="showSource" class="doc-markdown-source">{{ content }}</pre>
    <div v-else class="doc-markdown-body" v-html="html"></div>
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
.doc-markdown-body :deep(pre) {
  background: var(--td-bg-color-component); padding: 10px; border-radius: 6px; overflow: auto;
}
.doc-markdown-body :deep(code) { font-family: ui-monospace, monospace; }
.doc-markdown-body :deep(table) { border-collapse: collapse; margin: 8px 0; }
.doc-markdown-body :deep(th), .doc-markdown-body :deep(td) {
  border: 1px solid var(--td-component-stroke); padding: 4px 8px;
}
</style>
