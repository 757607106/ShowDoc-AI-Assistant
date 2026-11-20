<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import api, { type EntryDocumentPreview } from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { bindBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, listBases, uploadDocumentFile, type BasePermissionProfile } from '@/api/contextdb'
import { shouldRejectKnowledgeFileType } from '@/utils/fileTypeVerification'
import { formatFileSize } from '@/utils/files'
import DocMarkdown from '@/components/DocMarkdown.vue'
import { directoryPreview } from './importDirectories'
import ImportDirectoryLinks from './ImportDirectoryLinks.vue'

const props = withDefaults(defineProps<{embedded?:boolean}>(), {embedded:false})
const emit = defineEmits<{
  created:[receipt:{task_ids:string[];scope:string;knowledge_base_id:string;direct_count:number}]
  'show-tasks':[target:{scope:string;task_id?:string}]
  'busy-change':[busy:boolean]
}>()
const route = useRoute(), router = useRouter(), auth = useAuthStore()
const entries = ref<any[]>([]), spaces = ref<any[]>([]), profile = ref<BasePermissionProfile | null>(null)
const spaceScope = ref(''), entryKey = ref(''), url = ref(''), projectId = ref(''), userToken = ref(''), keyword = ref('')
const sourceChoices = [{key:'file',label:'上传文件'},{key:'web',label:'网页'},{key:'showdoc',label:'ShowDoc'}]
const crawlMode = ref('page'), maxPages = ref(0), maxDepth = ref(0), selection = ref('all')
const selectedIds = ref<string[]>([]), pages = ref<any[]>([]), listing = ref(false), listError = ref('')
const useServerAuth=ref(false),projects=ref<any[]>([]),projectsLoading=ref(false),projectsError=ref('')
const mode = ref('crawl'), files = ref<File[]>([]), launching = ref(false), loading = ref(false)
const activeSource = computed(() => mode.value === 'file' ? 'file' : entryKey.value)
const moreSources = computed(() => entries.value.filter(entry => !sourceChoices.some(choice => choice.key === entry.key))
  .map(entry => ({label:entry.display_name || entry.key,value:entry.key})))
const activeMoreSource = computed(() => moreSources.value.find(entry => entry.value === activeSource.value)?.value)
const sourceError = ref(''), directoryError = ref('')
const error = ref(''), taskId = ref(''), taskScope = ref('')
const taskIds = ref<string[]>([]), directCount = ref(0)
const maxUploadFiles = 50, taskUploadLimit = 100 * 1024 * 1024
const fileInput = ref<HTMLInputElement>(), folderInput = ref<HTMLInputElement>()
const fileIntakeIssues = ref<string[]>([])
const fileReceipt = ref<{libraryId:string;libraryName:string;taskFiles:number;failed:boolean} | null>(null)
const fileReceiptMessage = ref<HTMLElement>()
const showFileReceipt = computed(() => mode.value === 'file' && !!fileReceipt.value &&
  (taskIds.value.length > 0 || directCount.value > 0 || fileReceipt.value.failed))
const fileSubmitLabel = computed(() => fileReceipt.value?.failed ? '重试待提交文件' : '上传到知识库')
const uploadNotice = computed(() => directCount.value
  ? `${directCount.value} 个文件已提交到知识库。` : '')
const receiptTaskId = computed(() => taskIds.value.length === 1 ? taskIds.value[0] : '')
const receiptLibraryLocation = computed(() => ({name:'knowledgeBaseDetail',params:{kbId:fileReceipt.value?.libraryId || ''}}))
const directory = ref<{root_name:string;source_key:string;preview_complete?:boolean}|null>(null), rootName = ref('')
const importRoots = ref<unknown>([]), taskReadError = ref('')
const needsPreview = computed(() => mode.value === 'crawl' && !directory.value)
const inlineError = ref<HTMLElement>()
const previewTarget = ref<{id:string;title:string} | null>(null)
const documentPreview = ref<EntryDocumentPreview | null>(null)
const documentError = ref('')
const documentLoading = ref(false)
let documentRequest: AbortController | undefined
let previewTrigger: HTMLElement | null = null
const previewPages = computed(() => selection.value === 'selected' ? pages.value.filter(page => selectedIds.value.includes(String(page.page_id))) : pages.value)
const previewTree = computed(() => directory.value ? directoryPreview(rootName.value.trim(), previewPages.value) : [])
let pollTimer: number | undefined
let taskRequest = 0
const previewStatus = ref(), sourceField = ref(), rootInput = ref(), dragOver = ref(false)
let jumpAfterLaunch = ''
function guide(message: string, target?: any) {
  MessagePlugin.warning(message)
  scrollToField(target)
}
function scrollToField(target?: any) {
  const el = target?.$el ?? target
  el?.scrollIntoView?.({ block: 'nearest' })
}
function selectSource(key: string) {
  if (loading.value || launching.value) return
  if (key === 'file') { mode.value = 'file'; return }
  if (!entries.value.some(entry => entry.key === key)) return
  mode.value = 'crawl'; entryKey.value = key
}
function dropFiles(event: DragEvent) {
  dragOver.value = false
  if (launching.value) return
  const dropped = Array.from(event.dataTransfer?.files || [])
  if (dropped.length) selectFiles(dropped)
}
const space = computed(() => spaces.value.find(item => item.id === spaceScope.value))
const editable = computed(() => !!space.value && knowledgeAccess(space.value, profile.value, auth.hasRole('contributor')).write)
let requestId = 0
let listRequest = 0

function crawlerParams() {
  if (entryKey.value === 'web') {
    let target: URL
    try { target = new URL(url.value.trim()) } catch { throw new Error('请输入完整的网站地址') }
    if (!['http:', 'https:'].includes(target.protocol)) throw new Error('网站地址须以 http:// 或 https:// 开头')
    const sameSite = crawlMode.value === 'site'
    return {url: url.value.trim(), crawl_mode: crawlMode.value, max_pages: sameSite ? maxPages.value : 0, max_depth: sameSite ? maxDepth.value : 0}
  }
  if (entryKey.value === 'showdoc') {
    if (!projectId.value.trim()) throw new Error(useServerAuth.value ? '请选择 ShowDoc 项目' : '请输入项目编号')
    return {item_id: projectId.value.trim(), ...(useServerAuth.value ? {auth:true} : userToken.value.trim() ? {user_token: userToken.value.trim()} : {}), ...(keyword.value.trim() ? {keyword: keyword.value.trim()} : {})}
  }
  return {}
}
function validatedCrawlerParams() {
  sourceError.value = ''
  try { return crawlerParams() }
  catch (err: any) {
    sourceError.value = err.message
    void nextTick(() => scrollToField(sourceField.value))
  }
}
async function loadProjects(){
  if (launching.value || projectsLoading.value) return
  projectsLoading.value=true;projectsError.value=''
  try{projects.value=(await api.showdocProjects()).projects||[]}
  catch(err:any){projectsError.value=err.message}
  finally{projectsLoading.value=false}
}

async function loadPages() {
  if (loading.value || launching.value || listing.value) return
  if (!space.value) return guide('请先选择知识库')
  if (!editable.value) return guide('当前知识库无写入权限，请切换其他知识库')
  if (!entryKey.value) return guide('请先选择采集平台')
  const params = validatedCrawlerParams()
  if (!params) return
  const request = ++listRequest
  const rereading = !!directory.value
  listing.value = true; listError.value = ''
  try {
    const result = await api.entryDocuments(entryKey.value, { ...params, knowledge_base_id: spaceScope.value })
    if (request === listRequest) {
      if (!result.directory?.root_name || !result.directory?.source_key) throw new Error('未能读取来源目录，请重试')
      if (!directory.value || rootName.value === directory.value.root_name) rootName.value = result.directory.root_name
      pages.value = result.pages || []; directory.value = result.directory
      const available = new Set(pages.value.map(page => String(page.page_id)))
      selectedIds.value = selectedIds.value.filter(id => available.has(id))
      if (!pages.value.length) selection.value = 'all'
    }
  } catch (err: any) { if (request === listRequest) listError.value = err.message }
  finally {
    if (request === listRequest) {
      listing.value = false
      await nextTick()
      if (!rereading && request === listRequest && mode.value === 'crawl') {
        const el = previewStatus.value?.$el ?? previewStatus.value
        el?.scrollIntoView({ block: 'start' })
      }
    }
  }
}

function closeDocumentPreview() {
  documentRequest?.abort()
  documentRequest = undefined
  previewTarget.value = null
  documentPreview.value = null
  documentError.value = ''
  documentLoading.value = false
}
function restorePreviewFocus() {
  previewTrigger?.focus({preventScroll:true})
  previewTrigger = null
}
async function openDocumentPreview(id: string, title: string, event?: MouseEvent) {
  if (launching.value || listing.value || !directory.value || mode.value !== 'crawl') return
  const params = validatedCrawlerParams()
  if (!params) return
  if (event && event.currentTarget instanceof HTMLElement) previewTrigger = event.currentTarget
  documentRequest?.abort()
  const request = new AbortController()
  documentRequest = request
  previewTarget.value = {id,title}
  documentPreview.value = null
  documentError.value = ''
  documentLoading.value = true
  try {
    const result = await api.entryPreview(entryKey.value, {...params,doc_id:id}, request.signal)
    if (!request.signal.aborted) documentPreview.value = result
  } catch (error: any) {
    if (!request.signal.aborted) documentError.value = error.message
  } finally {
    if (!request.signal.aborted) {
      documentRequest = undefined
      documentLoading.value = false
    }
  }
}

async function readImportDirectories() {
  const id = taskId.value, request = ++taskRequest
  if (!id) return
  try {
    const result = await api.taskStatus(id)
    if (request !== taskRequest || id !== taskId.value) return
    importRoots.value = result.import_directories || []; taskReadError.value = ''
    if (['failed', 'cancelled'].includes(result.status) || result.directory_sync_complete) return
  } catch (err: any) { if (request !== taskRequest) return; taskReadError.value = err.message }
  pollTimer = window.setTimeout(() => { void readImportDirectories() }, 4000)
}
watch(taskId, id => {
  taskRequest++; window.clearTimeout(pollTimer); importRoots.value = []; taskReadError.value = ''
  if (id) void readImportDirectories()
})
onUnmounted(() => { taskRequest++; listRequest++; requestId++; closeDocumentPreview(); window.clearTimeout(pollTimer) })

async function load() {
  if (launching.value) return
  const request = ++requestId
  loading.value = true; error.value = ''; resetReceipt(); files.value = []; fileIntakeIssues.value = []
  try {
    const [catalog, result, permissions] = await Promise.all([api.entries(), listBases(), getBasePermissions()])
    if (request !== requestId) return
    entries.value = (catalog.entries || []).filter((item: any) => item.key !== 'file')
    spaces.value = result.data || []; profile.value = permissions
    const requested = typeof route.query.space === 'string' ? route.query.space : ''
    const kbId = typeof route.query.kb_id === 'string' ? route.query.kb_id : ''
    let targetId = kbId
    if (requested && !targetId) {
      const legacy = (await getSpaces()).spaces.find((item: any) => item.scope === requested)
      if (request !== requestId) return
      targetId = legacy?.knowledge_base_id || legacy?.wiki_kb_id || legacy?.graph_kb_id || ''
    }
    const match = spaces.value.find(item => item.id === targetId)
    spaceScope.value = match?.id || (!requested && !kbId ? spaces.value.find(item=>knowledgeAccess(item,permissions,auth.hasRole('contributor')).write)?.id || '' : '')
    if ((requested || kbId) && !match) error.value = '当前知识库不可读取，请返回知识库列表核对权限和状态。'
    mode.value = route.query.mode === 'file' ? 'file' : 'crawl'
    url.value = typeof route.query.url === 'string' ? route.query.url : ''
    entryKey.value = url.value || entries.value.some(entry => entry.key === 'web') ? 'web' : entries.value[0]?.key || ''
  } catch (err: any) { if (request === requestId) error.value = err.message }
  finally { if (request === requestId) loading.value = false }
}

function pickFiles(event: Event) {
  const input = event.target as HTMLInputElement
  selectFiles(Array.from(input.files || []))
  input.value = ''
}
function selectFiles(selected: File[]) {
  if (launching.value) return
  const pending = [...files.value], issues: string[] = []
  const fileKey = (file: File) => JSON.stringify([file.webkitRelativePath || file.name, file.size, file.lastModified])
  const pendingKeys = new Set(pending.map(fileKey))
  for (const [index, file] of selected.entries()) {
    if (pending.length >= maxUploadFiles) {
      issues.push(`已达到 ${maxUploadFiles} 个待提交文件上限，另有 ${selected.length - index} 个文件未添加。`)
      break
    }
    const key = fileKey(file)
    if (file.webkitRelativePath?.split('/').some(part => part.startsWith('.'))) issues.push(`${file.name} · 隐藏文件`)
    else if (!file.size) issues.push(`${file.name} · 空文件`)
    else if (shouldRejectKnowledgeFileType(file.name)) issues.push(`${file.name} · 格式不受支持`)
    else if (pendingKeys.has(key)) issues.push(`${file.name} · 已在待提交列表`)
    else {
      pending.push(file)
      pendingKeys.add(key)
    }
  }
  files.value = pending; mode.value = 'file'; fileIntakeIssues.value = issues
}
function showTasks(id = taskId.value) {
  if (launching.value) return
  if (props.embedded) emit('show-tasks', {scope:taskScope.value, ...(id ? {task_id:id} : {})})
  else router.push(taskLocation(id))
}
function taskLocation(id = '') {
  return {path:'/platform/tasks', query:{...(taskScope.value ? {space:taskScope.value} : {}), ...(id ? {task:id} : {})}}
}
function announceCreated(knowledgeBaseId:string, id?:string) {
  if (id) {
    taskId.value = id
    if (!taskIds.value.includes(id)) taskIds.value.push(id)
  }
  emit('created', {task_ids:[...taskIds.value],scope:taskScope.value,knowledge_base_id:knowledgeBaseId,direct_count:directCount.value})
}
function resetReceipt() {
  taskId.value = ''; taskIds.value = []; taskScope.value = ''; directCount.value = 0; fileReceipt.value = null
}
function showReceiptTasks() {
  showTasks(receiptTaskId.value)
}
function openReceiptLibrary() {
  if (!launching.value && fileReceipt.value) router.push(receiptLibraryLocation.value)
}
function runPrimaryAction() {
  return needsPreview.value ? loadPages() : launch()
}
async function launch() {
  if (loading.value || launching.value || (mode.value === 'crawl' && listing.value)) return
  if (!space.value) return guide('请先选择知识库')
  if (!editable.value) return guide('当前知识库无写入权限，请切换其他知识库')
  const launchMode = mode.value
  if (launchMode === 'file' && !files.value.length) return guide('请先选择文件，或将文件拖到来源文件区域')
  const knowledgeBaseId = spaceScope.value, source = entryKey.value
  const params = launchMode === 'crawl' ? validatedCrawlerParams() : {}
  if (!params) return
  const root = rootName.value.trim()
  if (launchMode === 'crawl') {
    if (selection.value === 'selected' && !selectedIds.value.length) return guide('请选择要采集的文档')
    if (!directory.value) return guide('请先读取目录预览，确认保存位置', previewStatus.value)
    if (!root || [...root].length > 200 || root === '.' || root === '..' || /[/\\\p{C}]/u.test(root)) {
      directoryError.value = root ? '导入目录名称须为 1～200 个字符，不能包含斜杠、控制字符或仅为 .、..' : '请输入导入目录名称'
      void nextTick(() => scrollToField(rootInput.value))
      return
    }
  }
  launching.value = true; error.value = ''; jumpAfterLaunch = ''
  if (launchMode === 'file') {
    if (fileReceipt.value?.libraryId !== knowledgeBaseId || !fileReceipt.value.failed) {
      resetReceipt()
      fileReceipt.value = {libraryId:knowledgeBaseId,libraryName:space.value.name,taskFiles:0,failed:false}
    }
    fileReceipt.value.failed = false
  } else if (fileReceipt.value) resetReceipt()
  const upload = fileReceipt.value
  try {
    const selected = [...selectedIds.value], selectOnly = selection.value === 'selected'
    taskScope.value = (await bindBase(knowledgeBaseId)).space.scope
    if (upload) {
      const remaining = [...files.value]
      while (remaining.length) {
        const first = remaining[0]!
        if (first.size > taskUploadLimit) {
          await uploadDocumentFile(knowledgeBaseId, first)
          remaining.shift(); files.value = files.value.filter(file=>file!==first); directCount.value++
          announceCreated(knowledgeBaseId)
        } else {
          const batch: File[] = []; let size = 0
          while (remaining[0] && remaining[0].size <= taskUploadLimit && size + remaining[0].size <= taskUploadLimit) { const file = remaining.shift()!; batch.push(file); size += file.size }
          const data = await api.uploadFiles(batch, knowledgeBaseId)
          files.value = files.value.filter(file=>!batch.includes(file))
          upload.taskFiles += batch.length
          announceCreated(knowledgeBaseId, data.task_id)
        }
      }
    } else {
      const payload: any = { ...params, knowledge_base_id: knowledgeBaseId, import_root_name: root }
      if (selectOnly) payload.selected_ids = selected
      const data = await api.startTask(source, payload)
      announceCreated(knowledgeBaseId, data.task_id)
      jumpAfterLaunch = data.task_id
    }
  } catch (err: any) {
    if (upload) upload.failed = true
    error.value = err.message
  }
  finally {
    launching.value = false
    if (jumpAfterLaunch) { const id = jumpAfterLaunch; jumpAfterLaunch = ''; showTasks(id) }
    else if (upload) void nextTick(() => {
      fileReceiptMessage.value?.focus({preventScroll:true})
      scrollToField(fileReceiptMessage.value)
    })
    else if (error.value) void nextTick(() => scrollToField(inlineError.value))
  }
}
watch(launching, value => emit('busy-change', value), {flush:'sync'})
watch([() => route.query.kb_id, () => route.query.space, () => route.query.mode, () => route.query.url], load, { immediate: true })
watch(spaceScope, () => {
  if (launching.value) return
  if (fileReceipt.value?.failed) error.value = ''
  resetReceipt()
})
watch([spaceScope, entryKey, url, projectId, userToken, keyword, crawlMode, maxPages, maxDepth, useServerAuth], () => {
  closeDocumentPreview()
  listRequest++; pages.value = []; selection.value = 'all'; selectedIds.value = []; directory.value = null; rootName.value = ''; listError.value = ''; listing.value = false
})
watch(mode, closeDocumentPreview)
watch([entryKey, url, projectId, useServerAuth], () => { sourceError.value = '' })
watch(rootName, () => { directoryError.value = '' })
</script>

<template>
  <t-card :title="embedded ? undefined : '添加资料'" :bordered="false" class="collection-card" :class="{'collection-embedded':embedded}">
    <template v-if="!embedded" #actions><t-button variant="text" @click="router.push('/platform/knowledge-bases')">知识库</t-button></template>
    <div v-if="error && !fileReceipt" ref="inlineError"><t-alert theme="error" :message="error" /></div>
    <t-loading :loading="loading">
      <t-form label-width="120px" :label-align="embedded ? 'top' : 'right'" class="collection-form" @submit.prevent>
        <t-form-item label="知识库" required>
          <t-select v-model="spaceScope" :disabled="launching" placeholder="选择资料所属知识库" :options="spaces.map(item => ({label: item.name, value: item.id, disabled: !knowledgeAccess(item,profile,auth.hasRole('contributor')).write}))" />
          <p v-if="space && !editable" class="hint">当前知识库无写入权限，请切换其他知识库。</p>
        </t-form-item>
        <t-form-item v-if="space" label="生成内容">
          <t-tag theme="primary" variant="light">{{knowledgeModeLabel(space)}}</t-tag>
        </t-form-item>
        <t-form-item label="资料来源">
          <t-space break-line size="small" class="source-options">
            <t-radio-group :value="activeSource" :disabled="loading || launching" aria-label="资料来源" @change="selectSource">
              <t-radio-button v-for="choice in sourceChoices" :key="choice.key" :value="choice.key"
                :disabled="choice.key !== 'file' && !entries.some(entry => entry.key === choice.key)">{{choice.label}}</t-radio-button>
            </t-radio-group>
            <t-select v-if="moreSources.length" class="more-sources" placeholder="更多来源" aria-label="更多来源"
              :value="activeMoreSource" :options="moreSources" :disabled="loading || launching" @change="selectSource" />
          </t-space>
        </t-form-item>
        <template v-if="mode === 'crawl'">
          <template v-if="entryKey === 'web'">
            <t-form-item ref="sourceField" label="网站地址" required-mark :status="sourceError ? 'error' : undefined">
              <t-input v-model="url" placeholder="https://example.com" :disabled="launching" />
              <template #tips><span v-if="sourceError" role="alert">{{sourceError}}</span></template>
            </t-form-item>
            <t-form-item label="网页范围"><t-radio-group v-model="crawlMode" :disabled="launching"><t-radio-button value="page">当前页面</t-radio-button><t-radio-button value="site">同一网站</t-radio-button></t-radio-group></t-form-item>
            <template v-if="crawlMode === 'site'">
              <t-form-item label="最多采集页数" help="0 表示不限制"><t-input-number v-model="maxPages" :disabled="launching" :min="0" :decimal-places="0" /></t-form-item>
              <t-form-item label="最大链接层级" help="0 表示不限制"><t-input-number v-model="maxDepth" :disabled="launching" :min="0" :decimal-places="0" /></t-form-item>
            </template>
          </template>
          <template v-if="entryKey === 'showdoc'">
            <t-form-item v-if="auth.hasRole('admin')" label="使用平台账号"><t-switch v-model="useServerAuth" :disabled="launching" aria-label="使用平台 ShowDoc 账号" /></t-form-item>
            <t-form-item v-if="useServerAuth" ref="sourceField" label="项目" required-mark :status="sourceError || projectsError ? 'error' : undefined">
              <div class="document-selection"><t-button variant="outline" :loading="projectsLoading" :disabled="launching || projectsLoading" @click="loadProjects">{{projectsLoading ? '正在读取项目…' : '读取项目列表'}}</t-button><t-select v-model="projectId" :disabled="launching" filterable placeholder="选择 ShowDoc 项目" :options="projects.map(project=>({value:String(project.item_id),label:project.item_name}))"/></div>
              <template #tips><span v-if="sourceError || projectsError" role="alert">{{sourceError || projectsError}}</span></template>
            </t-form-item>
            <template v-else>
            <t-form-item ref="sourceField" label="项目编号" required-mark :status="sourceError ? 'error' : undefined">
              <t-input v-model="projectId" :disabled="launching" placeholder="ShowDoc 项目编号" />
              <template #tips><span v-if="sourceError" role="alert">{{sourceError}}</span></template>
            </t-form-item>
            <t-form-item label="访问令牌"><t-input v-model="userToken" :disabled="launching" type="password" placeholder="公开项目无需填写" autocomplete="off" /></t-form-item></template>
            <t-form-item label="标题关键词"><t-input v-model="keyword" :disabled="launching" clearable /></t-form-item>
          </template>
          <t-form-item v-if="!directory && listError" ref="previewStatus">
            <t-alert theme="error" :message="listError" />
          </t-form-item>
          <section v-else-if="directory" ref="previewStatus" class="import-preview" aria-label="目录预览结果">
            <header class="import-preview-heading">
              <h3>目录预览</h3>
              <t-button variant="text" theme="primary" :loading="listing" :disabled="launching || listing" @click="loadPages">{{listing ? '正在重新读取…' : '重新读取目录'}}</t-button>
            </header>
            <t-alert v-if="listError" theme="warning" title="重新读取失败，已保留上次目录" :message="listError" />
            <t-form-item label="目标路径" label-align="top">
              <div class="import-location"><t-icon name="folder" /><span>{{space?.name}}</span><t-icon name="chevron-right" /><span>{{rootName.trim() || '导入目录'}}</span></div>
            </t-form-item>
            <t-form-item ref="rootInput" label="导入目录名称" label-align="top" required-mark :status="directoryError ? 'error' : undefined">
              <t-input v-model="rootName" :disabled="launching" :maxlength="200" aria-label="导入目录名称" placeholder="导入目录名称" />
              <template #tips><span v-if="directoryError" role="alert">{{directoryError}}</span></template>
            </t-form-item>
            <t-form-item label="采集文档" label-align="top"><t-radio-group v-model="selection" :disabled="launching"><t-radio-button value="all">全部文档</t-radio-button><t-radio-button value="selected" :disabled="!pages.length">选择文档</t-radio-button></t-radio-group></t-form-item>
            <t-form-item v-if="selection === 'selected' && pages.length" label="文档" label-align="top" required-mark>
              <t-select v-model="selectedIds" :disabled="launching" multiple filterable clearable placeholder="按标题选择文档" :options="pages.map(item => ({label: item.directory_path?.length ? `${item.page_title} · ${item.directory_path.join(' / ')}` : item.page_title, value: String(item.page_id)}))" />
            </t-form-item>
            <t-alert v-if="directory.preview_complete === false" theme="info"
              :message="`目录预览尚未完成，已发现 ${pages.length} 份文档。采集全部文档时会继续发现同站页面并保留目录结构。`" />
            <p v-if="directory.preview_complete !== false || selection === 'selected'" class="hint">已选 {{previewPages.length}} 份文档</p>
            <t-tree :data="previewTree" expand-all class="import-directory-tree">
              <template #operations="{node}">
                <t-button v-if="String(node.value).startsWith('page:')" size="small" variant="text" theme="primary"
                  :disabled="listing || launching" :aria-label="`预览 ${node.label}`"
                  @click.stop="openDocumentPreview(String(node.value).slice(5), String(node.label), $event)">预览</t-button>
              </template>
            </t-tree>
          </section>
        </template>
        <t-form-item v-else label="来源文件">
          <div :inert="launching" class="file-source" :class="{'file-drag-active':dragOver}" @dragover.prevent="dragOver=true" @dragleave="dragOver=false" @drop.prevent="dropFiles">
            <input ref="fileInput" type="file" multiple hidden @change="pickFiles" />
            <input ref="folderInput" type="file" webkitdirectory multiple hidden @change="pickFiles" />
            <t-space break-line>
              <t-button variant="outline" :disabled="launching" @click="fileInput?.click()">添加文件</t-button>
              <t-button variant="text" :disabled="launching" @click="folderInput?.click()">选择文件夹</t-button>
            </t-space>
            <p class="hint">也可拖拽文件到此处，最多 {{maxUploadFiles}} 个待提交文件。</p>
            <t-alert v-if="fileIntakeIssues.length" title="有文件未添加" theme="warning" role="status">
              <template #message>
                <ul class="file-issues"><li v-for="(issue, index) in fileIntakeIssues" :key="index">{{issue}}</li></ul>
              </template>
            </t-alert>
            <p v-if="files.length" class="hint" aria-live="polite">
              待提交 {{files.length}} / {{maxUploadFiles}} 个文件 · 共 {{formatFileSize(files.reduce((sum,file)=>sum+file.size,0))}}
            </p>
            <ul v-if="files.length" class="file-list">
              <li v-for="(file, index) in files" :key="index">
                <span class="file-name">{{file.webkitRelativePath || file.name}}</span>
                <span class="file-size">{{formatFileSize(file.size)}}</span>
                <t-button size="small" variant="text" :disabled="launching" :aria-label="'移除 '+(file.webkitRelativePath || file.name)" @click="files.splice(index, 1)">移除</t-button>
              </li>
            </ul>
          </div>
        </t-form-item>
      </t-form>
    </t-loading>
    <t-empty v-if="!loading && !spaces.length" description="请先创建知识库"><t-button @click="router.push('/platform/knowledge-bases')">创建知识库</t-button></t-empty>
    <ImportDirectoryLinks :directories="importRoots" />
    <t-alert v-if="taskReadError" theme="warning" :message="'暂时无法读取导入目录：'+taskReadError" />
    <t-alert v-if="showFileReceipt && fileReceipt" :theme="fileReceipt.failed ? 'warning' : 'success'"
      :title="launching ? '正在提交文件' : fileReceipt.failed ? '上传未完成' : '文件已提交'">
      <template #message>
        <div ref="fileReceiptMessage" class="file-receipt" role="status" tabindex="-1"
          :aria-label="fileReceipt.failed ? '上传未完成' : '文件已提交'">
          <p>目标知识库 · {{fileReceipt.libraryName}}</p>
          <p v-if="taskIds.length">{{fileReceipt.taskFiles}} 个文件已创建 {{taskIds.length}} 个资料任务。</p>
          <p v-if="uploadNotice">{{uploadNotice}}</p>
          <template v-if="fileReceipt.failed">
            <p v-if="error">{{error}}</p>
            <p v-if="files.length">还有 {{files.length}} 个文件待提交，请核对接收状态后重试。</p>
          </template>
        </div>
        <t-space v-if="taskIds.length || directCount" break-line size="small">
          <t-button v-if="taskIds.length" size="small" variant="outline" :disabled="launching"
            :href="files.length && !launching ? router.resolve(taskLocation(receiptTaskId)).href : undefined"
            :target="files.length ? '_blank' : undefined" rel="noopener" @click="!files.length && showReceiptTasks()">
            {{files.length ? '查看任务（新标签页）' : '查看任务'}}
          </t-button>
          <t-button v-if="directCount" size="small" variant="outline" :disabled="launching"
            :href="files.length && !launching ? router.resolve(receiptLibraryLocation).href : undefined"
            :target="files.length ? '_blank' : undefined" rel="noopener" @click="!files.length && openReceiptLibrary()">
            {{files.length ? '打开知识库（新标签页）' : '打开知识库'}}
          </t-button>
        </t-space>
      </template>
    </t-alert>
    <t-alert v-else-if="mode === 'crawl' && !fileReceipt && taskIds.length" theme="success" title="任务已创建">
      <template #operation><t-button variant="text" :disabled="launching" @click="showTasks()">查看任务</t-button></template>
    </t-alert>
    <t-dialog :visible="!!previewTarget" :header="documentPreview?.title || previewTarget?.title" attach="body"
      width="min(740px, calc(100vw - 32px))" :footer="false" @close="closeDocumentPreview" @closed="restorePreviewFocus">
      <section v-if="previewTarget" class="collection-document-preview" aria-label="文档正文">
        <div v-if="documentLoading" role="status">
          <p>正在读取正文…</p>
          <t-skeleton :row-col="[1, 1, 1]" />
        </div>
        <t-alert v-else-if="documentError" theme="error" :message="documentError">
          <template #operation><t-button variant="text" @click="openDocumentPreview(previewTarget.id, previewTarget.title)">重试</t-button></template>
        </t-alert>
        <DocMarkdown v-else-if="documentPreview" :content="documentPreview.content" :title="documentPreview.title"
          :source-base-url="documentPreview.source_base_url" />
      </section>
    </t-dialog>
    <Teleport to="#collect-view-drawer-footer" :disabled="!embedded" defer>
      <t-space break-line class="collection-footer">
        <t-button v-if="!showFileReceipt && (mode !== 'file' || !files.length)" variant="outline" :disabled="launching" @click="showTasks()">查看任务</t-button>
        <t-button v-if="!showFileReceipt || files.length || launching" theme="primary" :loading="launching || (needsPreview && listing)"
          :disabled="loading || launching || (mode === 'crawl' && listing)" @click="runPrimaryAction">
          {{ mode === 'file' ? (launching ? '正在提交文件…' : fileSubmitLabel) : launching ? '正在创建采集任务…' : needsPreview ? (listing ? '正在读取目录…' : '读取目录预览') : '采集到知识库' }}
        </t-button>
      </t-space>
    </Teleport>
  </t-card>
</template>

<style scoped>
.collection-card { height: 100%; overflow: auto; }
.collection-embedded { height: auto; overflow: visible; }
.collection-embedded :deep(.t-card__body) { padding: 0; }
.collection-card :deep(.t-alert) { margin-bottom: 16px; }
.collection-form { max-width: 900px; margin-top: 24px; }
.collection-footer { display: flex; justify-content: flex-end; padding-bottom: env(safe-area-inset-bottom); }
.source-options { align-items: center; max-width: 100%; }
.more-sources { width: 160px; }
.import-preview { padding: 16px; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); }
.import-preview-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.import-preview-heading h3 { margin: 0; font-size: var(--app-text-base); font-weight: 600; }
.import-preview :deep(.t-form__item) { margin-bottom: 16px; }
.import-location { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; overflow-wrap: anywhere; }
.import-location .t-icon { flex: none; }
.import-directory-tree { max-height: 320px; overflow: auto; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); padding: 12px; }
.import-directory-tree :deep(.t-tree__label) { min-width: 0; white-space: normal; overflow-wrap: anywhere; }
.collection-document-preview { min-height: 120px; max-height: 65dvh; overflow: auto; overflow-wrap: anywhere; }
.collection-document-preview :deep(.doc-markdown-body *) { box-sizing: border-box; min-width: 0; max-width: 100%; }
.hint { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.file-list { padding-left: 0; list-style: none; max-height: 240px; overflow: auto; overflow-wrap: anywhere; }
.file-list li { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.file-name { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.file-size { flex: none; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.file-source { width: 100%; min-width: 0; padding: 16px; border: 1px dashed var(--td-component-stroke); border-radius: var(--app-radius-md); }
.file-drag-active { border-color: var(--td-brand-color); background: var(--td-brand-color-light); }
.file-issues { margin: 0; padding-inline-start: 1.25em; max-height: 120px; overflow: auto; overflow-wrap: anywhere; }
.file-receipt p { margin: 0 0 8px; overflow-wrap: anywhere; }
.document-selection { display: grid; gap: 12px; width: 100%; }
</style>
