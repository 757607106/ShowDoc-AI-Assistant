import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, ref } from 'vue'
import ts from 'typescript'

const source=readFileSync(new URL('./doc-content.vue',import.meta.url),'utf8')
const start=source.indexOf('const canDeleteGeneratedQuestion =')
const end=source.indexOf('const refreshSummary =',start)
const script=ts.transpileModule(source.slice(start,end)+`\nreturn {canEditContent,canEditMetadata,metadataEditing,nativeMetadataDraft,startMetadataEdit,saveMetadata}`,{
  compilerOptions:{target:ts.ScriptTarget.ES2022},
}).outputText
function fixture(editable=true){
  const metadata={version:2,enabled:true,nested:{modules:['订单','库存']},empty:null}
  const props={canEditKB:true,details:{id:'doc-a',custom_metadata:metadata}}
  const writes:any[]=[],errors:string[]=[]
  const state=new Function('IS_CONTEXTDB','props','authStore','computed','ref','t','updateKnowledgeMetadata','MessagePlugin',script)(
    true,props,{hasRole:()=>editable},computed,ref,(key:string)=>key,
    async(id:string,value:any)=>{writes.push({id,value:JSON.parse(JSON.stringify(value))});return {success:true}},
    {success(){},error:(message:string)=>errors.push(message)},
  )
  return {state,props,writes,errors}
}

test('native preview allows metadata editing without enabling unsupported content operations',async()=>{
  const f=fixture()
  assert.equal(f.state.canEditContent.value,false)
  assert.equal(f.state.canEditMetadata.value,true)
  f.state.startMetadataEdit()
  f.state.nativeMetadataDraft.value={...f.state.nativeMetadataDraft.value,version:3}
  assert.equal(f.props.details.custom_metadata.version,2)
  await f.state.saveMetadata()
  assert.deepEqual(f.writes,[{id:'doc-a',value:{version:3,enabled:true,nested:{modules:['订单','库存']},empty:null}}])
  assert.equal(f.state.metadataEditing.value,false)
})

test('native metadata denies readonly writes and rejects more than 32 fields',async()=>{
  const reader=fixture(false)
  reader.state.startMetadataEdit();await reader.state.saveMetadata()
  assert.equal(reader.state.metadataEditing.value,false);assert.equal(reader.writes.length,0)
  const editor=fixture()
  editor.state.startMetadataEdit()
  editor.state.nativeMetadataDraft.value=Object.fromEntries(Array.from({length:33},(_,i)=>[`field${i}`,i]))
  await editor.state.saveMetadata()
  assert.equal(editor.writes.length,0);assert.match(editor.errors[0],/32/)
  assert.equal(editor.state.metadataEditing.value,true)
})

test('native summary status never schedules unsupported polling',()=>{
  const scheduler=source.slice(source.indexOf('const scheduleSummaryStatusPoll ='),source.indexOf('watch(\n  () => \[props.visible'))
  const code=ts.transpileModule(scheduler+'\nreturn scheduleSummaryStatusPoll', {compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const schedule=new Function('IS_CONTEXTDB','summaryStatusPollTimer','summaryStatusPollGeneration','props','isSummaryStatusInFlight','setTimeout',code)(
    true,null,0,{visible:true,details:{id:'doc-a',summary_status:'processing'}},()=>true,assert.fail,
  )
  assert.doesNotThrow(schedule)
})
