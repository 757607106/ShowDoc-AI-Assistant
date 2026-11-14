<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/backend'

const health = ref<any>(null)

async function load() {
  health.value = await api.health()
}

onMounted(load)
</script>

<template>
  <t-card title="平台健康状态" :bordered="false">
    <t-descriptions v-if="health" :column="2" bordered>
      <t-descriptions-item label="ContextDB 连接">
        <t-tag :theme="health.contextdb ? 'success' : 'error'">{{ health.contextdb ? '正常' : '不可用' }}</t-tag>
      </t-descriptions-item>
      <t-descriptions-item label="治理 Worker">
        <t-tag :theme="health.worker ? 'success' : 'warning'">{{ health.worker ? '运行中' : '未启动' }}</t-tag>
      </t-descriptions-item>
      <t-descriptions-item label="数据诊断">
        <span class="hint">本地规则质检(空正文/转换失败/重复);语义评分、冲突检测、AI 重写由 ContextDB 知识评审完成</span>
      </t-descriptions-item>
      <t-descriptions-item label="Agent LLM">
        <span class="hint">百炼 BYOK(qwen-max);未配置 Key 时回退专属端点(qwen-plus)</span>
      </t-descriptions-item>
    </t-descriptions>
    <t-divider align="left">架构说明</t-divider>
    <ul class="arch-notes">
      <li>存储、检索、切片、知识图谱、Wiki、治理状态、Agent 上下文全部在 <b>ContextDB 云</b>(零本地数据库)</li>
      <li>Agent Harness:<b>deepagents</b>(LangChain 官方,MIT 免费工具循环);知识库访问走 ContextDB MCP 官方通道</li>
      <li>治理沿用 ContextDB 原生能力:知识评审准入(评分/冲突/重写/撤回)、入库后正文编辑重评审、CAS 乐观并发</li>
      <li>ctxdb CLI 仅作开发诊断,不参与平台运行时</li>
    </ul>
    <t-button variant="outline" @click="load">刷新状态</t-button>
  </t-card>
</template>

<style scoped>
.arch-notes { margin: 0 0 16px; padding-left: 18px; line-height: 1.9; }
.hint { font-size: 12px; opacity: .7; }
</style>
