import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const script = ts.transpileModule(readFileSync(new URL('./background-work.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText

function fixture(response: unknown = { data: {} }, error?: Error) {
  const api: any = {}, calls: any[] = []
  runInNewContext(script, { exports: api, require: () => Object.fromEntries(['get', 'post'].map(method => [method,
    async (path: string, body: unknown) => {
      calls.push({ method, path, body })
      if (error) throw error
      return response
    },
  ])) })
  return { api, calls }
}

test('async follow-ups and complete interrupt responses use encoded session-owned paths', async () => {
  const { api, calls } = fixture()
  const responses = { first: false, second: null, third: { answer: ['a', 2] } }
  await api.updateBackgroundWork('session /?#', 'work /?#', '  Follow-up\n')
  await api.resumeBackgroundWork('session /?#', 'work /?#', responses)
  assert.deepEqual(calls.map(({ method, path }) => ({ method, path })), [
    { method: 'post', path: '/api/v1/sessions/session%20%2F%3F%23/background-work/work%20%2F%3F%23/update' },
    { method: 'post', path: '/api/v1/sessions/session%20%2F%3F%23/background-work/work%20%2F%3F%23/resume' },
  ])
  assert.equal(calls[0].body.message, '  Follow-up\n')
  assert.equal(calls[1].body.responses, responses, 'JSON response values and every interrupt ID remain unchanged')
})

test('async detail retains raw output, response schemas and server permissions', async () => {
  const detail = { work_id: 'task', kind: 'async_subagent', title: 'Review', state: 'waiting', read_only: false, can_cancel: true,
    result: { display_type: 'async_subagent', output: '<script>raw text</script>', structured_response: { answer: false },
      interrupts: [{ id: 'real-id', value: { question: 'Confirm?' }, response_schema: { type: 'boolean' } }] } }
  const { api, calls } = fixture({ data: detail })
  assert.equal(await api.getBackgroundWork('session', 'task'), detail)
  assert.equal(calls[0].path, '/api/v1/sessions/session/background-work/task')
  assert.equal(calls[0].body, undefined, 'detail reads never send a model cursor or run_id')
})

test('mutation failures reach the caller without retrying or losing their error', async () => {
  const error = new Error('upstream schema rejected')
  const { api, calls } = fixture(undefined, error)
  await assert.rejects(api.updateBackgroundWork('session', 'task', 'Follow up'), (value: unknown) => value === error)
  await assert.rejects(api.resumeBackgroundWork('session', 'task', { real: false }), (value: unknown) => value === error)
  assert.equal(calls.length, 2)
})

test('same task cancellation never shares an in-flight response across caller owners', async () => {
  let resolve!: (value: unknown) => void
  const response = new Promise(yes => { resolve = yes })
  const { api, calls } = fixture(response)
  const first = api.cancelBackgroundWork('session', 'task')
  const nextOwner = api.cancelBackgroundWork('session', 'task')
  assert.equal(calls.length, 2, 'component-local guards own duplicate suppression and reset with the owner')
  resolve({ data: { work_id: 'task', state: 'cancelled' } })
  await Promise.all([first, nextOwner])
  assert.ok(calls.every(call => call.path.endsWith('/background-work/task/cancel')))
})
