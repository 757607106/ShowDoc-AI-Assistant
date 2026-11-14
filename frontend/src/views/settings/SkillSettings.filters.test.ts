import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture'
import { matchesResourceQuery } from '../../utils/resourceListSearch'
import type { SkillCatalogItem } from '../../api/skill'

function item(id: string): SkillCatalogItem {
  return { id, name: id, description: '', created_at: '', updated_at: '', installations: [] }
}
async function setup(t: TestContext, initial: SkillCatalogItem[] = []) {
  let catalog = initial
  const writes: any[] = [], errors: string[] = []
  let releaseRegistration: (() => void) | undefined
  let deletion: { onConfirm: () => Promise<void> } | undefined
  const mounted = fixture(t).component(new URL('./SkillSettings.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    'tdesign-vue-next': { MessagePlugin: { error: (message: string) => errors.push(message), success() {} } },
    'tdesign-icons-vue-next': {},
    '@/components/settings/useConfirmDelete': { useConfirmDelete: () => (value: typeof deletion) => { deletion = value } },
    '@/utils/resourceListSearch': { matchesResourceQuery },
    '@/utils': { MAX_SKILL_BUNDLE_SIZE_MB: 100 },
    '@/types/mention': { SKILL_ICON: 'tools' },
    '@/api/skill': {
      listSkillCatalog: async () => ({ data: catalog }),
      registerSkillCatalogFromFile: async (file: any, progress: (value: number) => void) => {
        writes.push({ file }); progress(50)
        await new Promise<void>(resolve => { releaseRegistration = resolve })
      },
      registerSkillCatalogFromSource: async (source: string) => { writes.push({ source }) },
      deleteSkillCatalog: async (id: string) => { writes.push({ deleted: id }); catalog = catalog.filter(row => row.id !== id) },
    },
  })
  await flush()
  return { ...mounted, writes, errors,
    finishRegistration: () => releaseRegistration!(),
    confirmDelete: () => deletion!.onConfirm(),
    reload: async (rows: SkillCatalogItem[]) => { catalog = rows; await mounted.vm.loadCatalog(true) },
  }
}
const ids = (vm: any) => Array.from(vm.filteredCatalog, (row: any) => row.id)

test('a SKILL.md registers directly, prevents duplicate submission, and clears upload state', async t => {
  const f = await setup(t)
  assert.equal(f.vm.addPrimaryDisabled, true)
  f.vm.openAdd()
  const file = { name: 'SKILL.md', size: 100 }
  f.vm.acceptPendingFile(file)
  assert.equal(f.vm.pendingFile.name, 'SKILL.md')
  assert.equal(f.vm.addPrimaryDisabled, false)
  const registration = f.vm.registerCatalog()
  assert.equal(f.vm.addBusy, true)
  assert.equal(f.vm.uploadPercent, 50)
  await f.vm.registerCatalog()
  assert.equal(f.writes.length, 1)
  assert.equal(f.writes[0].file.name, 'SKILL.md')
  f.finishRegistration(); await registration
  assert.equal(f.vm.addBusy, false)
  assert.equal(f.vm.showAdd, false)
  assert.equal(f.vm.uploadPercent, 0)
  assert.deepEqual(f.errors, [])
})

test('registration accepts a trimmed source and rejects unsupported or oversized files', async t => {
  const f = await setup(t)
  f.vm.acceptPendingFile({ name: 'installer.sh', size: 100 })
  f.vm.acceptPendingFile({ name: 'large.zip', size: 100 * 1024 * 1024 })
  assert.equal(f.vm.pendingFile, null)
  assert.deepEqual(f.errors, ['settings.sandbox.skillUploadFailed', 'settings.sandbox.skillBundleTooLarge'])
  f.vm.sourceInput = '  https://example.com/skill.zip  '
  await f.vm.registerCatalog()
  assert.deepEqual(f.writes, [{ source: 'https://example.com/skill.zip' }])
  f.vm.acceptPendingFile({ name: 'allowed.ZIP', size: 99 * 1024 * 1024 })
  assert.equal(f.vm.pendingFile.name, 'allowed.ZIP')
})

test('skill search preserves row identity and opens files for the selected catalog entry', async t => {
  const data = [item('财务 Report'), item('other'), item('mixed')]
  data[2]!.description = '财务 REPORT'
  const f = await setup(t, data)
  f.vm.query = ' 财务 report '
  assert.deepEqual(ids(f.vm), ['财务 Report', 'mixed'])
  assert.equal(f.vm.filteredCatalog[1], f.vm.catalog[2])
  f.vm.openCatalogFiles(f.vm.filteredCatalog[1])
  assert.equal(f.vm.filesCatalogId, 'mixed')
  assert.equal(f.vm.filesDrawerVisible, true)
  assert.equal(f.vm.catalog.length, 3)
  f.vm.query = 'missing'
  assert.deepEqual(ids(f.vm), [])
  f.vm.query = '  '
  assert.deepEqual(ids(f.vm), data.map(row => row.id))
})

test('skill search follows catalog reloads while retaining the search query', async t => {
  const f = await setup(t, [item('report'), item('other')])
  f.vm.query = 'report'
  const updated = item('new'); updated.description = 'Report tools'
  await f.reload([item('other'), updated])
  assert.deepEqual(ids(f.vm), ['new'])
  assert.equal(f.vm.query, 'report')
  await f.reload([])
  assert.deepEqual(ids(f.vm), [])
})

test('deleting a catalog entry waits for confirmation and refreshes the list', async t => {
  const f = await setup(t, [item('first'), item('second')])
  f.vm.askDelete(f.vm.catalog[0])
  assert.equal(f.writes.length, 0)
  await f.confirmDelete()
  assert.deepEqual(f.writes, [{ deleted: 'first' }])
  assert.deepEqual(ids(f.vm), ['second'])
  assert.equal(f.vm.deletingId, '')
})
