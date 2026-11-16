import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import ts from 'typescript'
import { fixture, flush } from '../test-utils/vueFixture.ts'
import { reviewEditableContent } from '../utils/reviewContent.ts'

const permissionAPI = readFileSync(new URL('../api/contextdb.ts', import.meta.url), 'utf8')
const accessCode = ts.transpileModule(permissionAPI.slice(permissionAPI.indexOf('export function knowledgeAccess('), permissionAPI.indexOf('export async function getBasePermissions')).replace('export function', 'function') + '\nreturn knowledgeAccess', { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
const knowledgeAccess = new Function(accessCode)()
const plain = (value: any) => JSON.parse(JSON.stringify(value))
const review = (id = 'review-a', state = 'pending_human') => ({ review_id: id, document_id: `doc-${id}`, document_name: `${id}.md`, knowledge_base_id: 'kb-a', lifecycle_state: state, can_approve_review: true, rewritten_content: '完整重写正文🙂', original_content: { page: 1, total_pages: 1, total_chars: 4, text: '完整原文' } })
type Call = { method: string; path: string; data: any }
const fixtures = new WeakMap<TestContext, ReturnType<typeof fixture>>()
async function setup(t: TestContext, options: { query?: any; profile?: any; rows?: any[]; read?: (path: string, params: any) => Promise<any>; write?: (path: string, body: any) => Promise<any>; permissionFailure?: boolean } = {}) {
  const f = fixtures.get(t) || fixture(t), calls: Call[] = []
  fixtures.set(t, f)
  Object.assign(f.window, { confirm: () => true })
  const profile = options.profile || { member: { member_id: 'member-a', member_name: '测试成员', role: 'owner', status: 'active' } }
  const { vm } = f.component(new URL('./KnowledgeView.vue', import.meta.url), {
    'vue-router': { useRoute: () => ({ query: options.query || {} }), onBeforeRouteLeave: () => {} },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/api/contextdb': {
      knowledgeAccess, getBasePermissions: async () => { if (options.permissionFailure) throw new Error('permissions unavailable'); return profile },
      listBases: async () => ({ data: [{ id: 'kb-a', name: '可写知识库' }, { id: 'kb-read', name: '只读知识库' }] }),
      nativeAPI: {
        async get(path: string, params: any) {
          calls.push({ method: 'GET', path, data: params })
          if (options.read) return { data: await options.read(path, params) }
          if (path === 'knowledge/reviews') return { data: { reviews: options.rows || [review()], total: (options.rows || [review()]).length } }
          if (path === 'knowledge/reviews/detail') return { data: review(params.review_id) }
          if (path === 'knowledge/documents/detail') return { data: { id: params.document_id, knowledge_base_id: 'kb-a', ingest_status: 'processing' } }
          throw new Error(`Unexpected GET ${path}`)
        },
        async post(path: string, body: any) {
          calls.push({ method: 'POST', path, data: body })
          if (options.write) return { data: await options.write(path, body) }
          if (path === 'knowledge/reviews/action') return { data: review(body.review_id, body.action === 'reject' ? 'rejected' : body.action === 'retract' ? 'pending_human' : 'approved') }
          if (path === 'knowledge/reviews/batch') return { data: { results: body.ids.map((id: string) => ({ id, success: true })) } }
          if (path === 'knowledge/reviews/resolve-conflicts') return { data: { saved: body.resolutions.length } }
          throw new Error(`Unexpected POST ${path}`)
        },
      },
    },
    '@/utils/platformPresentation': { contextdbDateTime: (value: any) => value || '—' },
    '@/utils/contextdbDocumentName': { documentDisplayName: (row: any) => row?.document_name || row?.name || '' },
    '@/utils/reviewContent': { reviewEditableContent },
  })
  await flush(); await flush()
  return { vm, calls, window: f.window }
}
test('personal reviews omit a library while library mode uses its exact writable ID and native sorting', async t => {
  const personal = await setup(t)
  assert.equal(personal.calls.find(call => call.path === 'knowledge/reviews')!.data.knowledge_base_id, undefined)
  assert.equal(personal.vm.memberOptions[0].label, '测试成员 (member-a)')
  const f = await setup(t, { query: { kb_id: 'kb-a' } })
  assert.equal(f.calls.find(call => call.path === 'knowledge/reviews')!.data.knowledge_base_id, 'kb-a')
  f.vm.sortBy = 'confidence_score'; f.vm.sortOrder = 'asc'; f.vm.reviewState = ''; await flush()
  const params = f.calls.filter(call => call.path === 'knowledge/reviews').at(-1)!.data
  assert.deepEqual(plain(params), { knowledge_base_id: 'kb-a', page: 1, page_size: 10, sort_by: 'confidence_score', sort_order: 'asc' })
  assert.equal('user_id' in params, false); assert.equal('only_mine' in params, false)
})
test('knowledge-base choices require write permission and missing permission never enables actions', async t => {
  const f = await setup(t, { profile: { member: { role: 'member' }, knowledge_base_permissions: [{ knowledge_base_id: 'kb-a', current_permission: 'write' }, { knowledge_base_id: 'kb-read', current_permission: 'read' }] } })
  assert.deepEqual(plain(f.vm.writableBases.map((base: any) => base.id)), ['kb-a'])
  const denied = await setup(t, { query: { kb_id: 'kb-read' }, profile: { member: { role: 'member' }, knowledge_base_permissions: [{ knowledge_base_id: 'kb-read', current_permission: 'read' }] } })
  assert.equal(denied.vm.activeBaseId, ''); assert.equal(denied.calls.some(call => call.path === 'knowledge/reviews'), false)
  const failed = await setup(t, { permissionFailure: true })
  await failed.vm.actReview('confirm'); assert.equal(failed.calls.some(call => call.method === 'POST'), false)
  assert.equal(failed.vm.contextError, 'permissions unavailable')
})
test('single-review actions are gated by lifecycle and official approval permission', async t => {
  const f = await setup(t)
  for (const action of ['confirm', 'accept_rewrite', 'force_accept', 'reject']) assert.equal(f.vm.canReviewAction(review(), action), true)
  assert.equal(f.vm.canReviewAction(review('x', 'auto_accepted'), 'confirm'), false)
  assert.equal(f.vm.canReviewAction(review('x', 'approved'), 'retract'), true)
  assert.equal(f.vm.canReviewAction(review('x', 'failed'), 'retry_review'), true)
  assert.equal(f.vm.canReviewAction(review('x', 'rejected'), 'retract'), false)
  assert.equal(f.vm.canReviewAction({ ...review(), can_approve_review: false }, 'confirm'), false)
})
test('submitting an edited rewrite preserves full text and conflict choices while independently reading document state', async t => {
  const f = await setup(t)
  f.vm.editing = true; f.vm.editedContent = '完整原文\n人工修复的条件🙂'; f.vm.resolutions = { c1: 'merge' }
  await f.vm.actReview('accept_rewrite')
  assert.deepEqual(plain(f.calls.find(call => call.path === 'knowledge/reviews/action')!.data), { review_id: 'review-a', action: 'accept_rewrite', edited_content: '完整原文\n人工修复的条件🙂', conflict_resolutions: [{ conflict_id: 'c1', resolution: 'merge' }] })
  assert.equal(f.vm.reviewDetail.lifecycle_state, 'approved'); assert.equal(f.vm.reviewDocument.ingest_status, 'processing')
  assert.equal(f.vm.reviewDocument.wiki_status, undefined); assert.equal(f.vm.editing, false)
})
test('a rejected or mismatched action response keeps the editable draft and reports no success', async t => {
  for (const write of [async () => { throw new Error('upstream unavailable') }, async () => review('other')]) {
    const f = await setup(t, { write }); f.vm.editing = true; f.vm.editedContent = '保留的完整稿'
    await f.vm.actReview('accept_rewrite')
    assert.equal(f.vm.editing, true); assert.equal(f.vm.editedContent, '保留的完整稿'); assert.equal(f.vm.reviewNotice, '')
    assert.ok(f.vm.reviewError)
  }
})
test('reject requires its dialog confirmation and does not query a deleted document', async t => {
  const f = await setup(t)
  await f.vm.actReview('reject'); assert.equal(f.vm.rejectTarget, 'single'); assert.equal(f.calls.some(call => call.method === 'POST'), false)
  await f.vm.confirmReject(); assert.equal(f.vm.rejectTarget, ''); assert.equal(f.vm.reviewDetail.lifecycle_state, 'rejected')
  assert.equal(f.calls.some(call => call.path === 'knowledge/documents/detail'), false)
})
test('editing without a rewrite reads every original page and refuses incomplete text', async t => {
  const read = async (path: string, params: any) => path === 'knowledge/reviews' ? { reviews: [review()], total: 1 } : { ...review(params.review_id), rewritten_content: '', original_content: { page: params.content_page, total_pages: 2, total_chars: 6, text: params.content_page === 1 ? '第一段' : '第二段' } }
  const f = await setup(t, { read }); await f.vm.startEditing()
  assert.equal(f.vm.editedContent, '第一段第二段'); assert.equal(f.vm.editing, true)
  assert.deepEqual(f.calls.filter(call => call.path === 'knowledge/reviews/detail').slice(-2).map(call => call.data.content_page), [1, 2])
  const broken = await setup(t, { read: async (path, params) => {
    const data = await read(path, params); if (params?.content_page === 2) (data as any).original_content.total_chars = 7; return data
  } })
  await broken.vm.startEditing(); assert.equal(broken.vm.editing, false); assert.match(broken.vm.reviewError, /分页不完整|不完整/)
})
test('empty rewrite text cannot submit and existing unedited rewrites never send a truncated original', async t => {
  const f = await setup(t)
  f.vm.editing = true; f.vm.editedContent = ' '; await f.vm.actReview('accept_rewrite')
  assert.equal(f.calls.some(call => call.method === 'POST'), false)
  f.vm.editing = false; await f.vm.actReview('accept_rewrite')
  const body = f.calls.find(call => call.path === 'knowledge/reviews/action')!.data
  assert.equal(body.action, 'accept_rewrite'); assert.equal('edited_content' in body, false)
})
test('closing a review rejects delayed detail and document-state responses', async t => {
  let finish!: (value: any) => void
  const f = await setup(t)
  f.vm.reviewDetail = review(); const original = f.vm.reviewDetail
  const read = async (path: string, params: any) => {
    if (path === 'knowledge/reviews') return { reviews: [], total: 0 }
    return await new Promise(resolve => { finish = resolve })
  }
  const delayed = await setup(t, { rows: [], read })
  delayed.vm.reviewRow = review(); delayed.vm.reviewDetail = original
  const waiting = delayed.vm.loadReviewPage(2); delayed.vm.closeReview(); finish(review()); await waiting
  assert.equal(delayed.vm.reviewDetail, null)
  delayed.vm.reviewRow = review(); delayed.vm.reviewDetail = review()
  const status = delayed.vm.refreshReviewStatus(); delayed.vm.closeReview(); finish({ id: 'doc-review-a', knowledge_base_id: 'kb-a' }); await status
  assert.equal(delayed.vm.reviewDocument, null)
})
test('late list responses cannot overwrite a new filter or restore the old selection', async t => {
  let resolveOld!: (value: any) => void, delayed = false
  const f = await setup(t, { read: async (path, params) => {
    if (path === 'knowledge/reviews') {
      if (delayed && params.lifecycle_state === 'pending_human') return await new Promise(resolve => { resolveOld = resolve })
      return { reviews: [review('new', params.lifecycle_state)], total: 1 }
    }
    return review(params.review_id)
  } })
  delayed = true; const old = f.vm.loadReviews(false); f.vm.reviewState = 'approved'; await flush()
  resolveOld({ reviews: [review('old')], total: 1 }); await old
  assert.equal(f.vm.reviews[0].review_id, 'new'); assert.deepEqual(plain(f.vm.selectedReviewIds), [])
})
test('batch operations reject missing IDs, mixed lifecycle states and more than fifty records', async t => {
  const f = await setup(t, { rows: [review('a'), review('b', 'approved')] })
  f.vm.selectedReviewIds = ['a', 'missing']; assert.equal(f.vm.canBatchReview('confirm'), false)
  f.vm.selectedReviewIds = ['a', 'b']; assert.equal(f.vm.canBatchReview('confirm'), false)
  f.vm.reviews = Array.from({ length: 51 }, (_, index) => review(String(index))); f.vm.selectedReviewIds = f.vm.reviews.map((row: any) => row.review_id)
  assert.equal(f.vm.canBatchReview('confirm'), false)
})
test('batch results retain per-record failures and state-read errors without announcing total success', async t => {
  let afterAction = false
  const f = await setup(t, { rows: [review('a'), review('b')],
    read: async (path, params) => {
      if (path === 'knowledge/reviews') return { reviews: [review('a'), review('b')], total: 2 }
      if (afterAction && params.review_id === 'b') throw new Error('status unavailable')
      return review(params.review_id, afterAction ? 'approved' : 'pending_human')
    },
    write: async () => { afterAction = true; return { results: [{ id: 'a', success: true }, { id: 'b', success: false, error: 'permission denied' }] } },
  })
  f.vm.selectedReviewIds = ['a', 'b']; await f.vm.actReviews('confirm')
  assert.equal(f.vm.reviewBatchResults[0].state, 'approved'); assert.equal(f.vm.reviewBatchResults[1].success, false)
  assert.match(f.vm.reviewBatchResults[1].error, /permission denied.*status unavailable/); assert.deepEqual(plain(f.vm.selectedReviewIds), [])
})
test('batch rewrite verifies existing content instead of silently submitting an individual draft', async t => {
  const f = await setup(t, { read: async (path, params) => path === 'knowledge/reviews' ? { reviews: [review()], total: 1 } : { ...review(params.review_id), rewritten_content: '' } })
  f.vm.selectedReviewIds = ['review-a']; f.vm.editedContent = '只属于详情的草稿'; await f.vm.actReviews('accept_rewrite')
  assert.equal(f.calls.some(call => call.method === 'POST'), false); assert.match(f.vm.reviewBatchError, /无可采纳重写稿/)
})
test('saving conflict choices uses the official endpoint and remains separate from a review decision', async t => {
  const f = await setup(t); f.vm.resolutions = { c1: 'merge', c2: '' }; await f.vm.saveConflictDraft()
  assert.deepEqual(plain(f.calls.find(call => call.method === 'POST')), { method: 'POST', path: 'knowledge/reviews/resolve-conflicts', data: { review_id: 'review-a', resolutions: [{ conflict_id: 'c1', resolution: 'merge' }] } })
  assert.equal(f.vm.reviewDetail.lifecycle_state, 'pending_human')
})
test('clicking the selected card preserves an edited draft and cancelled navigation keeps it open', async t => {
  const f = await setup(t); f.vm.editing = true; f.vm.editedContent = '尚未提交的完整正文'
  await f.vm.openReview(review())
  assert.equal(f.vm.editedContent, '尚未提交的完整正文'); assert.equal(f.vm.editing, true)
  Object.assign(f.window, { confirm: () => false }); await f.vm.openReview(review('other')); f.vm.closeReview()
  assert.equal(f.vm.reviewRow.review_id, 'review-a'); assert.equal(f.vm.editedContent, '尚未提交的完整正文')
})
test('select-all skips records without write permission and single operations wait for batch work', async t => {
  const f = await setup(t, { rows: [review('a'), { ...review('readonly'), can_approve_review: false }, review('rejected', 'rejected')] })
  f.vm.toggleAll(true); assert.deepEqual(plain(f.vm.selectedReviewIds), ['a']); assert.equal(f.vm.allSelected, true)
  f.vm.reviewBatchActing = true; await f.vm.actReview('confirm')
  assert.equal(f.calls.some(call => call.method === 'POST'), false)
})
test('an in-flight single decision blocks pagination and member refresh without locking its completion', async t => {
  let complete!: (value: any) => void
  const f = await setup(t, { write: async () => await new Promise(resolve => { complete = resolve }) })
  const initialReads = f.calls.filter(call => call.path === 'knowledge/reviews').length
  const profile = f.vm.permissionProfile, pending = f.vm.actReview('confirm')
  assert.equal(f.vm.reviewActing, true)
  f.vm.changePage(2); await f.vm.loadContext()
  assert.equal(f.vm.reviewPage, 1); assert.equal(f.vm.reviewRow.review_id, 'review-a')
  assert.equal(f.vm.permissionProfile, profile); assert.equal(f.vm.contextLoading, false)
  assert.equal(f.calls.filter(call => call.path === 'knowledge/reviews').length, initialReads)
  complete(review('review-a', 'approved')); await pending
  assert.equal(f.vm.reviewActing, false); assert.equal(f.vm.reviewDetail.lifecycle_state, 'approved')
  f.vm.changePage(2); await flush(); assert.equal(f.vm.reviewPage, 2)
})
test('an in-flight batch decision blocks pagination and member refresh until every result is handled', async t => {
  let complete!: (value: any) => void
  const f = await setup(t, { rows: [review('a'), review('b')], write: async () => await new Promise(resolve => { complete = resolve }) })
  f.vm.selectedReviewIds = ['a', 'b']; const initialReads = f.calls.filter(call => call.path === 'knowledge/reviews').length
  const profile = f.vm.permissionProfile, pending = f.vm.actReviews('confirm')
  assert.equal(f.vm.reviewBatchActing, true)
  f.vm.changePage(2); await f.vm.loadContext()
  assert.equal(f.vm.reviewPage, 1); assert.deepEqual(plain(f.vm.selectedReviewIds), ['a', 'b'])
  assert.equal(f.vm.permissionProfile, profile); assert.equal(f.vm.contextLoading, false)
  assert.equal(f.calls.filter(call => call.path === 'knowledge/reviews').length, initialReads)
  complete({ results: [{ id: 'a', success: true }, { id: 'b', success: true }] }); await pending
  assert.equal(f.vm.reviewBatchActing, false); assert.equal(f.vm.reviewBatchResults.length, 2)
  f.vm.changePage(2); await flush(); assert.equal(f.vm.reviewPage, 2)
})
test('member refresh cannot discard an edited rewrite even when the next permission read would fail', async t => {
  let permissionFails = false, permissionReads = 0
  const f = await setup(t, { query: { kb_id: 'kb-a' }, get permissionFailure() { permissionReads++; return permissionFails } })
  await f.vm.startEditing(); f.vm.editedContent = '人工整理的完整重写稿\n保留必要条件🙂'
  const reads = permissionReads, profile = f.vm.permissionProfile
  permissionFails = true; await f.vm.loadContext()
  assert.equal(permissionReads, reads); assert.equal(f.vm.editing, true)
  assert.equal(f.vm.editedContent, '人工整理的完整重写稿\n保留必要条件🙂')
  assert.equal(f.vm.activeBaseId, 'kb-a'); assert.equal(f.vm.reviewDetail.review_id, 'review-a'); assert.equal(f.vm.permissionProfile, profile)
  f.vm.editing = false; await f.vm.loadContext(); await flush()
  assert.equal(permissionReads, reads + 1); assert.equal(f.vm.contextError, 'permissions unavailable'); assert.equal(f.vm.permissionProfile, null)
})
