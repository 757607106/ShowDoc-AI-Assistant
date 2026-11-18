import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'

const source = readFileSync(new URL('./index.vue', import.meta.url), 'utf8')

// Historical turns can contain several display segments. Only their persisted
// assistant ID addresses the original run when reconnecting or stopping it.
test('resume and stop address the persisted assistant id, not a fork id', () => {
  const fork = readFileSync(new URL('../../utils/steerStreamFork.ts', import.meta.url), 'utf8')
  assert.match(fork, /export function persistedAssistantId/)

  const start = source.indexOf('onAfterMsgList: async ()')
  const end = source.indexOf('onAgentQuery:', start)
  assert.notEqual(start, -1)
  assert.notEqual(end, -1)
  const hook = source.slice(start, end)

  assert.match(hook, /persistedAssistantId\(lastMessage\)/)
  assert.match(hook, /currentAssistantMessageId\.value = resumeId/)
  assert.match(hook, /query: resumeId/)
  assert.doesNotMatch(hook, /query: lastMessage\.id/)
  assert.match(hook, /findLastMessage\(\s*\(message\) => message\.role === 'assistant' && !message\.is_completed\s*\)/)
  assert.doesNotMatch(hook, /messagesList\[messagesList\.length - 1\]/)
})

function stopFailureFixture(messageId = 'reply-a') {
  const start = source.indexOf('const handleStopFailed = async')
  const end = source.indexOf('const sendMsg =', start)
  const message = { id: messageId, role: 'assistant', is_completed: true }
  const streams = []
  const context = {
    currentAssistantMessageId: { value: messageId },
    loading: { value: false },
    isReplying: { value: false },
    session_id: { value: 'session-a' },
    findLastMessage: predicate => predicate(message) ? message : undefined,
    persistedAssistantId: row => row.id,
    prepareResumedMessage: row => { row.is_completed = false },
    startStream: async request => { streams.push(request) },
  }
  const handleStopFailed = vm.runInNewContext(`${source.slice(start, end)}\nhandleStopFailed`, context)
  return { context, message, streams, handleStopFailed }
}

test('a failed stop reopens the local turn and attaches to its real stream', async () => {
  const f = stopFailureFixture()
  await f.handleStopFailed()
  assert.equal(f.message.is_completed, false)
  assert.equal(f.context.isReplying.value, true)
  assert.equal(f.context.loading.value, true)
  assert.equal(f.streams.length, 1)
  assert.equal(f.streams[0].session_id, 'session-a')
  assert.equal(f.streams[0].query, 'reply-a')
  assert.equal(f.streams[0].method, 'GET')
  assert.equal(f.streams[0].url, '/api/v1/sessions/continue-stream')
})

test('a failed stop without a local assistant has an explicit terminal state', async () => {
  const f = stopFailureFixture('')
  f.context.currentAssistantMessageId.value = 'missing'
  await f.handleStopFailed()
  assert.equal(f.context.isReplying.value, false)
  assert.equal(f.context.loading.value, false)
  assert.equal(f.context.currentAssistantMessageId.value, '')
  assert.equal(f.streams.length, 0)
})
