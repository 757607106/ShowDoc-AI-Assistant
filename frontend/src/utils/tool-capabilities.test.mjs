import assert from 'node:assert/strict'
import test from 'node:test'
import { deriveKbFilterFromTools, evaluateToolRequirement, toolsConsumeFiles } from './tool-capabilities.ts'

const wikiOnly = { vector: false, keyword: false, wiki: true, graph: false, faq: false }

test('official knowledge tools preserve their document and knowledge-base scope requirements', () => {
  assert.equal(toolsConsumeFiles(['knowledge.search']), true)
  assert.equal(toolsConsumeFiles(['knowledge.wiki_search']), false)
  assert.equal(evaluateToolRequirement('knowledge.get_graph', wikiOnly, true).ok, false)
  assert.deepEqual(deriveKbFilterFromTools(['knowledge.wiki_search']).any_of, ['wiki'])
})

test('document readers are usable on a wiki-only knowledge base', () => {
  for (const tool of ['read_document', 'list_documents']) {
    assert.deepEqual(evaluateToolRequirement(tool, wikiOnly, true), { ok: true, missKind: 'none' })
  }
  assert.equal(evaluateToolRequirement('search_knowledge', wikiOnly, true).ok, false)
})

test('document readers do not widen a RAG agent KB filter to wiki-only bases', () => {
  const rag = deriveKbFilterFromTools(['search_knowledge', 'read_document', 'list_documents'])
  assert.deepEqual([...rag.any_of].sort(), ['keyword', 'vector'])

  const wiki = deriveKbFilterFromTools(['wiki_search', 'wiki_read_page', 'read_document'])
  assert.deepEqual(wiki.any_of, ['wiki'])

  const readerOnly = deriveKbFilterFromTools(['read_document'])
  assert.deepEqual([...readerOnly.any_of].sort(), ['keyword', 'vector', 'wiki'])

  assert.equal(deriveKbFilterFromTools(['thinking']), null)
})
