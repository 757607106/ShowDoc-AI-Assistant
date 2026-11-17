import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive, ref } from 'vue'
import { fixture, flush } from '../../../test-utils/vueFixture'

function interaction(t: Parameters<typeof fixture>[0], file: string, props: Record<string, unknown>, fail = false) {
  const submissions = reactive(new Map()), calls: any[] = []
  const { vm } = fixture(t).component(new URL(file, import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error() {}, success() {} } },
    '@/api/mcp-service': {
      resolveToolApproval: async (...args: any[]) => { calls.push(args); return { resumed: false } },
      resolveAgentPrompt: async (...args: any[]) => { calls.push(args); if (fail) throw new Error('schema rejected'); return { resumed: false } },
    },
    '@/api/embed': { resolveEmbedToolApproval: async () => assert.fail('unexpected embed approval') },
    '@/utils/suspendedRun': { resumeSuspendedRunKey: Symbol('resume'), promptSubmissionTransportKey: Symbol('prompt-transport') },
    '@/composables/usePromptCountdown': { usePromptCountdown: () => ({ parked: ref(false), secondsLeft: ref(-1) }) },
    '@/composables/usePromptDock': {
      usePromptDock: () => undefined,
      promptSubmission: (id: string) => submissions.get(id),
      markPromptSubmitted: (id: string, value: unknown) => submissions.set(id, value),
    },
    '@/utils/promptKeys': { isSubmitKey: (event: any) => event.key === 'Enter' },
  }, { pendingId: 'session:interrupt:0', serviceName: 'change', mcpToolName: 'change', ...props })
  return { vm, calls, submissions }
}

test('approval exposes only allowed decisions and approval preserves the original arguments', async t => {
  const { vm, calls } = interaction(t, './ToolApprovalCard.vue', { allowedDecisions: ['approve'], argsJson: '{"value":1}' })
  assert.equal(vm.canDecide('edit'), false)
  assert.equal(vm.canDecide('respond'), false)
  vm.argsText = '{"value":2}'
  await vm.submit('edit'); assert.equal(calls.length, 0)
  await vm.submit('approve')
  assert.equal(calls[0][1].decision, 'approve')
  assert.equal(calls[0][1].modified_args, undefined)
})

test('edit accepts object arguments and respond submits text without executing the original tool', async t => {
  const edit = interaction(t, './ToolApprovalCard.vue', { allowedDecisions: ['edit'], argsJson: '{}' })
  edit.vm.argsText = '[]'; await edit.vm.submit('edit'); assert.equal(edit.calls.length, 0)
  edit.vm.argsText = '{"value":2}'; await edit.vm.submit('edit')
  assert.deepEqual(JSON.parse(JSON.stringify(edit.calls[0][1].modified_args)), { value: 2 })
  assert.equal(edit.calls[0][1].decision, 'edit')
})

test('respond submits text and prevents repeat submission', async t => {
  const respond = interaction(t, './ToolApprovalCard.vue', { allowedDecisions: ['respond'] })
  respond.vm.responseMessage = 'human result'; await respond.vm.submit('respond')
  assert.equal(respond.calls[0][1].message, 'human result')
  assert.equal(respond.calls[0][1].decision, 'respond')
  await flush(); await respond.vm.submit('respond'); assert.equal(respond.calls.length, 1)
})

for (const value of [false, null, { confirmed: true }]) {
  test('generic interrupt sends the original JSON value: ' + JSON.stringify(value), async t => {
    const { vm, calls } = interaction(t, './NativeInterruptCard.vue', {})
    vm.draft = JSON.stringify(value); await vm.submit()
    assert.equal(calls[0][1], 'native_interrupt')
    assert.deepEqual(JSON.parse(JSON.stringify(calls[0][2])), value)
    await flush(); await vm.submit(); assert.equal(calls.length, 1)
  })
}

test('generic interrupt keeps invalid or rejected drafts available for correction', async t => {
  const { vm, calls, submissions } = interaction(t, './NativeInterruptCard.vue', {}, true)
  vm.draft = '{'; await vm.submit(); assert.equal(calls.length, 0)
  vm.draft = '{"confirmed":false}'; await vm.submit()
  assert.equal(vm.error, 'schema rejected'); assert.equal(vm.draft, '{"confirmed":false}')
  assert.equal(submissions.size, 0)
})
