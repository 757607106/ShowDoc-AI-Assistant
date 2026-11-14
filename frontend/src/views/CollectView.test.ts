import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, effectScope, nextTick, ref, watch } from 'vue'
import ts from 'typescript'

const source = readFileSync(new URL('./CollectView.vue', import.meta.url), 'utf8')
const script = source.split('<script setup lang="ts">')[1].split('</script>')[0].replace(/^import .*$/gm, '')
const code = ts.transpileModule(script + '\nreturn {spaceScope,mode,files,url,entryKey,error,taskId,launch,selectFiles}', {
  compilerOptions: {target:ts.ScriptTarget.ES2022, module:ts.ModuleKind.None},
}).outputText
const flush = async () => { await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick() }
function fixture(failUpload = false) {
  const calls: any[] = [], scope = effectScope()
  const api = {
    entries: async () => ({entries:[{key:'web'},{key:'file'}]}),
    startTask: async (entry:string, payload:any) => { calls.push({entry,payload}); return {task_id:'crawl-1'} },
    uploadFiles: async (files:File[], space:string) => { calls.push({files,space}); if(failUpload) throw new Error('upload unavailable'); return {task_id:'file-1'} },
  }
  const state = scope.run(() => new Function('ref','computed','watch','useRoute','useRouter','useAuthStore','api','getSpaces', code)(
    ref,computed,watch,()=>({query:{space:'a'},fullPath:'/collect?space=a'}),()=>({push(){}}),()=>({hasRole:()=>true}),api,
    async()=>({spaces:[{scope:'a',name:'A',graph_enabled:false},{scope:'b',name:'B',graph_enabled:true}]}),
  ))
  return {state,calls,dispose:()=>scope.stop()}
}
test('crawler and file input both use the chosen space',async t=>{
  const f=fixture(); t.after(f.dispose); await flush()
  f.state.url.value='https://example.test';await flush()
  await f.state.launch()
  assert.equal(f.calls[0].payload.space_scope,'a')
  f.state.selectFiles([new File(['source'],'source.md')])
  await f.state.launch()
  assert.equal(f.calls[1].space,'a'); assert.equal(f.calls[1].files[0].name,'source.md')
  assert.equal(f.state.taskId.value,'file-1'); assert.equal(f.state.files.value.length,0)
})
test('failed upload preserves selected files and does not announce a submitted task',async t=>{
  const f=fixture(true); t.after(f.dispose); await flush()
  f.state.selectFiles([new File(['source'],'source.md')]); await f.state.launch()
  assert.equal(f.state.error.value,'upload unavailable')
  assert.equal(f.state.taskId.value,''); assert.equal(f.state.files.value.length,1)
})
test('invalid website addresses or missing space cannot enqueue work',async t=>{
  const f=fixture(); t.after(f.dispose); await flush()
  f.state.url.value='invalid'; await f.state.launch()
  assert.match(f.state.error.value,/网站地址/); assert.equal(f.calls.length,0)
  f.state.spaceScope.value='missing'; await f.state.launch(); assert.equal(f.calls.length,0)
})
