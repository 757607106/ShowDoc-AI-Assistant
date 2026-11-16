<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { bindBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, listBases, uploadDocumentFile, type BasePermissionProfile } from '@/api/contextdb'
import { CONTEXTDB_REVIEW_FORMAT_NOTICE } from '@/utils/contextdbReviewSupport'
import KbUploadSourceDropdown from './knowledge/components/KbUploadSourceDropdown.vue'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const entries = ref<any[]>([]), spaces = ref<any[]>([]), profile = ref<BasePermissionProfile | null>(null)
const spaceScope = ref(''), entryKey = ref(''), url = ref(''), projectId = ref(''), userToken = ref(''), keyword = ref('')
const crawlMode = ref('page'), maxPages = ref(0), maxDepth = ref(0), selection = ref('all')
const selectedIds = ref<string[]>([]), pages = ref<any[]>([]), listing = ref(false), listError = ref('')
const useServerAuth=ref(false),projects=ref<any[]>([]),projectsLoading=ref(false)
const mode = ref('crawl'), files = ref<File[]>([]), launching = ref(false), loading = ref(false)
const error = ref(''), taskId = ref(''), taskScope = ref(''), uploadNotice = ref('')
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
  projectsLoading.value=true;error.value=''
  try{projects.value=(await api.showdocProjects()).projects||[]}
  catch(err:any){error.value=err.message}
  finally{projectsLoading.value=false}
}

async function loadPages() {
  const request = ++listRequest
  listing.value = true; listError.value = ''; pages.value = []; selectedIds.value = []
  try {
    const result = await api.entryDocuments(entryKey.value, crawlerParams())
    if (request === listRequest) pages.value = result.pages || []
  } catch (err: any) { if (request === listRequest) listError.value = err.message }
  finally { if (request === listRequest) listing.value = false }
}

async function load() {
  const request = ++requestId
  loading.value = true; error.value = ''; taskId.value = ''; files.value = []
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
  if (selected.length > 50) {
    error.value = '一次最多选择 50 个文件。'; return
  }
  files.value = selected; mode.value = 'file'; error.value = ''; taskId.value = ''
}
function selectUrl(value: string) { mode.value = 'crawl'; entryKey.value = 'web'; url.value = value }
async function launch() {
  if (launching.value || !space.value || !editable.value) return
  launching.value = true; error.value = ''; taskId.value = ''; uploadNotice.value = ''
  try {
    taskScope.value = (await bindBase(spaceScope.value)).space.scope
    let data: any
    if (mode.value === 'file') {
      if (!files.value.length) throw new Error('请先选择文件')
      const remaining = [...files.value], limit = 100 * 1024 * 1024
      let direct = 0
      while (remaining.length) {
        const first = remaining[0]!
        if (first.size > limit) {
          await uploadDocumentFile(spaceScope.value, first)
          remaining.shift(); files.value = files.value.filter(file=>file!==first); direct++
          uploadNotice.value = `${direct} 份大文件已提交知识库，原件由 ContextDB 保存；请到文档中核对评审与入库状态。`
        } else {
          const batch: File[] = []; let size = 0
          while (remaining[0] && remaining[0].size <= limit && size + remaining[0].size <= limit) { const file = remaining.shift()!; batch.push(file); size += file.size }
          data = await api.uploadFiles(batch, spaceScope.value)
          taskId.value = data.task_id
          files.value = files.value.filter(file=>!batch.includes(file))
        }
      }
    } else {
      if (selection.value === 'selected' && !selectedIds.value.length) throw new Error('请选择要采集的文档')
      const payload: any = { ...crawlerParams(), knowledge_base_id: spaceScope.value }
      if (selection.value === 'selected') payload.selected_ids = selectedIds.value
      data = await api.startTask(entryKey.value, payload)
    }
    if(data?.task_id)taskId.value = data.task_id
  } catch (err: any) { error.value = `${err.message}${mode.value==='file'?'。已成功的文件不会重复提交；请先核对官方文档，再决定是否重试剩余文件。':''}` }
  finally { launching.value = false }
}
watch(() => route.fullPath, load, { immediate: true })
watch([entryKey, url, projectId, userToken, keyword, crawlMode, maxPages, maxDepth, useServerAuth], () => {
  listRequest++; pages.value = []; selectedIds.value = []; listError.value = ''; listing.value = false
})
</script>

<template>
  <t-card title="添加资料" :bordered="false" class="collection-card">
    <template #actions><t-button variant="text" @click="router.push('/platform/knowledge-bases')">知识库</t-button></template>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-alert v-if="uploadNotice" theme="info" :message="uploadNotice" />
    <p class="hint">资料采集成功后自动提交到所选知识库；需人工评审时在“知识评审”中处理。原文入库与图谱或 Wiki 编译分别推进。</p>
    <t-alert theme="info" :message="CONTEXTDB_REVIEW_FORMAT_NOTICE" />
    <t-loading :loading="loading">
      <t-form label-width="120px" class="collection-form" @submit.prevent>
        <t-form-item label="知识库" required>
          <t-select v-model="spaceScope" :disabled="launching" placeholder="选择资料所属知识库" :options="spaces.map(item => ({label: item.name, value: item.id, disabled: !knowledgeAccess(item,profile,auth.hasRole('contributor')).write}))" />
        </t-form-item>
        <t-form-item v-if="space" label="生成内容">
          <t-space><t-tag theme="primary" variant="light">{{knowledgeModeLabel(space)}}</t-tag><t-tag>{{space.review_enabled?'知识评审已开启':'知识评审已关闭'}}</t-tag></t-space>
        </t-form-item>
        <t-form-item label="资料来源"><t-radio-group v-model="mode" :disabled="launching"><t-radio-button value="crawl">网站采集</t-radio-button><t-radio-button value="file">文件上传</t-radio-button></t-radio-group></t-form-item>
        <template v-if="mode === 'crawl'">
          <t-form-item label="采集平台"><t-select v-model="entryKey" :options="entries.map(entry => ({label: entry.display_name, value: entry.key}))" /></t-form-item>
          <template v-if="entryKey === 'web'">
            <t-form-item label="网站地址" required><t-input v-model="url" placeholder="https://example.com" :disabled="launching" /></t-form-item>
            <t-form-item label="采集范围"><t-radio-group v-model="crawlMode"><t-radio-button value="page">当前页面</t-radio-button><t-radio-button value="site">同一网站</t-radio-button></t-radio-group></t-form-item>
            <template v-if="crawlMode === 'site'">
              <t-form-item label="最多采集页数" help="0 表示不限制"><t-input-number v-model="maxPages" :min="0" :decimal-places="0" /></t-form-item>
              <t-form-item label="最大链接层级" help="0 表示不限制"><t-input-number v-model="maxDepth" :min="0" :decimal-places="0" /></t-form-item>
            </template>
          </template>
          <template v-if="entryKey === 'showdoc'">
            <t-form-item v-if="auth.hasRole('admin')" label="使用平台账号"><t-switch v-model="useServerAuth" aria-label="使用平台 ShowDoc 账号" /></t-form-item>
            <t-form-item v-if="useServerAuth" label="项目" required><div class="document-selection"><t-button variant="outline" :loading="projectsLoading" @click="loadProjects">读取项目列表</t-button><t-select v-model="projectId" filterable placeholder="选择 ShowDoc 项目" :options="projects.map(project=>({value:String(project.item_id),label:project.item_name}))"/></div></t-form-item>
            <template v-else><t-form-item label="项目编号" required><t-input v-model="projectId" placeholder="ShowDoc 项目编号" /></t-form-item>
            <t-form-item label="访问令牌"><t-input v-model="userToken" type="password" placeholder="公开项目无需填写" autocomplete="off" /></t-form-item></template>
            <t-form-item label="标题关键词"><t-input v-model="keyword" clearable /></t-form-item>
          </template>
          <t-form-item label="采集文档"><t-radio-group v-model="selection"><t-radio-button value="all">全部文档</t-radio-button><t-radio-button value="selected">选择文档</t-radio-button></t-radio-group></t-form-item>
          <t-form-item v-if="selection === 'selected'" label="文档" required>
            <div class="document-selection"><t-button variant="outline" :loading="listing" @click="loadPages">读取文档列表</t-button>
              <t-select v-model="selectedIds" multiple filterable clearable placeholder="按标题选择文档" :loading="listing" :options="pages.map(item => ({label: item.category ? `${item.page_title} · ${item.category}` : item.page_title, value: String(item.page_id)}))" />
              <t-alert v-if="listError" theme="error" :message="listError" />
            </div>
          </t-form-item>
        </template>
        <t-form-item v-else label="来源文件">
          <div>
            <KbUploadSourceDropdown trigger-label="选择文件" @files="selectFiles" @url="selectUrl" />
            <p class="hint">最多 50 个文件；普通批次保留采集归档，超过 100 MB 的单文件直接保存到 ContextDB。</p>
            <ul v-if="files.length" class="file-list"><li v-for="(file, index) in files" :key="index">{{ file.name }} <t-button size="small" variant="text" :disabled="launching" :aria-label="'移除 '+file.name" @click="files.splice(index, 1)">移除</t-button></li></ul>
          </div>
        </t-form-item>
        <t-form-item><t-space>
          <t-button theme="primary" :loading="launching" :disabled="!editable || !space || (mode === 'file' && !files.length)" @click="launch">{{ mode === 'file' ? '上传到知识库' : '采集到知识库' }}</t-button>
          <t-button variant="outline" @click="router.push({path:'/platform/tasks', query:taskScope ? {space:taskScope} : {}})">查看任务</t-button>
        </t-space></t-form-item>
      </t-form>
    </t-loading>
    <t-empty v-if="!loading && !spaces.length" description="请先创建知识库"><t-button @click="router.push('/platform/knowledge-bases')">创建知识库</t-button></t-empty>
    <t-alert v-if="taskId" theme="success" title="任务已创建"><template #operation><t-button variant="text" @click="router.push({path:'/platform/tasks',query:{space:taskScope}})">查看任务</t-button></template></t-alert>
  </t-card>
</template>

<style scoped>
.collection-card { height: 100%; overflow: auto; }
.collection-card :deep(.t-alert) { margin-bottom: 16px; }
.collection-form { max-width: 900px; margin-top: 24px; }
.hint { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); }
.file-list { padding-left: 20px; max-height: 240px; overflow: auto; overflow-wrap: anywhere; }
.document-selection { display: grid; gap: 12px; width: 100%; }
</style>
