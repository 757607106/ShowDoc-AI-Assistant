<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { listWikiRevisions, getWikiRevisionDiff, type WikiRevision, type WikiRevisionDiff } from '@/api/contextdbWiki'
import { dateTime, stateLabel } from '@/utils/platformPresentation'

const props = defineProps<{ kbId: string; pageId: string; visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()
const revisions = ref<WikiRevision[]>([]), cursor = ref(''), target = ref(''), baseline = ref('')
const diff = ref<WikiRevisionDiff | null>(null), listError = ref(''), diffError = ref(''), loading = ref(false), comparing = ref(false)
const retryAppend = ref(false)
let listRequest = 0, diffRequest = 0
const options = computed(() => revisions.value.map(item => ({ value: item.revision_id,
  label: `${dateTime(item.created_at)} · ${item.edit_source === 'human' ? '人工编辑' : item.edit_source === 'agent' ? '智能体编辑' : '自动编译'} · ${stateLabel(item.review_status, 'revision')}` })))

async function load(append = false) {
  if (!props.visible || !props.pageId || (append && !cursor.value)) return
  const request = ++listRequest
  loading.value = true; listError.value = ''; retryAppend.value = append
  try {
    const result = await listWikiRevisions(props.kbId, props.pageId, { limit: 50, cursor: append ? cursor.value : undefined })
    if (request !== listRequest) return
    revisions.value = append ? [...revisions.value, ...result.items] : result.items
    cursor.value = result.next_cursor || ''
    if (!target.value && result.items.length) target.value = result.items[0]!.revision_id
  } catch (e: any) { if (request === listRequest) listError.value = e.message || '修订读取失败' }
  finally { if (request === listRequest) loading.value = false }
}
async function compare() {
  if (target.value && target.value === baseline.value) { baseline.value = ''; return }
  const request = ++diffRequest
  diff.value = null
  if (!props.visible || !target.value) { comparing.value = false; return }
  comparing.value = true; diffError.value = ''
  try {
    const result = await getWikiRevisionDiff(props.kbId, target.value, baseline.value || undefined)
    if (request === diffRequest) diff.value = result
  } catch (e: any) { if (request === diffRequest) diffError.value = e.message || '差异读取失败' }
  finally { if (request === diffRequest) comparing.value = false }
}
watch(() => [props.kbId, props.pageId, props.visible], () => {
  listRequest++; diffRequest++; revisions.value = []; cursor.value = ''; target.value = ''; baseline.value = ''
  diff.value = null; listError.value = ''; diffError.value = ''; loading.value = false; comparing.value = false
  if (props.visible) void load()
}, { immediate: true, flush: 'sync' })
watch([target, baseline], () => void compare())
</script>

<template>
  <t-drawer :visible="visible" header="版本历史" size="min(860px, 96vw)" :footer="false" :close-btn="true" @update:visible="(value: boolean) => emit('update:visible', value)">
    <div class="revision-toolbar">
      <label>查看版本<t-select v-model="target" :options="options" :loading="loading" placeholder="选择修订版本" /></label>
      <label>比较基准<t-select v-model="baseline" clearable :options="options.filter(item => item.value !== target)" placeholder="使用该修订的上一版本" /></label>
      <t-button variant="outline" :loading="loading" @click="load()">刷新</t-button>
    </div>
    <t-button v-if="cursor" variant="text" :loading="loading" @click="load(true)">加载更多版本</t-button>
    <t-alert v-if="listError" theme="error" :message="listError"><template #operation><t-button variant="text" @click="load(retryAppend)">重试读取版本</t-button></template></t-alert>
    <t-alert v-if="diffError" theme="error" :message="diffError"><template #operation><t-button variant="text" @click="compare">重试读取差异</t-button></template></t-alert>
    <t-loading :loading="comparing" class="revision-body">
      <template v-if="diff">
        <p class="diff-count"><span>新增 {{ diff.diff.added_count }} 行</span><span>删除 {{ diff.diff.removed_count }} 行</span></p>
        <t-alert v-if="diff.diff.truncated" theme="warning" message="差异已截断：任一版本超过 800 行时仅比较前 800 行，以下不是全文差异。" />
        <div class="diff-lines" aria-label="修订正文差异">
          <pre v-for="(hunk, index) in diff.diff.hunks" :key="index" :class="hunk.op"><span aria-hidden="true">{{ hunk.op === 'add' ? '+' : hunk.op === 'del' ? '−' : ' ' }}</span>{{ hunk.text }}</pre>
          <t-empty v-if="!diff.diff.hunks.length" description="这两个版本没有正文差异" />
        </div>
      </template>
      <t-empty v-else-if="!loading && !comparing && !listError && !diffError" :description="revisions.length ? '请选择要比较的版本' : '暂无修订记录'" />
    </t-loading>
  </t-drawer>
</template>

<style scoped lang="less">
.revision-toolbar{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.revision-toolbar label{display:flex;flex-direction:column;gap:6px;flex:1;min-width:200px;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}
.revision-body{display:block;min-height:160px}.diff-count{display:flex;gap:20px;color:var(--td-text-color-secondary)}
.diff-lines{margin-top:16px;border:1px solid var(--td-component-stroke);border-radius:var(--td-radius-default);overflow:hidden}
.diff-lines pre{margin:0;padding:6px 12px;white-space:pre-wrap;overflow-wrap:anywhere;font:var(--app-text-sm)/1.7 ui-monospace,monospace}
.diff-lines pre span{display:inline-block;width:20px;user-select:none}.add{background:var(--td-success-color-1);color:var(--td-success-color-8)}.del{background:var(--td-error-color-1);color:var(--td-error-color-8)}
</style>
