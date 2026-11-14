<!--
  治理语料:本地清洗产物的当前版本与历史版本浏览;语义评审在「知识库 → 知识评审」由 ContextDB 完成
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/backend'
import DocMarkdown from '@/components/DocMarkdown.vue'
import { getSpaces } from '@/api/knowledgeSpaces'
import { spaceName, dateTime } from '@/utils/platformPresentation'

const documents = ref<any[]>([])
const activeVersion = ref('')
const detail = ref<any>(null)
const detailLoading = ref(false)
const spaces = ref<any[]>([])

async function load() {
  const data = await api.documents()
  documents.value = data.documents || []
}

async function open(versionId: string) {
  detailLoading.value = true
  activeVersion.value = versionId
  try {
    const data = await api.documentDetail(versionId)
    detail.value = data.document
  } finally {
    detailLoading.value = false
  }
}

onMounted(()=>{void load();void getSpaces().then(result=>spaces.value=result.spaces||[]).catch(()=>{})})
</script>

<template>
  <div class="review-layout">
    <t-card title="来源资料" :bordered="false" class="review-list">
      <t-table
        row-key="version_id" :data="documents"
        :columns="[
          { colKey: 'title', title: '文档', ellipsis: true },
          { colKey: 'category', title: '分类', ellipsis: true },
          { colKey: 'source_format', title: '格式', width: 80 },
        ]" @row-click="(ctx: any) => open(ctx.row.version_id)"
      />
      <t-empty v-if="!documents.length" description="暂无来源资料" />
    </t-card>

    <t-card v-if="detail" :title="detail.title" :bordered="false" class="review-detail" v-loading="detailLoading">
      <template #actions>
        <t-button size="small" variant="text" @click="api.downloadFile(api.documentSourceUrl(activeVersion), activeVersion+'.source')">下载原件</t-button>
      </template>
      <t-descriptions :column="3" bordered size="small">
        <t-descriptions-item label="版本标识">{{ detail.version_id?.slice(0, 10) }}</t-descriptions-item>
        <t-descriptions-item label="当前版本">{{ detail.is_current ? '是' : '否' }}</t-descriptions-item>
        <t-descriptions-item label="知识库">{{ spaceName(detail.scope,spaces) }}</t-descriptions-item>
      </t-descriptions>
      <t-divider align="left">历史版本({{ detail.versions?.length || 0 }})</t-divider>
      <t-space break-line size="small">
        <t-tag
          v-for="version in detail.versions || []" :key="version.version_id"
          :theme="version.version_id === activeVersion ? 'primary' : 'default'" class="version-tag"
          @click="open(version.version_id)"
        >
          {{ version.version_id?.slice(0, 8) }} · {{ dateTime(version.created_at) }}
        </t-tag>
      </t-space>
      <t-divider align="left">正文</t-divider>
      <DocMarkdown :key="activeVersion" :content="detail.content || ''" />
    </t-card>
  </div>
</template>

<style scoped>
.review-layout { display: flex; gap: 16px; height: 100%; }
.review-list { width: 40%; flex: none; overflow: auto; }
.review-detail { flex: 1; overflow: auto; }
.version-tag { cursor: pointer; }
</style>
