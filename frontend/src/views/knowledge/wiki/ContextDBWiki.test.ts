import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { runInNewContext } from 'node:vm'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { createRenderer, createSSRApp, nextTick, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ts from 'typescript'
import { renderDocumentPreviewMarkdown } from '../../../utils/documentPreviewMarkdown.ts'

const require = createRequire(import.meta.url)
const flush = async () => { await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick() }
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes }); return { promise, resolve } }
const page = (overrides: Record<string, unknown> = {}) => ({ page_id: 'page-a', title: '页面 A', page_type: 'concept', version: 3, published: true, run_state: 'active', content: '正式正文', ...overrides })
async function fixture(options: { directory?: boolean; props?: any; api?: Record<string, (...args: any[]) => Promise<any>> } = {}) {
  const filename = fileURLToPath(new URL(options.directory ? './ContextDBWikiDirectory.vue' : './ContextDBWiki.vue', import.meta.url))
  const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
  const script = compileScript(descriptor, { id: 'native-wiki-test' }).content
    .replace('__expose();', '')
    .replace(/__expose\(\{\s*permitNavigation\s*\}\);?/, '')
    .replace('return __returned__', '__expose(__returned__); return __returned__')
  const compiled = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const calls: { name: string; args: any[] }[] = [], warnings: string[] = [], successes: string[] = []
  const guards: (() => boolean)[] = [], updateGuards: ((to: any, from: any) => boolean)[] = []
  const route = reactive({ query: (options.directory ? {} : { wikiPageId: 'page-a', tab: 'wiki', retained: 'yes' }) as Record<string, string>, fullPath: '/wiki' })
  let remote = page()
  const defaults: Record<string, (...args: any[]) => Promise<any>> = {
    getWikiPage: async () => remote,
    getWikiPageByReference: async () => remote,
    getWikiIndex: async () => ({ intro: '', groups: [] }),
    listWikiPages: async () => ({ items: [], next_cursor: null }),
    searchWikiPages: async () => ({ items: [], total: 0 }),
    updateWikiPage: async (_kb, _id, data) => { remote = page({ content: data.content, version: 4 }); return { version: 4 } },
    createWikiPage: async () => ({ page_id: 'created-page' }),
    createWikiDirectory: async () => ({ page_id: 'created-directory', event_id: 'created-event' }),
    organizeWikiPage: async () => ({ event_id: 'organize-event' }),
    organizeWikiDirectory: async () => ({ event_id: 'organize-event' }),
    deleteWikiPage: async () => ({ event_id: 'delete-event' }),
    getWikiEvent: async () => ({ status: 'SUCCEEDED' }),
    getDocument: async (id: string) => ({ data: { name: `${id}.md` } }),
    ...options.api,
  }
  const api = Object.fromEntries(Object.entries(defaults).map(([name, fn]) => [name, async (...args: any[]) => {
    calls.push({ name, args }); return fn(...args)
  }]))
  const exports: any = {}
  const windowEvents = new Map<string, Function>()
  runInNewContext(compiled, {
    exports, console,
    setTimeout: (callback: (...args: any[]) => void) => setTimeout(callback, 0), clearTimeout,
    window: { addEventListener: (name: string, callback: Function) => windowEvents.set(name, callback), removeEventListener: (name: string) => windowEvents.delete(name) },
    require(name: string) {
      if (name === 'vue') return require(name)
      if (name === 'vue-router') return {
        useRoute: () => route,
        useRouter: () => ({ replace: async (location: any) => {
          if (updateGuards.some(guard => !guard({ fullPath: '/next' }, { fullPath: route.fullPath }))) return
          route.query = location.query
        } }),
        onBeforeRouteLeave: (guard: () => boolean) => guards.push(guard),
        onBeforeRouteUpdate: (guard: (to: any, from: any) => boolean) => updateGuards.push(guard),
      }
      if (name === '@/api/contextdbWiki') return api
      if (name === '@/api/contextdb') return { getDocument: api.getDocument }
      if (name === '@/utils/contextdbDocumentName') return require('../../../utils/contextdbDocumentName.ts')
      if (name === '@/utils/notificationPreview') return require('../../../utils/notificationPreview.ts')
      if (name === '@/utils/security') return require('../../../utils/security.ts')
      if (name === '@/utils/wikiLineDiff') return require('../../../utils/wikiLineDiff.ts')
      if (name === '@/utils/platformPresentation') return require('../../../utils/platformPresentation.ts')
      if (name === 'tdesign-vue-next') return { MessagePlugin: { warning: (message: string) => warnings.push(message), success: (message: string) => successes.push(message), error() {}, info() {} } }
      if (name.endsWith('.vue')) return { default: {} }
      throw new Error(`Unexpected dependency: ${name}`)
    },
  })
  exports.default.render = () => null
  const renderer = createRenderer<any, any>({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}), insert() {}, remove() {},
    setElementText() {}, setText() {}, patchProp() {}, parentNode: () => null, nextSibling: () => null,
  })
  const app = renderer.createApp(exports.default, { kbId: 'kb-a', canEdit: true, ...options.props })
  const vm: any = app.mount({})
  await flush()
  return { vm, calls, warnings, successes, route, guards, updateGuards, windowEvents, remote: (next: any) => { remote = next }, close: () => app.unmount() }
}

test('directory reads only the current level, preserves opaque cursors and loads children lazily', async () => {
  const f = await fixture({ directory: true, api: { listWikiPages: async (_kb, params) => ({
    items: params.cursor ? [page({ page_id: 'page-b' })] : [page({ page_type: 'category' })], next_cursor: params.cursor ? null : 'opaque==cursor',
  }) } })
  try {
    assert.equal(f.calls.length, 1)
    assert.equal(f.calls[0].args[1].parent_page_id, undefined)
    f.vm.toggle('page-a')
    assert.equal(f.calls.length, 1, 'expanding state does not recursively preload the library')
    await f.vm.load(true)
    assert.equal(f.calls[1].args[1].cursor, 'opaque==cursor')
    assert.deepEqual(Array.from(f.vm.items, (item: any) => item.page_id), ['page-a', 'page-b'])
    assert.equal(f.vm.cursor, null)
  } finally { f.close() }
})

test('Wiki directory renders readable summary titles and ordinary directory names in labels and menus', async () => {
  const items = [
    page({ page_id: 'summary-a', page_type: 'summary', title: `doc-${'a'.repeat(64)}.md - Summary`, display_title: '采购单.md - Summary' }),
    page({ page_id: 'directory-a', page_type: 'category', title: '资料目录' }),
  ]
  const original = structuredClone(items)
  const f = await fixture({ directory: true, api: { listWikiPages: async () => ({ items }) } })
  try {
    const { descriptor } = parse(readFileSync(new URL('./ContextDBWikiDirectory.vue', import.meta.url), 'utf8'))
    const compiled = compileTemplate({ source: descriptor.template!.content, filename: 'ContextDBWikiDirectory.vue', id: 'wiki-directory-names', compilerOptions: { expressionPlugins: ['typescript'] } })
    assert.deepEqual(compiled.errors, [])
    const exports: any = {}
    runInNewContext(ts.transpileModule(compiled.code, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports, require })
    const app = createSSRApp({ render: () => exports.render({ ...f.vm.$props, ...f.vm }, []) })
    for (const name of ['t-icon', 't-dropdown', 't-button', 't-loading', 'ContextDBWikiDirectory']) app.component(name, { template: '<span><slot /></span>' })
    const html = (await renderToString(app)).replace(/<!--[\s\S]*?-->/g, '')
    assert.match(html, /<span>采购单\.md - Summary<\/span>/)
    assert.match(html, /aria-label="更多 采购单\.md - Summary"/)
    assert.match(html, /<span>资料目录<\/span>/)
    assert.match(html, /aria-label="展开资料目录"/)
    assert.match(html, /aria-label="更多 资料目录"/)
    assert.doesNotMatch(html, /doc-[a-f\d]{64}/i)
    assert.deepEqual(items, original)
  } finally { f.close() }
})

test('page navigation preserves the space route query and unsaved drafts block every navigation path', async () => {
  const f = await fixture()
  try {
    f.vm.startEditing(); f.vm.draft = '保留的草稿'
    await f.vm.openPage('page-b')
    assert.equal(f.route.query.wikiPageId, 'page-a')
    assert.equal(f.guards[0](), false)
    const unload = { preventDefault() { this.prevented = true }, prevented: false, returnValue: null }
    f.windowEvents.get('beforeunload')?.(unload)
    assert.equal(unload.prevented, true)
    assert.equal(f.vm.draft, '保留的草稿')
    f.vm.cancelEditing(); await f.vm.openPage('page-b'); await flush()
    assert.equal(f.route.query.wikiPageId, 'page-b')
    assert.equal(f.route.query.retained, 'yes')
    assert.equal(f.route.query.tab, 'wiki')
  } finally { f.close() }
})

test('Wiki view links retain the selected page and unsaved drafts prevent a view switch', async () => {
  const f = await fixture()
  try {
    await f.vm.switchTab('compile')
    assert.equal(f.route.query.wikiTab, 'compile')
    assert.equal(f.route.query.wikiPageId, 'page-a')
    await f.vm.switchTab('read')
    f.vm.startEditing(); f.vm.draft = '保留的正文'
    await f.vm.switchTab('compile')
    assert.equal(f.vm.internalTab, 'read')
    assert.equal(f.route.query.wikiTab, 'read')
    f.vm.cancelEditing()
  } finally { f.close() }
})

test('directory menu actions use their own page identity without changing the open article', async () => {
  const f = await fixture()
  try {
    f.vm.openAction('rename', page({ page_id: 'directory-b', page_type: 'category', title: '目录 B', version: 9 }))
    assert.equal(f.vm.actionTitle, '目录 B')
    f.vm.actionTitle = '目录新名称'
    await f.vm.submitAction()
    const call = f.calls.find(call => call.name === 'organizeWikiDirectory')!
    assert.equal(call.args[1], 'directory-b')
    assert.equal(call.args[2].expected_version, 9)
    assert.equal(call.args[2].title, '目录新名称')
    assert.equal(f.route.query.wikiPageId, 'page-a')
  } finally { f.close() }
})

test('deleting another page from its tree menu checks that version and keeps the current article open', async () => {
  const f = await fixture({ api: { getWikiPage: async (_kb, id) => page({ page_id: id, version: id === 'page-b' ? 9 : 3 }) } })
  try {
    f.vm.openAction('delete', page({ page_id: 'page-b', version: 9 }))
    await f.vm.submitAction()
    assert.equal(f.calls.find(call => call.name === 'deleteWikiPage')!.args[1], 'page-b')
    assert.equal(f.route.query.wikiPageId, 'page-a')
    assert.equal(f.vm.page.page_id, 'page-a')
  } finally { f.close() }
})

test('new Wiki pages default to entity and submit their complete Markdown body', async () => {
  const f = await fixture()
  try {
    f.vm.openAction('create-page')
    assert.equal(f.vm.actionType, 'entity')
    await f.vm.submitAction()
    assert.equal(f.calls.filter(call => call.name === 'createWikiPage').length, 0)
    f.vm.actionTitle = '新建主题'; f.vm.actionContent = '# 新建主题\n\n' + '完整正文。'.repeat(1000)
    await f.vm.submitAction()
    const call = f.calls.find(call => call.name === 'createWikiPage')!
    assert.equal(call.args[1].page_type, 'entity')
    assert.equal(call.args[1].content, '# 新建主题\n\n' + '完整正文。'.repeat(1000))
  } finally { f.close() }
})

test('CAS conflict retains the draft and latest-version comparison requires manual adoption', async () => {
  const f = await fixture({ api: { updateWikiPage: async () => { throw { status: 409 } } } })
  try {
    f.vm.startEditing(); f.vm.draft = '我的修改'
    f.remote(page({ content: '他人修改', version: 8 }))
    await f.vm.save()
    assert.equal(f.vm.editing, true); assert.equal(f.vm.draft, '我的修改'); assert.equal(f.vm.conflict, true)
    assert.equal(f.calls.find(call => call.name === 'updateWikiPage')?.args[2].expected_version, 3)
    assert.equal(f.vm.editVersion, 3); assert.equal(f.vm.latest.version, 8)
    f.vm.useLatestBase()
    assert.equal(f.vm.editVersion, 8); assert.equal(f.vm.draft, '我的修改'); assert.equal(f.vm.conflict, false)
  } finally { f.close() }
})

test('a returned version alone never confirms a save, while published matching正文 does', async () => {
  const f = await fixture({ api: { updateWikiPage: async () => ({ version: 99 }) } })
  try {
    f.vm.startEditing(); f.vm.draft = '等待发布的正文'
    f.remote(page({ version: 99, published: false, run_state: 'pending', content: '等待发布的正文' }))
    await f.vm.save()
    assert.equal(f.vm.editing, true); assert.equal(f.vm.submitted, true)
    assert.equal(f.vm.busyPage, true)
    assert.equal(f.successes.length, 0)
    assert.match(f.vm.saveNotice, /正式正文尚未/)
    f.remote(page({ version: 100, published: true, content: '等待发布的正文' }))
    await f.vm.verifySaved()
    assert.equal(f.vm.editing, false); assert.equal(f.successes.length, 1)
  } finally { f.close() }
})

test('pending pages block editing and moving sends both object and freshly read target versions', async () => {
  const f = await fixture()
  try {
    f.vm.page = page({ run_state: 'pending' }); f.vm.startEditing(); f.vm.openAction('delete')
    assert.equal(f.vm.editing, false); assert.equal(f.vm.action, '')
    f.vm.page = page(); f.vm.openAction('move')
    f.vm.targetDirectory = page({ page_id: 'directory-a', page_type: 'category', version: 5 })
    f.remote(page({ page_id: 'directory-a', page_type: 'category', version: 9 }))
    await f.vm.submitAction()
    const moved = f.calls.find(call => call.name === 'organizeWikiPage')
    assert.equal(moved?.args[1], 'page-a')
    assert.equal(moved?.args[2].expected_version, 3)
    assert.equal(moved?.args[2].expected_parent_version, 9)
    assert.equal(moved?.args[2].parent_page_id, 'directory-a')
  } finally { f.close() }
})

test('index pagination follows the selected group and Wiki slug links retain clickable navigation', async () => {
  const f = await fixture({ api: { getWikiIndex: async (_kb, params) => ({ intro: '', groups: [{ type: 'concept', total: 2, items: [page({ page_id: params.cursor ? 'second' : 'first' })], next_cursor: params.cursor ? null : 'concept-cursor==' }] }) } })
  try {
    await f.vm.loadGroup(f.vm.groups[0])
    assert.equal(f.calls.filter(call => call.name === 'getWikiIndex').at(-1)?.args[1].types, 'concept')
    assert.equal(f.calls.filter(call => call.name === 'getWikiIndex').at(-1)?.args[1].cursor, 'concept-cursor==')
    assert.equal(f.vm.groups[0].items.length, 2)
    f.vm.page = page({ links: [{ page_id: 'linked-id', slug: 'concept/linked', title: '关联主题' }] })
    assert.equal(f.vm.readingContent('[[concept/linked]]'), '[关联主题](#wiki-reference-linked-id)')
    assert.match(f.vm.readingContent('[[concept/missing|仍可定位]]'), /^\[仍可定位\]\(#wiki-reference-/)
  } finally { f.close() }
})

test('source names load without blocking正文, share a four-request limit and cache failures', async () => {
  const pending: { id: string; resolve: (value: any) => void; reject: (reason: Error) => void }[] = []
  let active = 0, peak = 0
  const f = await fixture({ api: { getDocument: async id => {
    active++; peak = Math.max(peak, active)
    try { return await new Promise((resolve, reject) => pending.push({ id, resolve, reject })) }
    finally { active-- }
  } } })
  try {
    f.vm.page = page({ source_document_ids: ['d1', 'd2', 'd3', 'd4', 'd5'] }); await flush()
    assert.equal(f.vm.page.content, '正式正文'); assert.equal(active, 4)
    f.vm.page = page({ page_id: 'page-b', source_document_ids: ['d1', 'd6'] }); await flush()
    assert.equal(active, 4, 'switching pages must share the existing concurrency budget')
    pending[0].resolve({ data: { name: 'hash.md', metadata: { filename: '真实资料.md' } } }); await flush()
    assert.equal(f.vm.sourceNames.d1, '真实资料.md'); assert.equal(active, 4)
    pending[1].reject(new Error('forbidden')); await flush()
    assert.equal(f.vm.sourceNames.d2, '查看来源文档'); assert.equal(peak, 4)
    for (const item of pending.slice(2)) item.resolve({ data: { name: `${item.id}.md` } })
    await flush()
    const count = f.calls.filter(call => call.name === 'getDocument').length
    f.vm.page = page({ source_document_ids: ['d1', 'd2'] }); await flush()
    assert.equal(f.calls.filter(call => call.name === 'getDocument').length, count)
  } finally { f.close() }
})

test('unpublished pages expose no source/link metadata and clearing search restores the full directory', async () => {
  const f = await fixture({ api: { searchWikiPages: async () => ({ items: [page({ page_id: 'result' })] }) } })
  try {
    f.vm.page = page({ published: false, content: '<script>oldBody()</script>', links: [{ page_id: 'private-link' }], backlinks: [{ page_id: 'private-backlink' }], source_document_ids: ['private-source'] })
    await flush()
    assert.equal(f.vm.relatedLinks.length, 0); assert.equal(f.vm.backlinks.length, 0)
    assert.equal(f.calls.filter(call => call.name === 'getDocument').length, 0)
    f.vm.query = '查询'; await f.vm.search()
    assert.equal(f.vm.searchResults.length, 1)
    f.vm.query = ''; await f.vm.search()
    assert.equal(f.vm.searchResults, null)
    assert.equal(f.calls.filter(call => call.name === 'listWikiPages').length, 0, 'search clearing never substitutes regex hits for the tree')
  } finally { f.close() }
})

test('Wiki link titles are inert text and malicious reference strings stay encoded inside the fragment', async () => {
  const f = await fixture()
  try {
    const content = f.vm.readingContent('[[javascript:alert(1)|<img src=x onerror=alert(1)>]]')
    const html = renderDocumentPreviewMarkdown(content, value => value)
    assert.match(html, /href="#wiki-reference-javascript%3Aalert%281%29"/)
    assert.doesNotMatch(html, /<(?:script|img)\b/i)
    assert.doesNotMatch(html, /href="javascript:/i)
    assert.match(html, /&lt;img/)
  } finally { f.close() }
})

test('Wiki labels use additive titles while editing and original content keep native values', async () => {
  const rawTitle = `doc-${'e'.repeat(64)}.html - Summary`
  const native = page({ title: rawTitle, display_title: '采购单.html - Summary',
    content: `# ${rawTitle}\n\n保留正式原文`,
    links: [{ page_id: 'related', title: rawTitle, display_title: '关联采购单.html - Summary' }] })
  const f = await fixture({ api: { getWikiPage: async () => native } })
  try {
    assert.equal(f.vm.linkTitle(f.vm.page.links[0]), '关联采购单.html - Summary')
    assert.equal(f.vm.linkTitle({ page_id: 'legacy', title: '历史页面' }), '历史页面')
    f.vm.openAction('rename')
    assert.equal(f.vm.actionTitle, rawTitle, 'A displayed alias must never become an implicit rename')
    f.vm.action = ''
    f.vm.startEditing()
    assert.equal(f.vm.draft, native.content)
    assert.equal(f.vm.page.title, rawTitle)
    assert.equal(f.vm.page.page_id, native.page_id)
  } finally { f.close() }
})

test('Wiki references replace native title labels with display titles and preserve custom aliases and source content', async () => {
  const rawTitle = `doc-${'e'.repeat(64)}.html - Summary`
  const content = `[[summary/source|${rawTitle}]]`
  const native = page({ content, links: [{ page_id: 'related-id', slug: 'summary/source', title: rawTitle, display_title: '采购单.html - Summary' }] })
  const f = await fixture({ api: { getWikiPage: async () => native } })
  try {
    for (const reference of ['summary/source', 'related-id']) {
      assert.equal(f.vm.readingContent(`[[${reference}|${rawTitle}]]`), '[采购单.html - Summary](#wiki-reference-related-id)')
      assert.equal(f.vm.readingContent(`[[${reference}|自定义引用名称]]`), '[自定义引用名称](#wiki-reference-related-id)')
    }
    assert.equal(f.vm.page.content, content)
    assert.equal(f.vm.page.links[0].title, rawTitle)
    assert.equal(native.content, content)
  } finally { f.close() }
})

test('late comparison responses cannot restore a cancelled draft or replace another page', async () => {
  const old = deferred<any>()
  let reads = 0
  const f = await fixture({ api: { getWikiPage: async (_kb, id) => ++reads === 2 ? old.promise : page({ page_id: id }) } })
  try {
    f.vm.startEditing(); const comparison = f.vm.compareLatest()
    f.vm.cancelEditing(); await f.vm.openPage('page-b'); await flush()
    old.resolve(page({ version: 20, content: '旧页面的迟到正文' })); await comparison
    assert.equal(f.vm.latest, null); assert.equal(f.vm.page.page_id, 'page-b')
    f.vm.useLatestBase(); assert.equal(f.vm.page.page_id, 'page-b')
  } finally { f.close() }
})

test('only the newest comparison can become the merge base on the same page', async () => {
  const first = deferred<any>(), second = deferred<any>()
  let reads = 0
  const f = await fixture({ api: { getWikiPage: async () => ++reads === 1 ? page() : reads === 2 ? first.promise : second.promise } })
  try {
    f.vm.startEditing(); const earlier = f.vm.compareLatest(), later = f.vm.compareLatest()
    second.resolve(page({ version: 10 })); await later
    first.resolve(page({ version: 4 })); await earlier
    assert.equal(f.vm.latest.version, 10)
    f.vm.useLatestBase(); assert.equal(f.vm.editVersion, 10)
  } finally { f.close() }
})

test('a slow reference lookup cannot override a newer link click or manual page navigation', async () => {
  const first = deferred<any>(), third = deferred<any>()
  const f = await fixture({ api: {
    getWikiPage: async (_kb, id) => page({ page_id: id }),
    getWikiPageByReference: async (_kb, reference) => reference === 'first' ? first.promise : reference === 'third' ? third.promise : page({ page_id: 'page-b' }),
  } })
  try {
    const earlier = f.vm.openReference('first')
    await f.vm.openReference('second'); await flush()
    first.resolve(page({ page_id: 'old-link' })); await earlier; await flush()
    assert.equal(f.route.query.wikiPageId, 'page-b')
    const slow = f.vm.openReference('third')
    await f.vm.openPage('page-c'); await flush()
    third.resolve(page({ page_id: 'late-link' })); await slow; await flush()
    assert.equal(f.route.query.wikiPageId, 'page-c')
    assert.equal(f.calls.filter(call => call.name === 'getWikiPage' && ['old-link', 'late-link'].includes(call.args[1])).length, 0)
  } finally { f.close() }
})

test('reader title deduplication removes only the repeated leading H1 and excerpts remain plain text', async () => {
  const markdown = '# 原生主题页\n\n正文说明。\n\n## 使用条件\n\n内容保留。'
  const html = renderDocumentPreviewMarkdown(markdown, value => value, { titles: ['原生主题页'] })
  assert.doesNotMatch(html, /<h1>/)
  assert.match(html, /<p>正文说明。<\/p>/)
  assert.match(html, /<h2>使用条件<\/h2>/)
  assert.match(renderDocumentPreviewMarkdown(markdown, value => value), /<h1>原生主题页<\/h1>/)
  assert.match(renderDocumentPreviewMarkdown(markdown, value => value, { titles: ['另一主题'] }), /<h1>原生主题页<\/h1>/)
  const f = await fixture()
  try {
    assert.equal(f.vm.summaryText('# 主题\n\n**说明**与[[concept/reference|关联页面]]。'), '主题 说明与关联页面。')
  } finally { f.close() }
})
