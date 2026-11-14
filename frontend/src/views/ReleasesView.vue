<script setup lang="ts">
import {get} from '@/utils/request'
import { onMounted, ref } from 'vue'
import api from '@/api/backend'
import { getSpaces } from '@/api/knowledgeSpaces'
import { stateLabel, spaceName, dateTime } from '@/utils/platformPresentation'

const releases = ref<any[]>([])
const mappings=ref<any[]>([])
const error=ref('')
const spaces=ref<any[]>([])
const mappingPage=ref(1),mappingTotal=ref(0)

async function load() {
  error.value=''
  try {
  const [data,sync] = await Promise.all([api.releases(),get('/api/kb/sync-mappings',{params:{page:mappingPage.value,page_size:20}})])
  releases.value = data.releases || []
  mappings.value=(sync.mappings || []).map((item:any)=>({...item,row_key:`${item.scope}:${item.source_id}:${item.target_mode}`}))
  mappingTotal.value=sync.total??mappings.value.length
  } catch(e:any) { error.value=e.message }
}
async function loadNames(){try{const result=await getSpaces();spaces.value=result.spaces||[]}catch{spaces.value=[]}}

async function activate(releaseId: string) {
  if (!window.confirm('重新提交该批次的资料，可能覆盖知识库中的同名文档。是否继续？')) return
  try { await api.activateRelease(releaseId); await load() } catch(e:any) { error.value=e.message }
}

onMounted(()=>{void load();void loadNames()})
</script>

<template>
  <t-card title="提交记录" :bordered="false">
    <t-alert v-if="error" theme="error" :message="error"/>
    <h3>文档处理状态</h3>
    <t-table row-key="row_key" :data="mappings" :columns="[{colKey:'scope',title:'知识库'},{colKey:'document',title:'文档'},{colKey:'target_mode',title:'处理目标'},{colKey:'review',title:'文档评审'},{colKey:'ingest',title:'文档入库'},{colKey:'derived',title:'生成状态'},{colKey:'error',title:'失败原因'}]">
      <template #scope="{row}">{{spaceName(row.scope,spaces)}}</template>
      <template #document="{row}"><span :title="row.source_id">{{row.official?.name || '名称未获取'}}</span></template>
      <template #target_mode="{row}">{{row.target_mode==='wiki'?'Wiki':'知识图谱'}}</template>
      <template #review="{row}">{{stateLabel(row.official?.lifecycle_state ?? row.official?.review_status,'review')}}</template>
      <template #ingest="{row}">{{stateLabel(row.official?.ingest_status,'ingest')}}</template>
      <template #derived="{row}">{{stateLabel(row.official?.[row.target_mode+'_status'],row.target_mode==='wiki'?'wiki':'graph')}}</template>
      <template #error="{row}">{{row.official_error || row.official?.ingest_error_message || row.official?.wiki_error_message || row.official?.graph_error_message || row.error || '—'}}</template>
    </t-table>
    <t-pagination :total="mappingTotal" :current="mappingPage" :page-size="20" :show-page-size="false" @current-change="(value:number)=>{mappingPage=value;load()}"/>
    <t-button variant="outline" @click="load">刷新状态</t-button>
    <h3>最近 50 个提交批次</h3>
    <t-table
      row-key="id" :data="releases"
      :columns="[
        { colKey: 'id', title: '批次编号', cell: 'id', width: 130 },
        { colKey: 'scope', title: '知识库' },
        { colKey: 'active', title: '状态', cell: 'active' },
        { colKey: 'created_at', title: '提交时间' },
        { colKey: 'operation', title: '操作', width: 200 },
      ]"
    >
      <template #id="{ row }">
        <span class="mono" :title="row.id">{{ row.id.slice(0, 8) }}</span>
      </template>
      <template #scope="{row}">{{spaceName(row.scope,spaces)}}</template>
      <template #created_at="{row}">{{dateTime(row.created_at)}}</template>
      <template #active="{ row }">
        <t-tag size="small" :theme="row.active ? 'success' : 'default'">{{ row.active ? '当前提交批次' : '历史批次' }}</t-tag>
      </template>
      <template #operation="{ row }">
        <t-space size="small">
          <t-button v-if="!row.active" size="small" variant="outline" @click="activate(row.id)">重新提交该批次</t-button>
          <t-button size="small" variant="text" @click="api.downloadFile(api.releaseDownloadUrl(row.id),row.id+'.zip')">下载资料包</t-button>
        </t-space>
      </template>
    </t-table>
    <t-empty v-if="!releases.length" description="暂无提交记录" />
  </t-card>
</template>

<style scoped>
.mono { font-family: ui-monospace, monospace; }
</style>
