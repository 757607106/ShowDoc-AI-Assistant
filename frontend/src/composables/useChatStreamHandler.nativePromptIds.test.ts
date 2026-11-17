import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import * as finalContent from '../utils/finalArtifactContent.ts'
import * as history from '../utils/rag-pipeline-history.ts'
import * as timestamps from '../utils/messageTimestamp.ts'
import * as steering from '../utils/steerStreamFork.ts'
import * as dataChange from '../utils/assistantDataChange.ts'
import * as thinkBlocks from '../utils/thinkBlocks.ts'
import * as presentation from '../utils/agentTimelinePresentation.ts'
import * as collaboration from '../utils/collaborationDisplay.ts'
import * as hostApproval from '../views/chat/components/hostApproval.ts'
import type { useChatStreamHandler as StreamHandler } from './useChatStreamHandler.ts'
import { fixture, flush } from '../test-utils/vueFixture'

const source = readFileSync(new URL('./useChatStreamHandler.ts', import.meta.url), 'utf8')
const modules: Record<string, unknown> = {
  vue, 'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
  '@/utils/finalArtifactContent': finalContent,
  '@/utils/rag-pipeline-history': history,
  '@/utils/messageTimestamp': timestamps,
  '@/utils/steerStreamFork': steering,
  '@/utils/assistantDataChange': dataChange,
  '@/utils/thinkBlocks': thinkBlocks,
  '@/views/chat/components/hostApproval': hostApproval,
}
const exports: { useChatStreamHandler?: typeof StreamHandler } = {}
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, {
  exports, console,
  require: (id: string) => {
    assert.ok(id in modules, `unexpected import ${id}`)
    return modules[id]
  },
})

const display = readFileSync(new URL('../views/chat/components/AgentStreamDisplay.vue', import.meta.url), 'utf8')
const start = display.indexOf('const isThinkingLikeEvent =')
const end = display.indexOf('// IDs of thinking events', start)
assert.ok(start >= 0 && end > start)
const buildTimeline = vm.runInNewContext(ts.transpileModule(
  display.slice(start, end) + '\nbuildFullEventList',
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText, { ...presentation, ...collaboration, props: { session: {} }, isSegmentDone: vue.ref(true) })

function setup() {
  const messagesList = vue.reactive<Record<string, any>[]>([])
  const handler = exports.useChatStreamHandler!({
    messagesList, loading: vue.ref(false), isReplying: vue.ref(false),
    currentAssistantMessageId: vue.ref(''), fullContent: vue.ref(''),
    isAgentStreamSession: () => true, scrollToBottom() {}, preserveIncompleteStreamReactive: true,
  })
  return { handler, messagesList }
}

const prompt = (id: string, question: string, tool_call_id: string | null = id) => ({
  pending_id: `session:interrupt-${id}:0`, kind: 'ask_user', tool_call_id,
  suspendable: true, suspended: true,
  request: { question, options: [], fields: [], multi_select: false, allow_free_text: true },
})
const tools = (message: Record<string, any>) => Array.from(message.agentEventStream as any[])
  .filter(event => event.type === 'tool_call').map(event => event.tool_call_id)
const cards = (message: Record<string, any>) => Array.from(message.agentEventStream as any[])
  .filter(event => event.type === 'agent_prompt_required')

for (const identical of [false, true]) {
  test(`parallel ${identical ? 'identical' : 'different'} question text preserves native IDs in SSE, refresh and resume`, async () => {
    const first = prompt('call-a', 'Question A')
    const second = prompt('call-b', identical ? 'Question A' : 'Question B')
    const { handler, messagesList } = setup()
    handler.processStreamChunk({ response_type: 'agent_query', id: 'request', assistant_message_id: 'assistant' })
    for (const card of [first, second]) {
      handler.processStreamChunk({ response_type: 'tool_call', id: 'request', data: {
        tool_call_id: card.tool_call_id, tool_name: 'ask_user', arguments: { question: card.request.question },
      } })
      handler.processStreamChunk({ response_type: 'agent_prompt_required', id: 'request', data: card })
    }
    handler.processStreamChunk({ response_type: 'tool_call', id: 'request', data: {
      tool_call_id: 'document-call', tool_name: 'knowledge.get_document', arguments: { document_id: 'document' },
    } })
    const message = messagesList[0]
    assert.deepEqual(cards(message).map(card => card.tool_call_id), ['call-a', 'call-b'])
    assert.deepEqual(Array.from(buildTimeline(message.agentEventStream) as any[])
      .filter(event => event.type === 'tool_call').map(event => event.tool_call_id), ['document-call'])
    handler.prepareResumedMessage(message, first.pending_id)
    assert.deepEqual(tools(message), ['call-b', 'document-call'])
    assert.deepEqual(cards(message).map(card => card.tool_call_id), ['call-a', 'call-b'])

    const refreshed = setup()
    await refreshed.handler.handleMsgList([{
      id: 'assistant', request_id: 'request', role: 'assistant', content: '', is_completed: false,
      run_state: 'awaiting_input', agent_steps: [{ iteration: 0, thought: '', tool_calls: [
        { id: 'call-a', name: 'ask_user', args: { question: first.request.question } },
        { id: 'call-b', name: 'ask_user', args: { question: second.request.question } },
        { id: 'document-call', name: 'knowledge.get_document', args: { document_id: 'document' } },
      ] }],
      delegated_prompts: [first, second].map((card, index) => ({
        id: card.pending_id, kind: card.kind, tool_call_id: card.tool_call_id, request: card.request,
        status: index === 0 ? 'answered' : 'suspended',
        ...(index === 0 ? { response: { answer: 'Answer for call-a' } } : {}),
      })),
    }])
    const restored = refreshed.messagesList[0]
    const [answered, pending] = cards(restored)
    assert.deepEqual([answered.tool_call_id, pending.tool_call_id], ['call-a', 'call-b'])
    assert.equal(answered.response.answer, 'Answer for call-a')
    assert.equal(answered.answered, true)
    assert.equal(pending.suspended, true)
    assert.deepEqual(Array.from(buildTimeline(restored.agentEventStream) as any[])
      .filter(event => event.type === 'tool_call').map(event => event.tool_call_id), ['document-call'])
    refreshed.handler.prepareResumedMessage(restored, second.pending_id)
    assert.deepEqual(tools(restored), ['call-a', 'document-call'])

    const completed = setup()
    await completed.handler.handleMsgList([{
      id: 'completed', role: 'assistant', content: 'Finished', is_completed: true,
      agent_steps: [{ iteration: 0, thought: '', tool_calls: [first, second].map(card => ({
        id: card.tool_call_id, name: 'ask_user', args: { question: card.request.question },
        result: { success: true, output: '', data: {
          display_type: 'ask_user', question: card.request, answered: true,
          answer: { answer: `Answer for ${card.tool_call_id}` },
        } },
      })) }],
    }])
    assert.deepEqual(cards(completed.messagesList[0]).map(card => [card.tool_call_id, card.response.answer]),
      [['call-a', 'Answer for call-a'], ['call-b', 'Answer for call-b']])
    assert.deepEqual(tools(completed.messagesList[0]), [])
  })
}

test('an ambiguous legacy question without a call ID does not hide or remove another question', () => {
  const { handler, messagesList } = setup()
  handler.processStreamChunk({ response_type: 'agent_query', id: 'request', assistant_message_id: 'assistant' })
  for (const id of ['call-a', 'call-b']) {
    handler.processStreamChunk({ response_type: 'tool_call', id: 'request', data: {
      tool_call_id: id, tool_name: 'ask_user', arguments: { question: 'Identical question' },
    } })
  }
  const unbound = prompt('legacy', 'Identical question', null)
  handler.processStreamChunk({ response_type: 'agent_prompt_required', id: 'request', data: unbound })
  const message = messagesList[0]
  assert.equal(cards(message)[0].tool_call_id, null)
  assert.deepEqual(Array.from(buildTimeline(message.agentEventStream) as any[])
    .filter(event => event.type === 'tool_call').map(event => event.tool_call_id), ['call-a', 'call-b'])
  handler.prepareResumedMessage(message, unbound.pending_id)
  assert.deepEqual(tools(message), ['call-a', 'call-b'])
})

test('structured results retain their native object through completion and history', async () => {
  const { handler, messagesList } = setup()
  handler.processStreamChunk({ response_type: 'agent_query', id: 'request', assistant_message_id: 'assistant' })
  handler.processStreamChunk({ response_type: 'complete', id: 'request', data: { structured_response: { answer: 42 } } })
  assert.deepEqual(JSON.parse(JSON.stringify(messagesList[0].structured_response)), { answer: 42 })
  const restored = setup()
  await restored.handler.handleMsgList([{ id: 'assistant', role: 'assistant', content: '', is_completed: true,
    structured_response: { answer: 42 }, agent_steps: [] }])
  assert.deepEqual(JSON.parse(JSON.stringify(restored.messagesList[0].structured_response)), { answer: 42 })
})

test('generic interrupt refresh preserves schema and false response without changing it to an object', async () => {
  const { handler, messagesList } = setup()
  await handler.handleMsgList([{ id: 'assistant', role: 'assistant', content: '', is_completed: false,
    run_state: 'awaiting_input', agent_steps: [], delegated_prompts: [{
      id: 'session:interrupt:0', kind: 'native_interrupt', status: 'answered', response: false,
      request: { value: 'Confirm', response_schema: { type: 'boolean' } },
    }] }])
  const card = cards(messagesList[0])[0]
  assert.equal(card.kind, 'native_interrupt'); assert.equal(card.response, false)
  assert.deepEqual(JSON.parse(JSON.stringify(card.request.response_schema)), { type: 'boolean' })
})

test('native background events wake an initially empty page and a new run of the same task', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const { createBackgroundWorkPoller } = await import('../utils/backgroundWork.ts')
  const { handler, messagesList } = setup()
  let calls = 0
  let items: any[] = []
  const seen: any[][] = []
  const poller = createBackgroundWorkPoller({ sessionId: 'session', intervalMs: 5,
    list: async () => { calls++; return items }, onUpdate: rows => seen.push(rows) })
  const page = readFileSync(new URL('../views/chat/index.vue', import.meta.url), 'utf8')
  const start = page.indexOf('const backgroundWorkStamp =')
  const end = page.indexOf('\nfunction forkAffordanceOf', start)
  assert.ok(start >= 0 && end > start)
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(ts.transpileModule(page.slice(start, end), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { computed: vue.computed, watch: vue.watch, messagesList,
    refreshBackgroundWork: () => poller.refresh() }))
  try {
    poller.start()
    await Promise.resolve()
    assert.equal(calls, 1)
    handler.processStreamChunk({ response_type: 'agent_query', id: 'request', assistant_message_id: 'assistant' })
    items = [{ work_id: 'task', kind: 'async_subagent', state: 'running', title: 'Worker' }]
    handler.processStreamChunk({ response_type: 'work_started', id: 'request', data: {
      ...items[0], payload: { run_id: 'run-one' },
    } })
    await vue.nextTick(); await Promise.resolve()
    assert.equal(calls, 2)
    assert.equal(seen.at(-1)?.[0]?.work_id, 'task')
    handler.processStreamChunk({ response_type: 'work_started', id: 'request', data: {
      ...items[0], payload: { run_id: 'run-two' },
    } })
    await vue.nextTick(); await Promise.resolve()
    assert.equal(calls, 3, 'same-task same-state update still wakes the new run')
    items = [{ ...items[0], state: 'succeeded' }]
    handler.processStreamChunk({ response_type: 'work_finished', id: 'request', data: {
      ...items[0], payload: { run_id: 'run-two' },
    } })
    await vue.nextTick(); await Promise.resolve()
    assert.equal(calls, 4)
    t.mock.timers.tick(100)
    await Promise.resolve()
    assert.equal(calls, 4, 'all-terminal task rows remain visible without perpetual polling')
  } finally { scope.stop(); poller.dispose() }
})

test('child viewer retains the projected image/audio/video/file history and refreshes a new run with the same terminal state', async t => {
  const fx = fixture(t)
  const media = '![Image](https://example.test/image.png)\n<audio controls src="https://example.test/audio.mp3"></audio>\n'
    + '<video controls src="https://example.test/video.mp4"></video>\n[Download](https://example.test/report.pdf)'
  let content = media
  const calls: string[] = []
  const { vm: child } = fx.component(new URL('../views/chat/components/ChildAgentStream.vue', import.meta.url), {
    'vue-i18n': modules['vue-i18n'],
    '@/composables/useChatScrollFollow': { useChatScrollFollow: () => ({ onScroll() {}, scrollToBottom() {}, rememberPosition() {} }) },
    '@/api/chat': { getMessageList: async ({ session_id }: any) => {
      calls.push(session_id)
      return { data: [{ id: 'remote-answer', role: 'assistant', content, is_completed: true,
        agent_steps: [{ iteration: 0, tool_calls: [] }] }] }
    } },
    '@/api/chat/streame': { useStream: () => ({ isStreaming: vue.ref(false), error: vue.ref(''), onChunk() {},
      startStream: () => assert.fail('completed media history does not open a new execution'), stopStream() {} }) },
    '@/composables/useChatStreamHandler': { useChatStreamHandler: exports.useChatStreamHandler,
      isAwaitingInput: (row: any) => row?.run_state === 'awaiting_input' },
    '@/utils/collaborationDisplay': collaboration,
  }, { task: { id: 'task', sessionId: 'subgraph~signed-remote', status: 'succeeded' }, refreshKey: 0 })
  await flush()
  const state = child.$.exposed
  assert.equal(state.messages[0].content, media)
  assert.equal(state.messages[0].agentEventStream.find((event: any) => event.type === 'answer').content, media)
  t.mock.timers.tick(5000)
  await flush()
  assert.deepEqual(calls, ['subgraph~signed-remote'], 'terminal history does not keep polling')
  content = media + '\nUpdated task result'
  child.$.props.refreshKey++
  await flush()
  assert.equal(state.messages[0].content, content)
  assert.deepEqual(calls, ['subgraph~signed-remote', 'subgraph~signed-remote'])
})
