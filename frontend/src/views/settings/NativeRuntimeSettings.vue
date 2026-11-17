<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { get, post } from '@/utils/request'

interface RuntimeRecord { id: string; name: string; enabled?: boolean; capabilities?: Record<string, boolean> }
interface ConnectionCheck { ok: boolean; checks: Array<{ name: string; ok: boolean; message?: string }> }
const auth=useAuthStore()
const records=ref<RuntimeRecord[]>([]),loading=ref(false),checking=ref(false),error=ref('')
const connection=ref<ConnectionCheck|null>(null)
const sandbox=computed(()=>records.value.find(item=>item.id==='opensandbox-local'))
let generation=0

async function load(){
  const request=++generation
  records.value=[];connection.value=null;error.value='';loading.value=true;checking.value=false
  try{
    const res=await get<{data:RuntimeRecord[]}>('/api/v1/sandbox-configs')
    if(request===generation)records.value=res.data||[]
  }catch(e:any){if(request===generation)error.value=e.message||'无法读取运行环境'}
  finally{if(request===generation)loading.value=false}
}
async function checkConnection(){
  if(checking.value||!auth.hasRole('admin')||!sandbox.value?.enabled)return
  const request=generation
  checking.value=true;error.value='';connection.value=null
  try{
    const res=await post<{data:ConnectionCheck}>('/api/v1/system/sandbox-check',{config_id:'opensandbox-local'})
    if(request===generation)connection.value=res.data
  }catch(e:any){if(request===generation)error.value=e.message||'连接检查失败'}
  finally{if(request===generation)checking.value=false}
}
watch(()=>auth.user?.id,()=>{checking.value=false;void load()},{immediate:true})
onUnmounted(()=>{generation++})
</script>

<template>
  <div class="runtime-settings">
    <h2>运行环境</h2>
    <p>Agent 的文件和命令由实际运行后端提供。部署配置由服务器管理。</p>
    <t-alert v-if="error" theme="error" :message="error"/>
    <t-button variant="outline" :loading="loading" :disabled="checking" @click="load">刷新状态</t-button>
    <t-card title="会话文件（无 Shell）" :bordered="true">
      <p>文件保存在当前会话的原生状态中，可读写、搜索和下载；不执行命令。</p>
      <p>会话恢复使用 checkpoint，跨会话记忆使用单独的 AGENTS.md 文件。</p>
    </t-card>
    <t-card v-if="sandbox" title="OpenSandbox" :bordered="true">
      <t-tag :theme="sandbox.enabled?'success':'default'">{{sandbox.enabled?'已配置':'未配置'}}</t-tag>
      <p>独立沙箱提供命令执行和真实文件环境。已配置不代表连接或执行测试通过。</p>
      <t-button v-if="auth.hasRole('admin')" variant="outline" :loading="checking" :disabled="loading||!sandbox.enabled" @click="checkConnection">检查连接</t-button>
      <template v-if="connection"><t-alert :theme="connection.ok?'success':'error'" :message="connection.ok?'控制服务连接正常':'控制服务连接失败'"/>
        <p v-for="item in connection.checks" :key="item.name">{{item.name}}：{{item.ok?'通过':item.message||'未通过'}}</p>
      </template>
    </t-card>
    <t-alert v-if="!error&&!loading&&!sandbox" theme="info" message="未提供沙箱配置，Agent 仍可使用会话文件。"/>
    <t-alert theme="info" message="停止对话、停止远端命令与销毁环境是不同操作；分支或回退不会撤销沙箱文件及外部工具的副作用。"/>
  </div>
</template>

<style scoped>.runtime-settings{display:flex;flex-direction:column;gap:16px}h2,p{margin:0}.t-card p+p{margin-top:8px}</style>
