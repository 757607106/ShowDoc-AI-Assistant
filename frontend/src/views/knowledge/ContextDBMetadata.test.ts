import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

async function setup(t: TestContext, metadata: Record<string, unknown> = {}, overrides: Record<string, unknown> = {}) {
  const f = fixture(t), updates: string[] = [], saves: string[] = [], closes: boolean[] = []
  let vm: any
  ;({ vm } = f.component(new URL('./ContextDBMetadata.vue', import.meta.url), {
    '@/utils/files': { formatFileSize: (value: unknown) => value == null ? '-' : `${value} B` },
    '@/utils/contextdbDocumentName': { documentDisplayName: (value: any) => value?.file_name || value?.name || '' },
    '@/utils/platformPresentation': { contextdbDateTime: (value: unknown) => value ? String(value) : '-' },
  }, {
    document: { id: 'document-1', name: '产品手册.md', metadata },
    canEdit: true, saving: false, error: '', text: JSON.stringify(metadata, null, 2), visible: true,
    'onUpdate:text': (value: string) => updates.push(value),
    onSave: () => saves.push(vm.draftText),
    onClose: () => closes.push(true),
    ...overrides,
  }))
  await flush()
  return { vm, updates, saves, closes }
}

test('metadata stays read only until editing is allowed, and unchanged metadata is never submitted', async t => {
  const f = await setup(t, { product: '保留值' }, { canEdit: false })
  f.vm.startEditing(); f.vm.addField(); f.vm.removeField(0); f.vm.clearFields(); f.vm.updateJson('{"product":"不应写入"}'); f.vm.save()
  assert.equal(f.vm.editing, false)
  assert.deepEqual(JSON.parse(f.vm.draftText), { product: '保留值' })
  assert.equal(f.updates.length, 0)
  assert.equal(f.saves.length, 0)
  f.vm.$.props.canEdit = true
  f.vm.startEditing(); f.vm.save()
  assert.equal(f.vm.editing, true)
  assert.equal(f.vm.dirty, false)
  assert.equal(f.saves.length, 0)
  f.vm.setView('json'); f.vm.updateJson('{ "product" : "保留值" }'); f.vm.save()
  assert.equal(f.vm.dirty, false, 'formatting alone does not replace metadata')
  assert.equal(f.saves.length, 0)
})

test('table edits round trip every supported scalar and array without dropping untouched fields', async t => {
  const original = { product: '手册\\版本"二"', version: 1.25, enabled: false, labels: ['安装', '使用'], values: [0, 2.5], flags: [true, false], empty: [] }
  const f = await setup(t, original)
  f.vm.startEditing()
  f.vm.fields.find((field: any) => field.key === 'version').value = '-4.5'
  f.vm.fields.find((field: any) => field.key === 'enabled').value = 'true'
  f.vm.fields.find((field: any) => field.key === 'values').value = '[1, 2]'
  assert.equal(f.vm.syncFields(), true)
  assert.equal(f.vm.validationError, '')
  const expected = { ...original, version: -4.5, enabled: true, values: [1, 2] }
  assert.deepEqual(JSON.parse(f.vm.draftText), expected)
  assert.deepEqual(JSON.parse(f.updates.at(-1)!), expected)
  assert.deepEqual(JSON.parse(JSON.stringify(f.vm.changes)), { added: 0, modified: 3, deleted: 0 })
  f.vm.save()
  assert.equal(f.saves.length, 1)
  assert.deepEqual(JSON.parse(f.saves[0]), expected)
})

test('table values must match their selected type before a replacement object is emitted', async t => {
  const f = await setup(t, { count: 1, retained: '保留' })
  f.vm.startEditing()
  const field = f.vm.fields.find((item: any) => item.key === 'count')
  field.value = '"not a number"'
  assert.equal(f.vm.syncFields(), false)
  assert.deepEqual(JSON.parse(f.vm.draftText), { count: 1, retained: '保留' })
  field.type = 'number[]'; field.value = '[1,"2"]'
  assert.equal(f.vm.syncFields(), false)
  assert.ok(f.vm.validationError)
  field.value = '[1,2]'
  assert.equal(f.vm.syncFields(), true)
  assert.deepEqual(JSON.parse(f.vm.draftText), { count: [1, 2], retained: '保留' })
})

test('metadata validation rejects unsupported values and enforces official key and value limits', async t => {
  const f = await setup(t)
  f.vm.startEditing(); f.vm.setView('json')
  const invalid = [
    'null', '[]', '{"nested": {"child": true}}', '{"nested": [["value"]]}', '{"missing": null}',
    '{"mixed": [1, "2"]}', '{"mixed": [true, 1]}', '{"number": 1e309}',
    JSON.stringify({ ['x'.repeat(65)]: 'value' }), JSON.stringify({ '   ': 'value' }),
    JSON.stringify({ text: 'x'.repeat(4097) }), JSON.stringify({ array: Array(101).fill('x') }),
    JSON.stringify(Object.fromEntries(Array.from({ length: 33 }, (_, index) => [`field-${index}`, index]))),
    ...['source_type', 'content_hash', 'snapshot_id', 'toc_path'].map(key => JSON.stringify({ [key]: 'reserved' })),
  ]
  for (const text of invalid) {
    f.vm.updateJson(text)
    assert.ok(f.vm.validationError, `must reject ${text.slice(0, 90)}`)
    f.vm.save()
  }
  assert.equal(f.saves.length, 0)
  const valid = { ['x'.repeat(64)]: 'x'.repeat(4096), array: Array(100).fill(1), flag: false, zero: 0, empty: '' }
  f.vm.updateJson(JSON.stringify(valid))
  assert.equal(f.vm.validationError, '')
  assert.deepEqual(JSON.parse(f.vm.draftText), valid)
  const maximum = Object.fromEntries(Array.from({ length: 32 }, (_, index) => [`field-${index}`, index]))
  f.vm.updateJson(JSON.stringify(maximum)); f.vm.setView('table'); f.vm.addField()
  assert.equal(f.vm.fields.length, 32)
  assert.equal(f.vm.validationError, '')
})

test('invalid JSON remains a complete editable draft and can be reset without switching into a partial table', async t => {
  const original = { product: '产品', release: 2, labels: ['stable'] }
  const f = await setup(t, original)
  f.vm.startEditing(); f.vm.setView('json')
  const text = '{"product":"草稿",\n"release":2,\n"labels":['
  f.vm.updateJson(text); f.vm.setView('table'); f.vm.save()
  assert.equal(f.vm.view, 'json')
  assert.equal(f.vm.draftText, text)
  assert.equal(f.updates.at(-1), text)
  assert.ok(f.vm.validationError)
  assert.equal(f.vm.dirty, true)
  assert.equal(f.saves.length, 0)
  f.vm.resetFields()
  assert.deepEqual(JSON.parse(f.vm.draftText), original)
  assert.equal(f.vm.validationError, '')
  assert.equal(f.vm.dirty, false)
  assert.equal(f.vm.editing, true)
})

test('duplicate table keys cannot overwrite a retained field and change counts follow additions and deletions', async t => {
  const f = await setup(t, { retained: '保持', edited: 1, removed: true })
  f.vm.startEditing()
  f.vm.fields.find((field: any) => field.key === 'edited').value = '2'
  f.vm.syncFields()
  f.vm.removeField(f.vm.fields.findIndex((field: any) => field.key === 'removed'))
  f.vm.addField()
  const added = f.vm.fields.at(-1)
  added.key = 'retained'; added.value = '不能覆盖'
  assert.equal(f.vm.syncFields(), false)
  assert.ok(f.vm.validationError)
  assert.equal(JSON.parse(f.vm.draftText).retained, '保持')
  added.key = 'added'; added.type = 'boolean'; added.value = 'false'
  assert.equal(f.vm.syncFields(), true)
  assert.deepEqual(JSON.parse(f.vm.draftText), { retained: '保持', edited: 2, added: false })
  assert.deepEqual(JSON.parse(JSON.stringify(f.vm.changes)), { added: 1, modified: 1, deleted: 1 })
  f.vm.cancelEditing()
  assert.equal(f.vm.editing, false)
  assert.deepEqual(JSON.parse(f.vm.draftText), { retained: '保持', edited: 1, removed: true })
  assert.equal(f.vm.dirty, false)
})

test('saving locks metadata mutations and duplicate submissions, while cancellation restores the full baseline', async t => {
  const f = await setup(t, { product: '原值', tags: ['a', 'b'] })
  f.vm.startEditing(); f.vm.setView('json'); f.vm.updateJson('{"product":"新值","tags":["a","b"]}')
  f.vm.$.props.saving = true
  const text = f.vm.draftText, fieldCount = f.vm.fields.length
  f.vm.addField(); f.vm.removeField(0); f.vm.clearFields(); f.vm.resetFields(); f.vm.cancelEditing(); f.vm.updateJson('{}'); f.vm.save(); f.vm.close()
  assert.equal(f.vm.draftText, text)
  assert.equal(f.vm.fields.length, fieldCount)
  assert.equal(f.vm.editing, true)
  assert.equal(f.saves.length, 0)
  assert.equal(f.closes.length, 0)
  f.vm.$.props.saving = false
  f.vm.cancelEditing()
  assert.deepEqual(JSON.parse(f.updates.at(-1)!), { product: '原值', tags: ['a', 'b'] })
  assert.equal(f.vm.editing, false)
})

test('prototype-like JSON keys remain ordinary metadata fields through table editing', async t => {
  const original = JSON.parse('{"__proto__":"原始字段","product":"产品"}')
  const f = await setup(t, original)
  f.vm.startEditing()
  f.vm.fields.find((field: any) => field.key === 'product').value = '已修改'
  assert.equal(f.vm.syncFields(), true)
  const updated = JSON.parse(f.vm.draftText)
  assert.equal(Object.hasOwn(updated, '__proto__'), true)
  assert.equal(updated.__proto__, '原始字段')
  assert.equal(updated.product, '已修改')
})

test('switching documents resets the editor to that document without submitting the previous draft', async t => {
  const f = await setup(t, { product: '第一份资料' })
  f.vm.startEditing(); f.vm.setView('json'); f.vm.updateJson('{"product":"第一份未保存草稿"}')
  f.vm.$.props.document = { id: 'document-2', name: '另一份.md', metadata: { version: 2 } }
  f.vm.$.props.text = '{"version":2}'
  await flush()
  assert.equal(f.vm.editing, false)
  assert.equal(f.vm.dirty, false)
  assert.deepEqual(JSON.parse(f.vm.draftText), { version: 2 })
  f.vm.save()
  assert.equal(f.saves.length, 0)
})
