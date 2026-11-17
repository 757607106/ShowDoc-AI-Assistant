import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

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
