import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from 'vue/server-renderer'
import { fixture, flush } from '../../../test-utils/vueFixture'
import { isBackgroundWorkActive } from '../../../utils/backgroundWork'

const file = new URL('./BackgroundWorkChip.vue', import.meta.url)
const dependencies = {
  'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
  '@/utils/backgroundWork': { isBackgroundWorkActive },
}
const native = (state = 'running') => ({ work_id: 'task', kind: 'async_subagent', state, title: 'research', read_only: false, can_cancel: true })

for (const rejected of [false, true]) {
  test(`cancel button re-enables when request settles (${rejected ? 'failure' : 'success'})`, async t => {
    let finish!: () => void
    let fail!: (reason: Error) => void
    let calls = 0
    const props = {
      items: [native()],
      cancelWork: () => {
        calls++
        return new Promise<void>((resolve, reject) => { finish = resolve; fail = reject })
      },
    }
    const mounted = fixture(t).component(file, dependencies, props)
    await flush()
    const state = mounted.vm.$.exposed
    const pending = state.onCancel('task')
    assert.equal(state.cancelling.value.has('task'), true)
    await state.onCancel('task')
    assert.equal(calls, 1, 'duplicate clicks are suppressed while pending')
    if (rejected) fail(new Error('HTTP 503'))
    else finish()
    await pending
    assert.equal(props.items[0]!.state, 'running', 'failed requests retain the last server state')
    assert.equal(state.cancelling.value.has('task'), false)
    assert.equal(state.cancelError.value, rejected ? 'HTTP 503' : '')
    const retry = state.onCancel('task')
    assert.equal(calls, 2)
    finish()
    await retry
  })
}

test('terminal, queued and waiting tasks render as viewable rows while legacy shell remains read only', async t => {
  const fx = fixture(t)
  const script = compileScript(parse(readFileSync(file, 'utf8')).descriptor, { id: 'background-work-chip', inlineTemplate: true }).content
  const component = fx.evaluate(script, { vue, ...dependencies }).default
  const app = vue.createSSRApp(component, { items: [native('succeeded'), { ...native('pending'), work_id: 'queued' },
    { ...native('waiting'), work_id: 'human' }, { work_id: 'legacy', kind: 'shell', state: 'running', title: '<shell>' }], cancelWork: async () => {} })
  app.config.globalProperties.$t = (key: string) => key
  app.component('t-popup', { setup: (_props: any, { slots }: any) => () => vue.h('div', [slots.default?.(), slots.content?.()]) })
  const html = await renderToString(app)
  assert.equal((html.match(/role="listitem"/g) ?? []).length, 4, 'finished tasks remain accessible')
  for (const state of ['succeeded', 'pending', 'waiting']) assert.match(html, new RegExp(`chat.backgroundWork.states.${state}`))
  assert.equal((html.match(/class="work-stop"/g) ?? []).length, 2, 'only queued and waiting native tasks are cancellable')
  assert.match(html, /&lt;shell&gt;/, 'task titles render as escaped text')
})

test('legacy and completed rows never dispatch native cancellation and still open their output', async t => {
  let calls = 0
  const views: string[] = []
  const mounted = fixture(t).component(file, dependencies, {
    items: [{ ...native('succeeded'), work_id: 'finished' }, { ...native(), kind: 'shell', work_id: 'legacy' }],
    cancelWork: async () => { calls++ }, onView: (id: string) => views.push(id),
  })
  await flush()
  const state = mounted.vm.$.exposed
  await state.onCancel('finished'); await state.onCancel('legacy')
  state.openOutput('finished')
  assert.equal(calls, 0)
  assert.deepEqual(views, ['finished'])
})

test('a late cancellation cannot change the next owner or clear their pending request', async t => {
  const requests: Array<{ resolve: () => void; reject: (error: Error) => void }> = []
  const mounted = fixture(t).component(file, dependencies, { items: [native()], scopeKey: 'owner-A:session',
    cancelWork: () => new Promise<void>((resolve, reject) => requests.push({ resolve, reject })),
  })
  await flush()
  const state = mounted.vm.$.exposed
  const first = state.onCancel('task')
  mounted.vm.$.props.scopeKey = 'owner-B:session'
  await vue.nextTick()
  const second = state.onCancel('task')
  requests[0]!.reject(new Error('old owner failure'))
  await first
  assert.equal(state.cancelError.value, '')
  assert.equal(state.cancelling.value.has('task'), true)
  requests[1]!.resolve()
  await second
  assert.equal(state.cancelling.value.has('task'), false)
})
