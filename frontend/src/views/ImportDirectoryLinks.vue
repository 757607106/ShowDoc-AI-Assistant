<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { importDirectories } from './importDirectories'
const props = defineProps<{ directories?: unknown }>()
const router = useRouter()
const items = computed(() => importDirectories(props.directories))
</script>
<template>
  <t-space v-if="items.length" size="small" break-line>
    <t-button v-for="item in items" :key="`${item.knowledge_base_id}:${item.node_id}`" size="small" variant="text"
      @click="router.push({path:'/platform/knowledge-bases/'+encodeURIComponent(item.knowledge_base_id),query:{tab:'documents',folder_id:item.node_id}})">
      查看导入目录 · {{item.root_name}}<t-icon name="jump" />
    </t-button>
  </t-space>
</template>
