import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const script = ts.transpileModule(readFileSync(new URL('./contextdbWiki.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText
function fixture(respond: (method: string, path: string, data?: any) => Promise<any>) {
  const exports: any = {}, calls: any[] = []
  const nativeAPI = Object.fromEntries(['get', 'post', 'put', 'del'].map(method => [method, async (path: string, data?: any) => {
    calls.push({ method, path, data })
    return { data: await respond(method, path, data) }
  }]))
  runInNewContext(script, { exports, URLSearchParams, require: () => ({ nativeAPI }) })
  return { api: exports, calls }
}

test('page deletion uses query parameters while edits and issue decisions retain their own version guards', async () => {
  const f = fixture(async () => ({ event_id: 'event' }))
  await f.api.deleteWikiPage('kb & other', 'page/?')
  const deletion = f.calls[0]
  assert.equal(deletion.method, 'del')
  const query = new URL(deletion.path, 'http://localhost').searchParams
  assert.equal(query.get('knowledge_base_id'), 'kb & other')
  assert.equal(query.get('page_id'), 'page/?')
  assert.equal(deletion.data, undefined)
  await f.api.updateWikiPage('kb', 'page', { content: 'draft', expected_version: 7 })
  await f.api.createWikiIssueTask('kb', { idempotency_key: 'same-request', items: [{ issue_id: 'issue', expected_version: 2, choice: 'manual_edit', manual_content: 'fixed' }] })
  assert.equal(f.calls[1].data.expected_version, 7)
  assert.equal(f.calls[2].data.items[0].expected_version, 2)
  assert.equal(f.calls[2].data.idempotency_key, 'same-request')
})

test('legacy slug lookup continues through the official index when capped search does not contain the page', async () => {
  const f = fixture(async (_method, path, data) => {
    if (path.endsWith('/search')) return { items: [], total: 0 }
    if (path.endsWith('/index')) return { groups: [{ type: data.types,
      items: data.types === 'concept' && data.cursor ? [{ page_id: 'found', slug: 'concept/older' }] : [],
      next_cursor: data.types === 'concept' && !data.cursor ? 'opaque== cursor' : null }] }
    if (path.endsWith('/detail')) return { page_id: data.page_id, published: true }
    assert.fail(`Unexpected ${path}`)
  })
  assert.equal((await f.api.getWikiPageByReference('kb', 'concept/older')).page_id, 'found')
  assert.equal(f.calls.find(row => row.data?.cursor)?.data.cursor, 'opaque== cursor')
  const count = f.calls.length
  await f.api.getWikiPageByReference('kb', '12345678-1234-1234-1234-123456789abc')
  assert.equal(f.calls.length, count + 1)
  assert.equal(f.calls.at(-1).path, 'knowledge/wiki/pages/detail')
})

test('unreadable links and invalid pagination fail visibly and official errors keep their status', async () => {
  const f = fixture(async (_method, path, data) => path.endsWith('/search') ? { items: [] } : { groups: [{ type: data.types, items: [], next_cursor: 'repeating' }] })
  await assert.rejects(f.api.getWikiPageByReference('kb', 'concept/missing'), /分页异常/)
  const denied = Object.assign(new Error('denied'), { status: 403 })
  const g = fixture(async () => { throw denied })
  await assert.rejects(g.api.getWikiIndex('kb'), (error: any) => error === denied && error.status === 403)
})
