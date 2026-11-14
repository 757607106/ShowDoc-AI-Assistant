import assert from 'node:assert/strict'
import test from 'node:test'
import { fixture } from '../../../../test-utils/vueFixture.ts'
import { splitKnowledgeResults } from '../../../../utils/contextdbSearchResults.ts'

function result(t:Parameters<typeof fixture>[0],output:unknown){
  return fixture(t).component(new URL('./ContextDBToolResult.vue',import.meta.url),{
    '@/utils/contextdbSearchResults':{splitKnowledgeResults},
  },{output}).vm
}

test('native tool results keep real document references separate from graph synthesis and unlinked records',t=>{
  const document={chunk_id:'chunk-a',doc_id:'doc-a',docnm_kwd:'产品手册',content_with_weight:'原文证据',similarity:0}
  const graph={chunk_id:'graph:kb:entity-a',doc_id:'',tag_kwd:['graphrag'],content_with_weight:'图谱综合信息'}
  const record={entity_id:'entity-a',content:'实体信息'}
  const vm=result(t,{chunks:[document,graph,record]})
  assert.equal(vm.documents.length,1)
  assert.equal(vm.documents[0].knowledge_id,'doc-a')
  assert.equal(vm.documents[0].knowledge_title,'产品手册')
  assert.equal(vm.documents[0].content,'原文证据')
  assert.equal(vm.documents[0].similarity,0)
  assert.equal(vm.results.graph.length,1)
  assert.equal(vm.results.graph[0],graph)
  assert.equal(vm.unlinked.length,1)
  assert.equal(vm.unlinked[0].entity_id,'entity-a')
  assert.equal(Object.hasOwn(document,'knowledge_id'),false)
})

test('tool output accepts JSON history and retains plain text and non-search data',t=>{
  const f=fixture(t)
  const mount=(output:unknown)=>f.component(new URL('./ContextDBToolResult.vue',import.meta.url),{
    '@/utils/contextdbSearchResults':{splitKnowledgeResults},
  },{output}).vm
  const json=mount(JSON.stringify({results:[{document_id:'doc-a',document_name:'手册',content:'原文'}]}))
  assert.equal(json.documents[0].knowledge_id,'doc-a')
  assert.equal(json.documents[0].knowledge_title,'手册')
  const record=mount({knowledge_bases:[{id:'kb-a',name:'产品资料'}]})
  assert.equal(record.structured,true)
  assert.equal(record.items,undefined)
  assert.equal(mount('操作失败：权限不足').value,'操作失败：权限不足')
  assert.equal(mount(null).structured,false)
})
