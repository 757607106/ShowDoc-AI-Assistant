<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSpace } from '@/api/knowledgeSpaces'
const route = useRoute(), router = useRouter(), error = ref(''), loading = ref(false)
let request = 0
async function resolve() {
  const token = ++request, scope = String(route.params.scope)
  loading.value = true; error.value = ''
  try {
    const { space } = await getSpace(scope)
    if (token !== request) return
    const graph = route.query.target === 'graph' || route.query.tab === 'graph'
    const id = space.legacy_targets?.[graph?'graph':'wiki'] || (graph ? space.graph_kb_id : space.wiki_kb_id) || (!graph || space.mode==='graph' ? space.knowledge_base_id : null) || (!graph ? space.graph_kb_id : null)
    if (!id) throw new Error('该历史入口未绑定可读取的知识库，请返回知识库列表核对。')
    const query = { ...route.query }
    delete query.target
    if (query.tab === 'progress') query.tab = 'documents'
    await router.replace({ path: `/platform/knowledge-bases/${encodeURIComponent(id)}`, query })
  } catch (e: any) { if (token === request) error.value = e.message }
  finally { if (token === request) loading.value = false }
}
watch(() => route.fullPath, resolve, { immediate: true })
</script>
<template><t-loading :loading="loading" text="正在打开知识库"><t-alert v-if="error" theme="error" :message="error" /><t-space v-if="error"><t-button @click="resolve">重试</t-button><t-button variant="outline" @click="router.push('/platform/knowledge-bases')">返回知识库</t-button></t-space></t-loading></template>
