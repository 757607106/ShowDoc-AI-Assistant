import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { runInNewContext } from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import { createRenderer, h, KeepAlive, nextTick, reactive, ref } from 'vue'

const require = createRequire(import.meta.url)
async function flush() { for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve)); await nextTick() }

async function fixture(name: 'Compile' | 'Issues', overrides: Record<string, any> = {}, canEdit = true, keepAlive = false) {
  const filename = fileURLToPath(new URL(`./ContextDBWiki${name}.vue`, import.meta.url))
  const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
  const script = compileScript(descriptor, { id: `wiki-${name}-test` }).content.replace(/__expose\([^\n;]*\);?/g, '').replace('return __returned__', '__expose(__returned__); return __returned__')
  const compiled = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const calls: { name: string; args: any[] }[] = [], timers = new Map<number, () => unknown>(), listeners = new Map<string, () => void>(), windowListeners = new Map<string, (event: any) => void>()
  const guards: (() => boolean)[] = [], updateGuards: ((to: any, from: any) => boolean)[] = [], warnings: string[] = []
  let timerId = 0, key = 0
  const handlers: Record<string, (...args: any[]) => any> = {
    listWikiCompileRuns: async () => ({ items: [], summary: {}, wiki_compile_paused: false }),
    controlWikiCompileRuns: async () => ({}), getWikiEvent: async () => ({ status: 'SUCCEEDED' }),
    listWikiIssues: async () => ({ items: [], total: 0 }),
    getWikiIssue: async (_kb: string, id: string) => ({ issue_id: id, page_id: 'page-1', version: 7, status: 'pending', evidence: { old: [{ quote: '旧版说明', document_id: 'old-doc' }], new: [{ quote: '新版说明', document_id: 'new-doc' }] } }),
    actOnWikiIssue: async () => ({}), createWikiIssueTask: async () => ({ event_id: 'task-1' }),
    getWikiIssueTask: async () => ({ event_id: 'task-1', status: 'succeeded', total_items: 1, succeeded_items: 1, failed_items: 0, items: [{ issue_id: 'issue-1', status: 'succeeded', resolution_revision_id: 'revision-1' }] }),
    getWikiPage: async () => ({ page_id: 'page-1', published: true, version: 14, head_revision_id: 'revision-1' }),
    getDocument: async (id: string) => ({ data: { file_name: `文档 ${id}` } }),
    ...overrides,
  }
  const api = Object.fromEntries(Object.keys(handlers).map(name => [name, async (...args: any[]) => { calls.push({ name, args }); return handlers[name](...args) }]))
  const doc = { visibilityState: 'visible', addEventListener: (name: string, fn: () => void) => listeners.set(name, fn), removeEventListener: (name: string) => listeners.delete(name) }
  const exports: any = {}
  runInNewContext(compiled, {
    exports, document: doc, crypto: { randomUUID: () => `request-${++key}` },
    window: { addEventListener: (name: string, fn: (event: any) => void) => windowListeners.set(name, fn), removeEventListener: (name: string) => windowListeners.delete(name) },
    setTimeout: (fn: () => unknown) => { timers.set(++timerId, fn); return timerId }, clearTimeout: (id: number) => timers.delete(id),
    require(name: string) {
      if (name === 'vue') return require(name)
      if (name === '@/stores/auth') return { useAuthStore: () => ({ hasRole: () => canEdit }) }
      if (name === 'vue-router') return { onBeforeRouteLeave: (guard: () => boolean) => guards.push(guard), onBeforeRouteUpdate: (guard: (to: any, from: any) => boolean) => updateGuards.push(guard) }
      if (name === 'tdesign-vue-next') return { MessagePlugin: { warning: (message: string) => warnings.push(message) } }
      if (name === '@/api/contextdbWiki' || name === '@/api/contextdb') return api
      if (name === '@/utils/platformPresentation') return { dateTime: (v: unknown) => v || '—' }
      if (name === '@/utils/contextdbDocumentName') return require('../../../utils/contextdbDocumentName.ts')
      throw new Error(`Unexpected dependency: ${name}`)
    },
  })
  exports.default.render = () => null
  const renderer = createRenderer<any, any>({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}), insert() {}, remove() {}, setElementText() {}, setText() {}, patchProp() {}, parentNode: () => null, nextSibling: () => null,
  })
  const props = reactive({ kbId: 'kb-1', canEdit }), child = ref<any>(), visible = ref(true)
  const app = renderer.createApp({ render: () => keepAlive ? h(KeepAlive, null, { default: () => visible.value ? h(exports.default, { ...props, ref: child }) : null }) : h(exports.default, { ...props, ref: child }) })
  app.mount({}); await flush()
  return { vm: child.value as any, props, calls, timers, doc, handlers, guards, updateGuards, windowListeners, warnings,
    async tick() { const current = [...timers.values()]; timers.clear(); for (const fn of current) await fn(); await flush() },
    hide() { doc.visibilityState = 'hidden'; listeners.get('visibilitychange')?.() },
    show() { doc.visibilityState = 'visible'; listeners.get('visibilitychange')?.() },
    async deactivate() { visible.value = false; await flush() },
    async activate() { visible.value = true; await flush() },
    close() { app.unmount() },
  }
}

test('compile pagination keeps its status and source names use four requests at a time with a cache', async () => {
  let inFlight = 0, peak = 0
  const f = await fixture('Compile', {
    listWikiCompileRuns: async (_kb: string, query: any) => ({ items: Array.from({ length: 9 }, (_, i) => ({ document_id: String(i), document_name: `doc-${i}.md`, run_state: 'pending' })), summary: { total: 9, pending: 9 }, next_cursor: query.cursor ? null : 'next-sources', wiki_compile_paused: false }),
    getDocument: async (id: string) => { inFlight++; peak = Math.max(peak, inFlight); await new Promise(resolve => setImmediate(resolve)); inFlight--; return { data: { file_name: `来源 ${id}` } } },
  })
  try {
    assert.equal(peak, 4); assert.equal(f.vm.rows[0].document_display_name, '来源 0')
    assert.equal(f.vm.rows[0].document_name, 'doc-0.md')
    f.vm.status = 'pending'; await flush(); await f.vm.load(true)
    const query = f.calls.filter(call => call.name === 'listWikiCompileRuns').at(-1)!.args[1]
    assert.equal(query.status, 'pending'); assert.equal(query.cursor, 'next-sources')
    await f.tick(); assert.equal(f.calls.filter(call => call.name === 'getDocument').length, 9)
    assert.equal(f.vm.rows[0].document_display_name, '来源 0', 'polling must retain the cached readable name')
    assert.equal(f.vm.rows[0].document_name, 'doc-0.md')
    assert.ok(f.timers.size > 0); f.hide(); assert.equal(f.timers.size, 0)
    f.show(); assert.ok(f.timers.size > 0)
  } finally { f.close() }
  assert.equal(f.timers.size, 0)
})

test('enriched compile names avoid redundant detail requests and retain source identities', async () => {
  const f = await fixture('Compile', {
    listWikiCompileRuns: async () => ({ items: [{ document_id: 'source-a', document_name: 'doc-hash.html', document_display_name: '采购明细.html', run_state: 'compiled' }], summary: {}, wiki_compile_paused: false }),
  })
  try {
    assert.equal(f.vm.rows[0].document_display_name, '采购明细.html')
    assert.equal(f.vm.rows[0].document_name, 'doc-hash.html')
    assert.equal(f.calls.filter(call => call.name === 'getDocument').length, 0)
    await f.vm.load()
    assert.equal(f.vm.rows[0].document_display_name, '采购明细.html')
  } finally { f.close() }
})

test('compile controls check the accepted event then reread the source state', async () => {
  let paused = false
  const f = await fixture('Compile', {
    controlWikiCompileRuns: async () => { paused = true; return { event_id: 'event-1' } },
    listWikiCompileRuns: async () => ({ items: [], summary: {}, wiki_compile_paused: paused }),
  })
  try {
    await f.vm.control('pause')
    assert.equal(f.vm.paused, true)
    const calls = f.calls.map(call => call.name)
    assert.deepEqual(calls.slice(-3), ['controlWikiCompileRuns', 'getWikiEvent', 'listWikiCompileRuns'])
    assert.match(f.vm.notice, /在途任务/)
    assert.equal(f.vm.event.status, 'SUCCEEDED')
  } finally { f.close() }
})

test('a late compile response cannot replace another knowledge base or restart polling after unmount', async () => {
  let resolve: (value: any) => void = () => {}
  const f = await fixture('Compile')
  try {
    f.handlers.listWikiCompileRuns = () => new Promise(done => { resolve = done })
    const loading = f.vm.load(), complete = resolve
    f.handlers.listWikiCompileRuns = async () => ({ items: [], summary: {}, wiki_compile_paused: false })
    f.props.kbId = 'kb-2'; await nextTick()
    complete({ items: [{ document_id: 'old', run_state: 'pending' }], summary: { pending: 1 } })
    await loading; await flush(); assert.equal(f.vm.rows.length, 0)
  } finally { f.close() }
  assert.equal(f.timers.size, 0)
})

test('read only viewers cannot submit compile actions or issue decisions', async () => {
  const compile = await fixture('Compile', {}, false), issues = await fixture('Issues', {}, false)
  try {
    await compile.vm.control('pause'); await issues.vm.openIssue({ issue_id: 'issue-1' }); await issues.vm.submitTask(); await issues.vm.changeStatus('ignore')
    assert.equal(compile.calls.filter(call => call.name === 'controlWikiCompileRuns').length, 0)
    assert.equal(issues.calls.filter(call => ['createWikiIssueTask', 'actOnWikiIssue'].includes(call.name)).length, 0)
  } finally { compile.close(); issues.close() }
})

test('a cached compile panel resumes after an in-flight request was deactivated', async () => {
  const f = await fixture('Compile', {}, true, true)
  let complete: (value: any) => void = () => {}
  try {
    f.handlers.listWikiCompileRuns = () => new Promise(resolve => { complete = resolve })
    const pending = f.vm.load(); await f.deactivate()
    complete({ items: [{ document_id: 'old', run_state: 'pending' }], summary: { pending: 1 } }); await pending
    assert.equal(f.vm.rows.length, 0); assert.equal(f.timers.size, 0)
    f.handlers.listWikiCompileRuns = async () => ({ items: [{ document_id: 'new', run_state: 'compiled' }], summary: { compiled: 1 }, wiki_compile_paused: false })
    await f.activate(); assert.equal(f.vm.rows[0].document_id, 'new'); assert.equal(f.vm.loading, false)
  } finally { f.close() }
})

test('issue evidence uses the issue version and identical uncertain submissions reuse their idempotency key', async () => {
  let accepted = false
  const f = await fixture('Issues', { createWikiIssueTask: async () => { if (!accepted) throw new Error('网络结果待确认'); return { event_id: 'task-1' } } })
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' }); f.vm.choice = 'use_new'
    assert.equal(f.vm.evidenceGroups[0][1][0].document_id, 'old-doc')
    await f.vm.submitTask(); await f.vm.submitTask()
    const submissions = f.calls.filter(call => call.name === 'createWikiIssueTask')
    assert.equal(submissions[0].args[1].idempotency_key, submissions[1].args[1].idempotency_key)
    assert.equal(submissions[0].args[1].items[0].expected_version, 7)
    await f.vm.openIssue({ issue_id: 'issue-1' }); f.vm.choice = 'use_new'; await f.vm.submitTask()
    assert.equal(f.calls.filter(call => call.name === 'createWikiIssueTask').at(-1)!.args[1].idempotency_key, submissions[0].args[1].idempotency_key)
    f.vm.note = '新版手册适用'; await f.vm.submitTask()
    assert.notEqual(f.calls.filter(call => call.name === 'createWikiIssueTask').at(-1)!.args[1].idempotency_key, submissions[0].args[1].idempotency_key)
    accepted = true; await f.vm.submitTask()
    assert.equal(f.vm.task.status, 'succeeded'); assert.match(f.vm.pageCheck, /正式正文可读/)
    assert.ok(f.calls.some(call => call.name === 'getWikiPage'))
  } finally { f.close() }
})

test('uncertain evidence only permits a nonempty manual correction and status actions carry the issue version', async () => {
  const f = await fixture('Issues', { getWikiIssue: async () => ({ issue_id: 'issue-1', page_id: 'page-1', version: 7, status: 'pending', body: { recheck_uncertain: true } }) })
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' })
    assert.equal(f.vm.choice, 'manual_edit'); assert.equal(f.vm.choiceOptions.length, 1)
    f.vm.choice = 'use_new'; await f.vm.submitTask(); assert.match(f.vm.detailError, /人工复核/)
    f.vm.choice = 'manual_edit'; await f.vm.submitTask(); assert.match(f.vm.detailError, /填写修订正文/)
    assert.equal(f.calls.filter(call => call.name === 'createWikiIssueTask').length, 0)
    await f.vm.changeStatus('ignore')
    assert.equal(f.calls.find(call => call.name === 'actOnWikiIssue')!.args[1].expected_version, 7)
    assert.match(f.vm.notice, /正文没有改变/)
  } finally { f.close() }
})

test('issue polling stops while hidden and reads per item failures without claiming a page update', async () => {
  let done = false
  const f = await fixture('Issues', { getWikiIssueTask: async () => done ? { event_id: 'task-1', status: 'failed', total_items: 1, failed_items: 1, items: [{ issue_id: 'issue-1', status: 'failed', error_message: '来源已变化' }] } : { event_id: 'task-1', status: 'running', items: [] } })
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' }); await f.vm.submitTask()
    assert.equal(f.vm.taskPending, true); assert.equal(f.timers.size, 1)
    f.hide(); assert.equal(f.timers.size, 0); done = true; f.show(); await f.tick()
    assert.equal(f.vm.task.failed_items, 1); assert.equal(f.vm.task.items[0].error_message, '来源已变化')
    assert.equal(f.vm.pageCheck, ''); assert.equal(f.calls.filter(call => call.name === 'getWikiPage').length, 0)
    assert.equal(f.timers.size, 0)
  } finally { f.close() }
})

test('issue corrections survive evidence refresh and block closing, switching issues and route changes until explicitly discarded', async () => {
  const f = await fixture('Issues')
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' }); f.vm.choice = 'manual_edit'; f.vm.manualContent = '核对后的完整修订'; f.vm.note = '保留适用范围'
    await f.vm.openIssue({ issue_id: 'issue-1' })
    assert.equal(f.vm.manualContent, '核对后的完整修订'); assert.equal(f.vm.note, '保留适用范围')
    f.vm.closeDrawer(false); assert.equal(f.vm.drawer, true)
    await f.vm.openIssue({ issue_id: 'issue-2' }); assert.equal(f.vm.detail.issue_id, 'issue-1')
    assert.equal(f.guards[0](), false); assert.equal(f.updateGuards[0]({ fullPath: '/next' }, { fullPath: '/current' }), false)
    const unload = { prevented: false, returnValue: null, preventDefault() { this.prevented = true } }
    f.windowListeners.get('beforeunload')!(unload); assert.equal(unload.prevented, true)
    f.vm.cancelDraft(); assert.equal(f.vm.draftDirty, false); assert.equal(f.guards[0](), true)
    f.vm.closeDrawer(false); assert.equal(f.vm.drawer, false)
    await f.vm.openIssue({ issue_id: 'issue-2' }); assert.equal(f.vm.detail.issue_id, 'issue-2')
  } finally { f.close() }
  assert.equal(f.windowListeners.size, 0)
})

test('accepted issue tasks block closing and discard until their final result is read', async () => {
  const f = await fixture('Issues', { getWikiIssueTask: async () => ({ event_id: 'task-1', status: 'running', items: [] }) })
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' }); f.vm.choice = 'manual_edit'; f.vm.manualContent = '修订内容'; await f.vm.submitTask()
    f.vm.closeDrawer(false); f.vm.cancelDraft(); assert.equal(f.vm.drawer, true); assert.equal(f.vm.manualContent, '修订内容')
    assert.equal(f.guards[0](), false)
    f.handlers.getWikiIssueTask = async () => ({ event_id: 'task-1', status: 'succeeded', items: [{ issue_id: 'issue-1', status: 'succeeded', resolution_revision_id: 'revision-1' }] })
    await f.vm.refreshTask(); assert.equal(f.vm.draftDirty, false); assert.equal(f.guards[0](), true)
  } finally { f.close() }
})

test('changing compile filters preserves an in-flight write lock and accepted event tracking', async () => {
  let complete: (value: any) => void = () => {}
  const f = await fixture('Compile', {
    controlWikiCompileRuns: () => new Promise(resolve => { complete = resolve }),
    getWikiEvent: async () => ({ status: 'RUNNING' }),
  })
  try {
    const pending = f.vm.control('recompile_affected', { document_id: 'source-1' })
    f.vm.status = 'pending'; await flush(); assert.equal(f.vm.busy, true)
    await f.vm.control('recompile_affected', { document_id: 'source-1' })
    assert.equal(f.calls.filter(call => call.name === 'controlWikiCompileRuns').length, 1)
    complete({ event_id: 'compile-event' }); await pending
    f.vm.status = 'compiled'; await flush(); assert.equal(f.vm.event.id, 'compile-event'); assert.equal(f.vm.eventPending, true)
  } finally { f.close() }
})

test('a successful issue task with a stale published page preserves its correction draft', async () => {
  const f = await fixture('Issues', { getWikiPage: async () => ({ page_id: 'page-1', published: true, version: 3, head_revision_id: 'old-revision' }) })
  try {
    await f.vm.openIssue({ issue_id: 'issue-1' }); f.vm.choice = 'manual_edit'; f.vm.manualContent = '应发布的新正文'; await f.vm.submitTask()
    assert.equal(f.vm.task.status, 'succeeded'); assert.equal(f.vm.manualContent, '应发布的新正文'); assert.equal(f.vm.draftDirty, true)
    assert.match(f.vm.pageCheck, /尚未与处理结果核对一致/)
  } finally { f.close() }
})
