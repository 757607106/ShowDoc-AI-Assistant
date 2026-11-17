import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { reactive } from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture'
import { matchesResourceQuery } from '../../utils/resourceListSearch'
import type { SkillCatalogItem } from '../../api/skill'

function item(id: string): SkillCatalogItem {
  return { id, name: id, description: '', created_at: '', updated_at: '' }
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
async function setup(t: TestContext, initial: SkillCatalogItem[] = [], admin = true) {
  let catalog = initial, readError = '', writeError = ''
  let nextRead: Promise<{data: SkillCatalogItem[]}> | undefined
  const writes: any[] = [], errors: string[] = [], successes: string[] = []
  const auth = reactive({user: {id: 'first'}, hasRole: () => admin})
  let releaseRegistration: (() => void) | undefined
  let deletion: {onConfirm: () => Promise<void>} | undefined
  const mounted = fixture(t).component(new URL('./SkillSettings.vue', import.meta.url), {
    'vue-i18n': {useI18n: () => ({t: (key: string) => key})},
    'tdesign-vue-next': {MessagePlugin: {error: (message: string) => errors.push(message), success: (message: string) => successes.push(message)}},
    'tdesign-icons-vue-next': {},
    '@/stores/auth': {useAuthStore: () => auth},
    '@/components/settings/useConfirmDelete': {useConfirmDelete: () => (value: typeof deletion) => {deletion = value}},
    '@/utils/resourceListSearch': {matchesResourceQuery},
    '@/utils': {MAX_SKILL_BUNDLE_SIZE_MB: 100, MAX_SKILL_BUNDLE_SIZE_BYTES: 100 * 1024 * 1024},
    '@/types/mention': {SKILL_ICON: 'tools'},
    '@/api/skill': {
      listSkillCatalog: async () => {
        if (nextRead) {const pending = nextRead; nextRead = undefined; return pending}
        if (readError) throw new Error(readError)
        return {data: catalog}
      },
      registerSkillCatalogFromFile: async (file: any, progress: (value: number) => void) => {
        writes.push({file}); progress(50)
        await new Promise<void>(resolve => {releaseRegistration = resolve})
        if (writeError) throw new Error(writeError)
        catalog = [...catalog, item('registered')]
        return {data: item('registered')}
      },
      registerSkillCatalogFromSource: async (source: string) => {
        writes.push({source})
        if (writeError) throw new Error(writeError)
        catalog = [...catalog, item('registered')]
        return {data: item('registered')}
      },
      deleteSkillCatalog: async (id: string) => {
        writes.push({deleted: id})
        if (writeError) throw new Error(writeError)
        catalog = catalog.filter(row => row.id !== id)
      },
    },
  })
  await flush()
  return {...mounted, writes, errors, successes, auth,
    finishRegistration: () => releaseRegistration!(),
    confirmDelete: () => deletion!.onConfirm(),
    failRead: (message: string) => {readError = message},
    failWrite: (message: string) => {writeError = message},
    delayRead: (value: Promise<{data: SkillCatalogItem[]}>) => {nextRead = value},
    reload: async (rows: SkillCatalogItem[]) => {catalog = rows; await mounted.vm.loadCatalog()},
  }
}
const ids = (vm: any) => Array.from(vm.filteredCatalog, (row: any) => row.id)

test('a ZIP registers once without installation and refreshes the actual directory', async t => {
  const f = await setup(t)
  assert.equal(f.vm.addPrimaryDisabled, true)
  f.vm.openAdd()
  f.vm.acceptPendingFile({name: 'skill.zip', size: 100})
  const registration = f.vm.handleAddPrimary()
  assert.equal(f.vm.addBusy, true); assert.equal(f.vm.uploadPercent, 50)
  f.vm.setAddVisible(false); assert.equal(f.vm.showAdd, true)
  await f.vm.handleAddPrimary(); assert.equal(f.writes.length, 1)
  f.finishRegistration(); await registration
  assert.equal(f.vm.addBusy, false); assert.equal(f.vm.showAdd, false)
  assert.deepEqual(ids(f.vm), ['registered'])
  assert.deepEqual(f.successes, ['settings.skills.registerAccepted'])
})

test('registration accepts a trimmed source and rejects unsupported or oversized files', async t => {
  const f = await setup(t)
  f.vm.acceptPendingFile({name: 'installer.sh', size: 100})
  f.vm.acceptPendingFile({name: 'SKILL.md', size: 100})
  f.vm.acceptPendingFile({name: 'large.zip', size: 100 * 1024 * 1024 + 1})
  assert.equal(f.vm.pendingFile, null)
  assert.deepEqual(f.errors, ['settings.sandbox.skillUploadFailed', 'settings.sandbox.skillUploadFailed', 'settings.sandbox.skillBundleTooLarge'])
  f.vm.acceptPendingFile({name: 'allowed.ZIP', size: 100 * 1024 * 1024})
  assert.equal(f.vm.pendingFile.name, 'allowed.ZIP')
  f.vm.pendingFile = null; f.vm.sourceInput = '  https://example.com/skill.zip  '
  await f.vm.handleAddPrimary()
  assert.deepEqual(f.writes, [{source: 'https://example.com/skill.zip'}])
})

test('failed import retains its draft and never claims success', async t => {
  const f = await setup(t)
  f.vm.openAdd(); f.vm.sourceInput = 'https://example.com/skill.zip'; f.failWrite('Invalid archive')
  await f.vm.handleAddPrimary()
  assert.equal(f.vm.showAdd, true); assert.equal(f.vm.sourceInput, 'https://example.com/skill.zip')
  assert.deepEqual(f.errors, ['Invalid archive']); assert.deepEqual(f.successes, [])
  assert.deepEqual(ids(f.vm), []); assert.equal(f.vm.addBusy, false)
})

test('skill search preserves row identity and opens files for the selected catalog entry', async t => {
  const data = [item('财务 Report'), item('other'), item('mixed')]
  data[2]!.description = '财务 REPORT'
  const f = await setup(t, data)
  f.vm.query = ' 财务 report '
  assert.deepEqual(ids(f.vm), ['财务 Report', 'mixed'])
  assert.equal(f.vm.filteredCatalog[1], f.vm.catalog[2])
  f.vm.openCatalogFiles(f.vm.filteredCatalog[1])
  assert.equal(f.vm.filesCatalogId, 'mixed'); assert.equal(f.vm.filesDrawerVisible, true)
  const updated = item('new'); updated.description = '财务 Report tools'
  await f.reload([item('other'), updated])
  assert.deepEqual(ids(f.vm), ['new']); assert.equal(f.vm.query, ' 财务 report ')
})

test('deletion waits for confirmation and preserves a historically referenced directory on failure', async t => {
  const f = await setup(t, [item('first'), item('second')])
  f.vm.askDelete(f.vm.catalog[0]); assert.equal(f.writes.length, 0)
  f.failWrite('Historical reference'); await f.confirmDelete()
  assert.deepEqual(ids(f.vm), ['first', 'second']); assert.deepEqual(f.errors, ['Historical reference'])
  f.failWrite(''); f.vm.askDelete(f.vm.catalog[1]); await f.confirmDelete()
  assert.deepEqual(ids(f.vm), ['first']); assert.equal(f.vm.deletingId, '')
})

test('read-only users can browse files without catalog write operations', async t => {
  const f = await setup(t, [item('visible')], false)
  f.vm.openAdd(); f.vm.acceptPendingFile({name: 'skill.zip', size: 100}); f.vm.sourceInput = 'https://example.com'
  await f.vm.handleAddPrimary(); f.vm.askDelete(f.vm.catalog[0])
  assert.equal(f.vm.showAdd, false); assert.deepEqual(f.writes, [])
  f.vm.openCatalogFiles(f.vm.catalog[0]); assert.equal(f.vm.filesCatalogId, 'visible')
})

test('a catalog failure can be retried without treating the failure as an empty directory', async t => {
  const f = await setup(t, [item('first')]); f.failRead('offline'); await f.vm.loadCatalog()
  assert.equal(f.vm.error, 'offline'); assert.deepEqual(ids(f.vm), ['first'])
  f.failRead(''); await f.vm.loadCatalog(); assert.equal(f.vm.error, '')
})

test('old account reads and pending deletion confirmation cannot change the new account', async t => {
  const f = await setup(t, [item('first')]), pending = deferred<{data: SkillCatalogItem[]}>()
  f.vm.askDelete(f.vm.catalog[0]); f.delayRead(pending.promise)
  const oldRead = f.vm.loadCatalog()
  f.vm.openCatalogFiles(f.vm.catalog[0]); f.auth.user.id = 'second'; await flush()
  assert.equal(f.vm.filesDrawerVisible, false); assert.equal(f.vm.filesCatalogId, '')
  await f.reload([item('second')]); pending.resolve({data: [item('old response')]}); await oldRead
  await f.confirmDelete()
  assert.deepEqual(ids(f.vm), ['second']); assert.deepEqual(f.writes, [])
})

test('a completed upload from another account cannot update the current catalog or display success', async t => {
  const f = await setup(t)
  f.vm.openAdd(); f.vm.acceptPendingFile({name: 'skill.zip', size: 100})
  const upload = f.vm.handleAddPrimary()
  f.auth.user.id = 'second'; await flush(); await f.reload([item('second')])
  f.finishRegistration(); await upload
  assert.deepEqual(ids(f.vm), ['second']); assert.deepEqual(f.successes, [])
  assert.equal(f.vm.showAdd, false); assert.equal(f.vm.pendingFile, null)
})
