import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import * as sorting from '../../utils/resourceSorting.ts'
import { change, fixture, flush } from '../../test-utils/vueFixture.ts'

test('refreshes data source controls after assistant changes and stops on unmount', async t => {
  const f = fixture(t)
  const listDataSources = t.mock.fn(async (_id: string) => ({ data: [] }))
  const { close } = f.component(new URL('./settings/DataSourceSettings.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error: assert.fail } },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/utils/cronHumanize': {},
    '@/composables/useConnectorLabel': { useConnectorLabel: () => ({ connectorLabel: (type: string) => type }) },
    '@/api/datasource': { listDataSources },
  }, { kbId: 'kb' })
  await flush()
  listDataSources.mock.resetCalls()
  f.emit(change('agent.update'))
  t.mock.timers.tick(300)
  assert.equal(listDataSources.mock.callCount(), 0)
  f.emit(change('data_source.pause'))
  f.emit(change('data_source.sync'))
  f.emit(change('data_source.update_sync'))
  t.mock.timers.tick(300)
  await flush()
  assert.equal(listDataSources.mock.callCount(), 1)
  assert.equal(listDataSources.mock.calls[0].arguments[0], 'kb')
  close()
  f.emit(change('data_source.resume'))
  t.mock.timers.tick(300)
  assert.equal(listDataSources.mock.callCount(), 1)
})

test('refreshes the mounted KB list with force for knowledge_base changes only', async t => {
  const f = fixture(t)
  const fetchKnowledgeBasesForList = t.mock.fn(async (_params: unknown, _force: boolean) => [{ id: 'kb', name: 'Updated KB' }])
  const { vm } = f.component(new URL('./KnowledgeBaseList.vue', import.meta.url), {
    '@/config/contextdb':{IS_CONTEXTDB:false},
    'vue-router': { useRoute: () => ({ query: {} }), useRouter: () => ({}) },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: {} },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => true }) },
    '@/stores/ui': { useUIStore: () => ({}) },
    '@/stores/organization': { useOrganizationStore: () => ({
      sharedKnowledgeBases: [], async fetchOrganizations() {}, async fetchSharedKnowledgeBases() {},
    }) },
    '@/stores/chatResources': { useChatResourcesStore: () => ({ fetchKnowledgeBasesForList }) },
    '@/components/settings/useConfirmDelete': { useConfirmDelete: () => ({}) },
    '@/composables/useTenantModelReadiness': { useTenantModelReadiness: () => ({ loaded: vue.ref(true), isReadyForDocumentKb: vue.ref(true) }) },
    '@/composables/useListUrlState': { useListUrlState: () => ({ scope: vue.ref('all'), creator: vue.ref('all'), query: vue.ref('') }) },
    '@/composables/useResourcePins': { useResourcePins: () => ({ favorites: vue.ref([]), recents: vue.ref([]) }) },
    '@/api/knowledge-base': {}, '@/api/organization': {}, '@/config/contextualGuides': {},
    '@/utils/index': {}, '@/utils/kbPermission': {},
    '@/utils/resourceListSearch': {}, '@/utils/card-list-badge': {}, '@/utils/resourceSorting': sorting,
  })
  await flush()
  fetchKnowledgeBasesForList.mock.resetCalls()
  f.emit(change('unknown.update'))
  t.mock.timers.tick(300)
  assert.equal(fetchKnowledgeBasesForList.mock.callCount(), 0)
  f.emit(change('knowledge_base.generate_profile'))
  t.mock.timers.tick(300)
  await flush()
  assert.equal(fetchKnowledgeBasesForList.mock.callCount(), 1)
  assert.equal(fetchKnowledgeBasesForList.mock.calls[0].arguments[1], true)
  assert.equal(vm.kbs[0].name, 'Updated KB')
})
