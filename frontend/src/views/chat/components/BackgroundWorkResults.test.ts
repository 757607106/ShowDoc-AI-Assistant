import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from 'vue/server-renderer'
import { fixture, flush } from '../../../test-utils/vueFixture'
import { asyncPromptResponses, isBackgroundWorkActive } from '../../../utils/backgroundWork'
import type { AsyncSubagentPayload, BackgroundWorkDetail } from '../../../api/chat/background-work'

type Action = 'update' | 'resume' | 'cancel'
const { nextTick } = vue

function deferred() {
  let resolve!: (value?: unknown) => void
  let reject!: (error: Error) => void
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function nativeDetail(state: BackgroundWorkDetail['state'] = 'waiting'): BackgroundWorkDetail {
  return {
    work_id: 'task', title: 'Research', kind: 'async_subagent', state, read_only: false, can_cancel: true,
    result: {
      display_type: 'async_subagent', output: '<script>raw output</script>', structured_response: { answer: false },
      interrupts: state === 'waiting' ? [
        { id: 'interrupt-a', value: false, response_schema: { type: 'boolean' } },
        { id: 'interrupt-b', value: null, response_schema: { type: ['null', 'object'] } },
      ] : [],
    },
  }
}

function resultsFixture(t: TestContext, initial: BackgroundWorkDetail = nativeDetail(), get?: (...args: string[]) => Promise<unknown>) {
  const calls: { action: 'get' | Action; args: any[] }[] = [], changed: unknown[] = []
  const handlers: Partial<Record<Action, (...args: any[]) => Promise<unknown>>> = {}
  let value = initial
  let read = get ?? (async () => value)
  const mutation = (action: Action) => (...args: any[]) => {
    calls.push({ action, args })
    return handlers[action]?.(...args) ?? Promise.resolve({ work_id: 'task', state: 'running' })
  }
  const mounted = fixture(t).component(new URL('./BackgroundWorkResults.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    '@/utils/backgroundWork': { asyncPromptResponses, isBackgroundWorkActive },
    '@/utils/suspendedRun': { promptSubmissionTransportKey: Symbol('prompt-transport'), resumeSuspendedRunKey: Symbol('resume') },
    '@/composables/usePromptDock': { providePromptDock() {} },
    '@/api/chat/background-work': {
      getBackgroundWork: (...args: string[]) => { calls.push({ action: 'get', args }); return read(...args) },
      updateBackgroundWork: mutation('update'), resumeBackgroundWork: mutation('resume'), cancelBackgroundWork: mutation('cancel'),
    },
  }, { sessionId: 'session-a', workId: 'task', ownerKey: 'owner-a', onChanged: (...args: unknown[]) => changed.push(args) })
  return {
    state: mounted.vm.$.exposed, props: mounted.vm.$.props, close: mounted.close, calls, changed, handlers,
    setDetail(next: BackgroundWorkDetail) { value = next },
    setRead(next: (...args: string[]) => Promise<unknown>) { read = next },
    mutations: (action?: Action) => calls.filter(call => call.action !== 'get' && (!action || call.action === action)),
  }
}

test('async detail retains original interrupt values, schemas and raw structured output', async t => {
  const original = nativeDetail(), before = JSON.stringify(original)
  const { state } = resultsFixture(t, original)
  await flush()
  const result = state.nativeResult.value
  assert.equal(result.output, '<script>raw output</script>')
  assert.deepEqual(JSON.parse(JSON.stringify(result.structured_response)), { answer: false })
  assert.equal(result.interrupts[0].value, false)
  assert.equal(result.interrupts[1].value, null)
  assert.deepEqual(JSON.parse(JSON.stringify(result.interrupts.map((item: any) => item.response_schema))), [
    { type: 'boolean' }, { type: ['null', 'object'] },
  ])
  assert.equal(JSON.stringify(original), before, 'rendering does not rewrite the server interrupt payload')
})

test('native output, false/null results and interrupt schemas render as escaped preformatted text', async t => {
  const fx = fixture(t)
  const file = new URL('./BackgroundWorkResults.vue', import.meta.url)
  const script = compileScript(parse(readFileSync(file, 'utf8')).descriptor, { id: 'background-work-results', inlineTemplate: true }).content
  for (const structuredResponse of [false, null]) {
    const detail = nativeDetail()
    detail.read_only = true
    const result = detail.result as AsyncSubagentPayload
    result.output = '<script>alert("raw")</script> **raw text**'
    result.structured_response = structuredResponse
    const read = Promise.resolve(detail)
    const component = fx.evaluate(script, {
      vue, 'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
      '@/utils/backgroundWork': { asyncPromptResponses, isBackgroundWorkActive },
    '@/utils/suspendedRun': { promptSubmissionTransportKey: Symbol('prompt-transport'), resumeSuspendedRunKey: Symbol('resume') },
    '@/composables/usePromptDock': { providePromptDock() {} },
      '@/api/chat/background-work': { getBackgroundWork: () => read },
      './ChildAgentStream.vue': { default: {} },
      './PendingPromptDock.vue': { default: {} },
      './tool-results/ShellExecResult.vue': { default: {} },
    }).default
    // Let SSR wait for the component's initial detail read before rendering.
    component.serverPrefetch = () => read
    const app = vue.createSSRApp(component, { sessionId: 'session', workId: 'task' })
    app.config.globalProperties.$t = (key: string) => key
    const control = { setup: (_props: any, { slots }: any) => () => vue.h('div', slots.default?.()) }
    app.component('t-button', control)
    app.component('t-textarea', control)
    const html = await renderToString(app)
    const blocks = Array.from(html.matchAll(/<pre(?:\s[^>]*)?>([\s\S]*?)<\/pre>/g), match => match[1])
    assert.equal(blocks.length, 6, 'output, structured response, interrupt values and both schemas use pre elements')
    assert.match(blocks[0]!, /&lt;script&gt;alert\(&quot;raw&quot;\)&lt;\/script&gt; \*\*raw text\*\*/)
    assert.equal(blocks[1], String(structuredResponse))
    assert.equal(blocks[2], 'false')
    assert.equal(blocks[4], 'null')
    assert.match(blocks[3]!, /&quot;type&quot;: &quot;boolean&quot;/)
    assert.match(blocks[5]!, /&quot;null&quot;/)
    assert.doesNotMatch(html, /<script\b|<strong\b/)
  }
})

test('remote conversation uses the original child viewer and submits only a complete native card batch', async t => {
  const detail = nativeDetail()
  Object.assign(detail.result!, {
    view_session_id: 'subgraph~signed-remote-view',
    prompts: [
      { pending_id: 'second', interrupt_id: 'batch', kind: 'tool_approval', action_index: 1, action_count: 2, mcp_tool_name: 'edit_file' },
      { pending_id: 'first', interrupt_id: 'batch', kind: 'tool_approval', action_index: 0, action_count: 2, mcp_tool_name: 'write_file' },
      { pending_id: 'boolean', interrupt_id: 'typed', kind: 'native_interrupt' },
    ],
  })
  const { state, mutations, changed } = resultsFixture(t, detail)
  await flush()
  assert.equal(state.viewerTask.value.sessionId, 'subgraph~signed-remote-view')
  assert.equal(state.promptMessages[0].agentEventStream[0].type, 'tool_approval_required')
  await state.submitPrompt('second', 'tool_approval', { decision: 'reject', reason: 'No' })
  await state.submitPrompt('boolean', 'native_interrupt', false)
  assert.equal(mutations().length, 0, 'staging two cards cannot partially resume a three-card snapshot')
  await state.submitPrompt('first', 'tool_approval', { decision: 'edit', modified_args: { content: 'Edited' } })
  assert.deepEqual(JSON.parse(JSON.stringify(mutations('resume')[0]!.args)), [
    'session-a', 'task', { batch: { decisions: [
      { type: 'edit', edited_action: { name: 'write_file', args: { content: 'Edited' } } },
      { type: 'reject', message: 'No' },
    ] }, typed: false },
  ])
  assert.equal(changed.length, 1)
  assert.equal(state.canResume.value, false)
})

test('a missing action in native approval metadata cannot become a partial decisions array', () => {
  assert.equal(asyncPromptResponses([
    { pending_id: 'second', interrupt_id: 'batch', kind: 'tool_approval', action_index: 1, action_count: 2 },
  ], { second: { decision: 'approve' } }), null)
})

test('remote card errors keep the staged batch for retry and late responses cannot affect a new owner', async t => {
  const detail = nativeDetail()
  Object.assign(detail.result!, { view_session_id: 'remote', prompts: [
    { pending_id: 'card', interrupt_id: 'typed', kind: 'native_interrupt' },
  ] })
  const { state, props, handlers, mutations, changed } = resultsFixture(t, detail)
  await flush()
  handlers.resume = async () => { throw new Error('remote schema rejected') }
  await assert.rejects(state.submitPrompt('card', 'native_interrupt', null), /remote schema rejected/)
  assert.equal(state.promptResponses.value.card, null)
  assert.equal(state.canResume.value, true)
  const request = deferred()
  handlers.resume = () => request.promise
  const late = state.submitPrompt('card', 'native_interrupt', null)
  props.ownerKey = 'owner-b'
  await vue.nextTick()
  request.resolve()
  assert.deepEqual(JSON.parse(JSON.stringify(await late)), { resumed: false, stale: true })
  assert.equal(mutations('resume').length, 2)
  assert.equal(changed.length, 0)
  assert.equal(Object.keys(state.promptResponses.value).length, 0)
})

test('resume validates every draft and submits the complete real interrupt ID map once', async t => {
  const { state, mutations, changed } = resultsFixture(t)
  await flush()
  state.responseDrafts.value = { 'interrupt-a': 'false', 'interrupt-b': '{' }
  await state.act('resume')
  assert.equal(mutations().length, 0, 'one invalid response prevents a partial resume')
  assert.ok(state.actionError.value)
  assert.equal(state.responseDrafts.value['interrupt-b'], '{')
  state.responseDrafts.value['interrupt-b'] = 'null'
  await state.act('resume')
  const request = mutations('resume')[0]!
  assert.deepEqual(Array.from(request.args.slice(0, 2)), ['session-a', 'task'])
  assert.deepEqual(JSON.parse(JSON.stringify(request.args[2])), { 'interrupt-a': false, 'interrupt-b': null })
  assert.equal(changed.length, 1)
  assert.equal(state.canResume.value, false, 'the same interrupted snapshot cannot be resubmitted after success')
  await state.act('resume')
  assert.equal(mutations('resume').length, 1)
})

test('server-rejected interrupt responses remain editable and can be retried', async t => {
  const { state, handlers, mutations } = resultsFixture(t)
  await flush()
  state.responseDrafts.value = { 'interrupt-a': 'false', 'interrupt-b': '{"answer":2}' }
  handlers.resume = async () => { throw new Error('response schema rejected') }
  await state.act('resume')
  assert.equal(state.actionError.value, 'response schema rejected')
  assert.equal(state.responseDrafts.value['interrupt-a'], 'false')
  assert.equal(state.responseDrafts.value['interrupt-b'], '{"answer":2}')
  assert.equal(state.detail.value.state, 'waiting')
  assert.equal(state.canResume.value, true)
  handlers.resume = async () => undefined
  await state.act('resume')
  assert.equal(mutations('resume').length, 2)
})

for (const state of ['succeeded', 'failed'] as const) {
  test(`a writable ${state} task can receive another update`, async t => {
    const { state: view, mutations } = resultsFixture(t, nativeDetail(state))
    await flush()
    assert.equal(view.canUpdate.value, true)
    assert.equal(view.canCancel.value, false)
    view.messageDraft.value = 'Continue this task'
    await view.act('update')
    assert.equal(mutations('update').length, 1)
    assert.deepEqual(Array.from(mutations('update')[0]!.args), ['session-a', 'task', 'Continue this task'])
    assert.equal(view.messageDraft.value, '')
  })
}

for (const state of ['cancelled', 'lost'] as const) {
  test(`a ${state} task cannot receive an update`, async t => {
    const { state: view, mutations } = resultsFixture(t, nativeDetail(state))
    await flush()
    assert.equal(view.canUpdate.value, false)
    view.messageDraft.value = 'Do not submit this'
    await view.act('update')
    assert.equal(mutations().length, 0)
    assert.equal(view.messageDraft.value, 'Do not submit this')
  })
}

for (const action of ['update', 'cancel'] as const) {
  test(`${action} failure preserves the task and message draft while suppressing duplicate actions`, async t => {
    const { state, handlers, mutations } = resultsFixture(t, nativeDetail('running'))
    await flush()
    state.messageDraft.value = '  Keep this follow-up\n'
    const gate = deferred()
    handlers[action] = () => gate.promise
    const pending = state.act(action)
    assert.equal(state.busy.value, action)
    await state.act(action)
    await state.act(action === 'update' ? 'cancel' : 'update')
    assert.equal(mutations().length, 1)
    gate.reject(new Error('remote task unavailable'))
    await pending
    assert.equal(state.actionError.value, 'remote task unavailable')
    assert.equal(state.busy.value, '')
    assert.equal(state.detail.value.state, 'running')
    assert.equal(state.messageDraft.value, '  Keep this follow-up\n')
    handlers[action] = async () => undefined
    await state.act(action)
    assert.equal(mutations(action).length, 2, 'a settled failure permits an explicit retry')
  })
}

for (const mode of ['legacy', 'read-only', 'missing-permission'] as const) {
  test(`${mode} work never calls native mutation APIs`, async t => {
    const detail = nativeDetail()
    if (mode === 'legacy') {
      detail.kind = 'shell'
      detail.result = { display_type: 'shell_exec', stdout: 'Old result', stderr: '' } as any
    } else if (mode === 'read-only') detail.read_only = true
    else delete detail.read_only
    const { state, mutations } = resultsFixture(t, detail)
    await flush()
    state.messageDraft.value = 'Follow up'
    state.responseDrafts.value = { 'interrupt-a': 'false', 'interrupt-b': 'null' }
    await state.act('update'); await state.act('resume'); await state.act('cancel')
    assert.equal(mutations().length, 0)
  })
}

test('failed refresh preserves the last task snapshot and unsubmitted JSON drafts', async t => {
  const { state, setRead } = resultsFixture(t)
  await flush()
  state.messageDraft.value = 'Still editing'
  state.responseDrafts.value = { 'interrupt-a': 'false', 'interrupt-b': '{' }
  setRead(async () => { throw new Error('status read failed') })
  await state.refreshDetail()
  assert.equal(state.detail.value.state, 'waiting')
  assert.equal(state.messageDraft.value, 'Still editing')
  assert.equal(state.responseDrafts.value['interrupt-b'], '{')
})

for (const key of ['sessionId', 'ownerKey'] as const) {
  test(`a late detail read cannot overwrite a different ${key}`, async t => {
    const gate = deferred()
    let reads = 0
    const next = { ...nativeDetail('succeeded'), title: 'New context' }
    const { state, props, changed } = resultsFixture(t, nativeDetail(), () => ++reads === 1 ? gate.promise : Promise.resolve(next))
    props[key] = `${key}-new`
    await nextTick(); await flush()
    assert.equal(state.detail.value.title, 'New context')
    state.messageDraft.value = 'New context draft'
    gate.resolve(nativeDetail())
    await flush()
    assert.equal(state.detail.value.title, 'New context')
    assert.equal(state.messageDraft.value, 'New context draft')
    assert.equal(state.loading.value, false)
    assert.equal(changed.length, 0)
  })
}

for (const scenario of [
  { action: 'resume', key: 'ownerKey', rejects: false },
  { action: 'update', key: 'sessionId', rejects: true },
  { action: 'cancel', key: 'sessionId', rejects: false },
] as const) {
  test(`late ${scenario.action} ${scenario.rejects ? 'failure' : 'success'} is ignored after ${scenario.key} changes`, async t => {
    const { state, props, handlers, changed, calls, setDetail } = resultsFixture(t,
      nativeDetail(scenario.action === 'resume' ? 'waiting' : 'running'))
    await flush()
    state.messageDraft.value = 'Old message'
    state.responseDrafts.value = { 'interrupt-a': 'false', 'interrupt-b': 'null' }
    const gate = deferred()
    handlers[scenario.action] = () => gate.promise
    const pending = state.act(scenario.action)
    setDetail({ ...nativeDetail(), title: 'New context' })
    props[scenario.key] = `${scenario.key}-new`
    await nextTick(); await flush()
    assert.equal(state.detail.value.title, 'New context')
    assert.equal(state.busy.value, '')
    state.messageDraft.value = 'New message'
    state.responseDrafts.value = { 'interrupt-a': 'true', 'interrupt-b': '{"new":true}' }
    if (scenario.rejects) gate.reject(new Error('old request failed'))
    else gate.resolve()
    await pending; await flush()
    assert.equal(state.detail.value.title, 'New context')
    assert.equal(state.messageDraft.value, 'New message')
    assert.equal(state.responseDrafts.value['interrupt-a'], 'true')
    assert.equal(state.responseDrafts.value['interrupt-b'], '{"new":true}')
    assert.equal(state.notice.value, '')
    assert.equal(state.actionError.value, '')
    assert.equal(changed.length, 0)
    assert.equal(calls.filter(call => call.action === 'get').length, 2, 'an old mutation must not refresh the new context')
    assert.equal(state.canResume.value, true, 'old resumed IDs must not mark the new owner snapshot as submitted')
  })
}

test('unmounting ignores a mutation completion and does not restart polling', async t => {
  const { state, handlers, close, calls, changed } = resultsFixture(t, nativeDetail('running'))
  await flush()
  state.messageDraft.value = 'Follow-up'
  const gate = deferred()
  handlers.update = () => gate.promise
  const pending = state.act('update')
  close()
  gate.resolve()
  await pending; await flush()
  t.mock.timers.tick(10000)
  await flush()
  assert.equal(changed.length, 0)
  assert.equal(calls.filter(call => call.action === 'get').length, 1)
})
