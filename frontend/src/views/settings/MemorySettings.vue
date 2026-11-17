<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listAgents, type CustomAgent } from '@/api/agent'
import { get, put } from '@/utils/request'
import { MessagePlugin } from 'tdesign-vue-next'

interface MemoryPolicy { enabled?: boolean; effective: boolean; storage_mode?: string }
interface MemoryFile { content: string; file_path: string; effective: boolean; modified_at?: string|null }
const emit=defineEmits<{(event:'dirty',value:boolean):void}>()
const auth=useAuthStore()
const agents=ref<CustomAgent[]>([]),selectedAgentId=ref(''),policy=ref<MemoryPolicy|null>(null)
const file=ref<MemoryFile|null>(null),content=ref(''),savedContent=ref(''),error=ref('')
const loading=ref(false),fileLoading=ref(false),saving=ref(false),policySaving=ref(false)
const enabled=computed(()=>policy.value?.enabled??policy.value?.effective??false)
const canEdit=computed(()=>auth.hasRole('contributor'))
const agentMemoryDisabled=computed(()=>agents.value.find(agent=>agent.id===selectedAgentId.value)?.config?.memory_enabled===false)
const dirty=computed(()=>file.value!==null&&content.value!==savedContent.value)
let identityGeneration=0,fileGeneration=0
const isCurrent=(identity:number,request:number,id:string)=>identity===identityGeneration&&request===fileGeneration&&id===selectedAgentId.value

async function loadFile(){
  const identity=identityGeneration,request=++fileGeneration,id=selectedAgentId.value
  file.value=null;content.value='';savedContent.value='';fileLoading.value=!!id;error.value=''
  if(!id)return
  try{
    const res=await get<{data:MemoryFile}>(`/api/v1/agents/${encodeURIComponent(id)}/memory-file`)
    if(!isCurrent(identity,request,id))return
    file.value=res.data;content.value=res.data.content;savedContent.value=res.data.content
  }catch(e:any){if(isCurrent(identity,request,id))error.value=e.message||'无法读取记忆文件'}
  finally{if(isCurrent(identity,request,id))fileLoading.value=false}
}
async function load(){
  const identity=++identityGeneration
  fileGeneration++;file.value=null;content.value='';savedContent.value='';selectedAgentId.value=''
  agents.value=[];policy.value=null;error.value='';loading.value=true;fileLoading.value=false;saving.value=false;policySaving.value=false
  try{
    const [settings,result]=await Promise.all([get<{data:MemoryPolicy}>('/api/v1/memory/settings'),listAgents()])
    if(identity!==identityGeneration)return
    policy.value=settings.data;agents.value=result.data||[];selectedAgentId.value=agents.value[0]?.id||''
    await loadFile()
  }catch(e:any){if(identity===identityGeneration)error.value=e.message||'无法读取文件记忆设置'}
  finally{if(identity===identityGeneration)loading.value=false}
}
async function setEnabled(value:boolean){
  if(!policy.value||policySaving.value)return
  const identity=identityGeneration
  policySaving.value=true;error.value=''
  try{
    const res=await put<{data:MemoryPolicy}>('/api/v1/memory/settings',{enabled:value})
    if(identity!==identityGeneration)return
    policy.value=res.data
  }catch(e:any){if(identity===identityGeneration)error.value=e.message||'记忆开关保存失败'}
  finally{if(identity===identityGeneration)policySaving.value=false}
}
async function save(){
  if(!canEdit.value||!file.value||!dirty.value||saving.value)return
  const identity=identityGeneration,request=fileGeneration,id=selectedAgentId.value,submitted=content.value
  saving.value=true;error.value=''
  try{
    const res=await put<{data:MemoryFile}>(`/api/v1/agents/${encodeURIComponent(id)}/memory-file`,{content:submitted})
    if(!isCurrent(identity,request,id))return
    file.value=res.data;savedContent.value=res.data.content
    if(content.value===submitted)content.value=res.data.content
    MessagePlugin.success('记忆文件已保存，新会话会读取更新')
  }catch(e:any){if(isCurrent(identity,request,id))error.value=e.message||'记忆文件保存失败'}
  finally{if(isCurrent(identity,request,id))saving.value=false}
}
function selectAgent(id:string){
  if(dirty.value||saving.value||id===selectedAgentId.value)return
  selectedAgentId.value=id;void loadFile()
}
function discard(){if(!saving.value)content.value=savedContent.value}
watch(dirty,value=>emit('dirty',value),{immediate:true})
watch(()=>auth.user?.id,()=>{void load()},{immediate:true})
onUnmounted(()=>{identityGeneration++;fileGeneration++;emit('dirty',false)})
</script>

<template>
  <div class="memory-settings">
    <h2>文件记忆</h2>
    <p>每个 Agent 使用自己的 AGENTS.md，记忆按当前账号与 Agent 隔离，跨会话保存。</p>
    <t-alert v-if="error" theme="error" :message="error"/>
    <div class="setting-row"><label>启用我的文件记忆</label><t-switch :value="enabled" :loading="policySaving" :disabled="loading||!policy" @change="setEnabled"/></div>
    <p>关闭不会删除已有文件。新会话读取文件更新，正在进行的会话沿用原生记忆缓存。</p>
    <t-button v-if="!policy" variant="outline" :loading="loading" @click="load">重新加载</t-button>
    <template v-else>
      <label for="memory-agent">Agent</label>
      <t-select id="memory-agent" :value="selectedAgentId" :options="agents.map(agent=>({value:agent.id,label:agent.name}))" :disabled="loading||fileLoading||saving||dirty" @change="selectAgent"/>
      <p v-if="!loading&&!agents.length">当前没有可用的 Agent。</p>
      <template v-if="selectedAgentId">
        <p v-if="file" class="memory-path">{{file.file_path}}</p>
        <t-alert v-if="file&&agentMemoryDisabled&&enabled" theme="info" message="当前 Agent 未启用文件记忆；可在智能体配置中修改。"/>
        <t-alert v-if="!canEdit" theme="info" message="当前账号只能查看记忆文件。"/>
        <t-textarea v-model="content" :disabled="!canEdit||loading||fileLoading||!file||saving" :maxlength="100000" :autosize="{minRows:12,maxRows:24}" placeholder="记录希望 Agent 在后续会话中遵循的事实、偏好和工作约定"/>
        <t-space>
          <t-button v-if="canEdit" :disabled="!file||!dirty||fileLoading" :loading="saving" @click="save">保存文件</t-button>
          <t-button v-if="dirty" variant="outline" :disabled="saving" @click="discard">放弃修改</t-button>
          <t-button v-if="!file" variant="outline" :loading="fileLoading" :disabled="loading" @click="loadFile">重新读取文件</t-button>
        </t-space>
      </template>
    </template>
  </div>
</template>

<style scoped>.memory-settings{display:flex;flex-direction:column;gap:16px}h2,p{margin:0}.setting-row{display:flex;align-items:center;justify-content:space-between}.memory-path{font-family:var(--app-font-mono);overflow-wrap:anywhere}</style>
