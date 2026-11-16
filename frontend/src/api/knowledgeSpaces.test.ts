import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('./knowledgeSpaces.ts', import.meta.url), 'utf8')
const script = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText

test('business rename refreshes both native library names through the existing resource event', async () => {
  const api: any = {}, events: any[] = [], requests: any[] = []
  runInNewContext(script, { exports: api, require: (path: string) => path === '@/utils/request' ? {
    patch: async (path: string, body: any) => {
      requests.push({ path, body })
      return { space: { scope: 'space:a', name: '新资料', wiki_kb_id: 'wiki', graph_kb_id: 'graph' } }
    },
  } : { emitAssistantDataChange: (event: any) => events.push(event) } })
  const result = await api.updateSpace('space:a', { name: '新资料' })
  assert.equal(result.space.name, '新资料')
  assert.equal(requests[0].path, '/api/kb/spaces/space%3Aa')
  assert.equal(events[0].operation, 'knowledge_base.update')
  assert.equal(events[0].area, 'knowledge_base')
  assert.deepEqual(Array.from(events[0].ids.knowledge_base_id), ['wiki', 'graph'])
  await api.updateSpace('space:a', { graph_enabled: true })
  assert.equal(events.length, 1)
})

test('failed business rename never announces a changed name', async () => {
  const api: any = {}, events: any[] = []
  runInNewContext(script, { exports: api, require: (path: string) => path === '@/utils/request' ? {
    patch: async () => { throw new Error('名称未保存') },
  } : { emitAssistantDataChange: (event: any) => events.push(event) } })
  await assert.rejects(api.updateSpace('space', { name: '新资料' }), /名称未保存/)
  assert.equal(events.length, 0)
})
