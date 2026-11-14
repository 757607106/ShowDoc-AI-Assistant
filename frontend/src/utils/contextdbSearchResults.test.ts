import assert from 'node:assert/strict'
import test from 'node:test'
import { splitKnowledgeResults } from './contextdbSearchResults.ts'

test('ContextDB GraphRAG synthesis is kept apart from document evidence and keeps real provenance',()=>{
  const synthesis={chunk_id:'graph:kb-a:entity-a',doc_id:'',tag_kwd:['graphrag'],content_with_weight:'关联摘要',graph:{entities:[{entity_id:'entity-a',source_document_ids:['doc-1']}],relations:[]}}
  const result=splitKnowledgeResults([synthesis,{chunk_id:'chunk-1',doc_id:'doc-1',docnm_kwd:'手册.md',content_with_weight:'真实原文',similarity:0}])
  assert.equal(result.graph.length,1);assert.equal(result.documents.length,1)
  assert.equal(result.graph[0],synthesis)
  assert.equal(result.documents[0].doc_id,'doc-1');assert.equal(result.documents[0].content,'真实原文')
  assert.equal(result.documents[0].doc_name,'手册.md');assert.equal(result.documents[0].similarity,0)
  assert.equal(splitKnowledgeResults([{chunk_id:'graph:kb-a:no-source',doc_id:''}]).documents.length,0)
})
