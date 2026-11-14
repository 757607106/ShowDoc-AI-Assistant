<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listSandboxConfigs, type SandboxConfigRecord } from '@/api/system'
import { matchesResourceQuery } from '@/utils/resourceListSearch'

const records = ref<SandboxConfigRecord[]>([])
const loading = ref(false)
const error = ref('')
const query = ref('')
const archived = computed(() => records.value.filter(record => record.id !== 'state-backend' && matchesResourceQuery(record, query.value)))
async function load() {
  loading.value = true
  error.value = ''
  try { records.value = (await listSandboxConfigs()).data || [] }
  catch (failure) { error.value = failure instanceof Error ? failure.message : '无法读取历史配置。' }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="session-files-settings">
    <div class="section-header">
      <h2>会话文件</h2>
      <p class="section-description">Agent 使用官方 StateBackend。文件保存在当前会话的检查点中，重新打开会话后仍可查看。</p>
    </div>
    <t-alert theme="info" message="当前会话支持文件读取、写入与编辑，不执行 Shell、Docker 或浏览器。"
      description="技能以指令和文本文件加载；写入权限在智能体设置中配置。不会安装或执行技能脚本。" />
    <t-alert v-if="error" theme="error" :message="error">
      <template #operation><t-button variant="text" @click="load">重新加载</t-button></template>
    </t-alert>
    <t-loading v-if="loading" text="正在读取历史配置…" />
    <template v-else-if="records.some(record => record.id !== 'state-backend')">
      <h3>已停用的历史配置</h3>
      <p class="section-description">以下配置仅保留供查看，不用于新 Agent 会话。</p>
      <t-input v-model="query" clearable placeholder="搜索历史配置" />
      <article v-for="record in archived" :key="record.id" class="archive-card">
        <strong>{{ record.name }}</strong>
        <t-tag theme="default">已停用</t-tag>
        <p v-if="record.description">{{ record.description }}</p>
        <small>{{ record.sandbox_type }} · {{ record.id }}</small>
      </article>
    </template>
  </div>
</template>

<style scoped lang="less">
@import (reference) '@/components/css/settings-section.less';
.section-header { .settings-section-header(); }
.session-files-settings { display: flex; flex-direction: column; gap: 16px; }
.archive-card { padding: 16px; border: 1px solid var(--td-component-stroke); border-radius: var(--app-radius-md); }
.archive-card strong { margin-right: 12px; }
.archive-card small, .archive-card p { color: var(--td-text-color-secondary); }
</style>
