import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { compileTemplate, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import ts from 'typescript'

const source = readFileSync(new URL('./AgentStreamDisplay.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const compiled = compileTemplate({ source: descriptor.template!.content, filename: 'AgentStreamDisplay.vue', id: 'stop-test' })
assert.deepEqual(compiled.errors, [])
const exports: any = {}
vm.runInNewContext(ts.transpileModule(compiled.code, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, {
  exports,
  require: () => ({ ...vue, resolveComponent: (name: string) => name, resolveDirective: () => ({}), withCtx: (fn: unknown) => fn }),
})

function nodes(node: any): any[] {
  if (!node || typeof node !== 'object') return []
  if (Array.isArray(node)) return node.flatMap(nodes)
  return [node, ...nodes(node.children)]
}
function text(node: any): string {
  if (typeof node === 'string') return node
  if (Array.isArray(node)) return node.map(text).join('')
  return node?.children ? text(node.children) : ''
}
function render(stream: unknown[], stepCount: number) {
  const stop = source.match(/const wasUserStopped = .*;/)![0]
  const collapse = source.slice(source.indexOf('const shouldShowCollapsedSteps ='), source.indexOf('const isThinkingLikeEvent ='))
  const state = vm.runInNewContext(ts.transpile(`${stop}\n${collapse}\n({ wasUserStopped, shouldShowCollapsedSteps })`), {
    computed: vue.computed, eventStream: vue.ref(stream), props: { ragMode: false },
    intermediateStepsCount: vue.ref(stepCount), timelineCompleted: vue.ref(true),
  })
  return exports.render({
    selectedChild: null, session: {}, embeddedMode: false, ragMode: false,
    shouldShowCollapsedSteps: state.shouldShowCollapsedSteps.value, wasUserStopped: state.wasUserStopped.value,
    showIntermediateSteps: false, intermediateStepsSummaryHtml: '调用 1 次工具', displayEvents: [],
    showAgentActivityIndicator: false, childActivity: null, imagePreviewVisible: false, wikiDrawerVisible: false,
    hasArtifacts: false, citationFloat: {}, t: (key: string) => key === 'input.messages.stopSuccess' ? '已停止生成' : key,
  }, [])
}

test('stopping before any tool or thinking step renders a visible terminal status after reload', () => {
  const rendered = render([{ type: 'stop', reason: 'user_requested' }], 0)
  assert.equal(text(rendered).match(/已停止生成/g)?.length, 1)
  assert.ok(nodes(rendered).some(node => node.props?.role === 'status' && text(node).includes('已停止生成')))
})

test('a stopped tool tree retains one summary without adding another standalone stop row', () => {
  const rendered = render([{ type: 'tool_call', tool_call_id: 't' }, { type: 'stop' }], 1)
  assert.equal(text(rendered).match(/已停止生成/g)?.length, 1)
  assert.ok(!nodes(rendered).some(node => node.props?.role === 'status'))
})

test('an empty or completed execution does not claim the user stopped it', () => {
  for (const stream of [[], [{ type: 'agent_complete' }]]) assert.ok(!text(render(stream, 0)).includes('已停止生成'))
})
