<script setup lang="ts">
interface Chunk {
  content: string
  doc_name?: string
  doc_id?: string
  similarity?: number
  toc_path?: string
}

defineProps<{ chunks: Chunk[]; title?: string }>()
</script>

<template>
  <div class="knowledge-chunks-list">
    <div v-if="title" class="chunks-header">{{ title }}</div>
    <div v-for="(chunk, index) in chunks" :key="index" class="chunk-card">
      <div class="chunk-meta">
        <t-tag size="small" variant="light">{{ chunk.doc_name || chunk.doc_id || '未命名' }}</t-tag>
        <span v-if="typeof chunk.similarity === 'number'" class="chunk-score">相关度 {{ chunk.similarity }}</span>
      </div>
      <div v-if="chunk.toc_path" class="chunk-toc">{{ chunk.toc_path }}</div>
      <div class="chunk-content">{{ chunk.content }}</div>
    </div>
    <t-empty v-if="!chunks.length" size="small" description="暂无知识片段" />
  </div>
</template>

<!-- Adapted from WeKnora KnowledgeChunksList (Tencent, MIT License) -->

<style scoped>
.chunks-header { font-weight: 600; margin-bottom: 8px; font-size: var(--app-text-md); }
.chunk-card {
  border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-sm);
  padding: 10px 12px; margin-bottom: 8px; background: var(--td-bg-color-container);
}
.chunk-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.chunk-score { font-size: var(--app-text-xs); color: var(--td-brand-color); font-weight: 600; }
.chunk-toc { font-size: var(--app-text-xs); opacity: .5; margin-bottom: 4px; }
.chunk-content {
  font-size: 12.5px; line-height: 1.5; max-height: 200px; overflow: hidden;
  position: relative;
}
.chunk-content::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 40px;
  background: linear-gradient(transparent, var(--td-bg-color-container));
}
</style>
