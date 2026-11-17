import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('./index.ts', import.meta.url), 'utf8')
const start = source.indexOf('export async function getChunkByIdOnly(')
const end = source.indexOf('// Delete a single generated question', start)
const script = ts.transpileModule(source.slice(start, end), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText

test('citation reads the exact official chunk across pages and reports removed chunks', async () => {
  const requests: any[] = []
  const exports: any = {}
  runInNewContext(script, { exports, contextdb: { nativeAPI: { get: async (path: string, params: any) => {
    requests.push({ path, ...params })
    return { data: { document_id: 'doc', total: 2, chunks: params.offset === 0
      ? [{ chunk_id: 'first', content: 'First passage' }] : [{ chunk_id: 'second', content: 'Exact cited passage' }] } }
  } } } })
  const result = await exports.getChunkByIdOnly('second', 'doc')
  assert.equal(result.data.content, 'Exact cited passage')
  assert.equal(result.data.knowledge_id, 'doc')
  assert.deepEqual(requests.map(row => row.offset), [0, 1])
  assert.ok(requests.every(row => row.path === 'knowledge/documents/chunks' && row.document_id === 'doc'))
  await assert.rejects(exports.getChunkByIdOnly('removed', 'doc'), /未找到/)
  const count = requests.length
  await assert.rejects(exports.getChunkByIdOnly('second'), /文档 ID/)
  assert.equal(requests.length, count)
})

const pageStart = source.indexOf('export const KNOWLEDGE_CHUNK_PAGE_SIZE')
const pageScript = ts.transpileModule(source.slice(pageStart, source.indexOf('export interface ChunkEditPayload', pageStart)), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText

test('document chunk pages retain native attachment coordinates and use the requested pagination without mutating data', async () => {
  const requests: any[] = [], exports: any = {}
  const chunk = { chunk_id: 'chunk-a', content: '原文', chunk_index: 50, attachments: [{ type: 'image', asset_id: 'asset-a' }] }
  runInNewContext(pageScript, { exports, contextdb: { nativeAPI: { async get(path: string, params: any) {
    requests.push({ path, ...params }); return { data: { document_id: 'doc-a', chunks: [chunk], total: 51 } }
  } } } })
  const result = await exports.getKnowledgeDetailsCon('doc-a', 3)
  assert.deepEqual(requests, [{ path: 'knowledge/documents/chunks', document_id: 'doc-a', offset: 50, limit: 25 }])
  assert.equal(result.success, true); assert.equal(result.total, 51); assert.equal(result.data[0].id, 'chunk-a')
  assert.deepEqual(result.data[0].attachments, chunk.attachments); assert.equal('id' in chunk, false)
})

test('document chunk pages reject absent or mismatched document ownership rather than presenting another source', async () => {
  for (const data of [{ chunks: [], total: 0 }, { document_id: 'another-doc', chunks: [{ chunk_id: 'wrong', content: '错误来源' }], total: 1 }]) {
    const exports: any = {}
    runInNewContext(pageScript, { exports, contextdb: { nativeAPI: { get: async () => ({ data }) } } })
    await assert.rejects(exports.getKnowledgeDetailsCon('doc-a', 1), /切片归属不一致/)
  }
})

test('document chunk page read failures preserve their upstream error', async () => {
  const exports: any = {}, error = Object.assign(new Error('source denied'), { status: 403 })
  runInNewContext(pageScript, { exports, contextdb: { nativeAPI: { get: async () => { throw error } } } })
  await assert.rejects(exports.getKnowledgeDetailsCon('doc-a', 1), (value: any) => value === error)
})
