<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import {
  listWikiPages, getWikiIndex, getWikiPage, getWikiPageByReference, searchWikiPages, updateWikiPage, createWikiPage,
  createWikiDirectory, organizeWikiPage, organizeWikiDirectory, deleteWikiPage, getWikiEvent,
  type WikiPage, type WikiIndexGroup,
} from '@/api/contextdbWiki'
import DocMarkdown from '@/components/DocMarkdown.vue'
import EmptyState from '@/components/EmptyState.vue'
import ContextDBWikiDirectory from './ContextDBWikiDirectory.vue'
import ContextDBWikiRevisions from './ContextDBWikiRevisions.vue'
import { diffWikiLines } from '@/utils/wikiLineDiff'
import { getDocument } from '@/api/contextdb'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { escapeHTML } from '@/utils/security'
import { notificationPreview } from '@/utils/notificationPreview'

const props = defineProps<{ kbId: string; canEdit?: boolean }>()
const emit = defineEmits<{ 'open-source-doc': [id: string]; 'page-change': [id: string] }>()
const route = useRoute(), router = useRouter()
const internalTab = ref('read'), query = ref(''), searchResults = ref<WikiPage[] | null>(null)
const searching = ref(false), searchError = ref(''), page = ref<WikiPage | null>(null)
const loading = ref(false), error = ref(''), intro = ref(''), groups = ref<WikiIndexGroup[]>([])
const indexLoading = ref(false), indexError = ref(''), groupLoading = ref(''), treeRevision = ref(0)
const directoryItems = ref<WikiPage[]>([]), directoryCursor = ref<string | null>(null), directoryLoading = ref(false)
const editing = ref(false), draft = ref(''), editVersion = ref(0), saving = ref(false)
const latest = ref<WikiPage | null>(null), conflict = ref(false), verifying = ref(false)
const submitted = ref(false), saveNotice = ref(''), revisionsVisible = ref(false)
let pageRequest = 0, searchRequest = 0, indexRequest = 0, comparisonRequest = 0, referenceRequest = 0
let disposed = false
const activePageId = computed(() => typeof route.query.wikiPageId === 'string' ? route.query.wikiPageId : '')
const legacyReference = computed(() => !activePageId.value && typeof route.query.slug === 'string' ? route.query.slug : '')
const isDirectory = computed(() => page.value?.page_type === 'category')
const busyPage = computed(() => page.value?.run_state === 'pending')
const canChange = computed(() => !!props.canEdit && !!page.value && !busyPage.value && !saving.value && !verifying.value)
const typeNames: Record<string, string> = { category: '目录', entity: '实体', concept: '概念', synthesis: '综合', comparison: '对比', summary: '文档摘要' }
const conflictLines = computed(() => latest.value ? diffWikiLines(latest.value.published ? latest.value.content || '' : '', draft.value) : [])
const relatedLinks = computed(() => page.value?.published ? page.value.links || [] : [])
const backlinks = computed(() => page.value?.published ? page.value.backlinks || [] : [])
const sourceNames = ref<Record<string, string>>({})
const sourceQueue: string[] = [], sourceRequested = new Set<string>()
let sourceActive = 0
function loadSourceNames() {
  while (!disposed && sourceActive < 4 && sourceQueue.length) {
    const id = sourceQueue.shift()!
    sourceActive++
    void getDocument(id).then(result => {
      if (!disposed) sourceNames.value[id] = documentDisplayName(result.data) || '查看来源文档'
    }).catch(() => {
      if (!disposed) sourceNames.value[id] = '查看来源文档'
    }).finally(() => { sourceActive--; loadSourceNames() })
  }
}
watch(() => page.value?.published === true ? page.value.source_document_ids : [], ids => {
  for (const id of ids || []) {
    if (!sourceRequested.has(id)) { sourceRequested.add(id); sourceQueue.push(id) }
  }
  loadSourceNames()
})
function linkId(link: any) { return typeof link === 'string' ? link : link.page_id }
function linkTitle(link: any) { return typeof link === 'string' ? '打开相关页面' : link.title || '未命名页面' }
function summaryText(content = '') {
  return notificationPreview(content.replace(/\[\[([^|\]]+)(?:\|([^\]]+))?\]\]/g, (_whole, target: string, label?: string) => label || target))
}
function readingContent(content: string) {
  const links = [...relatedLinks.value, ...backlinks.value]
  return content.replace(/\[\[([^\]]+)\]\]/g, (_, inner: string) => {
    const [target, label] = inner.split('|').map(part => part.trim())
    const link = links.find((item: any) => linkId(item) === target || item.slug === target)
    const title = escapeHTML(label || (link ? linkTitle(link) : target)).replace(/[\[\]\\]/g, '\\$&')
    const reference = encodeURIComponent(link ? linkId(link) : target).replace(/[()]/g, character => character === '(' ? '%28' : '%29')
    return `[${title}](#wiki-reference-${reference})`
  })
}
function onContentClick(event: MouseEvent) {
  const anchor = (event.target as HTMLElement).closest('a')
  const href = anchor?.getAttribute('href') || ''
  if (href.startsWith('#wiki-reference-')) { event.preventDefault(); void openReference(decodeURIComponent(href.slice(16))) }
}
async function openReference(reference: string) {
  if (!permitNavigation()) return
  const token = ++referenceRequest, kb = props.kbId, id = activePageId.value, request = pageRequest
  if (/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(reference)) { await openPage(reference); return }
  try {
    const target = await getWikiPageByReference(kb, reference)
    if (disposed || token !== referenceRequest || kb !== props.kbId || id !== activePageId.value || request !== pageRequest) return
    await openPage(target.page_id)
  } catch (e: any) {
    if (!disposed && token === referenceRequest && kb === props.kbId && id === activePageId.value && request === pageRequest) MessagePlugin.error(e.message || '页面链接无法读取')
  }
}
function permitNavigation() {
  if (action.value) { MessagePlugin.warning('请先完成或取消当前整理操作'); return false }
  if (!editing.value && !saving.value && !verifying.value && !actionBusy.value) return true
  MessagePlugin.warning('请先保存并核对正文，或取消当前草稿')
  return false
}
defineExpose({ permitNavigation })
onBeforeRouteLeave(permitNavigation)
onBeforeRouteUpdate((to, from) => to.fullPath === from.fullPath || permitNavigation())
function beforeUnload(event: BeforeUnloadEvent) {
  if (editing.value || saving.value || verifying.value || action.value) { event.preventDefault(); event.returnValue = '' }
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeUnmount(() => { disposed = true; pageRequest++; indexRequest++; searchRequest++; comparisonRequest++; referenceRequest++; window.removeEventListener('beforeunload', beforeUnload) })
async function openPage(id = '') {
  if (!permitNavigation()) return
  referenceRequest++
  internalTab.value = 'read'
  if (id === activePageId.value) { await loadPage(); return }
  const next = { ...route.query }
  delete next.slug
  if (id) next.wikiPageId = id; else delete next.wikiPageId
  await router.replace({ query: next })
}
async function loadIndex() {
  const token = ++indexRequest, kb = props.kbId
  indexLoading.value = true; indexError.value = ''
  try {
    const result = await getWikiIndex(kb, { limit: 30 })
    if (token !== indexRequest || kb !== props.kbId || disposed) return
    intro.value = result.intro || ''; groups.value = result.groups || []
  } catch (e: any) { if (token === indexRequest) indexError.value = e.message || '索引读取失败' }
  finally { if (token === indexRequest) indexLoading.value = false }
}
async function loadGroup(group: WikiIndexGroup) {
  if (!group.next_cursor || groupLoading.value) return
  const token = indexRequest, kb = props.kbId
  groupLoading.value = group.type; indexError.value = ''
  try {
    const result = await getWikiIndex(kb, { types: group.type, limit: 30, cursor: group.next_cursor })
    if (token !== indexRequest || kb !== props.kbId || disposed) return
    const next = result.groups.find(item => item.type === group.type)
    if (next) {
      const seen = new Set(group.items.map(item => item.page_id))
      group.items.push(...next.items.filter(item => !seen.has(item.page_id)))
      group.next_cursor = next.next_cursor; group.total = next.total
    }
  } catch (e: any) { if (token === indexRequest) indexError.value = e.message || '索引读取失败' }
  finally { if (token === indexRequest) groupLoading.value = '' }
}
async function loadPage() {
  comparisonRequest++; referenceRequest++; latest.value = null
  const token = ++pageRequest, kb = props.kbId, id = activePageId.value
  page.value = null; error.value = ''; directoryItems.value = []; directoryCursor.value = null; directoryLoading.value = false
  loading.value = !!id
  emit('page-change', id)
  if (!id) return
  try {
    const result = await getWikiPage(kb, id)
    if (token !== pageRequest || kb !== props.kbId || disposed) return
    page.value = result
    if (result.page_type === 'category') await loadDirectory(false, token)
  } catch (e: any) { if (token === pageRequest) error.value = e.message || '页面读取失败' }
  finally { if (token === pageRequest) loading.value = false }
}
async function loadDirectory(append = false, token = pageRequest) {
  const kb = props.kbId, id = page.value?.page_id
  if (!id || (append && !directoryCursor.value) || directoryLoading.value) return
  directoryLoading.value = true
  try {
    const result = await listWikiPages(kb, { parent_page_id: id, cursor: append ? directoryCursor.value || undefined : undefined, limit: 50 })
    if (token !== pageRequest || disposed) return
    const existing = append ? directoryItems.value : [], seen = new Set(existing.map(item => item.page_id))
    directoryItems.value = [...existing, ...result.items.filter(item => !seen.has(item.page_id))]
    directoryCursor.value = result.next_cursor || null
  } catch (e: any) { if (token === pageRequest) error.value = e.message || '子目录读取失败' }
  finally { if (token === pageRequest) directoryLoading.value = false }
}
async function search() {
  const token = ++searchRequest, kb = props.kbId, value = query.value.trim()
  searchError.value = ''; searching.value = !!value
  if (!value) { searchResults.value = null; return }
  try {
    const result = await searchWikiPages(kb, value, { limit: 50 })
    if (token === searchRequest && kb === props.kbId && !disposed) searchResults.value = result.items
  } catch (e: any) { if (token === searchRequest) { searchError.value = e.message || '搜索失败'; searchResults.value = [] } }
  finally { if (token === searchRequest) searching.value = false }
}
function startEditing() {
  if (!canChange.value || !page.value?.published || isDirectory.value) return
  comparisonRequest++; referenceRequest++
  draft.value = page.value.content || ''; editVersion.value = page.value.version
  editing.value = true; conflict.value = false; latest.value = null; submitted.value = false; saveNotice.value = ''
}
function cancelEditing() {
  if (saving.value || verifying.value) return
  comparisonRequest++; referenceRequest++
  editing.value = false; draft.value = ''; conflict.value = false; latest.value = null; submitted.value = false; saveNotice.value = ''
}
async function compareLatest() {
  if (!page.value || !editing.value) return
  const token = ++comparisonRequest, kb = props.kbId, id = page.value.page_id, routeId = activePageId.value, request = pageRequest
  const isCurrent = () => !disposed && token === comparisonRequest && kb === props.kbId && id === page.value?.page_id && routeId === activePageId.value && request === pageRequest && editing.value
  try {
    const result = await getWikiPage(kb, id)
    if (isCurrent()) latest.value = result
  } catch (e: any) { if (isCurrent()) MessagePlugin.error(e.message || '最新页面读取失败') }
}
function useLatestBase() {
  if (!editing.value || !latest.value || latest.value.page_id !== page.value?.page_id || latest.value.run_state === 'pending') return
  editVersion.value = latest.value.version; page.value = latest.value
  conflict.value = false; submitted.value = false; latest.value = null
  saveNotice.value = '已采用最新版本。请先在编辑器中合并差异，再提交草稿。'
}
async function verifySaved() {
  if (!page.value || verifying.value) return
  const id = page.value.page_id, kb = props.kbId, content = draft.value
  verifying.value = true
  try {
    for (let attempt = 0; attempt < 4; attempt++) {
      if (attempt) await new Promise(resolve => setTimeout(resolve, 700))
      if (disposed || kb !== props.kbId || id !== activePageId.value) return
      const current = await getWikiPage(kb, id)
      if (disposed || kb !== props.kbId || id !== activePageId.value) return
      page.value = current
      if (current.published === true && current.content === content && current.run_state !== 'pending') {
        editing.value = false; submitted.value = false; conflict.value = false; latest.value = null
        saveNotice.value = '已核对正式正文，修改已生效。'
        MessagePlugin.success('正式正文已更新'); void loadIndex(); treeRevision.value++
        return
      }
    }
    saveNotice.value = '请求已受理，正式正文尚未与草稿一致。草稿已保留，请稍后核对正文或查看修订记录。'
  } catch (e: any) { saveNotice.value = `已保留草稿；正式正文核对失败：${e.message || '请重试'}` }
  finally { verifying.value = false }
}
async function save() {
  if (!page.value || !editing.value || saving.value || submitted.value || busyPage.value || conflict.value) return
  saving.value = true; saveNotice.value = ''
  try {
    await updateWikiPage(props.kbId, page.value.page_id, { content: draft.value, expected_version: editVersion.value })
    submitted.value = true
    await verifySaved()
  } catch (e: any) {
    if (e.status === 409 || e.errorCode === 4033 || e.code === 4033) {
      conflict.value = true; saveNotice.value = '页面已发生变化，草稿已保留。读取最新正文并手动合并后再提交。'
      await compareLatest()
    } else MessagePlugin.error(e.message || '保存失败，草稿已保留')
  } finally { saving.value = false }
}

type Action = 'create-page' | 'create-directory' | 'rename' | 'move' | 'archive' | 'delete'
const action = ref<Action | ''>(''), actionBusy = ref(false), actionError = ref('')
const actionTitle = ref(''), actionContent = ref(''), actionType = ref('concept')
const targetDirectory = ref<WikiPage | null>(null), actionSource = ref<WikiPage | null>(null)
const actionLabel = computed(() => ({ 'create-page': '新建主题页', 'create-directory': '新建目录', rename: '重命名', move: '移动到目录', archive: '归档主题页', delete: isDirectory.value ? '删除空目录' : '删除主题页' }[action.value as Action] || '整理 Wiki'))
function openAction(next: Action) {
  if (!props.canEdit || !permitNavigation() || (page.value && busyPage.value)) return
  action.value = next; actionError.value = ''; actionTitle.value = next === 'rename' ? page.value?.title || '' : ''
  actionContent.value = ''; actionType.value = 'concept'; actionSource.value = page.value
  targetDirectory.value = next.startsWith('create') && isDirectory.value ? page.value : null
}
async function checkEvent(result: any) {
  if (!result?.event_id) return ''
  for (let attempt = 0; attempt < 4; attempt++) {
    if (attempt) await new Promise(resolve => setTimeout(resolve, 500))
    if (disposed) return ''
    const event = await getWikiEvent(result.event_id)
    const status = String(event.status || '').toUpperCase()
    if (['FAILED', 'CANCELLED', 'SUCCEEDED'].includes(status)) return status
  }
  return ''
}
async function submitAction() {
  if (!action.value || actionBusy.value || !props.canEdit) return
  const selectedAction = action.value, source = actionSource.value, kb = props.kbId
  if (['create-page', 'create-directory', 'rename'].includes(selectedAction) && !actionTitle.value.trim()) { actionError.value = '请输入标题'; return }
  if (selectedAction === 'create-page' && !actionContent.value.trim()) { actionError.value = '请输入正文'; return }
  actionBusy.value = true; actionError.value = ''
  try {
    const target = targetDirectory.value ? await getWikiPage(kb, targetDirectory.value.page_id) : null
    if (target && (target.page_type !== 'category' || target.run_state === 'pending')) throw new Error('目标目录当前不可用，请重新选择')
    if (selectedAction === 'move' && source && target && (target.page_id === source.page_id || (target.ancestors || []).some((item: any) => item.page_id === source.page_id))) throw new Error('不能移动到自身或下级目录')
    let result: any
    if (selectedAction === 'create-page') result = await createWikiPage(kb, { title: actionTitle.value.trim(), content: actionContent.value, page_type: actionType.value as 'concept' | 'entity', parent_page_id: target?.page_id })
    else if (selectedAction === 'create-directory') result = await createWikiDirectory(kb, { title: actionTitle.value.trim(), parent_page_id: target?.page_id })
    else if (source) {
      if (source.run_state === 'pending') throw new Error('页面正在编译，请稍后操作')
      if (selectedAction === 'delete' && source.page_type !== 'category') {
        const current = await getWikiPage(kb, source.page_id)
        if (current.version !== source.version || current.run_state === 'pending') throw new Error('页面已变化，请重新读取后操作')
        result = await deleteWikiPage(kb, source.page_id)
      } else {
        const payload = { action: selectedAction, expected_version: source.version,
          ...(selectedAction === 'rename' ? { title: actionTitle.value.trim() } : {}),
          ...(selectedAction === 'move' ? { parent_page_id: target?.page_id, expected_parent_version: target?.version } : {}) }
        result = source.page_type === 'category'
          ? await organizeWikiDirectory(kb, source.page_id, payload as any)
          : await organizeWikiPage(kb, source.page_id, payload as any)
      }
    }
    let eventStatus = ''
    try { eventStatus = await checkEvent(result) } catch { /* The write was accepted; a failed event read must not repeat it. */ }
    action.value = ''; treeRevision.value++; void loadIndex()
    if (eventStatus === 'FAILED' || eventStatus === 'CANCELLED') MessagePlugin.error('操作事件未完成，请读取当前页面核对结果')
    else MessagePlugin.info(eventStatus === 'SUCCEEDED' ? '操作事件已完成，正在读取页面核对' : '操作已受理，正在读取页面核对；列表可能稍后更新')
    actionBusy.value = false
    if (selectedAction === 'create-page' || selectedAction === 'create-directory') {
      if (result.page_id) await openPage(result.page_id)
    } else if (selectedAction === 'delete' || selectedAction === 'archive') await openPage('')
    else await loadPage()
  } catch (e: any) { actionError.value = e.message || '操作失败，请重新核对当前页面' }
  finally { actionBusy.value = false }
}
watch(() => [props.kbId, activePageId.value], () => { void loadPage() }, { immediate: true })
watch(() => [props.kbId, legacyReference.value], () => { if (legacyReference.value) void openReference(legacyReference.value) }, { immediate: true })
watch(() => props.kbId, () => {
  query.value = ''; searchResults.value = null; searchError.value = ''; searchRequest++
  editing.value = false; draft.value = ''; submitted.value = false; conflict.value = false; saveNotice.value = ''
  treeRevision.value++; void loadIndex()
}, { immediate: true })
</script>

<template>
  <section class="contextdb-wiki">
    <nav class="wiki-workspace-tabs" aria-label="Wiki 工作区">
      <button type="button" :class="{active:internalTab==='read'}" @click="internalTab='read'"><t-icon name="book-open" />阅读</button>
      <button type="button" :class="{active:internalTab==='compile'}" :disabled="editing" @click="internalTab='compile'"><t-icon name="task" />编译进度</button>
    </nav>
    <div v-if="internalTab==='compile'" class="compile-area"><slot name="compile"><EmptyState title="暂无编译进度" /></slot></div>
    <div v-show="internalTab==='read'" class="wiki-workspace">
      <aside class="wiki-navigation" aria-label="Wiki 页面导航">
        <div class="wiki-nav-top">
          <t-input v-model="query" clearable placeholder="搜索标题、简介和正文" @enter="search" @clear="search"><template #prefix-icon><t-icon name="search" /></template></t-input>
          <div class="wiki-nav-actions"><t-button size="small" variant="text" :loading="searching" @click="search">搜索</t-button><t-dropdown v-if="canEdit" :options="[{content:'新建主题页',value:'create-page'},{content:'新建目录',value:'create-directory'}]" @click="(item: any)=>openAction(item.value as Action)"><t-button size="small" variant="text" :disabled="editing||busyPage"><t-icon name="add" />新建</t-button></t-dropdown></div>
        </div>
        <div class="wiki-nav-scroll">
          <div v-if="searchResults!==null" class="search-results">
            <p class="navigation-label">搜索结果 · {{searchResults.length}} 项</p><p class="navigation-hint">最多返回 50 项，更多主题请浏览索引。</p>
            <p v-if="searchError" class="error-message" role="alert">{{searchError}}</p>
            <button v-for="item in searchResults" :key="item.page_id" class="search-result" :class="{selected:item.page_id===activePageId}" @click="openPage(item.page_id)"><strong>{{item.title||'未命名页面'}}</strong><span>{{summaryText((item as any).match_snippet||item.summary)}}</span></button>
            <EmptyState v-if="!searching&&!searchError&&!searchResults.length" compact title="没有找到相关页面" />
            <t-button size="small" variant="text" @click="query='';search()">返回目录</t-button>
          </div>
          <template v-else>
            <button class="wiki-home" :class="{selected:!activePageId}" @click="openPage()"><t-icon name="catalog" />索引概览</button>
            <p class="navigation-label">主题目录</p>
            <ContextDBWikiDirectory :key="`${kbId}:${treeRevision}`" :kb-id="kbId" :selected-id="activePageId" @select="item=>openPage(item.page_id)" />
          </template>
        </div>
      </aside>
      <main class="wiki-reading" @click="onContentClick">
        <t-alert v-if="error" theme="error" :message="error"><template #operation><t-button variant="text" @click="loadPage">重试读取</t-button></template></t-alert>
        <div v-if="loading" class="reading-loading"><t-loading text="正在读取页面" /></div>
        <article v-else-if="page" class="wiki-article">
          <t-breadcrumb class="wiki-breadcrumb"><t-breadcrumb-item @click="openPage()">Wiki</t-breadcrumb-item><t-breadcrumb-item v-for="ancestor in page.ancestors||[]" :key="ancestor.page_id" @click="openPage(ancestor.page_id)">{{ancestor.title||'目录'}}</t-breadcrumb-item></t-breadcrumb>
          <header class="article-header"><div><div class="article-eyebrow">{{typeNames[page.page_type]||'主题页'}}<span>v{{page.version}}</span></div><h1>{{page.title||'未命名页面'}}</h1></div>
            <div class="article-actions"><t-tag v-if="busyPage" theme="warning" variant="light">编译中</t-tag><t-tag v-else-if="!isDirectory" :theme="page.published?'success':'default'" variant="light">{{page.published?'正文已发布':'暂无正式正文'}}</t-tag><template v-if="!editing"><t-button v-if="!isDirectory" size="small" variant="outline" @click="revisionsVisible=true">修订记录</t-button><t-button v-if="canEdit&&!isDirectory" size="small" :disabled="!canChange||!page.published" @click="startEditing">编辑正文</t-button><t-dropdown v-if="canEdit" :disabled="!canChange" :options="[{content:'重命名',value:'rename'},{content:'移动',value:'move'},...(!isDirectory?[{content:'归档',value:'archive'}]:[]),{content:isDirectory?'删除空目录':'删除主题页',value:'delete'}]" @click="(item: any)=>openAction(item.value as Action)"><t-button size="small" variant="outline" :disabled="!canChange">整理<t-icon name="chevron-down" /></t-button></t-dropdown></template></div>
          </header>
          <t-alert v-if="busyPage" theme="info" message="页面正在编译，完成后可重新读取并编辑。" />
          <t-alert v-if="saveNotice" :theme="editing?'info':'success'" :message="saveNotice" />
          <section v-if="editing" class="wiki-editor">
            <div class="editor-toolbar"><span>Markdown 正文 · 基于 v{{editVersion}}</span><t-space><t-button variant="text" :disabled="saving||verifying" @click="cancelEditing">取消草稿</t-button><t-button v-if="submitted" :loading="verifying" @click="verifySaved">核对正式正文</t-button><t-button v-else :loading="saving" :disabled="conflict||busyPage" @click="save">提交修订</t-button></t-space></div>
            <label class="wiki-field-label"><span class="wiki-field-name">Wiki 正文草稿</span><t-textarea v-model="draft" name="wiki_content" :readonly="saving||verifying||submitted" :autosize="{minRows:18,maxRows:36}" /></label>
            <div v-if="conflict||submitted" class="merge-actions"><t-button size="small" variant="outline" @click="compareLatest">读取最新版本并比较</t-button><t-button v-if="latest" size="small" :disabled="latest.run_state==='pending'" @click="useLatestBase">保留草稿，采用最新版本继续合并</t-button><t-button size="small" variant="text" @click="revisionsVisible=true">查看修订记录</t-button></div>
            <section v-if="latest" class="conflict-comparison"><p>正式正文 v{{latest.version}} → 当前草稿。请在上方编辑器手动合并后提交。</p><p v-if="!latest.published" class="navigation-hint">当前页面没有可读正式正文，以下以空正文比较。</p><pre><span v-for="(line,i) in conflictLines" :key="i" :class="line.type">{{line.type==='add'?'+':line.type==='del'?'-':' '}}{{line.text}}{{'\n'}}</span></pre></section>
          </section>
          <template v-else-if="isDirectory"><p class="navigation-hint">浏览此目录下的页面和子目录。</p><button v-for="item in directoryItems" :key="item.page_id" class="directory-card" @click="openPage(item.page_id)"><t-icon :name="item.page_type==='category'?'folder':'file'" /><span>{{item.title||'未命名页面'}}</span><t-icon name="chevron-right" /></button><t-button v-if="directoryCursor" :loading="directoryLoading" variant="text" @click="loadDirectory(true)">加载更多</t-button><EmptyState v-else-if="!directoryItems.length&&!directoryLoading" compact title="此目录暂无页面" /></template>
          <template v-else-if="page.published===true"><DocMarkdown :content="readingContent(page.content||'')" :title="page.title" /><footer class="article-footer"><section v-if="page.source_document_ids?.length"><h3>来源文档</h3><t-button v-for="id in page.source_document_ids" :key="id" size="small" variant="text" @click="emit('open-source-doc',id)"><t-icon name="file" />{{sourceNames[id]||'查看来源文档'}}</t-button></section><section v-if="relatedLinks.length"><h3>相关页面 <span>{{page.links_total??relatedLinks.length}}</span></h3><button v-for="link in relatedLinks" :key="linkId(link)" class="related-link" @click="openPage(linkId(link))">{{linkTitle(link)}}</button><p v-if="page.links_truncated" class="navigation-hint">仅显示前 {{relatedLinks.length}} 项相关页面，请通过索引或搜索继续查找。</p></section><section v-if="backlinks.length"><h3>引用此页 <span>{{page.backlinks_total??backlinks.length}}</span></h3><button v-for="link in backlinks" :key="linkId(link)" class="related-link" @click="openPage(linkId(link))">{{linkTitle(link)}}</button><p v-if="page.backlinks_truncated" class="navigation-hint">仅显示前 {{backlinks.length}} 项引用。</p></section></footer></template>
          <EmptyState v-else icon="file" title="暂无可读的正式正文" description="来源可能已撤回、失效或页面仍在处理。请核对编译进度与修订记录。" />
        </article>
        <article v-else-if="!activePageId&&!error" class="wiki-index"><div class="article-eyebrow">知识库 Wiki</div><h1>索引概览</h1><p class="article-summary">从主题出发，阅读整理后的知识与来源。</p><t-alert v-if="indexError" theme="error" :message="indexError"><template #operation><t-button variant="text" @click="loadIndex">重新读取</t-button></template></t-alert><DocMarkdown v-if="intro" :content="intro" /><t-loading v-if="indexLoading" text="正在读取索引" /><section v-for="group in groups" :key="group.type" class="index-group"><h2>{{typeNames[group.type]||group.type}}<span>{{group.total}}</span></h2><button v-for="item in group.items" :key="item.page_id" class="index-entry" @click="openPage(item.page_id)"><span><strong>{{item.title||'未命名页面'}}</strong><small v-if="item.category_path?.length">{{item.category_path.join(' / ')}}</small><p v-if="item.summary">{{summaryText(item.summary)}}</p></span><t-icon name="chevron-right" /></button><t-button v-if="group.next_cursor" size="small" variant="text" :loading="groupLoading===group.type" @click="loadGroup(group)">加载更多{{typeNames[group.type]||'主题'}}</t-button></section><EmptyState v-if="!indexLoading&&!indexError&&!groups.some(group=>group.items.length)" icon="book-open" title="Wiki 主题尚未生成" description="资料处理完成后可在编译进度中核对，或手动创建主题页。" /></article>
      </main>
    </div>
    <ContextDBWikiRevisions :kb-id="kbId" :page-id="page?.page_id||''" v-model:visible="revisionsVisible" />
    <t-dialog :visible="!!action" :header="actionLabel" :confirm-btn="{content:actionLabel,loading:actionBusy,theme:action==='delete'?'danger':'primary'}" :close-on-overlay-click="!actionBusy" :close-btn="!actionBusy" :cancel-btn="{disabled:actionBusy}" @close="!actionBusy&&(action='')" @cancel="!actionBusy&&(action='')" @confirm="submitAction">
      <t-alert v-if="actionError" theme="error" :message="actionError" />
      <t-form label-align="top"><t-form-item v-if="['create-page','create-directory','rename'].includes(action)" label="标题" required><t-input v-model="actionTitle" :maxlength="120" /></t-form-item><t-form-item v-if="action==='create-page'" label="主题类型"><t-radio-group v-model="actionType" :options="[{label:'概念',value:'concept'},{label:'实体',value:'entity'}]" /></t-form-item><t-form-item v-if="action==='create-page'" label="正文" required><label class="wiki-field-label"><span class="wiki-field-name">新主题页正文</span><t-textarea v-model="actionContent" name="wiki_create_content" :autosize="{minRows:8,maxRows:18}" /></label></t-form-item><t-form-item v-if="action==='move'||action.startsWith('create')" label="目标目录"><div class="directory-picker"><button type="button" class="wiki-home" :class="{selected:!targetDirectory}" @click="targetDirectory=null"><t-icon name="folder" />根目录</button><ContextDBWikiDirectory :key="`${kbId}:${action}:${treeRevision}`" :kb-id="kbId" :selected-id="targetDirectory?.page_id" directories-only :blocked-id="action==='move'?page?.page_id:undefined" @select="targetDirectory=$event" /></div></t-form-item></t-form>
      <p v-if="action==='archive'">归档后正式正文退出检索，历史记录保留。</p><p v-if="action==='delete'">{{isDirectory?'仅可删除没有直接子项的空目录。':'删除会清理修订和旧证据，并阻止自动编译恢复同一页。此操作不可恢复。'}}</p>
    </t-dialog>
  </section>
</template>

<style scoped lang="less">
.contextdb-wiki{display:flex;flex-direction:column;min-height:0;height:100%;color:var(--td-text-color-primary)}
.wiki-workspace-tabs{display:flex;gap:24px;flex:none;border-bottom:1px solid var(--td-component-stroke);padding:0 24px;background:var(--td-bg-color-container)}
.wiki-workspace-tabs button{display:flex;gap:7px;align-items:center;border:0;border-bottom:2px solid transparent;background:none;color:var(--td-text-color-secondary);padding:13px 2px;font:inherit;cursor:pointer}.wiki-workspace-tabs button.active{border-bottom-color:var(--td-brand-color);color:var(--td-brand-color);font-weight:600}.wiki-workspace-tabs button:disabled{opacity:.5;cursor:default}
.wiki-workspace{display:flex;flex:1;min-height:0;background:var(--td-bg-color-container)}.wiki-navigation{display:flex;flex-direction:column;width:270px;min-width:230px;flex:none;border-right:1px solid var(--td-component-stroke)}
.wiki-nav-top{padding:18px 16px 10px}.wiki-nav-actions{display:flex;justify-content:space-between;margin-top:6px}.wiki-nav-scroll{padding:0 12px 24px;overflow:auto;flex:1}.navigation-label{font-size:var(--app-text-sm);font-weight:600;letter-spacing:.04em;color:var(--td-text-color-placeholder);margin:20px 10px 8px}.navigation-hint{font-size:var(--app-text-sm);line-height:1.7;color:var(--td-text-color-secondary)}
.wiki-home{display:flex;gap:9px;align-items:center;padding:10px;width:100%;text-align:left;border:0;border-radius:var(--app-radius-sm);background:none;color:var(--td-text-color-secondary);font:inherit;cursor:pointer}.wiki-home.selected,.search-result.selected{background:var(--td-brand-color-light);color:var(--td-brand-color)}
.wiki-reading{overflow:auto;flex:1;min-width:0;padding:32px 42px 64px}.wiki-article,.wiki-index{max-width:1060px;margin:0 auto}.reading-loading{display:flex;justify-content:center;padding:100px 0}.wiki-breadcrumb{margin-bottom:24px}.article-header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:28px}.article-eyebrow{display:flex;align-items:center;gap:10px;font-size:var(--app-text-sm);color:var(--td-text-color-placeholder);letter-spacing:.05em}.article-eyebrow span{font-size:var(--app-text-xs);border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-xs);padding:0 5px}.wiki-article h1,.wiki-index h1{font-size:var(--app-text-4xl);line-height:1.4;font-weight:600;margin:10px 0 12px;letter-spacing:-.02em}.article-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end;padding-top:2px}
.wiki-article :deep(.t-alert),.wiki-index :deep(.t-alert){margin-bottom:18px}.wiki-article :deep(.doc-markdown-body),.wiki-index :deep(.doc-markdown-body){font-size:var(--app-text-md);line-height:1.9;overflow-wrap:anywhere}.wiki-article :deep(.doc-markdown-body h2){margin-top:32px;padding-bottom:10px;border-bottom:1px solid var(--td-component-stroke);font-size:var(--app-text-2xl)}.wiki-article :deep(.doc-markdown-body h3){font-size:var(--app-text-lg)}.wiki-article :deep(.doc-markdown-body pre){padding:18px}
.search-result{display:flex;flex-direction:column;gap:5px;width:100%;padding:12px 10px;border:0;border-bottom:1px solid var(--td-component-stroke);background:none;text-align:left;color:inherit;cursor:pointer}.search-result strong{font-size:var(--app-text-md);font-weight:500}.search-result span{font-size:var(--app-text-sm);color:var(--td-text-color-secondary);line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.error-message{font-size:var(--app-text-sm);color:var(--td-error-color)}
.index-group{margin-top:34px}.index-group h2{font-size:var(--app-text-xl);font-weight:600;display:flex;gap:12px;align-items:center}.index-group h2>span,.article-footer h3>span{color:var(--td-text-color-placeholder);font-size:var(--app-text-sm);font-weight:400}.index-entry{display:flex;align-items:center;justify-content:space-between;gap:18px;width:100%;padding:15px 0;border:0;border-bottom:1px solid var(--td-component-stroke);background:none;text-align:left;color:inherit;cursor:pointer}.index-entry strong{font-weight:500;font-size:var(--app-text-md)}.index-entry small{display:block;margin-top:5px;color:var(--td-text-color-placeholder)}.index-entry p{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;color:var(--td-text-color-secondary);margin:5px 0 0;font-size:var(--app-text-sm);line-height:1.7}.index-entry:hover strong,.related-link:hover{color:var(--td-brand-color)}.index-entry> .t-icon{color:var(--td-text-color-placeholder);flex:none}
.directory-card{display:flex;align-items:center;gap:12px;width:100%;padding:16px 12px;border:0;border-bottom:1px solid var(--td-component-stroke);background:none;font:inherit;text-align:left;color:inherit;cursor:pointer}.directory-card>span{flex:1}.directory-card:hover{background:var(--td-bg-color-container-hover)}.directory-picker{width:100%;max-height:280px;overflow:auto;border:1px solid var(--td-component-stroke);border-radius:var(--app-radius-sm);padding:8px}
.article-footer{border-top:1px solid var(--td-component-stroke);margin-top:40px;padding-top:8px}.article-footer section{margin-top:20px}.article-footer h3{font-size:var(--app-text-sm);font-weight:500;color:var(--td-text-color-secondary);display:flex;gap:10px}.related-link{background:none;border:0;color:var(--td-brand-color);font:inherit;font-size:var(--app-text-sm);padding:4px 14px 4px 0;cursor:pointer}.editor-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:16px 0;font-size:var(--app-text-sm);color:var(--td-text-color-secondary)}.wiki-field-label{display:block;width:100%}.wiki-field-name{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.wiki-editor :deep(textarea){font-family:ui-monospace,monospace;line-height:1.8}.merge-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.conflict-comparison{margin-top:20px;font-size:var(--app-text-sm)}.conflict-comparison pre{white-space:pre-wrap;overflow:auto;max-height:360px;background:var(--td-bg-color-secondarycontainer);padding:14px;line-height:1.7}.conflict-comparison .add{color:var(--td-success-color)}.conflict-comparison .del{color:var(--td-error-color)}.compile-area{flex:1;min-height:0;overflow:auto}
@media(max-width:1000px){.wiki-reading{padding:24px}.wiki-navigation{width:240px}.article-header{flex-direction:column}.article-actions{justify-content:flex-start}}@media(max-width:700px){.wiki-workspace{flex-direction:column}.wiki-navigation{width:auto;min-width:0;max-height:260px;border-right:0;border-bottom:1px solid var(--td-component-stroke)}.wiki-reading{padding:22px 18px}.editor-toolbar{align-items:flex-start;flex-direction:column}}
</style>
