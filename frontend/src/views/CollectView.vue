<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { bindBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, listBases, uploadDocumentFile, type BasePermissionProfile } from '@/api/contextdb'
import { CONTEXTDB_REVIEW_FORMAT_NOTICE } from '@/utils/contextdbReviewSupport'
import { formatFileSize } from '@/utils/files'
import { directoryPreview } from './importDirectories'
import ImportDirectoryLinks from './ImportDirectoryLinks.vue'
import KbUploadSourceDropdown from './knowledge/components/KbUploadSourceDropdown.vue'

const props = withDefaults(defineProps<{embedded?:boolean}>(), {embedded:false})
const emit = defineEmits<{
  created:[receipt:{task_ids:string[];scope:string;knowledge_base_id:string;direct_count:number}]
  'show-tasks':[target:{scope:string;task_id?:string}]
  'busy-change':[busy:boolean]
}>()
const route = useRoute(), router = useRouter(), auth = useAuthStore()
const entries = ref<any[]>([]), spaces = ref<any[]>([]), profile = ref<BasePermissionProfile | null>(null)
const spaceScope = ref(''), entryKey = ref(''), url = ref(''), projectId = ref(''), userToken = ref(''), keyword = ref('')
const crawlMode = ref('page'), maxPages = ref(0), maxDepth = ref(0), selection = ref('all')
const selectedIds = ref<string[]>([]), pages = ref<any[]>([]), listing = ref(false), listError = ref('')
const useServerAuth=ref(false),projects=ref<any[]>([]),projectsLoading=ref(false)
const mode = ref('crawl'), files = ref<File[]>([]), launching = ref(false), loading = ref(false)
const error = ref(''), taskId = ref(''), taskScope = ref(''), uploadNotice = ref('')
const taskIds = ref<string[]>([]), directCount = ref(0)
const directory = ref<{root_name:string;source_key:string;preview_complete?:boolean}|null>(null), rootName = ref('')
const importRoots = ref<unknown>([]), taskReadError = ref('')
const previewPages = computed(() => selection.value === 'selected' ? pages.value.filter(page => selectedIds.value.includes(String(page.page_id))) : pages.value)
const previewTree = computed(() => directory.value ? directoryPreview(rootName.value.trim(), previewPages.value) : [])
let pollTimer: number | undefined
let taskRequest = 0
const previewButton = ref(), rootInput = ref(), dragOver = ref(false)
let jumpAfterLaunch = ''
function guide(message: string, target?: any) {
  MessagePlugin.warning(message)
  const el = target?.$el ?? target
  el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
}
function dropFiles(event: DragEvent) {
  dragOver.value = false
  if (launching.value) return
  const dropped = Array.from(event.dataTransfer?.files || [])
  if (dropped.length) selectFiles([...files.value, ...dropped])
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
    return {url: url.value.trim(), crawl_mode: crawlMode.value, max_pages: maxPages.value, max_depth: maxDepth.value}
  }
  if (entryKey.value === 'showdoc') {
    if (!projectId.value.trim()) throw new Error('请输入项目编号')
    return {item_id: projectId.value.trim(), ...(useServerAuth.value ? {auth:true} : userToken.value.trim() ? {user_token: userToken.value.trim()} : {}), ...(keyword.value.trim() ? {keyword: keyword.value.trim()} : {})}
  }
  return {}
}
async function loadProjects(){
  if (launching.value) return
  projectsLoading.value=true;error.value=''
  try{projects.value=(await api.showdocProjects()).projects||[]}
  catch(err:any){error.value=err.message}
  finally{projectsLoading.value=false}
}

async function loadPages() {
  if (launching.value) return
  const request = ++listRequest
  listing.value = true; listError.value = ''; pages.value = []; selectedIds.value = []; directory.value = null; rootName.value = ''
  try {
    const result = await api.entryDocuments(entryKey.value, { ...crawlerParams(), knowledge_base_id: spaceScope.value })
    if (request === listRequest) {
      if (!result.directory?.root_name || !result.directory?.source_key) throw new Error('未能读取来源目录，请重试')
      pages.value = result.pages || []; directory.value = result.directory; rootName.value = result.directory.root_name
    }
  } catch (err: any) { if (request === listRequest) listError.value = err.message }
  finally { if (request === listRequest) listing.value = false }
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
onUnmounted(() => { taskRequest++; listRequest++; requestId++; window.clearTimeout(pollTimer) })

async function load() {
  if (launching.value) return
  const request = ++requestId
  loading.value = true; error.value = ''; taskId.value = ''; taskIds.value = []; directCount.value = 0; uploadNotice.value = ''; files.value = []
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
    entryKey.value = url.value ? 'web' : entries.value[0]?.key || ''
  } catch (err: any) { if (request === requestId) error.value = err.message }
  finally { if (request === requestId) loading.value = false }
}

function selectFiles(selected: File[]) {
  if (launching.value) return
  if (selected.length > 50) {
    error.value = '一次最多选择 50 个文件。'; return
  }
  files.value = selected; mode.value = 'file'; error.value = ''; taskId.value = ''; taskIds.value = []; directCount.value = 0; uploadNotice.value = ''
}
function selectUrl(value: string) { if (launching.value) return; mode.value = 'crawl'; entryKey.value = 'web'; url.value = value }
function showTasks(id = taskId.value) {
  if (launching.value) return
  if (props.embedded) emit('show-tasks', {scope:taskScope.value, ...(id ? {task_id:id} : {})})
  else router.push({path:'/platform/tasks', query:{...(taskScope.value ? {space:taskScope.value} : {}), ...(id ? {task:id} : {})}})
}
function announceCreated(knowledgeBaseId:string, id?:string) {
  if (id) {
    taskId.value = id
    if (!taskIds.value.includes(id)) taskIds.value.push(id)
  }
  emit('created', {task_ids:[...taskIds.value],scope:taskScope.value,knowledge_base_id:knowledgeBaseId,direct_count:directCount.value})
}
async function launch() {
  if (launching.value) return
  if (!space.value) return guide('请先选择知识库')
  if (!editable.value) return guide('当前知识库无写入权限，请切换其他知识库')
  const launchMode = mode.value
  if (launchMode === 'file' && !files.value.length) return guide('请先选择文件，或将文件拖到来源文件区域')
  if (launchMode === 'crawl') {
    if (selection.value === 'selected' && !selectedIds.value.length) return guide('请选择要采集的文档')
    if (!directory.value) return guide('请先读取目录预览，确认保存位置', previewButton.value)
    if (!rootName.value.trim()) return guide('请输入导入目录名称', rootInput.value)
  }
  const knowledgeBaseId = spaceScope.value, source = entryKey.value
  let params: any
  try { params = launchMode === 'crawl' ? crawlerParams() : undefined }
  catch (err: any) { return guide(err.message) }
  launching.value = true; error.value = ''; jumpAfterLaunch = ''
  try {
    const selected = [...selectedIds.value], root = rootName.value.trim(), selectOnly = selection.value === 'selected'
    taskScope.value = (await bindBase(knowledgeBaseId)).space.scope
    if (launchMode === 'file') {
      const remaining = [...files.value], limit = 100 * 1024 * 1024
      while (remaining.length) {
        const first = remaining[0]!
        if (first.size > limit) {
          await uploadDocumentFile(knowledgeBaseId, first)
          remaining.shift(); files.value = files.value.filter(file=>file!==first); directCount.value++
          uploadNotice.value = `${directCount.value} 份大文件已提交知识库，原件由 ContextDB 保存；请到文档中核对评审与入库状态。`
          announceCreated(knowledgeBaseId)
        } else {
          const batch: File[] = []; let size = 0
          while (remaining[0] && remaining[0].size <= limit && size + remaining[0].size <= limit) { const file = remaining.shift()!; batch.push(file); size += file.size }
          const data = await api.uploadFiles(batch, knowledgeBaseId)
          files.value = files.value.filter(file=>!batch.includes(file))
          announceCreated(knowledgeBaseId, data.task_id)
        }
      }
      if (taskIds.value.length === 1 && directCount.value === 0) jumpAfterLaunch = taskIds.value[0]
    } else {
      const payload: any = { ...params, knowledge_base_id: knowledgeBaseId, import_root_name: root }
      if (selectOnly) payload.selected_ids = selected
      const data = await api.startTask(source, payload)
      announceCreated(knowledgeBaseId, data.task_id)
      jumpAfterLaunch = data.task_id
    }
  } catch (err: any) { error.value = `${err.message}${launchMode==='file'?'。已成功的文件不会重复提交；请先核对官方文档，再决定是否重试剩余文件。':''}` }
  finally {
    launching.value = false
    if (jumpAfterLaunch) { const id = jumpAfterLaunch; jumpAfterLaunch = ''; showTasks(id) }
  }
}
watch(launching, value => emit('busy-change', value), {flush:'sync'})
watch([() => route.query.kb_id, () => route.query.space, () => route.query.mode, () => route.query.url], load, { immediate: true })
watch(spaceScope, () => {
  if (launching.value) return
  taskId.value = ''; taskIds.value = []; taskScope.value = ''; directCount.value = 0; uploadNotice.value = ''
})
watch([spaceScope, entryKey, url, projectId, userToken, keyword, crawlMode, maxPages, maxDepth, useServerAuth], () => {
  listRequest++; pages.value = []; selectedIds.value = []; directory.value = null; rootName.value = ''; listError.value = ''; listing.value = false
})
</script>

<template>
  <t-card :title="embedded ? undefined : '添加资料'" :bordered="false" class="collection-card" :class="{'collection-embedded':embedded}">
    <template v-if="!embedded" #actions><t-button variant="text" @click="router.push('/platform/knowledge-bases')">知识库</t-button></template>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="uploadNotice" theme="info" :message="uploadNotice" />
    <p class="hint">资料采集成功后自动提交到所选知识库；需人工评审时在“知识评审”中处理。原文入库与图谱或 Wiki 编译分别推进。</p>
    <t-alert theme="info" :message="CONTEXTDB_REVIEW_FORMAT_NOTICE" />
    <t-loading :loading="loading">
      <t-form label-width="120px" :label-align="embedded ? 'top' : 'right'" class="collection-form" @submit.prevent>
        <t-form-item label="知识库" required>
          <t-select v-model="spaceScope" :disabled="launching" placeholder="选择资料所属知识库" :options="spaces.map(item => ({label: item.name, value: item.id, disabled: !knowledgeAccess(item,profile,auth.hasRole('contributor')).write}))" />
          <p v-if="space && !editable" class="hint">当前知识库无写入权限，请切换其他知识库。</p>
        </t-form-item>
        <t-form-item v-if="space" label="生成内容">
          <t-space break-line><t-tag theme="primary" variant="light">{{knowledgeModeLabel(space)}}</t-tag><t-tag>{{space.review_enabled?'知识评审已开启':'知识评审已关闭'}}</t-tag></t-space>
        </t-form-item>
        <t-form-item label="资料来源"><t-radio-group v-model="mode" :disabled="launching"><t-radio-button value="crawl">网站采集</t-radio-button><t-radio-button value="file">文件上传</t-radio-button></t-radio-group></t-form-item>
        <template v-if="mode === 'crawl'">
          <t-form-item label="采集平台"><t-select v-model="entryKey" :disabled="launching" :options="entries.map(entry => ({label: entry.display_name, value: entry.key}))" /></t-form-item>
          <template v-if="entryKey === 'web'">
            <t-form-item label="网站地址" required><t-input v-model="url" placeholder="https://example.com" :disabled="launching" /></t-form-item>
            <t-form-item label="采集范围"><t-radio-group v-model="crawlMode" :disabled="launching"><t-radio-button value="page">当前页面</t-radio-button><t-radio-button value="site">同一网站</t-radio-button></t-radio-group></t-form-item>
            <template v-if="crawlMode === 'site'">
              <t-form-item label="最多采集页数" help="0 表示不限制"><t-input-number v-model="maxPages" :disabled="launching" :min="0" :decimal-places="0" /></t-form-item>
              <t-form-item label="最大链接层级" help="0 表示不限制"><t-input-number v-model="maxDepth" :disabled="launching" :min="0" :decimal-places="0" /></t-form-item>
            </template>
          </template>
          <template v-if="entryKey === 'showdoc'">
            <t-form-item v-if="auth.hasRole('admin')" label="使用平台账号"><t-switch v-model="useServerAuth" :disabled="launching" aria-label="使用平台 ShowDoc 账号" /></t-form-item>
            <t-form-item v-if="useServerAuth" label="项目" required><div class="document-selection"><t-button variant="outline" :loading="projectsLoading" :disabled="launching" @click="loadProjects">读取项目列表</t-button><t-select v-model="projectId" :disabled="launching" filterable placeholder="选择 ShowDoc 项目" :options="projects.map(project=>({value:String(project.item_id),label:project.item_name}))"/></div></t-form-item>
            <template v-else><t-form-item label="项目编号" required><t-input v-model="projectId" :disabled="launching" placeholder="ShowDoc 项目编号" /></t-form-item>
            <t-form-item label="访问令牌"><t-input v-model="userToken" :disabled="launching" type="password" placeholder="公开项目无需填写" autocomplete="off" /></t-form-item></template>
            <t-form-item label="标题关键词"><t-input v-model="keyword" :disabled="launching" clearable /></t-form-item>
          </template>
          <t-form-item label="采集文档"><t-radio-group v-model="selection" :disabled="launching"><t-radio-button value="all">全部文档</t-radio-button><t-radio-button value="selected">选择文档</t-radio-button></t-radio-group></t-form-item>
          <t-form-item label="目录预览"><t-button ref="previewButton" :variant="directory || listing ? 'outline' : 'base'" :loading="listing" :disabled="launching" @click="loadPages">{{directory ? '重新读取目录' : '读取目录预览'}}</t-button></t-form-item>
          <t-form-item v-if="listError" label=""><t-alert theme="error" :message="listError" /></t-form-item>
          <t-form-item v-if="selection === 'selected'" label="文档" required>
            <div class="document-selection">
              <t-select v-model="selectedIds" :disabled="launching" multiple filterable clearable placeholder="按标题选择文档" :loading="listing" :options="pages.map(item => ({label: item.directory_path?.length ? `${item.page_title} · ${item.directory_path.join(' / ')}` : item.page_title, value: String(item.page_id)}))" />
            </div>
          </t-form-item>
          <t-form-item v-if="directory" label="保存到" required>
            <div class="import-preview">
              <div class="import-location"><t-icon name="folder" /><span>{{space?.name}}</span><t-icon name="chevron-right" /><t-input ref="rootInput" v-model="rootName" :disabled="launching" :maxlength="200" aria-label="导入目录名称" placeholder="导入目录名称" /></div>
              <p class="hint">以来源名称创建一级目录，保留原始子目录；根页面直接保存在此目录下。已选 {{previewPages.length}} 份文档。</p>
              <t-alert v-if="directory.preview_complete === false" theme="info" message="网站链接尚未全部发现，当前显示已发现的目录；采集时会继续发现页面并保留其目录。" />
              <t-tree :data="previewTree" expand-all class="import-directory-tree" />
            </div>
          </t-form-item>
        </template>
        <t-form-item v-else label="来源文件">
          <div :inert="launching" class="file-source" :class="{'file-drag-active':dragOver}" @dragover.prevent="dragOver=true" @dragleave="dragOver=false" @drop.prevent="dropFiles">
            <KbUploadSourceDropdown trigger-label="选择文件" @files="selectFiles" @url="selectUrl" />
            <p class="hint">最多 50 个文件，可拖拽到此处；普通批次保留采集归档，超过 100 MB 的单文件直接保存到 ContextDB。</p>
            <p v-if="files.length" class="hint">已选 {{files.length}} / 50 个文件 · 共 {{formatFileSize(files.reduce((sum,file)=>sum+file.size,0))}}</p>
            <ul v-if="files.length" class="file-list"><li v-for="(file, index) in files" :key="index"><span class="file-name">{{ file.name }}</span><span class="file-size">{{formatFileSize(file.size)}}</span><t-tag v-if="file.size>100*1024*1024" size="small" variant="light">直接入库</t-tag><t-button size="small" variant="text" :disabled="launching" :aria-label="'移除 '+file.name" @click="files.splice(index, 1)">移除</t-button></li></ul>
          </div>
        </t-form-item>
        <t-form-item><t-space break-line>
          <t-button theme="primary" :loading="launching" :disabled="launching" @click="launch">{{ mode === 'file' ? '上传到知识库' : '采集到知识库' }}</t-button>
          <t-button variant="outline" :disabled="launching" @click="showTasks()">查看任务</t-button>
        </t-space></t-form-item>
      </t-form>
    </t-loading>
    <t-empty v-if="!loading && !spaces.length" description="请先创建知识库"><t-button @click="router.push('/platform/knowledge-bases')">创建知识库</t-button></t-empty>
    <ImportDirectoryLinks :directories="importRoots" />
    <t-alert v-if="taskReadError" theme="warning" :message="'暂时无法读取导入目录：'+taskReadError" />
    <t-alert v-if="taskIds.length" theme="success" :title="taskIds.length>1 ? `已创建 ${taskIds.length} 个资料任务` : '任务已创建'"><template #operation><t-space break-line><t-button v-for="id in taskIds" :key="id" variant="text" :disabled="launching" @click="showTasks(id)">{{taskIds.length>1 ? '查看任务 '+id.slice(0,8) : '查看任务'}}</t-button></t-space></template></t-alert>
  </t-card>
</template>

<style scoped>
.collection-card { height: 100%; overflow: auto; }
.collection-embedded { height: auto; overflow: visible; }
.collection-embedded :deep(.t-card__body) { padding: 0; }
.collection-card :deep(.t-alert) { margin-bottom: 16px; }
.collection-form { max-width: 900px; margin-top: 24px; }
.import-preview { width: 100%; }
.import-location { display: flex; align-items: center; gap: 8px; }
.import-location .t-input__wrap { flex: 1; max-width: 360px; }
.collection-embedded .import-location { flex-wrap: wrap; }
.collection-embedded .import-location .t-input__wrap { min-width: 0; }
.import-directory-tree { max-height: 320px; overflow: auto; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); padding: 12px; }
.hint { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.file-list { padding-left: 0; list-style: none; max-height: 240px; overflow: auto; overflow-wrap: anywhere; }
.file-list li { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.file-name { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.file-size { flex: none; color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.file-source { border-radius: var(--app-radius-md); transition: outline-color .15s; outline: 2px dashed transparent; outline-offset: 6px; }
.file-drag-active { outline-color: var(--td-brand-color); }
.document-selection { display: grid; gap: 12px; width: 100%; }
</style>
