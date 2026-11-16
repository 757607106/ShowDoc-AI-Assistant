<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { listWikiRevisions, getWikiRevisionDiff, type WikiRevision, type WikiRevisionDiff } from '@/api/contextdbWiki'
import { contextdbDateTime as dateTime, stateLabel } from '@/utils/platformPresentation'

const props = defineProps<{ kbId: string; pageId: string; pageTitle?: string; visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()
const revisions = ref<WikiRevision[]>([]), cursor = ref(''), target = ref('')
const diff = ref<WikiRevisionDiff | null>(null), listError = ref(''), diffError = ref(''), loading = ref(false), comparing = ref(false)
const retryAppend = ref(false)
let listRequest = 0, diffRequest = 0
const selectedRevision = computed(() => revisions.value.find(item => item.revision_id === target.value))
function revisionState(value?: string) {
  if (value === 'superseded') return '已被替代'
  const label = stateLabel(value, 'revision')
  return label === '未返回' || label === '未知状态' ? '状态未知' : label
}
function revisionReason(item: WikiRevision) {
  return item.review_reason || (item.edit_source === 'human' ? '人工编辑' : item.edit_source === 'agent' ? '智能体编辑' : '自动编译')
}

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
  const request = ++diffRequest
  diff.value = null
  if (!props.visible || !target.value) { comparing.value = false; return }
  comparing.value = true; diffError.value = ''
  try {
    const result = await getWikiRevisionDiff(props.kbId, target.value)
    if (request === diffRequest) diff.value = result
  } catch (e: any) { if (request === diffRequest) diffError.value = e.message || '差异读取失败' }
  finally { if (request === diffRequest) comparing.value = false }
}
watch(() => [props.kbId, props.pageId, props.visible], () => {
  listRequest++; diffRequest++; revisions.value = []; cursor.value = ''; target.value = ''
  diff.value = null; listError.value = ''; diffError.value = ''; loading.value = false; comparing.value = false
  if (props.visible) void load()
}, { immediate: true, flush: 'sync' })
watch(target, () => void compare())
</script>

<template>
  <t-drawer :visible="visible" header="版本历史" size="min(1120px, 96vw)" :footer="false" :close-btn="true" @update:visible="(value: boolean) => emit('update:visible', value)">
    <div class="revision-history">
      <h2 v-if="pageTitle" class="history-page-title">{{pageTitle}}</h2>
      <t-alert v-if="listError" theme="error" :message="listError"><template #operation><t-button variant="text" @click="load(retryAppend)">重试读取版本</t-button></template></t-alert>
      <div class="revision-workspace">
        <aside class="revision-list" aria-label="版本列表">
          <button v-for="item in revisions" :key="item.revision_id" type="button" class="revision-option" :class="{selected:target===item.revision_id}" :aria-pressed="target===item.revision_id" @click="target=item.revision_id"><span class="revision-meta"><time>{{dateTime(item.created_at)}}</time><t-tag size="small" :theme="item.review_status==='published'?'success':'default'" variant="light">{{revisionState(item.review_status)}}</t-tag></span><span class="revision-reason">{{revisionReason(item)}}</span></button>
          <t-loading v-if="loading" size="small" />
          <t-button v-if="cursor" variant="text" :loading="loading" @click="load(true)">加载更多版本</t-button>
          <t-empty v-if="!loading&&!listError&&!revisions.length" description="暂无版本历史" />
        </aside>
        <section class="revision-diff" aria-label="版本差异">
          <header v-if="selectedRevision" class="diff-heading"><time>{{dateTime(selectedRevision.created_at)}}</time><t-tag size="small" :theme="selectedRevision.review_status==='published'?'success':'default'" variant="light">{{revisionState(selectedRevision.review_status)}}</t-tag></header>
          <t-alert v-if="diffError" theme="error" :message="diffError"><template #operation><t-button variant="text" @click="compare">重试读取差异</t-button></template></t-alert>
          <t-loading :loading="comparing" class="revision-body">
            <template v-if="diff">
              <p class="diff-count"><span class="added">+{{diff.diff.added_count}}</span><span class="removed">-{{diff.diff.removed_count}}</span></p>
              <t-alert v-if="diff.diff.truncated" theme="warning" message="差异已截断：任一版本超过 800 行时仅比较前 800 行，以下不是全文差异。" />
              <div class="diff-lines" aria-label="修订正文差异"><template v-for="(hunk,index) in diff.diff.hunks" :key="index"><pre v-for="(line,lineIndex) in hunk.text.split('\n')" :key="lineIndex" :class="hunk.op"><span aria-hidden="true">{{hunk.op==='add'?'+':hunk.op==='del'?'-':' '}}</span>{{line}}</pre></template><t-empty v-if="!diff.diff.hunks.length" description="这两个版本没有正文差异" /></div>
            </template>
          </t-loading>
        </section>
      </div>
    </div>
  </t-drawer>
</template>

<style scoped lang="less">
.revision-history{display:flex;flex-direction:column;height:100%;min-height:0;font-family:var(--app-font-family);font-size:var(--app-text-base)}.history-page-title{font-size:var(--app-text-3xl);line-height:28px;font-weight:600;margin:0 0 20px}.revision-workspace{display:flex;flex:1;min-height:0;gap:20px}.revision-list{width:240px;flex:none;overflow:auto;display:flex;flex-direction:column;gap:8px}.revision-option{display:block;text-align:left;border:1px solid transparent;border-radius:var(--app-radius-md);background:var(--td-bg-color-secondarycontainer);color:var(--td-text-color-primary);padding:12px;cursor:pointer;font:inherit}.revision-option.selected{border-color:var(--app-selection-border);background:var(--app-selection-bg);color:var(--app-selection-text)}.revision-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;line-height:20px}.revision-meta time{font-size:var(--app-text-sm);white-space:nowrap}.revision-meta :deep(.t-tag){font-size:var(--app-text-sm);white-space:nowrap}.revision-reason{display:block;font-size:var(--app-text-md);color:var(--td-text-color-secondary);line-height:20px;margin-top:6px;overflow-wrap:anywhere}.revision-diff{flex:1;min-width:0;overflow:auto}.diff-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;line-height:24px;margin-bottom:16px}.diff-heading time{font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}.revision-body{display:block;min-height:160px}.diff-count{display:flex;gap:12px;margin:0 0 12px;line-height:20px}.added{color:var(--td-success-color)}.removed{color:var(--td-error-color)}
.diff-lines{border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-md);overflow:hidden}.diff-lines pre{margin:0;padding:6px 12px;white-space:pre-wrap;overflow-wrap:anywhere;font: var(--app-text-base)/1.7 var(--app-font-family-mono)}.diff-lines pre span{display:inline-block;width:20px;user-select:none}.add{background:var(--td-success-color-1);color:var(--td-success-color-8)}.del{background:var(--td-error-color-1);color:var(--td-error-color-8)}
@media(max-width:700px){.revision-workspace{flex-direction:column}.revision-list{width:auto;max-height:240px}.revision-meta{justify-content:flex-start}}
</style>
