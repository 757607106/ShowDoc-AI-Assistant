<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { MessagePlugin } from 'tdesign-vue-next'
import ResourceIcon from '@/components/icons/ResourceIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import KbTypeAvatar from './components/KbTypeAvatar.vue'
import { createSpace, getSpaces, type KnowledgeSpace, spaceTargetStatus, spaceTargetNotice } from '@/api/knowledgeSpaces'
import { spaceName } from '@/utils/platformPresentation'

const router = useRouter(), auth = useAuthStore()
const spaces = ref<KnowledgeSpace[]>([]), availableBases = ref<any[]>([])
const loading = ref(false), error = ref(''), query = ref(''), dialog = ref(false), saving = ref(false)
const linking = ref(false)
const name = ref(''), wikiId = ref(''), graphId = ref(''), graphEnabled = ref(false)
const filtered = computed(() => spaces.value.filter(space => `${spaceName(space.scope,spaces.value)} ${space.scope}`.toLowerCase().includes(query.value.trim().toLowerCase())))
const wikiBases = computed(() => availableBases.value.filter(base => base.wiki_enabled))
const graphBases = computed(() => availableBases.value.filter(base => base.graph_enabled && !base.wiki_enabled))
async function load() {
  loading.value = true; error.value = ''
  try { const result = await getSpaces(); spaces.value = result.spaces; availableBases.value = result.available_bases || [] }
  catch (e: any) { error.value = e.message }
  finally { loading.value = false }
}
function openCreate(base?: any) {
  name.value = base?.name || ''; wikiId.value = base?.wiki_enabled ? base.id : ''
  graphId.value = ''; graphEnabled.value = false; linking.value = false; dialog.value = true
}
async function save() {
  if (saving.value) return
  if (!name.value.trim()) { MessagePlugin.warning('请输入知识库名称'); return }
  saving.value = true
  try {
    const result = await createSpace({ name: name.value.trim(), graph_enabled: graphEnabled.value,
      ...(wikiId.value ? { wiki_kb_id: wikiId.value } : {}), ...(graphEnabled.value && graphId.value ? { graph_kb_id: graphId.value } : {}) })
    dialog.value = false
    await router.push(`/platform/knowledge-spaces/${encodeURIComponent(result.space.scope)}`)
  } catch (e: any) { MessagePlugin.error(e.message) }
  finally { saving.value = false }
}
const open = (space: KnowledgeSpace) => router.push(`/platform/knowledge-spaces/${encodeURIComponent(space.scope)}`)
function refreshAvailability(){if(document.visibilityState!=='hidden'&&!loading.value)void load()}
onMounted(()=>{void load();window.addEventListener('focus',refreshAvailability);document.addEventListener('visibilitychange',refreshAvailability)})
onUnmounted(()=>{window.removeEventListener('focus',refreshAvailability);document.removeEventListener('visibilitychange',refreshAvailability)})
</script>

<template>
  <div class="kb-list-container"><div class="kb-list-content">
    <header class="header">
      <div class="header-title"><h2><ResourceIcon type="knowledge" :size="24" />知识库</h2></div>
      <t-space><t-button variant="text" :loading="loading" @click="load">刷新</t-button><t-button variant="outline" @click="linking=true">关联已有库</t-button><t-button v-if="auth.hasRole('contributor')" @click="openCreate()"><template #icon><t-icon name="folder-add" /></template>新建知识库</t-button></t-space>
    </header>
    <t-input v-model="query" class="space-search" clearable placeholder="搜索知识库"><template #prefix-icon><t-icon name="search" /></template></t-input>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-loading :loading="loading" class="kb-list-main">
      <div class="kb-card-wrap">
        <div v-for="space in filtered" :key="space.scope" class="kb-card" role="link" tabindex="0" @click="open(space)" @keydown.enter.self.prevent="open(space)" @keydown.space.self.prevent="open(space)">
          <div class="card-header"><KbTypeAvatar type="document" /><span class="card-title">{{ spaceName(space.scope,spaces) }}</span></div>
          <div class="card-content"><t-space break-line><t-tag :theme="spaceTargetStatus(space,'wiki')==='missing'?'warning':'primary'" variant="light">{{spaceTargetStatus(space,'wiki')==='missing'?'Wiki 库不存在':'Wiki'}}</t-tag><t-tag v-if="space.graph_enabled" :theme="spaceTargetStatus(space,'graph')==='missing'?'warning':'success'" variant="light">{{spaceTargetStatus(space,'graph')==='missing'?'图谱库不存在':'知识图谱'}}</t-tag></t-space></div>
          <div class="card-bottom"><span>{{ spaceTargetStatus(space,'wiki')==='available' ? '查看资料与 Wiki' : spaceTargetNotice(space,'wiki') }}</span><t-icon name="chevron-right" /></div>
        </div>
      </div>
      <EmptyState v-if="!loading && !filtered.length" :icon="query ? 'search' : 'folder'" :title="query ? '没有匹配的知识库' : '暂无知识库'"><t-button v-if="!query && auth.hasRole('contributor')" @click="openCreate()">新建知识库</t-button></EmptyState>
    </t-loading>
    <t-dialog v-model:visible="linking" header="关联已有库" width="760px" :footer="false">
      <p class="hint">可将已有 Wiki 库关联为业务知识库。其他模式的库可直接查看资料，已有内容与引用保持可用。</p>
      <t-loading :loading="loading">
        <t-table row-key="id" :data="availableBases" :columns="[{colKey:'name',title:'名称'},{colKey:'mode',title:'类型'},{colKey:'actions',title:'操作',width:240}]">
          <template #mode="{row}">{{row.wiki_enabled ? 'Wiki' : row.graph_enabled ? '知识图谱' : '文档检索'}}</template>
          <template #actions="{row}"><t-space><t-button variant="text" @click="router.push(`/platform/knowledge-bases/${row.id}`)">查看资料</t-button><t-button v-if="row.wiki_enabled && auth.hasRole('contributor')" variant="text" @click="openCreate(row)">关联为知识库</t-button></t-space></template>
        </t-table>
      </t-loading>
    </t-dialog>
    <t-dialog v-model:visible="dialog" header="新建知识库" :confirm-btn="{content:'创建',loading:saving}" :close-on-overlay-click="!saving" @confirm="save">
      <t-form label-align="top">
        <t-form-item label="知识库名称"><t-input v-model="name" :maxlength="100" placeholder="例如：产品交付知识" /></t-form-item>
        <t-form-item label="Wiki 主库"><t-select v-model="wikiId" clearable placeholder="首次提交资料时创建，也可关联已有 Wiki 库" :options="wikiBases.map(base=>({label:base.name,value:base.id}))" /></t-form-item>
        <t-form-item label="启用知识图谱" help="启用后，同一资料分别投递到 Wiki 库和图谱库，产生两份入库和独立评审状态；Wiki 修订不会自动同步到图谱。"><t-switch v-model="graphEnabled" /></t-form-item>
        <t-form-item v-if="graphEnabled" label="关联已有图谱库"><t-select v-model="graphId" clearable placeholder="首次提交资料时创建" :options="graphBases.map(base=>({label:base.name,value:base.id}))" /></t-form-item>
      </t-form>
    </t-dialog>
  </div></div>
</template>

<style scoped lang="less">
@import (reference) '@/components/css/resource-card.less';
.kb-list-container{height:100%;display:flex;min-height:0;min-width:0}.kb-list-content{.resource-list-content()}.kb-list-main{.resource-list-main();display:block}.kb-card-wrap{.resource-card-grid()}.kb-card{.resource-card();.resource-card-footer()}.header{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:20px}.header-title h2{display:flex;align-items:center;gap:10px;font-size:var(--app-text-3xl);margin:0}.header-title p,.hint,.existing-bases p,.card-description{color:var(--td-text-color-secondary);line-height:1.6}.space-search{max-width:360px;margin-bottom:24px}.card-header{display:flex;align-items:center;gap:10px}.card-title{font-weight:600;overflow-wrap:anywhere}.card-content{margin:16px 0}.card-description{overflow-wrap:anywhere;margin:0 0 12px}.card-bottom{display:flex;justify-content:space-between;color:var(--td-text-color-secondary);font-size:var(--app-text-sm)}.existing-bases{margin-top:32px}.switch-description{margin-left:10px}.hint{font-size:var(--app-text-md)}@media(max-width:700px){.header{align-items:flex-start;flex-direction:column}}
</style>
