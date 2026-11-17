import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { fixture, flush } from '../../../test-utils/vueFixture'
import { asyncPromptResponses, isBackgroundWorkActive } from '../../../utils/backgroundWork'
import * as askUser from '../../../utils/askUser'
import * as promptKeys from '../../../utils/promptKeys'
import * as steering from '../../../utils/steerStreamFork'

test('real nested dock and native cards submit to the child task and discard unsent answers on owner change', async t => {
  const fx = fixture(t)
  const transport = fx.evaluate(readFileSync(new URL('../../../utils/suspendedRun.ts', import.meta.url), 'utf8'), {})
  const dock = fx.evaluate(readFileSync(new URL('../../../composables/usePromptDock.ts', import.meta.url), 'utf8'), {
    vue, '@/utils/steerStreamFork': steering,
    '@/composables/useChatStreamHandler': { isAwaitingInput: (row: any) => row?.run_state === 'awaiting_input' },
    '@/views/chat/components/hostApproval': { isHostApprovalEvent: () => false },
  })
  const instances = new Map<string, vue.ComponentInternalInstance[]>()
  const pass = { setup: (_: unknown, { slots }: any) => () => vue.h('div', slots.default?.()) }
  const runtime = { ...vue, Transition: pass, defineComponent(options: any) {
    const setup = options.setup
    options.setup = (props: unknown, context: unknown) => {
      const instance = vue.getCurrentInstance()!
      const list = instances.get(options.__name) ?? []
      list.push(instance); instances.set(options.__name, list)
      return setup(props, context)
    }
    return vue.defineComponent(options)
  } }
  const forbidden = () => assert.fail('a nested async card must not submit to the parent session API')
  const requests: any[][] = []
  const prompts = [
    { pending_id: 'approval', interrupt_id: 'approval-batch', kind: 'tool_approval', action_index: 0,
      action_count: 1, mcp_tool_name: 'write_file', allowed_decisions: ['approve'], args_json: '{"path":"/report.md"}' },
    { pending_id: 'question', interrupt_id: 'question-id', kind: 'ask_user', request: { question: 'Which topic?' } },
    { pending_id: 'typed', interrupt_id: 'typed-id', kind: 'native_interrupt', request: { value: false } },
  ]
  const detail = { work_id: 'child-task', title: 'Research', kind: 'async_subagent', state: 'waiting', read_only: false,
    result: { display_type: 'async_subagent', view_session_id: 'subgraph~signed', output: '',
      interrupts: prompts.map(prompt => ({ id: prompt.interrupt_id, value: {} })), prompts } }
  const dependencies: Record<string, unknown> = {
    vue: runtime, 'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error: forbidden, success() {} } },
    'tdesign-icons-vue-next': { CheckIcon: pass },
    '@/utils/backgroundWork': { asyncPromptResponses, isBackgroundWorkActive },
    '@/utils/suspendedRun': transport, '@/composables/usePromptDock': dock,
    '@/utils/askUser': askUser, '@/utils/promptKeys': { ...promptKeys, isTextEntry: () => false },
    '@/composables/usePromptCountdown': { usePromptCountdown: () => ({ parked: vue.ref(false), secondsLeft: vue.ref(-1) }) },
    '@/api/mcp-service': { resolveToolApproval: forbidden, resolveAgentPrompt: forbidden },
    '@/api/embed': { resolveEmbedToolApproval: forbidden, resolveEmbedAgentPrompt: forbidden },
    '@/components/ChatTimelineIcon.vue': pass,
    './McpOAuthCard.vue': pass, './SecureFormCard.vue': pass,
    './ChildAgentStream.vue': pass, './tool-results/ShellExecResult.vue': pass,
    '@/api/chat/background-work': { getBackgroundWork: async () => detail,
      resumeBackgroundWork: async (...args: any[]) => { requests.push(args) },
      updateBackgroundWork: forbidden, cancelBackgroundWork: forbidden },
  }
  function component(name: string, expose = '') {
    const file = new URL(`./${name}.vue`, import.meta.url)
    let source = readFileSync(file, 'utf8')
    if (expose) source = source.replace(/defineExpose\([^\n]+\)/, '')
      .replace('</script>', `defineExpose({ ${expose} })\n</script>`)
    const script = compileScript(parse(source, { filename: file.pathname }).descriptor,
      { id: name, inlineTemplate: true }).content
    return fx.evaluate(script, dependencies).default
  }
  dependencies['./ToolApprovalCard.vue'] = component('ToolApprovalCard', 'submit')
  dependencies['./AskUserCard.vue'] = component('AskUserCard', 'submit, text')
  dependencies['./NativeInterruptCard.vue'] = component('NativeInterruptCard', 'submit, draft')
  dependencies['./PendingPromptDock.vue'] = component('PendingPromptDock')
  const results = component('BackgroundWorkResults', 'promptSubmissions')
  const props = vue.reactive({ sessionId: 'parent-session', workId: 'child-task', ownerKey: 'owner-a' })
  let parentDock: any
  const host = { setup() {
    parentDock = dock.providePromptDock(vue.reactive([{ role: 'assistant', is_completed: false,
      agentEventStream: [{ ...prompts[0], pending_id: 'parent-approval', type: 'tool_approval_required' }] }]))
    return () => vue.h(results, props)
  } }
  const remove = (node: any) => {
    const siblings = node.parent?.children
    if (siblings) siblings.splice(siblings.indexOf(node), 1)
    node.parent = null
  }
  const renderer = vue.createRenderer<any, any>({
    createElement: () => ({ style: {}, children: [], focus() {} }), createText: () => ({}), createComment: () => ({}),
    insert(node, parent, anchor) {
      remove(node)
      const children = parent.children ??= []
      children.splice(anchor ? children.indexOf(anchor) : children.length, 0, node)
      node.parent = parent
    },
    remove, setElementText() {}, setText() {}, patchProp() {}, parentNode: node => node.parent,
    nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1] ?? null,
  })
  const app = renderer.createApp(host)
  app.config.globalProperties.$t = (key: string) => key
  for (const name of ['t-icon', 't-button', 't-textarea', 't-checkbox', 't-input-number', 't-option', 't-select', 't-input']) app.component(name, pass)
  app.mount({})
  t.after(() => app.unmount())
  await flush()
  const latest = (name: string) => instances.get(name)!.at(-1)!.exposed as any
  await latest('ToolApprovalCard').submit('approve')
  await flush()
  assert.equal(requests.length, 0)
  assert.equal(dock.promptSubmission('approval'), undefined, 'staging stays out of the global parent map')
  assert.equal(latest('BackgroundWorkResults').promptSubmissions.get('approval').decision, 'approve')
  props.ownerKey = 'owner-b'
  await flush()
  assert.equal(latest('BackgroundWorkResults').promptSubmissions.size, 0)
  await latest('ToolApprovalCard').submit('approve')
  const question = latest('AskUserCard')
  question.text.value = 'LangGraph'
  await question.submit(false)
  await flush()
  assert.equal(requests.length, 0, 'all interrupt values are required before a native resume')
  const typed = latest('NativeInterruptCard')
  typed.draft.value = 'false'
  await typed.submit()
  await flush()
  assert.deepEqual(JSON.parse(JSON.stringify(requests)), [[
    'parent-session', 'child-task', { 'approval-batch': { decisions: [{ type: 'approve' }] },
      'question-id': { text: 'LangGraph' }, 'typed-id': false },
  ]])
  assert.equal(parentDock.prompts.value[0].pending_id, 'parent-approval')
  assert.equal(dock.promptSubmission('typed'), undefined)
})
