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
