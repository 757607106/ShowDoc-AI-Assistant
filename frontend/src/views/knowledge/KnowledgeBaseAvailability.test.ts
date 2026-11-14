import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import * as vue from 'vue'
import * as stall from '../../utils/knowledgeProcessingStall.ts'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

const base = () => ({ id: 'wiki-kb', name: '远端 Wiki', type: 'document', indexing_strategy: { wiki_enabled: true } })
async function setup(t: TestContext, initialError?: unknown) {
  t.mock.method(console, 'error', () => {})
  const f = fixture(t)
  const route = vue.reactive({ params: { kbId: 'wiki-kb' }, query: { tab: 'wiki' } })
  let failure = initialError
  let read: () => Promise<any> = async () => { if (failure) throw failure; return { data: base() } }
  const getKnowledgeBaseById = t.mock.fn(async () => read())
  const hook = {
    cardList: vue.ref<any[]>([]), total: vue.ref(0), moreIndex: vue.ref(-1), details: vue.reactive({ id: '' }),
    getKnowled: t.mock.fn(async () => {}), getCardDetails() {}, getfDetails() {}, onVisibleChange() {},
  }
  const page = f.component(new URL('./KnowledgeBase.vue', import.meta.url), {
    '@/config/contextdb': { IS_CONTEXTDB: true },
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace() {}, push() {} }) },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { success() {}, error() {}, info() {}, warning() {} } },
    '@/hooks/useKnowledgeBase': () => hook,
    '@/stores/ui': { useUIStore: () => ({ clearSelectedTagIds() {} }) },
    '@/stores/organization': { useOrganizationStore: () => ({ sharedKnowledgeBases: [], getKBPermission: () => 'owner' }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/stores/chatResources': { useChatResourcesStore: () => ({
      fetchKnowledgeBaseById: () => assert.fail('the direct native view must revalidate remote metadata'),
      rawKnowledgeBases: [], async ensureKnowledgeBases() {},
    }) },
    '@/stores/editorResources': { useEditorResourcesStore: () => ({ parserEngines: [], async ensureParserEngines() {} }) },
    '@/stores/uploadConfirm': { useUploadConfirmStore: () => ({}) },
    '@/stores/uploadTasks': { useUploadTasksStore: () => ({}) },
    '@/hooks/useMarqueeSelect': { useMarqueeSelect: () => ({}) },
    '@/composables/useAssistantPageContext': { useAssistantPageContext() {} },
    '@/utils/kbPermission': { permissionCanEditKB: () => true, permissionCanManageKB: () => true },
    '@/utils/knowledgeDeletion': {}, '@/utils/knowledgeTrace': {}, '@/utils/knowledgeProcessingStall': stall,
    '@/api/knowledge-base': {},
    '@/api/knowledge-base/index': {
      getKnowledgeBaseById, listKnowledgeTags: async () => ({ data: { data: [], total: 0 } }),
      listKnowledgeFolders: async () => ({ data: { folders: [] } }),
    },
  })
  await flush()
  return { ...page, hook, route, getKnowledgeBaseById, fail: (error: unknown) => { failure = error }, read: (next: () => Promise<any>) => { read = next } }
}

test('external deletion shows unavailability without clearing historical cards or the selected Wiki tab', async t => {
  const f = await setup(t)
  const previousInfo = f.vm.kbInfo
  f.hook.cardList.value = [{ id: 'historical-document', parse_status: 'completed' }]; f.hook.total.value = 1
  f.hook.getKnowled.mock.resetCalls()
  f.fail({ status: 404, message: 'Knowledge base not found' })
  await f.vm.loadKnowledgeBaseInfo('wiki-kb', true)
  assert.match(f.vm.kbLoadError.title, /不存在/)
  assert.equal(f.vm.kbInfo, previousInfo)
  assert.equal(f.hook.cardList.value[0].id, 'historical-document'); assert.equal(f.hook.total.value, 1)
  assert.equal(f.hook.getKnowled.mock.callCount(), 0)
  assert.equal(f.vm.shownKbTab, 'wiki'); assert.equal(f.route.query.tab, 'wiki')
  assert.equal(f.vm.kbLoading, false)
})

for (const [label, error, title] of [
  ['forbidden', { status: 403, message: 'Permission denied' }, /无权读取/],
  ['network', { message: '网络连接失败' }, /暂时无法读取/],
] as const) {
  test(`${label} metadata failure is visible and never treated as an empty library`, async t => {
    const f = await setup(t, error)
    assert.match(f.vm.kbLoadError.title, title)
    assert.equal(f.vm.kbInfo, null)
    assert.equal(f.hook.getKnowled.mock.callCount(), 0)
    assert.equal(f.vm.shownKbTab, 'wiki')
    f.fail(undefined)
    await f.vm.loadKnowledgeBaseInfo('wiki-kb', true)
    assert.equal(f.vm.kbLoadError, null)
    assert.equal(f.vm.kbInfo.id, 'wiki-kb')
    assert.ok(f.hook.getKnowled.mock.callCount() > 0)
    assert.equal(f.route.query.tab, 'wiki')
  })
}

test('a successful empty library remains distinct from an unavailable remote library', async t => {
  const f = await setup(t)
  assert.equal(f.vm.kbLoadError, null)
  assert.equal(f.vm.kbInfo.id, 'wiki-kb')
  assert.ok(f.hook.getKnowled.mock.callCount() > 0)
  assert.equal(f.hook.cardList.value.length, 0)
})

test('a slow earlier metadata failure cannot overwrite a successful retry', async t => {
  const f = await setup(t)
  let reject!: (error: unknown) => void
  f.read(() => new Promise((_resolve, no) => { reject = no }))
  const earlier = f.vm.loadKnowledgeBaseInfo('wiki-kb', true)
  f.read(async () => ({ data: base() }))
  await f.vm.loadKnowledgeBaseInfo('wiki-kb', true)
  reject({ status: 404 }); await earlier
  assert.equal(f.vm.kbLoadError, null)
  assert.equal(f.vm.kbInfo.id, 'wiki-kb')
  assert.equal(f.vm.kbLoading, false)
})

test('the native deleted-library error is recognized without misclassifying unrelated bad requests', async t => {
  const f = await setup(t, { status: 400, error_code: 1001, message: 'COMMON_BAD_REQUEST: knowledge base not found (errorCode=1001)' })
  assert.match(f.vm.kbLoadError.title, /不存在/)
  f.fail({ status: 400, error_code: 1001, message: 'invalid request parameter' })
  await f.vm.loadKnowledgeBaseInfo('wiki-kb', true)
  assert.match(f.vm.kbLoadError.title, /暂时无法读取/)
})
