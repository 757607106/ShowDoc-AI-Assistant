<script setup lang="ts">
import { computed } from 'vue'
import SearchResults from './SearchResults.vue'
import GraphQueryResults from './GraphQueryResults.vue'
import StructuredFields from '@/components/StructuredFields.vue'
import DocMarkdown from '@/components/DocMarkdown.vue'
import { splitKnowledgeResults } from '@/utils/contextdbSearchResults'

const props=defineProps<{output:unknown}>()
const value=computed(()=>{
  if(typeof props.output!=='string')return props.output
  try{return JSON.parse(props.output)}catch{return props.output}
})
const structured=computed(()=>value.value!==null&&typeof value.value==='object')
const items=computed(()=>value.value?.chunks??value.value?.results)
const results=computed(()=>splitKnowledgeResults(Array.isArray(items.value)?items.value:[]))
const documents=computed(()=>results.value.documents.filter(item=>item.document_id||item.doc_id||item.knowledge_id).map(item=>({...item,
  knowledge_id:item.document_id||item.doc_id||item.knowledge_id,
  knowledge_title:item.doc_name||item.knowledge_title||'来源文档',
})))
const unlinked=computed(()=>results.value.documents.filter(item=>!item.document_id&&!item.doc_id&&!item.knowledge_id))
</script>

<template>
  <div class="contextdb-tool-result">
    <template v-if="Array.isArray(items)">
      <SearchResults v-if="documents.length" :data="{display_type:'search_results',results:documents}" />
      <GraphQueryResults v-if="results.graph.length" :context-chunks="results.graph" />
      <StructuredFields v-for="(item,index) in unlinked" :key="index" :model-value="item" readonly />
      <t-empty v-if="!items.length" size="small" description="暂无结果" />
    </template>
    <StructuredFields v-else-if="structured" :model-value="value" readonly />
    <DocMarkdown v-else :content="value==null?'未返回结果':String(value)" />
  </div>
</template>
