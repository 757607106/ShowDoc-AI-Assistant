<template>
  <div class="graph-query-results">
    <!-- Graph Configuration Card -->
    <div v-if="data?.graph_config && !contextChunks" class="stats-card">
      <div class="stats-title">{{ $t('chat.graphConfigTitle') }}</div>
      <div class="info-field">
        <span class="field-label">{{ $t('chat.entityTypesLabel') }}</span>
        <span class="field-value">{{ data.graph_config.nodes.join(', ') }}</span>
      </div>
      <div class="info-field">
        <span class="field-label">{{ $t('chat.relationTypesLabel') }}</span>
        <span class="field-value">{{ data.graph_config.relations.join(', ') }}</span>
      </div>
    </div>

    <!-- Results List -->
    <div v-if="results.length > 0" class="results-list">
      <div class="results-header">
        {{ contextChunks ? `图谱关联信息（${results.length}）` : $t('chat.graphResultsHeader', { count: data?.count }) }}
      </div>
      
      <div 
        v-for="result in results"
        :key="result.chunk_id"
        class="result-card"
      >
        <div class="result-header" @click="toggleResult(result.chunk_id)">
          <div class="result-title">
            <span class="result-index">#{{ result.result_index }}</span>
            <span v-if="!contextChunks" class="relevance-badge" :class="getRelevanceClass(result.relevance_level)">
              {{ getRelevanceLabel(result.relevance_level) }}
            </span>
            <span class="knowledge-title">{{ result.knowledge_title }}</span>
          </div>
          <div class="result-meta">
            <span v-if="!contextChunks && typeof result.score === 'number'" class="score">相关度 {{ result.score }}</span>
            <span class="expand-icon" :class="{ expanded: expandedResults.includes(result.chunk_id) }">
              ▶
            </span>
          </div>
        </div>
        
        <div class="result-content" :class="{ expanded: expandedResults.includes(result.chunk_id) }">
          <div class="full-content">{{ result.content }}</div>
          <slot v-if="contextChunks" name="sources" :chunk="contextChunks[result.result_index - 1]" />
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      {{ $t('chat.graphNoResults') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { GraphQueryResultsData, RelevanceLevel } from '@/types/tool-results';
import { useI18n } from 'vue-i18n';

const props = defineProps<{
  data?: GraphQueryResultsData;
  contextChunks?: any[];
}>();
const results = computed(() => props.contextChunks
  ? props.contextChunks.map((chunk, index) => ({chunk_id:chunk.chunk_id, result_index:index+1,
    knowledge_title:chunk.graph?.entities?.map((entity:any)=>entity.entity_name).filter(Boolean).join('、') || '图谱关联信息',
    content:chunk.content ?? chunk.content_with_weight ?? '', score:undefined, relevance_level:undefined}))
  : props.data?.results || []);

const { t } = useI18n();

const expandedResults = ref<string[]>([]);

const toggleResult = (chunkId: string) => {
  const index = expandedResults.value.indexOf(chunkId);
  if (index > -1) {
    expandedResults.value.splice(index, 1);
  } else {
    expandedResults.value.push(chunkId);
  }
};

const getRelevanceClass = (level?: RelevanceLevel): string => {
  const classMap: Record<RelevanceLevel, string> = {
    'High Relevance': 'high',
    'Medium Relevance': 'medium',
    'Low Relevance': 'low',
    'Weak Relevance': 'weak',
  };
  return level ? classMap[level] || 'weak' : 'weak';
};

const getRelevanceLabel = (level?: RelevanceLevel): string => {
  const labelMap: Record<RelevanceLevel, string> = {
    'High Relevance': t('chat.relevanceHigh'),
    'Medium Relevance': t('chat.relevanceMedium'),
    'Low Relevance': t('chat.relevanceLow'),
    'Weak Relevance': t('chat.relevanceWeak'),
  };
  return level ? labelMap[level] || level : '';
};
</script>

<style lang="less" scoped>
@import './tool-results.less';

.graph-query-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.results-header {
  font-size: var(--app-text-md);
  font-weight: 600;
  color: var(--td-text-color-primary);
  padding: 4px 0;
}

.result-index {
  font-size: var(--app-text-md);
  color: var(--td-text-color-placeholder);
  font-weight: 600;
}

.knowledge-title {
  font-size: var(--app-text-md);
  color: var(--td-text-color-primary);
  flex: 1;
}

.score {
  font-size: var(--app-text-sm);
  color: var(--td-text-color-placeholder);
  font-weight: 500;
}
</style>

