import assert from 'node:assert/strict'
import test from 'node:test'
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

