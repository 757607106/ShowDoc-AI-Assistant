import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import { createBackgroundWorkPoller } from '../../utils/backgroundWork.ts'

test('chat page retries its first failed background query and stops after a confirmed empty list', async (t) => {
  const source = readFileSync(new URL('./index.vue', import.meta.url), 'utf8')
  const start = source.indexOf('const backgroundPoller = createBackgroundWorkPoller(')
  const end = source.indexOf('\nfunction startBackgroundWork()', start)
  assert.ok(start >= 0 && end > start)
  t.mock.timers.enable({ apis: ['setTimeout'] })
  let calls = 0
  const backgroundItems = { value: [] as any[] }
  const running = [{ work_id: 'sj_0123', kind: 'shell', title: 'build', state: 'running' }]
  const poller = runInNewContext(`${source.slice(start, end)}\nbackgroundPoller`, {
    session_id: { value: 's' }, backgroundItems,
    createBackgroundWorkPoller: (options: Parameters<typeof createBackgroundWorkPoller>[0]) =>
      createBackgroundWorkPoller({ ...options, intervalMs: 10 }),
    listBackgroundWork: async () => {
      calls++
      if (calls === 1) throw new Error('HTTP 503')
      return calls === 2 ? running : []
    },
    replaceBackgroundItems: (items: any[]) => { backgroundItems.value = items },
  })
  try {
    poller.start()
    await Promise.resolve()
    t.mock.timers.tick(10)
    await Promise.resolve()
    assert.equal(calls, 2, 'the real page callback must not stop retries while its initial list is empty')
    assert.deepEqual(backgroundItems.value, running)
    t.mock.timers.tick(10)
    await Promise.resolve()
    assert.deepEqual(backgroundItems.value, [])
    t.mock.timers.tick(100)
    assert.equal(calls, 3, 'a successful empty response ends polling')
  } finally { poller.dispose() }
})

test('chat cancellation refreshes only its original owner/session generation and exposes failures for retry', async () => {
  const source = readFileSync(new URL('./index.vue', import.meta.url), 'utf8')
  const start = source.indexOf('async function onCancelWork(')
  const end = source.indexOf('\nwatch([session_id, backgroundOwnerKey]', start)
  assert.ok(start >= 0 && end > start)
  let finish!: () => void
  let fail!: (error: Error) => void
  let cancellations = 0, refreshes = 0
  const context = {
    session_id: { value: 'same-session' }, backgroundGeneration: 1,
    backgroundItems: { value: [{ work_id: 'task', kind: 'async_subagent', read_only: false, can_cancel: true }] },
    cancelBackgroundWork: () => {
      cancellations++
      return new Promise<void>((resolve, reject) => { finish = resolve; fail = reject })
    },
    refreshBackgroundWork: async () => { refreshes++ },
  }
  const cancel = runInNewContext(`${source.slice(start, end)}\nonCancelWork`, context)
  const oldOwner = cancel('task')
  context.backgroundGeneration++
  finish(); await oldOwner
  assert.equal(refreshes, 0, 'a late request cannot refresh the same session ID under its next owner')
  const current = cancel('task')
  fail(new Error('cancel unavailable'))
  await assert.rejects(current, /cancel unavailable/)
  assert.equal(refreshes, 1, 'a failed cancellation rechecks the current server state')
  context.backgroundItems.value[0]!.kind = 'shell'
  await cancel('task')
  assert.equal(cancellations, 2, 'archived shell work never reaches the native cancellation endpoint')
})
