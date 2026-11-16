import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

const config = (kb = 'one') => ({ knowledge_base_id: kb, review_enabled: false, high_threshold: 0.73,
  rewrite_enabled: true, conflict_detection_enabled: false, rewrite_auto_ingest_enabled: true, max_rewrite_iterations: 3 })
async function setup(t: TestContext, canEdit = true, read?: (kb: string) => Promise<any>) {
  const f = fixture(t), writes: any[] = [], reads: string[] = []
  let stored = config()
  const { vm } = f.component(new URL('./ContextDBReviewSettings.vue', import.meta.url), {
    '@/api/contextdb': { nativeAPI: {
      get: async (path: string, params: any) => { assert.equal(path, 'knowledge/review_settings'); reads.push(params.knowledge_base_id); return read ? read(params.knowledge_base_id) : { data: stored } },
      patch: async (path: string, body: any) => { assert.equal(path, 'knowledge/review_settings'); writes.push(body); stored = { ...stored, ...body }; return { data: body } },
    } },
  }, { kbId: 'one', canEdit })
  await flush(); return { vm, props: vm.$.props, writes, reads, setStored: (value: any) => { stored = { ...stored, ...value } } }
}
test('settings use the official values and re-read after saving without sending metadata or reserved thresholds', async t => {
  const { vm, writes, reads } = await setup(t)
  assert.equal(vm.settings.high_threshold, 0.73); assert.equal(vm.settings.review_enabled, false)
  vm.settings.review_enabled = true; await vm.save()
  assert.deepEqual(JSON.parse(JSON.stringify(writes)), [{ knowledge_base_id: 'one', review_enabled: true }])
  assert.deepEqual(reads, ['one', 'one', 'one']); assert.equal(vm.settings.high_threshold, 0.73); assert.equal(vm.notice, '配置已保存')
  assert.equal(vm.dirty, false)
})
test('unchanged settings stay disabled, read-only callers cannot write, and invalid thresholds never reach the API', async t => {
  const f = await setup(t, false); await f.vm.save(); assert.equal(f.writes.length, 0)
  f.props.canEdit = true; await flush()
  assert.equal(f.vm.dirty, false); await f.vm.save(); assert.equal(f.writes.length, 0)
  for (const value of [-0.1, 1.1, NaN]) { f.vm.settings.high_threshold = value; await f.vm.save() }
  assert.equal(f.writes.length, 0)
  for (const value of [0, 1]) { f.vm.settings.high_threshold = value; await f.vm.save() }
  assert.equal(f.writes.length, 2)
})
test('late responses from a previous knowledge base cannot replace the current settings', async t => {
  let complete!: (value: any) => void
  const f = await setup(t, true, kb => kb === 'one' ? new Promise(resolve => { complete = resolve }) : Promise.resolve({ data: config(kb) }))
  f.props.kbId = 'two'; await flush(); assert.equal(f.vm.settings.knowledge_base_id, 'two')
  complete({ data: config('one') }); await flush(); assert.equal(f.vm.settings.knowledge_base_id, 'two')
})
test('a failed read never creates local defaults or enables saving', async t => {
  const failed = await setup(t, true, async () => { throw new Error('unavailable') })
  await failed.vm.save(); assert.equal(failed.vm.settings, null); assert.equal(failed.writes.length, 0); assert.equal(failed.vm.error, 'unavailable')
})
test('mismatched library settings cannot be saved', async t => {
  const mismatch = await setup(t, true, async () => ({ data: config('other') }))
  await mismatch.vm.save(); assert.equal(mismatch.vm.settings, null); assert.equal(mismatch.writes.length, 0)
})
test('an external change to an edited setting blocks the write without discarding the draft', async t => {
  const f = await setup(t)
  f.vm.settings.high_threshold = 0.9; f.setStored({ high_threshold: 0.8 }); await f.vm.save()
  assert.equal(f.writes.length, 0); assert.match(f.vm.error, /已被更新/)
  assert.equal(f.vm.settings.high_threshold, 0.9); assert.equal(f.vm.dirty, true)
})
test('patching only edited fields preserves external changes and hidden policy fields', async t => {
  const f = await setup(t)
  f.vm.settings.review_enabled = true
  f.setStored({ high_threshold: 0.92, max_rewrite_iterations: 7, conflict_detection_enabled: true })
  await f.vm.save()
  assert.deepEqual(JSON.parse(JSON.stringify(f.writes)), [{ knowledge_base_id: 'one', review_enabled: true }])
  assert.equal(f.vm.settings.high_threshold, 0.92); assert.equal(f.vm.dirty, false)
  assert.equal(f.vm.settings.max_rewrite_iterations, undefined)
  assert.equal(f.vm.settings.conflict_detection_enabled, undefined)
})
test('switching libraries while checking for external changes cannot submit the old draft', async t => {
  let checks = 0, complete!: (value: any) => void
  const f = await setup(t, true, async kb => {
    if (kb === 'one' && ++checks === 2) return new Promise(resolve => { complete = resolve })
    return { data: config(kb) }
  })
  f.vm.settings.review_enabled = true; const pending = f.vm.save()
  f.props.kbId = 'two'; await flush(); complete({ data: config('one') }); await pending
  assert.equal(f.writes.length, 0); assert.equal(f.vm.settings.knowledge_base_id, 'two')
})
