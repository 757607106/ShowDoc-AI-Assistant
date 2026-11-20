import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../test-utils/vueFixture.ts'
import * as presentation from '../utils/platformPresentation.ts'

const snapshot = (id: string, scope = 'a', active = false) => ({ id, scope, active, job_id: 'capture-' + id, version_ids: ['one', 'two'], created_at: '2026-11-17T10:00:00Z' })
const plain = (value: any) => JSON.parse(JSON.stringify(value))

async function setup(t: TestContext, options: {
  embedded?: boolean; writable?: boolean; names?: boolean
  releases?: (scope?: string) => Promise<any>
  mappings?: (params: any) => Promise<any>
  activate?: (id: string) => Promise<any>
  download?: () => Promise<any>
} = {}) {
  const f = fixture(t), reads: any[] = [], writes: string[] = [], downloads: any[] = [], routes: any[] = [], shown: string[] = []
  let nameReads = 0, confirmations = 0, confirm = true
  Object.assign(f.window, { confirm: (message: string) => { confirmations++; assert.match(message, /旧内容覆盖/); return confirm } })
  const mounted = f.component(new URL('./ReleasesView.vue', import.meta.url), {
    'vue-router': { useRouter: () => ({ push: (route: any) => routes.push(plain(route)) }) },
    '@/stores/auth': { useAuthStore: () => ({ hasRole: () => options.writable !== false }) },
    '@/utils/platformPresentation': presentation,
    '@/api/knowledgeSpaces': { getSpaces: async () => { nameReads++; return { spaces: [{ scope: 'a', name: 'A' }] } } },
    '@/utils/request': { get: async (path: string, config: any) => { reads.push({ path, ...plain(config.params) }); return options.mappings ? options.mappings(config.params) : { mappings: [{ scope: config.params.space_scope, source_id: 'one', target_mode: 'wiki', official: { name: '手册', ingest_status: 'succeeded' } }], total: 41 } } },
    '@/api/backend': {
      releases: async (scope?: string) => { reads.push({ history: scope }); return options.releases ? options.releases(scope) : { releases: [snapshot('old', scope)] } },
      activateRelease: async (id: string) => { writes.push(id); return options.activate?.(id) },
      releaseDownloadUrl: (id: string) => '/api/releases/' + id + '/download',
      downloadFile: async (url: string, name: string) => { downloads.push({ url, name }); return options.download?.() },
    },
  }, { embedded: options.embedded !== false, scope: 'a', ...(options.names ? {} : { spaces: [{ scope: 'a', name: 'A' }] }), onShowTask: (id: string) => shown.push(id) })
  await flush()
  return { ...mounted, props: mounted.vm.$.props, reads, writes, downloads, routes, shown, nameReads: () => nameReads, confirmations: () => confirmations, confirm: (value: boolean) => { confirm = value } }
}

test('embedded history uses the supplied scope and names; document states load only when expanded and preserve paging', async t => {
  const f = await setup(t)
  assert.deepEqual(plain(f.reads), [{ history: 'a' }]); assert.equal(f.nameReads(), 0)
  assert.equal(f.vm.releases[0].version_ids.length, 2)
  f.vm.expanded = ['documents']; await flush()
  assert.deepEqual(f.reads[1], { path: '/api/kb/sync-mappings', space_scope: 'a', page: 1, page_size: 20 })
  assert.equal(f.vm.mappings[0].official.ingest_status, 'succeeded'); assert.equal(f.vm.mappingTotal, 41)
  f.vm.changeMappingPage(3); await flush()
  assert.equal(f.reads.at(-1).page, 3)
  f.vm.openDetails(f.vm.releases[0]); f.vm.showTask(f.vm.detail)
  assert.deepEqual(f.shown, ['capture-old']); assert.equal(f.vm.detail, null); assert.deepEqual(f.routes, [])
})

test('scope changes reset details and mapping page; delayed old history and mapping responses cannot replace the current scope', async t => {
  let oldHistory!: (value: any) => void, oldMappings!: (value: any) => void
  const f = await setup(t, {
    releases: async scope => scope === 'a' ? new Promise(resolve => { oldHistory = resolve }) : { releases: [snapshot('new', scope)] },
    mappings: async params => params.space_scope === 'a' ? new Promise(resolve => { oldMappings = resolve }) : { mappings: [{ scope: 'b', source_id: 'new', target_mode: 'graph' }], total: 1 },
  })
  f.vm.openDetails(snapshot('old')); f.vm.expanded = ['documents']; f.vm.mappingPage = 3; await flush()
  f.props.scope = 'b'; await flush()
  assert.equal(f.vm.detail, null); assert.equal(f.vm.mappingPage, 1)
  assert.equal(f.vm.releases[0].scope, 'b'); assert.equal(f.vm.mappings[0].scope, 'b')
  oldHistory({ releases: [snapshot('old')] }); oldMappings({ mappings: [{ scope: 'a', source_id: 'old', target_mode: 'wiki' }], total: 99 }); await flush()
  assert.equal(f.vm.releases[0].id, 'new'); assert.equal(f.vm.mappings[0].source_id, 'new'); assert.equal(f.vm.mappingTotal, 1)
  assert.equal(f.vm.loading, false); assert.equal(f.vm.mappingLoading, false)
})

test('historical resubmission requires confirmation and cannot dispatch twice while pending', async t => {
  let finish!: () => void, active = false
  const f = await setup(t, {
    releases: async scope => ({ releases: [snapshot('old', scope, active)] }),
    activate: async () => { await new Promise<void>(resolve => { finish = resolve }); active = true },
  })
  f.vm.openDetails(f.vm.releases[0]); f.confirm(false); await f.vm.activate('old')
  assert.equal(f.writes.length, 0)
  f.confirm(true); const pending = f.vm.activate('old'); await f.vm.activate('old')
  assert.deepEqual(f.writes, ['old']); assert.equal(f.vm.busy, 'old')
  finish(); await pending
  assert.equal(f.vm.detail.active, true); assert.equal(f.vm.busy, '')
  await f.vm.activate('old'); assert.deepEqual(f.writes, ['old'], 'current snapshots cannot be resubmitted as historical snapshots')
})

test('read-only users cannot resubmit and a rejected download remains visible in snapshot details', async t => {
  const f = await setup(t, { writable: false, download: async () => { throw new Error('HTTP 404 /api/releases/old/download') } })
  f.vm.openDetails(f.vm.releases[0]); await f.vm.activate('old')
  assert.deepEqual(f.writes, []); assert.equal(f.confirmations(), 0)
  await f.vm.download('old')
  assert.deepEqual(f.downloads, [{ url: '/api/releases/old/download', name: 'old.zip' }])
  assert.equal(f.vm.detailError, '暂时无法下载资料包。'); assert.equal(f.vm.downloading, '')
})

test('history and document-state failures are independent', async t => {
  const f = await setup(t, { releases: async () => { throw new Error('历史不可用') }, mappings: async () => ({ mappings: [{ scope: 'a', source_id: 'one', target_mode: 'wiki' }], total: 1 }) })
  assert.equal(f.vm.error, '历史不可用')
  f.vm.expanded = ['documents']; await flush()
  assert.equal(f.vm.mappings.length, 1); assert.equal(f.vm.mappingError, '')
})

test('closed components ignore later history failures', async t => {
  let fail!: (error: Error) => void
  const delayed = await setup(t, { releases: async () => new Promise((_, reject) => { fail = reject }) })
  delayed.close(); fail(new Error('迟到的错误')); await flush()
  assert.equal(delayed.vm.error, '')
})

test('standalone compatibility resolves names and opens the trigger task in the unified page', async t => {
  const f = await setup(t, { embedded: false, names: true })
  assert.equal(f.nameReads(), 1)
  f.vm.showTask(snapshot('old'))
  assert.deepEqual(f.routes, [{ path: '/platform/tasks', query: { task: 'capture-old', space: 'a' } }])
})
