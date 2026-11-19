<script setup lang="ts">
import { ref, watch } from 'vue'
import { listWikiPages, type WikiPage } from '@/api/contextdbWiki'
import KnowledgeActionMenu from '../components/KnowledgeActionMenu.vue'

const props = withDefaults(defineProps<{
  kbId: string
  parentId?: string
  selectedId?: string
  directoriesOnly?: boolean
  blockedId?: string
  canEdit?: boolean
}>(), { parentId: '', selectedId: '', blockedId: '', directoriesOnly: false, canEdit: false })
type Action = 'rename' | 'move' | 'archive' | 'delete'
const emit = defineEmits<{ select: [page: WikiPage]; action: [action: Action, page: WikiPage] }>()
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
  <div class="native-wiki-tree" role="group" aria-label="页面目录">
    <div v-for="item in items" :key="item.page_id">
      <div class="tree-row" :class="{ selected: item.page_id === selectedId }">
        <button v-if="item.page_type === 'category'" class="tree-toggle" type="button"
          :aria-label="`${expanded.has(item.page_id) ? '收起' : '展开'}${item.display_title || item.title || '目录'}`"
          :aria-expanded="expanded.has(item.page_id)" :disabled="item.page_id === blockedId" @click="toggle(item.page_id)">
          <t-icon :name="expanded.has(item.page_id) ? 'chevron-down' : 'chevron-right'" />
        </button>
        <span v-else class="tree-spacer" />
        <button class="tree-label" type="button" :disabled="item.page_id === blockedId" :aria-current="item.page_id === selectedId ? 'page' : undefined" @click="emit('select', item)">
          <span>{{ item.display_title || item.title || (item.page_type === 'category' ? '未命名目录' : '未命名页面') }}</span>
        </button>
        <span v-if="item.run_state==='pending'" class="tree-status">编译中</span>
        <span v-else-if="item.page_type!=='category'&&item.published" class="tree-status">正式</span>
        <KnowledgeActionMenu v-if="canEdit" icon-only :disabled="item.run_state==='pending'" :label="`更多 ${item.display_title||item.title||'未命名条目'}`"
          :options="[{content:'重命名',value:'rename'},{content:'移动',value:'move'},...(item.page_type!=='category'?[{content:'归档',value:'archive'}]:[]),{content:'删除',value:'delete',theme:'error'}]"
          @select="(value: string) => emit('action', value as Action, item)" />
      </div>
      <div v-if="item.page_type === 'category' && expanded.has(item.page_id)" class="tree-children">
        <ContextDBWikiDirectory :kb-id="kbId" :parent-id="item.page_id" :selected-id="selectedId"
          :directories-only="directoriesOnly" :blocked-id="blockedId" :can-edit="canEdit" @select="emit('select', $event)" @action="(next,target)=>emit('action',next,target)" />
      </div>
    </div>
    <t-button v-if="cursor" size="small" variant="text" :loading="loading" @click="load(true)">加载更多</t-button>
    <div v-if="error" class="tree-error" role="alert">{{ error }} <t-button size="small" variant="text" @click="load(!!items.length)">重试</t-button></div>
    <div v-else-if="loading" class="tree-hint"><t-loading size="small" /> 正在读取</div>
    <div v-else-if="!items.length" class="tree-hint">暂无{{ directoriesOnly ? '子目录' : '页面' }}</div>
  </div>
</template>

<style scoped>
.tree-row{display:flex;align-items:center;min-height:36px;border-radius:var(--app-radius-xs);color:var(--td-text-color-primary);font-family:var(--app-font-family)}
.tree-row:hover{background:var(--td-bg-color-container-hover)}.tree-row.selected{background:var(--app-selection-bg);color:var(--app-selection-text)}
.tree-toggle,.tree-label{border:0;background:transparent;color:inherit;cursor:pointer;font:inherit;display:flex;align-items:center}
.tree-toggle,.tree-spacer{width:20px;flex:none;justify-content:center}.tree-toggle{height:30px;padding:0}
.tree-label{min-width:0;flex:1;text-align:left;padding:8px 4px 8px 0;font-size:var(--app-text-base);line-height:20px}
.tree-label>span:first-of-type{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.tree-label:disabled{opacity:.45;cursor:default}
.tree-status{font-size:var(--app-text-sm);color:var(--td-text-color-placeholder);white-space:nowrap;margin-right:4px}.tree-row :deep(.t-button){width:24px;height:28px;color:var(--td-text-color-secondary)}.tree-children{padding-left:16px}
.tree-hint,.tree-error{padding:8px 12px;font-size:var(--app-text-sm);color:var(--td-text-color-placeholder)}.tree-error{color:var(--td-error-color)}
</style>
