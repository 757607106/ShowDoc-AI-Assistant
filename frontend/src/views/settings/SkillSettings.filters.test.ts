import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture'
import { matchesResourceQuery } from '../../utils/resourceListSearch'
import type { SkillCatalogItem } from '../../api/skill'
import { ref } from 'vue'
import * as skillTarget from '../../utils/skillTarget'
import * as skillUpgrade from '../../utils/skillUpgrade'

function item(id: string): SkillCatalogItem {
  return { id, name: id, description: '', created_at: '', updated_at: '', installations: [] }
}
async function setup(t: TestContext, initial: SkillCatalogItem[] = []) {
  let catalog = initial
  const writes: any[] = [], errors: string[] = [], successes: string[] = []
  let releaseRegistration: (() => void) | undefined
  let deletion: { onConfirm: () => Promise<void> } | undefined
  const mounted = fixture(t).component(new URL('./SkillSettings.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key, te: () => false, locale: ref('en-US') }) },
    'tdesign-vue-next': { MessagePlugin: { error: (message: string) => errors.push(message), success: (message: string) => successes.push(message), warning() {} } },
    'tdesign-icons-vue-next': {},
    '@/components/settings/useConfirmDelete': { useConfirmDelete: () => (value: typeof deletion) => { deletion = value } },
    '@/utils/resourceListSearch': { matchesResourceQuery },
    '@/utils': { MAX_SKILL_BUNDLE_SIZE_MB: 100, MAX_SKILL_BUNDLE_SIZE_BYTES: 100 * 1024 * 1024 },
    '@/types/mention': { SKILL_ICON: 'tools' },
    '@/stores/ui': { useUIStore: () => ({}) },
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({ ensureLoaded: async () => {}, isSupported: (key: string) => key.endsWith('.remote') }) },
    '@/composables/useSkillInstallerModel': { useSkillInstallerModel: () => ({ installerModelId: ref(''), savingInstallerModel: ref(false), loadInstallerModel: async () => {}, persistInstallerModel: async () => {} }) },
    '@/composables/useConfigSkillInstallProgress': { useConfigSkillInstallProgress: () => ({ percentOf: () => null, sync() {}, stopAll() {} }) },
    '@/api/system': { listSandboxConfigs: async () => ({ data: [], workspace_scripts_disabled: true }), isNamedSandboxBackend: (type: string) => ['cube', 'e2b', 'docker'].includes(type) },
    '@/utils/skillTarget': skillTarget,
    '@/utils/skillUpgrade': skillUpgrade,
    '@/api/skill': {
      listSkillCatalog: async () => ({ data: catalog }),
      registerSkillCatalogFromFile: async (file: any, progress: (value: number) => void) => {
        writes.push({ file }); progress(50)
        await new Promise<void>(resolve => { releaseRegistration = resolve })
        return { data: item('registered') }
      },
      registerSkillCatalogFromSource: async (source: string) => { writes.push({ source }); return { data: item('registered') } },
      installSkillCatalog: async (id: string, targets: string[]) => { writes.push({ installed: id, targets: Array.from(targets) }); throw new Error('Installation unsupported') },
      deleteSkillCatalog: async (id: string) => { writes.push({ deleted: id }); catalog = catalog.filter(row => row.id !== id) },
    },
  })
  await flush()
  return { ...mounted, writes, errors, successes,
    finishRegistration: () => releaseRegistration!(),
    confirmDelete: () => deletion!.onConfirm(),
    reload: async (rows: SkillCatalogItem[]) => { catalog = rows; await mounted.vm.loadCatalog(true) },
  }
}
const ids = (vm: any) => Array.from(vm.filteredCatalog, (row: any) => row.id)

test('a ZIP registers once and advances the official wizard without installing', async t => {
  const f = await setup(t)
  assert.equal(f.vm.addPrimaryDisabled, true)
  await f.vm.openAdd()
  const file = { name: 'skill.zip', size: 100 }
  f.vm.acceptPendingFile(file)
  assert.equal(f.vm.pendingFile.name, 'skill.zip')
  assert.equal(f.vm.addPrimaryDisabled, false)
  const registration = f.vm.handleAddPrimary()
  assert.equal(f.vm.addBusy, true)
  assert.equal(f.vm.uploadPercent, 50)
  await f.vm.handleAddPrimary()
  assert.equal(f.writes.length, 1)
  assert.equal(f.writes[0].file.name, 'skill.zip')
  f.finishRegistration(); await registration
  assert.equal(f.vm.addBusy, false)
  assert.equal(f.vm.showAdd, true)
  assert.equal(f.vm.addStep, 1)
  assert.equal(f.vm.registeredCatalog.id, 'registered')
  assert.deepEqual(Array.from(f.vm.addTargetIds), [])
  await f.vm.handleAddPrimary()
  assert.equal(f.vm.showAdd, false)
  assert.deepEqual(f.errors, [])
})

test('registration accepts a trimmed source and rejects unsupported or oversized files', async t => {
  const f = await setup(t)
  f.vm.acceptPendingFile({ name: 'installer.sh', size: 100 })
  f.vm.acceptPendingFile({ name: 'SKILL.md', size: 100 })
  f.vm.acceptPendingFile({ name: 'large.zip', size: 100 * 1024 * 1024 + 1 })
  assert.equal(f.vm.pendingFile, null)
  assert.deepEqual(f.errors, ['settings.sandbox.skillUploadFailed', 'settings.sandbox.skillUploadFailed', 'settings.sandbox.skillBundleTooLarge'])
  f.vm.acceptPendingFile({ name: 'allowed.ZIP', size: 100 * 1024 * 1024 })
  assert.equal(f.vm.pendingFile.name, 'allowed.ZIP')
  f.vm.pendingFile = null
  f.vm.sourceInput = '  https://example.com/skill.zip  '
  await f.vm.handleAddPrimary()
  assert.deepEqual(f.writes, [{ source: 'https://example.com/skill.zip' }])
})

test('an unsupported installation stays uninstalled and surfaces the server error', async t => {
  const f = await setup(t, [item('skill')])
  f.vm.records = [{ id: 'managed', name: 'Managed', sandbox_type: 'docker', config: { sandbox_type: 'docker' } }]
  f.vm.installCatalog = f.vm.catalog[0]
  f.vm.installTargetIds = ['managed']
  f.vm.installerModelId = 'model'
  f.vm.showInstall = true
  await f.vm.confirmInstall()
  assert.deepEqual(f.writes, [{ installed: 'skill', targets: ['managed'] }])
  assert.deepEqual(f.errors, ['Installation unsupported'])
  assert.deepEqual(f.successes, [])
  assert.equal(f.vm.installing, false)
  assert.equal(f.vm.showInstall, true)
  assert.equal(f.vm.catalog[0].installations.length, 0)
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
