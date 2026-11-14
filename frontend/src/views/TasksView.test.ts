import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { ref } from 'vue'
import ts from 'typescript'
import { stateLabel } from '../utils/platformPresentation.ts'

const source=readFileSync(new URL('./TasksView.vue',import.meta.url),'utf8')
const script=source.slice(source.indexOf('let detailRequest ='),source.indexOf('async function load()'))
const code=ts.transpileModule(script+'\nreturn {openDetails,closeDetails,duration}',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
function fixture(read:(id:string)=>Promise<any>){
  const detailId=ref(''),detail=ref<any>(null),detailLoading=ref(false),detailError=ref('')
  const actions=new Function('api','detailId','detail','detailLoading','detailError',code)({taskStatus:read},detailId,detail,detailLoading,detailError)
  return {...actions,detailId,detail,detailLoading,detailError}
}
test('changing or closing task details ignores a delayed earlier response',async()=>{
  let resolve!:(value:any)=>void
  const f=fixture(async id=>id==='slow'?new Promise(yes=>resolve=yes):{task_id:id,failure_details:[{title:'视频来源',error:'源正文为空'}]})
  const pending=f.openDetails('slow')
  await f.openDetails('current')
  resolve({task_id:'slow'});await pending
  assert.equal(f.detail.value.task_id,'current')
  assert.equal(f.detail.value.failure_details[0].error,'源正文为空')
  const closing=f.openDetails('slow');f.closeDetails();resolve({task_id:'slow'});await closing
  assert.equal(f.detailId.value,'');assert.equal(f.detail.value,null);assert.equal(f.detailLoading.value,false)
})
test('failure to read details is shown and queue/run durations remain independently readable',async()=>{
  const f=fixture(async()=>{throw new Error('任务详情暂不可用')})
  await f.openDetails('failed')
  assert.equal(f.detail.value,null);assert.equal(f.detailError.value,'任务详情暂不可用')
  assert.equal(f.duration(1800),'30 分 0 秒');assert.equal(f.duration(13),'13 秒')
})

test('captured, queued and failed submissions are distinct from completed cloud processing',()=>{
  const script=source.slice(source.indexOf('function statusLabel('),source.indexOf('watch(spaceScope,'))
  const code=ts.transpileModule(script+'\nreturn statusLabel',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const label=new Function('stateLabel',code)(stateLabel)
  assert.equal(label({kind:'crawl',status:'completed',phase:'submission_failed'}),'提交失败')
  assert.equal(label({kind:'crawl',status:'completed',phase:'submitted'}),'已排队提交')
  assert.equal(label({kind:'crawl',status:'completed',phase:'completed'}),stateLabel('completed','task'))
  assert.equal(label({kind:'ctxdb_sync',status:'completed',phase:'submitted'}),'提交完成')
  assert.equal(label({kind:'ctxdb_sync',status:'failed',phase:'failed'}),stateLabel('failed','upload'))
})
