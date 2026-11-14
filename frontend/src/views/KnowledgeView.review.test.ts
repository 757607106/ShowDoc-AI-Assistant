import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { ref, watch } from 'vue'
import ts from 'typescript'
import { reviewEditableContent } from '../utils/reviewContent.ts'

const source = readFileSync(new URL('./KnowledgeView.vue', import.meta.url), 'utf8')

test('knowledge review opens reviews by default and retired memory links fall back to reviews', () => {
  const declaration = source.match(/^const tab = .+$/m)![0]
  const select = new Function('ref', 'route', `${declaration}; return tab.value`)
  for (const tab of [undefined, 'memory', 'promotions', 'unknown']) {
    assert.equal(select(ref, { query: { tab } }), 'reviews')
  }
  for (const tab of ['reviews', 'search', 'graph', 'documents', 'templates', 'settings']) {
    assert.equal(select(ref, { query: { tab } }), tab)
  }
})

test('loading knowledge bases and review settings makes no memory or promotion requests', async () => {
  const bases = ref<any[]>([]), activeBaseId = ref(''), reviewSettings = ref<any>(null), calls: string[] = []
  const api = new Proxy({}, { get: (_, method: string) => async () => {
    calls.push(method)
    if (method === 'kbBases') return { bases: [{ id: 'wiki-a' }] }
    if (method === 'kbReviewSettings') return { settings: { high_threshold: 0.8 } }
    throw new Error(`Unexpected request: ${method}`)
  } })
  const code = ts.transpileModule(
    source.slice(source.indexOf('async function loadBases()'), source.indexOf('watch(activeBaseId,')) +
    source.slice(source.indexOf('async function loadSettings()'), source.indexOf('async function saveReviewSettings()')) +
    '\nreturn { loadBases, loadSettings }', { compilerOptions: { target: ts.ScriptTarget.ES2022 } },
  ).outputText
  const actions = new Function('api', 'bases', 'activeBaseId', 'reviewSettings', 'reviewSettingsKbId', 'wikiBases', 'route', `let reviewSettingsRequest = 0; ${code}`)(
    api, bases, activeBaseId, reviewSettings, ref(''), { get value() { return bases.value } }, { query: {} },
  )
  await actions.loadBases()
  await actions.loadSettings()
  assert.deepEqual(calls, ['kbBases', 'kbReviewSettings'])
  assert.equal(activeBaseId.value, 'wiki-a')
  assert.equal(reviewSettings.value.high_threshold, 0.8)
})

test('content templates use only knowledge-review endpoints scoped to the selected library', async () => {
  const template=readFileSync(new URL('./knowledge/ContextDBTemplates.vue',import.meta.url),'utf8')
  const script=template.slice(template.indexOf('const props='),template.indexOf('</script>'))
  const code=ts.transpileModule(script+'\nreturn {load,edit,save,remove,name,sections}',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const calls:any[]=[]
  const api=new Proxy({}, {get:(_,method:string)=>async(path:string)=>{calls.push([method,path]);return {data:[]}}})
  const state=new Function('ref','watch','defineProps','useAuthStore','nativeAPI',code)(ref,()=>{},()=>({kbId:'kb-a'}),()=>({}),api)
  await state.load()
  state.edit();state.name.value='文档模板';state.sections.value=[{level:1,title:'主题',guidance:'保留事实'}]
  await state.save()
  state.edit({id:'template-a',name:'文档模板',sections:state.sections.value});await state.save()
  await state.remove({id:'template-a'})
  assert.deepEqual(calls,[
    ['get','knowledge/review_templates?knowledge_base_id=kb-a'],
    ['post','knowledge/review_templates?knowledge_base_id=kb-a'],
    ['get','knowledge/review_templates?knowledge_base_id=kb-a'],
    ['put','knowledge/review_templates?knowledge_base_id=kb-a&template_id=template-a'],
    ['get','knowledge/review_templates?knowledge_base_id=kb-a'],
    ['del','knowledge/review_templates?knowledge_base_id=kb-a&template_id=template-a'],
    ['get','knowledge/review_templates?knowledge_base_id=kb-a'],
  ])
})

const permissionSource = source.slice(source.indexOf('function canReviewAction('), source.indexOf('function canBatchReview('))
const code = ts.transpileModule(permissionSource + source.slice(source.indexOf('async function loadReviewPage('), source.indexOf('async function loadKbDocuments()')) + '\nreturn { actReview, saveConflictDraft, refreshReviewStatus, openReviewWiki, loadReviewPage, openReview, startEditing }', {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText

function fixture(options: { action?: (...args: any[]) => Promise<any>; read?: (...args: any[]) => Promise<any>; page?: (...args: any[]) => Promise<any>; editRead?: () => Promise<string> } = {}) {
  const review = { review_id: 'review-a', document_id: 'doc-a', knowledge_base_id: 'kb-a', lifecycle_state: 'pending_human' }
  const calls: any[] = [], routes: any[] = []
  const state = {
    reviewActing: ref(false), reviewError: ref(''), reviewNotice: ref(''), conflictNotice: ref(''),
    reviewRow: ref<any>({ ...review }), reviewDetail: ref<any>({ ...review }), reviewDrawer: ref(true),
    reviewDocument: ref<any>(null), reviewStatusLoading: ref(false), reviewStatusError: ref(''),
    reviewBase: ref<any>({ id: 'kb-a', wiki_enabled: true }), resolutions: ref({ 'conflict-a': 'merge' }),
    editing: ref(true), editedContent: ref('完整原文\n人工修复的条件🙂'),
    contentPage: ref(1),
  }
  const dependencies = { ...state,
    auth: { hasRole: () => true },
    api: {
      async kbReviewAction(...args: any[]) { calls.push(['action', ...args]); return options.action ? options.action(...args) : { review: { ...review, lifecycle_state: 'approved' } } },
      async kbReviewConflicts(...args: any[]) { calls.push(['draft', ...args]); return { result: { saved: 1 } } },
      async kbReviewDetail(...args: any[]) { return options.page ? options.page(...args) : { review: { ...review } } },
    },
    nativeAPI: { async get(...args: any[]) { calls.push(['get', ...args]); return options.read ? options.read(...args) : { data: { id: 'doc-a', knowledge_base_id: 'kb-a', ingest_status: 'processing' } } } },
    router: { push: (route: any) => routes.push(route) }, window: { confirm: () => true },
    watch, parseJson: (value: any) => typeof value === 'string' ? JSON.parse(value) : value,
    reviewEditableContent: options.editRead || reviewEditableContent,
    loadReviews: async () => calls.push(['reviews']), loadKbDocuments: async () => calls.push(['documents']),
  }
  const functions = new Function('dependencies', `const {${Object.keys(dependencies).join(',')}} = dependencies; let reviewStatusRequest = 0, reviewRequest = 0; ${code}`)(dependencies)
  return { ...state, ...functions, calls, routes }
}

test('submitting a complete repair preserves the drawer and waits for independent official processing', async () => {
  const f = fixture()
  await f.actReview('accept_rewrite')
  assert.deepEqual(f.calls[0], ['action', 'review-a', 'accept_rewrite', {
    editedContent: '完整原文\n人工修复的条件🙂', conflictResolutions: [{ conflict_id: 'conflict-a', resolution: 'merge' }],
  }])
  assert.deepEqual(f.calls[1], ['get', 'knowledge/documents/detail', { knowledge_base_id: 'kb-a', document_id: 'doc-a' }])
  assert.equal(f.reviewDrawer.value, true)
  assert.equal(f.reviewDetail.value.lifecycle_state, 'approved')
  assert.equal(f.reviewDocument.value.ingest_status, 'processing')
  assert.equal(f.reviewDocument.value.wiki_status, undefined)
  assert.match(f.reviewNotice.value, /已受理/)
  assert.equal(f.editing.value, false)
  f.openReviewWiki()
  assert.deepEqual(f.routes, [{ path: '/platform/knowledge-bases/kb-a', query: { tab: 'wiki' } }])
})

test('failed submission keeps the complete editable draft and does not announce acceptance', async () => {
  const f = fixture({ action: async () => { throw new Error('upstream unavailable') } })
  await f.actReview('accept_rewrite')
  assert.equal(f.reviewError.value, 'upstream unavailable')
  assert.equal(f.editedContent.value, '完整原文\n人工修复的条件🙂')
  assert.equal(f.editing.value, true)
  assert.equal(f.reviewDrawer.value, true)
  assert.equal(f.reviewNotice.value, '')
  assert.equal(f.calls.length, 1)
})

test('status read failure after acceptance stays distinct from submission failure', async () => {
  const f = fixture({ read: async () => { throw new Error('status unavailable') } })
  await f.actReview('confirm')
  assert.equal(f.reviewDetail.value.lifecycle_state, 'approved')
  assert.match(f.reviewNotice.value, /已受理/)
  assert.equal(f.reviewError.value, '')
  assert.equal(f.reviewStatusError.value, 'status unavailable')
  assert.equal(f.reviewDocument.value, null)
})

test('saving conflict choices is a draft and does not approve or start document processing', async () => {
  const f = fixture()
  await f.saveConflictDraft()
  assert.deepEqual(f.calls, [['draft', 'review-a', [{ conflict_id: 'conflict-a', resolution: 'merge' }]]])
  assert.match(f.conflictNotice.value, /仍需提交评审决定/)
  assert.equal(f.reviewDetail.value.lifecycle_state, 'pending_human')
})

test('successful ingest and failed Wiki compilation retain their separate official outcomes', async () => {
  const f = fixture({ read: async () => ({ data: { id: 'doc-a', knowledge_base_id: 'kb-a', ingest_status: 'succeeded', wiki_status: 'failed', wiki_error_message: 'compile failed' } }) })
  await f.actReview('accept_rewrite')
  assert.equal(f.reviewDocument.value.ingest_status, 'succeeded')
  assert.equal(f.reviewDocument.value.wiki_status, 'failed')
  assert.equal(f.reviewDocument.value.wiki_error_message, 'compile failed')
  assert.doesNotMatch(f.reviewNotice.value, /已完成|全部成功/)
})

test('official document ownership mismatch and stale reads cannot replace current status', async () => {
  const mismatch = fixture({ read: async () => ({ data: { id: 'doc-a', knowledge_base_id: 'another-kb', ingest_status: 'succeeded' } }) })
  await mismatch.refreshReviewStatus()
  assert.equal(mismatch.reviewDocument.value, null)
  assert.match(mismatch.reviewStatusError.value, /归属/)

  let finish!: (value: any) => void
  const f = fixture({ read: () => new Promise(resolve => { finish = resolve }) })
  const waiting = f.refreshReviewStatus()
  f.reviewDetail.value = { review_id: 'review-b', document_id: 'doc-b', knowledge_base_id: 'kb-b' }
  finish({ data: { id: 'doc-a', knowledge_base_id: 'kb-a', ingest_status: 'succeeded', wiki_status: 'succeeded' } })
  await waiting
  assert.equal(f.reviewDocument.value, null)
})

test('a delayed review action cannot overwrite a newly opened review', async () => {
  let finish!: (value: any) => void
  const f = fixture({ action: () => new Promise(resolve => { finish = resolve }) })
  const waiting = f.actReview('accept_rewrite')
  f.reviewRow.value = { review_id: 'review-b' }
  f.reviewDetail.value = { review_id: 'review-b', lifecycle_state: 'pending_human' }
  finish({ review: { review_id: 'review-a', lifecycle_state: 'approved' } })
  await waiting
  assert.equal(f.reviewDetail.value.review_id, 'review-b')
  assert.equal(f.reviewDetail.value.lifecycle_state, 'pending_human')
  assert.equal(f.reviewNotice.value, '')
})

test('a pending page response cannot roll an approved review back to pending', async () => {
  let finish!: (value: any) => void
  const f = fixture({ page: () => new Promise(resolve => { finish = resolve }) })
  const page = f.loadReviewPage(2)
  await f.actReview('confirm')
  assert.equal(f.reviewDetail.value.lifecycle_state, 'approved')
  finish({ review: { ...f.reviewDetail.value, lifecycle_state: 'pending_human' } })
  await page
  assert.equal(f.reviewDetail.value.lifecycle_state, 'approved')
  assert.equal(f.contentPage.value, 1)
})

test('latest review page wins and a closed/reopened review ignores its old full-text read', async () => {
  const pending = new Map<number, (value: any) => void>()
  const f = fixture({ page: (_id, page) => new Promise(resolve => pending.set(page, resolve)) })
  const older = f.loadReviewPage(2), newer = f.loadReviewPage(3)
  pending.get(3)!({ review: { ...f.reviewDetail.value, marker: 'newest page' } })
  await newer
  pending.get(2)!({ review: { ...f.reviewDetail.value, marker: 'stale page' } })
  await older
  assert.equal(f.contentPage.value, 3)
  assert.equal(f.reviewDetail.value.marker, 'newest page')

  let finishEdit!: (value: string) => void
  const editing = fixture({ editRead: () => new Promise(resolve => { finishEdit = resolve }) })
  editing.editing.value = false
  const reading = editing.startEditing()
  editing.reviewDrawer.value = false
  await editing.openReview({ review_id: 'review-a' })
  finishEdit('stale full text')
  await reading
  assert.equal(editing.editing.value, false)
  assert.equal(editing.editedContent.value, '')
})

test('status reads started before a review action cannot replace post-action status', async () => {
  let finish!: (value: any) => void, reads = 0
  const f = fixture({ read: () => ++reads === 1 ? new Promise(resolve => { finish = resolve }) : Promise.resolve({ data: { id: 'doc-a', knowledge_base_id: 'kb-a', ingest_status: 'succeeded' } }) })
  const earlier = f.refreshReviewStatus()
  await f.actReview('confirm')
  finish({ data: { id: 'doc-a', knowledge_base_id: 'kb-a', ingest_status: 'pending_review' } })
  await earlier
  assert.equal(f.reviewDocument.value.ingest_status, 'succeeded')
})

test('rejection reports asynchronous deletion without treating a missing document as processing failure', async () => {
  const f = fixture({ action: async () => ({ review: { lifecycle_state: 'rejected' } }), read: async () => { throw new Error('document deleted') } })
  await f.actReview('reject')
  assert.equal(f.reviewDetail.value.lifecycle_state, 'rejected')
  assert.match(f.reviewNotice.value, /异步删除/)
  assert.equal(f.reviewStatusError.value, '')
  assert.equal(f.calls.some((call: any[]) => call[0] === 'get'), false)
})

const batchSource = source.slice(source.indexOf('function canReviewAction('), source.indexOf('function parseJson('))
const batchWatch = source.slice(source.indexOf('watch([activeBaseId, reviewState, reviewPage]'), source.indexOf('\n\nasync function search()'))
const batchCode = ts.transpileModule(batchWatch + batchSource + '\nreturn { canReviewAction, canBatchReview, actReviews }', {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText

function batchFixture(options: { batch?: () => Promise<any>; detail?: (id: string) => Promise<any>; confirm?: boolean; writable?: boolean } = {}) {
  const calls: any[] = []
  const state = {
    activeBaseId: ref('kb-a'), reviewState: ref('pending_human'), reviewPage: ref(1),
    reviewsKbId: ref('kb-a'),
    selectedReviewIds: ref(['r1', 'r2']), reviewLoading: ref(false), reviewBatchActing: ref(false),
    reviewBatchResults: ref<any[]>([]), reviewBatchError: ref(''),
    reviews: ref<any[]>(['r1', 'r2'].map(id => ({ review_id: id, document_name: `${id}.md`, lifecycle_state: 'pending_human' }))),
  }
  const dependencies = { ...state, watch,
    auth: { hasRole: () => options.writable !== false }, window: { confirm: () => options.confirm !== false },
    api: {
      async kbReviewBatch(...args: any[]) { calls.push(['batch', ...args]); return options.batch ? options.batch() : { results: [
        { id: 'r1', success: true }, { id: 'r2', success: false, error: 'state changed' },
      ] } },
      async kbReviewDetail(id: string) { calls.push(['detail', id]); return options.detail ? options.detail(id) : { review: { lifecycle_state: id === 'r1' ? 'approved' : 'pending_human' } } },
    },
    loadReviews: async () => { calls.push(['reviews']) }, loadKbDocuments: async () => { calls.push(['documents']) },
  }
  const functions = new Function('dependencies', `const {${Object.keys(dependencies).join(',')}} = dependencies; let reviewBatchRequest = 0; ${batchCode}`)(dependencies)
  return { ...state, ...functions, calls }
}

test('batch review enforces lifecycle, permission, current-page membership and the 50-item limit', () => {
  const f = batchFixture()
  assert.equal(f.canBatchReview('confirm'), true)
  assert.equal(f.canBatchReview('retract'), false)
  assert.equal(f.canBatchReview('retry_review'), false)
  f.reviews.value[0].can_approve_review = false
  assert.equal(f.canBatchReview('confirm'), false)
  f.reviews.value[0].can_approve_review = true
  f.selectedReviewIds.value.push('another-page')
  assert.equal(f.canBatchReview('confirm'), false)
  f.selectedReviewIds.value = ['r1']
  f.reviews.value[0].lifecycle_state = 'auto_accepted'
  assert.equal(f.canBatchReview('retract'), true)
  assert.equal(f.canBatchReview('confirm'), false)
  f.reviews.value[0].lifecycle_state = 'failed'
  assert.equal(f.canBatchReview('retry_review'), true)
  f.selectedReviewIds.value = Array(51).fill('r1')
  assert.equal(f.canBatchReview('retry_review'), false)
  assert.equal(batchFixture({ writable: false }).canBatchReview('confirm'), false)
})

test('batch review uses one official batch request and reads each result state without discarding partial failures', async () => {
  const f = batchFixture()
  await f.actReviews('confirm')
  assert.deepEqual(f.calls, [['batch', ['r1', 'r2'], 'confirm'], ['detail', 'r1'], ['detail', 'r2'], ['reviews'], ['documents']])
  assert.deepEqual(f.selectedReviewIds.value, [])
  assert.equal(f.reviewBatchResults.value[0].success, true)
  assert.equal(f.reviewBatchResults.value[0].lifecycle_state, 'approved')
  assert.equal(f.reviewBatchResults.value[1].success, false)
  assert.equal(f.reviewBatchResults.value[1].error, 'state changed')
  assert.equal(f.reviewBatchResults.value[1].lifecycle_state, 'pending_human')
  assert.equal(f.reviewBatchActing.value, false)
})

test('uncertain batch response is not retried and state-read failure stays distinct from action failure', async () => {
  const f = batchFixture({ batch: async () => { throw new Error('timeout') }, detail: async id => {
    if (id === 'r2') throw new Error('read unavailable')
    return { review: { lifecycle_state: 'approved' } }
  } })
  await f.actReviews('confirm')
  assert.match(f.reviewBatchError.value, /结果待确认.*timeout/)
  assert.equal(f.calls.filter((call: any[]) => call[0] === 'batch').length, 1)
  assert.equal(f.reviewBatchResults.value[0].success, undefined)
  assert.equal(f.reviewBatchResults.value[0].lifecycle_state, 'approved')
  assert.equal(f.reviewBatchResults.value[1].status_error, 'read unavailable')
  assert.equal(f.reviewBatchResults.value[1].error, undefined)
})

test('batch destructive actions require confirmation and filter or library changes discard old results', async () => {
  const cancelled = batchFixture({ confirm: false })
  await cancelled.actReviews('reject')
  assert.deepEqual(cancelled.calls, [])
  let finish!: (value: any) => void
  const f = batchFixture({ batch: () => new Promise(resolve => { finish = resolve }) })
  const pending = f.actReviews('confirm')
  f.activeBaseId.value = 'kb-b'
  finish({ results: [{ id: 'r1', success: true }] })
  await pending
  assert.deepEqual(f.reviewBatchResults.value, [])
  assert.equal(f.reviewBatchActing.value, false)
  f.selectedReviewIds.value = ['r1']
  f.reviewPage.value = 2
  assert.deepEqual(f.selectedReviewIds.value, [])
  f.selectedReviewIds.value = ['r1']
  f.reviewState.value = 'approved'
  assert.deepEqual(f.selectedReviewIds.value, [])
})

test('review master switch is persisted and round wording does not promise N rewrites', async () => {
  const code = ts.transpileModule(source.slice(source.indexOf('async function saveReviewSettings()'), source.indexOf('\nonMounted(')) + '\nreturn saveReviewSettings', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const calls: any[] = []
  const settings = { review_enabled: false, max_rewrite_iterations: 1 }
  const save = new Function('api', 'activeBaseId', 'reviewSettings', 'reviewSettingsKbId', 'reviewSettingsSaving', 'loadSettings', `let reviewSettingsRequest = 0; ${code}`)(
    { kbReviewSettingsUpdate: async (...args: any[]) => calls.push(args) }, ref('kb-a'), ref(settings), ref('kb-a'), ref(false), async () => calls.push('read-settings'),
  )
  await save()
  assert.equal(calls[0][1].review_enabled, false)
  assert.equal(calls[0][1].max_rewrite_iterations, 1)
  assert.equal(calls[1], 'read-settings')
  assert.match(source, /label="最多评审轮次"/)
  assert.doesNotMatch(source, /最多重写次数|待发布修订/)
  assert.match(source, /v-if="reviewBase\?\.wiki_enabled" class="hint-text"/)
})

test('late settings from another library cannot replace current values or be saved to the current library', async () => {
  const code = ts.transpileModule(source.slice(source.indexOf('async function loadSettings()'), source.indexOf('\nonMounted(')) + '\nreturn { loadSettings, saveReviewSettings }', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const pending = new Map<string, (value: any) => void>(), calls: any[] = []
  const activeBaseId = ref('kb-a'), reviewSettings = ref<any>(null), reviewSettingsKbId = ref('')
  const reviewSettingsSaving = ref(false)
  let finishSave!: () => void
  const api = {
    kbReviewSettings: (id: string) => new Promise(resolve => pending.set(id, resolve)),
    kbReviewSettingsUpdate: (...args: any[]) => { calls.push(args); return new Promise<void>(resolve => { finishSave = resolve }) },
  }
  const actions = new Function('api', 'activeBaseId', 'reviewSettings', 'reviewSettingsKbId', 'reviewSettingsSaving', `let reviewSettingsRequest = 0; ${code}`)(api, activeBaseId, reviewSettings, reviewSettingsKbId, reviewSettingsSaving)
  const older = actions.loadSettings()
  activeBaseId.value = 'kb-b'
  const latest = actions.loadSettings()
  pending.get('kb-b')!({ settings: { review_enabled: false, max_rewrite_iterations: 1 } })
  await latest
  pending.get('kb-a')!({ settings: { review_enabled: true, max_rewrite_iterations: 3 } })
  await older
  assert.equal(reviewSettingsKbId.value, 'kb-b')
  assert.equal(reviewSettings.value.review_enabled, false)
  activeBaseId.value = 'kb-c'
  await actions.saveReviewSettings()
  assert.deepEqual(calls, [], 'old library settings cannot be submitted under another library ID')
  activeBaseId.value = 'kb-b'
  const saving = actions.saveReviewSettings()
  assert.equal(calls[0][0], 'kb-b')
  activeBaseId.value = 'kb-c'
  finishSave()
  await saving
  assert.equal(reviewSettingsSaving.value, false)
  assert.equal(pending.has('kb-c'), false, 'late save completion must not reload or replace the new library settings')
})

test('review switches expose their values and Space or Enter uses the component click path', () => {
  const code = ts.transpileModule(source.slice(source.indexOf('function activateSettingsSwitch('), source.indexOf('\nonMounted(')) + '\nreturn activateSettingsSwitch', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const activate = new Function(code)()
  let clicks = 0, prevented = 0
  for (const key of [' ', 'Enter', 'Tab']) {
    activate({ key, preventDefault: () => prevented++, currentTarget: { click: () => clicks++ } })
  }
  assert.equal(clicks, 2)
  assert.equal(prevented, 2)
  for (const label of ['启用知识评审', '自动重写', '冲突检测', '重写稿自动入库']) {
    assert.match(source, new RegExp(`role="switch" aria-label="${label}" :aria-checked=`))
  }
})

test('failed loading of another library clears old rows and cannot enable a batch action on them', async () => {
  const code = ts.transpileModule(source.slice(source.indexOf('async function loadReviews()'), source.indexOf('async function actReviews(')) + '\nreturn { loadReviews, canBatchReview }', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const state = {
    activeBaseId: ref('kb-a'), reviewState: ref('pending_human'), reviewPage: ref(1),
    reviewsKbId: ref('kb-a'), selectedReviewIds: ref(['review-a']), reviewTotal: ref(1),
    reviews: ref<any[]>([{ review_id: 'review-a', knowledge_base_id: 'kb-a', lifecycle_state: 'pending_human' }]),
    reviewLoading: ref(false), reviewBatchActing: ref(false),
  }
  let finishOld!: (value: any) => void
  const dependencies = { ...state, auth: { hasRole: () => true }, api: {
    kbReviews: (id: string) => id === 'kb-a' ? new Promise(resolve => { finishOld = resolve }) : Promise.reject(new Error('library B unavailable')),
  } }
  const actions = new Function('dependencies', `const {${Object.keys(dependencies).join(',')}} = dependencies; let reviewListRequest = 0; ${code}`)(dependencies)
  assert.equal(actions.canBatchReview('reject'), true)
  const loadingOld = actions.loadReviews()
  state.activeBaseId.value = 'kb-b'
  assert.equal(actions.canBatchReview('reject'), false)
  await assert.rejects(actions.loadReviews(), /library B unavailable/)
  finishOld({ reviews: [{ review_id: 'review-a', knowledge_base_id: 'kb-a', lifecycle_state: 'pending_human' }], total: 1 })
  await loadingOld
  assert.equal(state.reviewLoading.value, false)
  assert.equal(state.reviewTotal.value, 0)
  assert.equal(state.reviewsKbId.value, '')
  assert.deepEqual(state.reviews.value, [])
  state.selectedReviewIds.value = ['review-a']
  assert.equal(actions.canBatchReview('reject'), false)
})
