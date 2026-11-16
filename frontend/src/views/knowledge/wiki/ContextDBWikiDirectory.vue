<script setup lang="ts">
import { ref, watch } from 'vue'
import { listWikiPages, type WikiPage } from '@/api/contextdbWiki'

const props = withDefaults(defineProps<{
  kbId: string
  parentId?: string
  selectedId?: string
  directoriesOnly?: boolean
  blockedId?: string
}>(), { parentId: '', selectedId: '', blockedId: '', directoriesOnly: false })
const emit = defineEmits<{ select: [page: WikiPage] }>()
const items = ref<WikiPage[]>([]), cursor = ref<string | null>(null)
const loading = ref(false), error = ref(''), expanded = ref(new Set<string>())
let request = 0
async function load(append = false) {
  if (loading.value || (append && !cursor.value)) return
  const token = ++request
  loading.value = true; error.value = ''
  try {
    const result = await listWikiPages(props.kbId, {
      parent_page_id: props.parentId || undefined,
      page_type: props.directoriesOnly ? 'category' : undefined,
      cursor: append ? cursor.value || undefined : undefined, limit: 50,
    })
    if (token !== request) return
    const existing = append ? items.value : []
    const seen = new Set(existing.map(item => item.page_id))
    items.value = [...existing, ...result.items.filter(item => !seen.has(item.page_id))]
    cursor.value = result.next_cursor || null
  } catch (e: any) { if (token === request) error.value = e.message || '目录读取失败' }
  finally { if (token === request) loading.value = false }
}
function toggle(id: string) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  expanded.value = next
}
watch(() => [props.kbId, props.parentId, props.directoriesOnly], () => {
  request++; loading.value = false; items.value = []; cursor.value = null; expanded.value = new Set()
  void load()
}, { immediate: true })
</script>

<template>
  <div class="native-wiki-tree" role="group">
    <div v-for="item in items" :key="item.page_id">
      <div class="tree-row" :class="{ selected: item.page_id === selectedId }">
        <button v-if="item.page_type === 'category'" class="tree-toggle" type="button"
          :aria-label="`${expanded.has(item.page_id) ? '收起' : '展开'}${item.display_title || item.title || '目录'}`"
          :aria-expanded="expanded.has(item.page_id)" :disabled="item.page_id === blockedId" @click="toggle(item.page_id)">
          <t-icon :name="expanded.has(item.page_id) ? 'chevron-down' : 'chevron-right'" />
        </button>
        <span v-else class="tree-spacer" />
        <button class="tree-label" type="button" :disabled="item.page_id === blockedId" @click="emit('select', item)">
          <t-icon :name="item.page_type === 'category' ? 'folder' : 'file'" />
          <span>{{ item.display_title || item.title || (item.page_type === 'category' ? '未命名目录' : '未命名页面') }}</span>
          <span v-if="item.run_state === 'pending'" class="tree-pending" title="编译中">·</span>
        </button>
      </div>
      <div v-if="item.page_type === 'category' && expanded.has(item.page_id)" class="tree-children">
        <ContextDBWikiDirectory :kb-id="kbId" :parent-id="item.page_id" :selected-id="selectedId"
          :directories-only="directoriesOnly" :blocked-id="blockedId" @select="emit('select', $event)" />
      </div>
    </div>
    <t-button v-if="cursor" size="small" variant="text" :loading="loading" @click="load(true)">加载更多</t-button>
    <div v-if="error" class="tree-error" role="alert">{{ error }} <t-button size="small" variant="text" @click="load(!!items.length)">重试</t-button></div>
    <div v-else-if="loading" class="tree-hint"><t-loading size="small" /> 正在读取</div>
    <div v-else-if="!items.length" class="tree-hint">暂无{{ directoriesOnly ? '子目录' : '页面' }}</div>
  </div>
</template>

<style scoped>
.tree-row{display:flex;align-items:center;min-height:34px;border-radius:var(--app-radius-sm);color:var(--td-text-color-secondary)}
.tree-row:hover{background:var(--td-bg-color-container-hover)}.tree-row.selected{background:var(--td-brand-color-light);color:var(--td-brand-color)}
.tree-toggle,.tree-label{border:0;background:transparent;color:inherit;cursor:pointer;font:inherit;display:flex;align-items:center}
.tree-toggle,.tree-spacer{width:24px;flex:none;justify-content:center}.tree-toggle{height:30px;padding:0}
.tree-label{gap:8px;min-width:0;flex:1;text-align:left;padding:7px 8px 7px 0;font-size:var(--app-text-md)}
.tree-label>span:first-of-type{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.tree-label:disabled{opacity:.45;cursor:default}
.tree-pending{color:var(--td-warning-color);font-size:var(--app-text-3xl)}.tree-children{padding-left:16px;border-left:1px solid var(--td-component-stroke);margin-left:12px}
.tree-hint,.tree-error{padding:8px 12px;font-size:var(--app-text-sm);color:var(--td-text-color-placeholder)}.tree-error{color:var(--td-error-color)}
</style>
