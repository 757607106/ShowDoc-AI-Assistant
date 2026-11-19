<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { MessagePlugin } from 'tdesign-vue-next'
import ResourceIcon from '@/components/icons/ResourceIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import KbTypeAvatar from './components/KbTypeAvatar.vue'
import KnowledgeActionMenu from './components/KnowledgeActionMenu.vue'
import ContextDBBaseEditor from './ContextDBBaseEditor.vue'
import { deleteBase, getBasePermissions, knowledgeAccess, knowledgeModeLabel, listBases, updateBase, type ContextDBBase, type BasePermissionProfile } from '@/api/contextdb'
import { dateTime } from '@/utils/platformPresentation'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const bases = ref<ContextDBBase[]>([]), profile = ref<BasePermissionProfile | null>(null)
const loading = ref(false), error = ref(''), permissionError = ref(''), page = ref(1)
const editor = ref(false), renaming = ref<ContextDBBase | null>(null), name = ref(''), deleting = ref<ContextDBBase | null>(null), saving = ref(false), actionError = ref('')
const pageSize = 12
const defaultOrder = 'updated_desc'
const orderOptions = [
  { value: defaultOrder, label: '最近更新' },
  { value: 'created_desc', label: '最近创建' },
  { value: 'name', label: '名称' },
]
const query = computed({
  get: () => typeof route.query.q === 'string' ? route.query.q : '',
  set: (value: string) => { void router.replace({ query: { ...route.query, q: value || undefined } }) },
})
const order = computed({
  get: () => orderOptions.find(option => option.value === route.query.sort)?.value ?? defaultOrder,
  set: (value: string) => { void router.replace({ query: { ...route.query, sort: value === defaultOrder ? undefined : value } }) },
})
const canCreate = computed(() => auth.hasRole('contributor') && !!profile.value && (!profile.value.evaluation_state || profile.value.evaluation_state === 'active') && (!profile.value.member?.status || profile.value.member.status === 'active') && (profile.value.mode === 'personal_compatibility' || ['owner', 'admin'].includes(profile.value.member?.role || '')))
const access = (base: ContextDBBase) => knowledgeAccess(base, profile.value, auth.hasRole('contributor'))
function permissionLabel(base: ContextDBBase) {
  if (!profile.value) return '权限待确认'
  const rights=access(base)
  if(rights.manage)return '可管理'
  if(rights.write)return '可写'
  return profile.value.knowledge_base_permissions?.find(item=>item.knowledge_base_id===base.id)?.current_permission==='none'?'无权限':'只读'
}
const filtered = computed(() => {
  const items = bases.value.filter(base => `${base.name} ${base.description || ''}`.toLowerCase().includes(query.value.trim().toLowerCase()))
  return items.sort((a, b) => order.value === 'name' ? a.name.localeCompare(b.name, 'zh-CN') : String(b[order.value === 'created_desc' ? 'created_at' : 'updated_at'] || '').localeCompare(String(a[order.value === 'created_desc' ? 'created_at' : 'updated_at'] || '')))
})
const visibleBases = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const hasMultiplePages = computed(() => filtered.value.length > pageSize)
watch([query, order], () => { page.value = 1 })
let requestId = 0
async function load() {
  const request = ++requestId
  loading.value = true; error.value = ''; permissionError.value = ''; profile.value = null
  const [libraries, permissions] = await Promise.allSettled([listBases(), getBasePermissions()])
  if (request !== requestId) return
  if (libraries.status === 'fulfilled') {
    bases.value = libraries.value.data
    page.value = Math.min(page.value, Math.max(1, Math.ceil(filtered.value.length / pageSize)))
  } else error.value = libraries.reason.message || '知识库读取失败'
  if (permissions.status === 'fulfilled') profile.value = permissions.value
  else permissionError.value = '暂时无法核对官方权限，写入操作已停用。请刷新重试。'
  loading.value = false
}
function baseLocation(id: string, tab?: string) {
  return {
    path: `/platform/knowledge-bases/${encodeURIComponent(id)}`,
    query: { q: query.value || undefined, sort: order.value === defaultOrder ? undefined : order.value, tab },
  }
}
async function saved(id: string) { editor.value = false; await load(); await router.push(baseLocation(id)) }
function menu(base: ContextDBBase) {
  return [...(base.wiki_enabled ? [{ content: '知识 Wiki', value: 'wiki' }] : []),
    ...(access(base).manage ? [{ content: '重命名', value: 'rename' }] : []), ...(access(base).delete ? [{ content: '删除', value: 'delete', theme: 'error' as const }] : [])]
}
function act(base: ContextDBBase, action: string) {
  if (action === 'wiki' && base.wiki_enabled) return router.push(baseLocation(base.id, 'wiki'))
  if (!access(base).manage) return
  actionError.value = ''
  if (action === 'rename') { renaming.value = base; name.value = base.name }
  if (action === 'delete' && access(base).delete) deleting.value = base
}
async function rename() {
  if (saving.value || !renaming.value || !access(renaming.value).manage) return
  if (!name.value.trim()) { actionError.value = '请输入知识库名称'; return }
  saving.value = true; actionError.value = ''
  try { await updateBase(renaming.value.id, { name: name.value.trim() }); renaming.value = null; await load(); MessagePlugin.success('名称已更新') }
  catch (e: any) { actionError.value = e.message }
  finally { saving.value = false }
}
async function remove() {
  if (saving.value || !deleting.value || !access(deleting.value).delete) return
  saving.value = true; actionError.value = ''
  try { await deleteBase(deleting.value.id); deleting.value = null; await load(); MessagePlugin.success('删除请求已完成') }
  catch (e: any) { actionError.value = `${e.message}。若库非空或仍有处理任务，请先在文档中核对并处理后再重试。` }
  finally { saving.value = false }
}
function refreshAvailability() { if (document.visibilityState !== 'hidden' && !loading.value) void load() }
onMounted(() => { void load(); window.addEventListener('focus', refreshAvailability); document.addEventListener('visibilitychange', refreshAvailability) })
onUnmounted(() => { requestId++; window.removeEventListener('focus', refreshAvailability); document.removeEventListener('visibilitychange', refreshAvailability) })
</script>

<template>
  <div class="kb-list-container"><div class="kb-list-content">
    <header class="header"><div class="header-title"><h2><ResourceIcon type="knowledge" :size="24" />知识库</h2></div><t-space><t-button variant="outline" :loading="loading" @click="load"><template #icon><t-icon name="refresh" /></template>刷新</t-button><t-button v-if="canCreate" @click="editor=true"><template #icon><t-icon name="folder-add" /></template>新建知识库</t-button></t-space></header>
    <div class="list-toolbar">
      <t-input class="kb-search" v-model="query" clearable placeholder="搜索知识库名称或说明"><template #prefix-icon><t-icon name="search" /></template></t-input>
      <t-select class="kb-order" v-model="order" aria-label="知识库排序" :options="orderOptions" />
      <span class="kb-result-count" role="status">{{ error || (loading && !bases.length) ? '' : `共 ${filtered.length} 个知识库` }}</span>
    </div>
    <t-alert v-if="error" theme="error" :message="error" /><t-alert v-if="permissionError" theme="warning" :message="permissionError" />
    <t-loading :loading="loading" class="kb-list-main">
      <div class="kb-card-wrap"><div v-for="base in visibleBases" :key="base.id" class="kb-card">
        <div class="card-header">
          <KbTypeAvatar type="document" />
          <router-link class="card-title" :to="baseLocation(base.id)">{{ base.name }}</router-link>
          <KnowledgeActionMenu v-if="menu(base).length" class="card-actions" :label="base.name + '的操作'"
            :options="menu(base)" icon-only @select="act(base, $event)" />
        </div>
        <p class="card-description" :class="{ 'is-empty': !base.description }">{{base.description || '暂无说明'}}</p><t-space break-line><t-tag variant="light">{{knowledgeModeLabel(base)}}</t-tag><t-tag :theme="base.review_enabled?'success':'default'" variant="light">{{base.review_enabled?'评审已开启':'评审已关闭'}}</t-tag><t-tag variant="outline">{{permissionLabel(base)}}</t-tag></t-space>
        <div class="card-bottom"><span>{{base.document_count ?? 0}} 份文档</span><span>{{dateTime(base.updated_at || base.created_at)}}</span></div>
      </div></div>
      <EmptyState v-if="!loading&&!error&&!filtered.length" :icon="query?'search':'folder'" :title="query?'没有匹配的知识库':'暂无知识库'"><t-button v-if="!query&&canCreate" @click="editor=true">新建知识库</t-button></EmptyState>
    </t-loading>
    <t-pagination v-if="hasMultiplePages" :current="page" :total="filtered.length" :page-size="pageSize" :total-content="false" :show-page-size="false" @current-change="(value: number)=>page=value" />
    <ContextDBBaseEditor :visible="editor" mode="create" @update:visible="editor=$event" @success="saved" />
    <t-dialog :visible="!!renaming" header="重命名知识库" :confirm-btn="{content:'保存',loading:saving}" :close-on-overlay-click="!saving" @update:visible="(value: boolean)=>{if(!value&&!saving)renaming=null}" @confirm="rename"><t-input v-model="name" :maxlength="255" @enter="rename" /><t-alert v-if="actionError" theme="error" :message="actionError" /></t-dialog>
    <t-dialog :visible="!!deleting" header="删除知识库" :confirm-btn="{content:'删除',theme:'danger',loading:saving}" :close-on-overlay-click="!saving" @update:visible="(value: boolean)=>{if(!value&&!saving)deleting=null}" @confirm="remove"><p>确认删除“{{deleting?.name}}”？此操作不可恢复。非空或正在处理的知识库可能被官方服务拒绝，请先核对文档与任务。</p><t-alert v-if="actionError" theme="error" :message="actionError" /></t-dialog>
  </div></div>
</template>

<style scoped lang="less">
@import (reference) '@/components/css/resource-card.less';
.kb-list-container{font-family:var(--app-font-family);font-size:var(--app-text-base);height:100%;display:flex;min-height:0;min-width:0}.kb-list-content{.resource-list-content()}.kb-list-main{.resource-list-main();display:block}.kb-card-wrap{.resource-card-grid()}.kb-card{.resource-card();.resource-card-footer()}.header,.list-toolbar,.card-header,.card-bottom{display:flex;align-items:center;gap:12px}.header{justify-content:space-between;margin-bottom:20px}.header-title h2{display:flex;align-items:center;gap:10px;margin:0;font-size:var(--app-text-4xl);font-weight:600}.list-toolbar{margin-bottom:20px}.list-toolbar>.kb-search{width:440px;max-width:100%;flex:0 1 440px}.list-toolbar>.kb-order{width:160px;flex:none}.card-title{overflow-wrap:anywhere;flex:1}.card-description{color:var(--td-text-color-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-height:24px}.kb-card .card-description{font-size:var(--app-text-md);line-height:20px}.kb-card .card-description.is-empty{font-size:var(--app-text-sm)}.card-bottom{justify-content:space-between;color:var(--td-text-color-secondary);font-size:var(--app-text-sm);margin-top:20px}.t-alert{margin-bottom:16px}@media(max-width:700px){.list-toolbar{flex-wrap:wrap}.header{flex-wrap:wrap;align-items:center;gap:12px}}
.kb-result-count { color: var(--td-text-color-secondary); font-size: var(--app-text-sm); white-space: nowrap; }
.card-title { text-decoration: none; }
.card-title::after { content: ''; position: absolute; inset: 0; border-radius: var(--app-radius-md); }
.card-title:focus-visible { outline: none; }
.card-title:focus-visible::after { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
.card-actions { position: relative; z-index: 1; margin-left: auto; }
</style>
