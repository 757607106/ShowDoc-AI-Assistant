import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { reactive } from 'vue'
import ts from 'typescript'
import { fixture, flush } from '../../test-utils/vueFixture.ts'
import { spaceName } from '../../utils/platformPresentation.ts'

const apiSource = readFileSync(new URL('../../api/knowledgeSpaces.ts', import.meta.url), 'utf8')
const helpers = ts.transpileModule(apiSource.slice(apiSource.indexOf('export function spaceTargetStatus'), apiSource.indexOf('const spacePath')),
  { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const exported: any = {}
new Function('exports', helpers)(exported)
const { spaceTargetStatus, spaceTargetNotice } = exported

async function setup(t: TestContext, initial: any) {
  const f = fixture(t)
  const route = reactive({ params: { scope: 'product' }, query: { tab: 'wiki', wikiPageId: 'old-page', retained: 'yes' } as Record<string, string> })
  const routes: any[] = [], reads: string[] = []
  let response = initial, permitRoute = true
  const { vm } = f.component(new URL('./ContextDBSpaceDetail.vue', import.meta.url), {
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace: async (value: any) => {
      routes.push(value); if (permitRoute) route.query = value.query
    }, push() {} }) },
    'tdesign-vue-next': { MessagePlugin: { error() {}, warning() {}, success() {} } },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/utils/platformPresentation': { spaceName },
    '@/api/knowledgeSpaces': { spaceTargetStatus, spaceTargetNotice,
      getSpace: async (scope: string) => { reads.push(scope); return { space: response } },
      getSpaces: async () => ({ spaces: [response], available_bases: [] }), submitSpace: async () => ({}), updateSpace: async () => ({ space: response }),
    },
  })
  await flush()
  return { vm, route, routes, reads, response: (value: any) => { response = value }, permit: (value: boolean) => { permitRoute = value } }
}
const space = (status: string, id: string | null = null) => ({ scope: 'product', name: '产品知识', graph_enabled: true,
  wiki_kb_id: id, graph_kb_id: 'graph', targets: { wiki: { status, knowledge_base_id: id, ...(status === 'missing' ? { missing_knowledge_base_id: 'deleted' } : {}) }, graph: { status: 'available', knowledge_base_id: 'graph' } } })

test('deleted libraries stop mounting content while healthy graph targets and preserved history remain selectable', async t => {
  const f = await setup(t, space('missing'))
  assert.equal(f.vm.nativeId, null)
  assert.equal(f.vm.unavailable, true)
  assert.match(f.vm.targetNotice, /Wiki.*(不存在|删除)/)
  f.vm.tab = 'graph'; await flush()
  assert.equal(f.vm.nativeId, 'graph')
  f.vm.tab = 'progress'; await flush()
  assert.equal(f.vm.tab, 'progress')
})

for (const status of ['forbidden', 'unknown']) test(`${status} libraries remain distinguishable from deletion and never mount stale contents`, async t => {
    const f = await setup(t, space(status, 'original'))
    assert.equal(f.vm.space.wiki_kb_id, 'original')
    assert.equal(f.vm.nativeId, null)
    assert.doesNotMatch(f.vm.targetNotice, /删除/)
    assert.equal(f.vm.targetStatus, status)
})

test('a restored target clears only old resource links and refresh cannot discard a live draft', async t => {
  const f = await setup(t, space('missing'))
  f.response(space('available', 'new-wiki'))
  await f.vm.load(); await flush()
  assert.equal(f.vm.nativeId, 'new-wiki')
  assert.deepEqual({ ...f.route.query }, { tab: 'wiki', retained: 'yes' })
  f.vm.knowledgeRef = { canRefresh: () => false }
  const count = f.reads.length
  await f.vm.load()
  assert.equal(f.reads.length, count)
})

test('outer tab changes wait for route approval so a Wiki guard can keep its editor mounted', async t => {
  const f = await setup(t, space('available', 'wiki'))
  f.permit(false)
  f.vm.tab = 'documents'; await flush()
  assert.equal(f.vm.tab, 'wiki')
  assert.equal(f.route.query.wikiPageId, 'old-page')
})

test('renaming a business space updates the mounted switcher alongside the page title', async t => {
  const f = await setup(t, space('available', 'wiki'))
  const renamed = { ...space('available', 'wiki'), name: '新的产品资料' }
  f.response(renamed); f.vm.name = renamed.name
  await f.vm.save(); await flush()
  assert.equal(f.vm.space.name, renamed.name)
  assert.equal(f.vm.spaces.find((item: any) => item.id === 'product').name, renamed.name)
  assert.equal(f.vm.nativeId, 'wiki')
})
