import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import { fixture } from '../../../test-utils/vueFixture.ts'
import { buildReferenceList, mergeDocumentReferences } from '../../../utils/referenceSources.ts'

const source = readFileSync(new URL('./AgentStreamDisplay.vue', import.meta.url), 'utf8')
const drawer = source.slice(source.indexOf('const getReferencesForDrawer ='), source.indexOf('const cleanToolOutputContent ='))
const references = source.slice(source.indexOf('const isMcpTool ='), source.indexOf('configureMarkedForChatMarkdown();'))
const clicks = source.slice(source.indexOf('const handleActionHeaderClick ='), source.indexOf('// Delegated handlers for span-based citation'))
const code = ts.transpileModule(`${drawer}\n${references}\n${clicks}\n({ openReferencesDrawer, handleActionHeaderClick, handleActionCardClick, hasExpandableResults })`, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText

function setup(items: any[] = []) {
  const props = vue.reactive({ session: { id: 'answer-1', knowledge_references: items } })
  const calls: any[] = [], expanded: string[] = []
  const state = vm.runInNewContext(code, {
    props, mergeDocumentReferences,
    referencesDrawer: { open: (options: any) => calls.push(options), toggle: (options: any) => calls.push(options) },
    toggleEvent: (id: string) => expanded.push(id),
  })
  return { state, props, calls, expanded }
}

test('live and restored knowledge.search steps expand their complete output while citations retain readable source names', async t => {
  const runtime = fixture(t), require = createRequire(import.meta.url)
  const { useChatStreamHandler } = runtime.evaluate(readFileSync(new URL('../../../composables/useChatStreamHandler.ts', import.meta.url), 'utf8'), {
    vue, 'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
  }, id => require(fileURLToPath(new URL('../../../' + id.slice(2) + '.ts', import.meta.url))))
  const reference = { id: 'chunk-1', knowledge_id: 'doc-1', knowledge_base_id: 'kb-1',
    knowledge_title: 'doc-source.md', document_display_name: '采购明细.md', content: '原始证据' }
  for (const mode of ['live', 'history']) {
    const toolName = 'knowledge.search'
    const messagesList = vue.reactive<any[]>([])
    const handler = useChatStreamHandler({
      messagesList, loading: vue.ref(false), isReplying: vue.ref(false),
      currentAssistantMessageId: vue.ref(''), fullContent: vue.ref(''),
      isAgentStreamSession: () => true, scrollToBottom() {},
    })
    const native = { results: [{ chunk_id: reference.id, document_id: reference.knowledge_id,
      knowledge_base_id: reference.knowledge_base_id, document_name: reference.knowledge_title,
      content: '完整返回正文。'.repeat(200) }] }
    const result = { tool_call_id: 'search-1', tool_name: toolName, success: true, output: JSON.stringify(native) }
    if (mode === 'live') {
      handler.processStreamChunk({ response_type: 'agent_query', id: 'r1', assistant_message_id: 'answer-1' })
      handler.processStreamChunk({ response_type: 'tool_call', id: 'r1', data: { tool_call_id: result.tool_call_id, tool_name: toolName, arguments: {} } })
      handler.processStreamChunk({ response_type: 'tool_result', id: 'r1', data: { ...result, data: native } })
      handler.processStreamChunk({ response_type: 'references', id: 'r1', data: { references: [reference] } })
    } else {
      await handler.handleMsgList([{ id: 'answer-1', role: 'assistant', is_completed: true, knowledge_references: [reference],
        agent_steps: [{ iteration: 1, tool_calls: [{ id: result.tool_call_id, name: toolName, args: {},
          result: { ...result, data: { ...native, ...result } } }] }] }])
    }
    const message = messagesList[0], event = message.agentEventStream.find((item: any) => item.type === 'tool_call')
    assert.ok(event, `${mode} reconstructs the actual tool step`)
    const f = setup()
    f.props.session = message
    f.state.handleActionHeaderClick(event)
    assert.deepEqual(f.expanded, ['search-1'], `${mode} expands the result inside its step`)
    assert.equal(f.state.hasExpandableResults(event), true)
    f.state.handleActionCardClick(event)
    assert.equal(f.calls.length, 0, 'tool steps never open the source panel')
    assert.equal(event.output, result.output)
    const highlight = { chunkId: reference.id, knowledgeBaseId: reference.knowledge_base_id, openSource: true }
    assert.equal(f.state.openReferencesDrawer(highlight), true)
    assert.equal(f.calls.length, 1)
    assert.equal(buildReferenceList(f.calls[0].references)[0].title, '采购明细.md')
    assert.equal(f.calls[0].references[0].knowledge_title, reference.knowledge_title)
    assert.equal(f.calls[0].highlight, highlight)
  }
})

test('knowledge.search keeps empty, graph and failed responses available inside the step', () => {
  for (const response of [
    { success: true, output: '{"results":[]}' },
    { success: true, output: '{"chunks":[{"type":"graph_context","content":"关系上下文"}]}' },
    { success: false, output: '检索失败：连接超时' },
  ]) {
    const f = setup([{ id: 'chunk-1', knowledge_id: 'doc-1', knowledge_base_id: 'kb-1', document_display_name: '采购明细.md' }])
    const event = { tool_name: 'knowledge.search', tool_call_id: 'search-1', tool_data: {}, ...response }
    f.state.handleActionHeaderClick(event)
    assert.deepEqual(f.expanded, ['search-1'])
    assert.equal(f.state.hasExpandableResults(event), true)
    assert.equal(f.calls.length, 0)
    assert.equal(event.output, response.output)
  }
})
