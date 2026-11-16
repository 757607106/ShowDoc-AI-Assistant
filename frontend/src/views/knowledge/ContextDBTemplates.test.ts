import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'
import { fixture, flush } from '../../test-utils/vueFixture.ts'

const record = (kb = 'one') => ({ id: 'template', knowledge_base_id: kb, name: '完整模板', is_default: false,
  sections: [{ level: 2, title: '完整章节', guidance: '完整指引' }], content: '## 完整章节\n完整指引' })
async function setup(t: TestContext, options: { canEdit?: boolean; get?: (path: string) => Promise<any>; post?: (path: string, body: any) => Promise<any>; del?: (path: string) => Promise<any> } = {}) {
  const f = fixture(t), writes: any[] = [], reads: string[] = []
  let stored = record()
  const { vm, close } = f.component(new URL('./ContextDBTemplates.vue', import.meta.url), {
    '@/api/contextdb': { nativeAPI: {
      get: async (path: string) => { reads.push(path); if (options.get) return options.get(path); const url = new URL(path, 'http://fixture.invalid'); const kb = url.searchParams.get('knowledge_base_id')!; return { data: url.pathname.endsWith('/detail') ? { ...stored, knowledge_base_id: kb } : [{ ...stored, knowledge_base_id: kb, name: '列表摘要' }] } },
      post: async (path: string, body: any) => { writes.push({ method: 'POST', path, body: JSON.parse(JSON.stringify(body)) }); return options.post ? options.post(path, body) : { data: { ...record(), ...body } } },
      put: async (path: string, body: any) => { writes.push({ method: 'PUT', path, body: JSON.parse(JSON.stringify(body)) }); stored = { ...stored, ...body }; return { data: stored } },
      del: async (path: string) => { writes.push({ method: 'DELETE', path }); return options.del ? options.del(path) : { data: { deleted: true } } },
    } },
  }, { kbId: 'one', canEdit: options.canEdit !== false })
  await flush(); return { vm, props: vm.$.props, writes, reads, close, setStored: (value: any) => { stored = { ...stored, ...value } } }
}
test('new templates use the official three-section draft and duplicate confirmations send one request', async t => {
  let finish!: (value: any) => void
  const f = await setup(t, { post: () => new Promise(resolve => { finish = resolve }) })
  await f.vm.edit(); assert.equal(f.vm.sections.length, 3); assert.equal(f.vm.sections[0].title, '概述')
  assert.equal(f.vm.isDefault, false); f.vm.name = ' 新模板 '
  const pending = f.vm.save(); await f.vm.save(); assert.equal(f.writes.length, 1)
  assert.equal(f.writes[0].body.name, '新模板'); assert.equal(f.writes[0].body.sections[1].level, 2)
  finish({ data: { id: 'new' } }); await pending; assert.equal(f.vm.visible, false)
})
test('editing reads complete detail and sends only changed fields, preserving remote default changes', async t => {
  const f = await setup(t)
  await f.vm.edit(f.vm.templates[0]); assert.equal(f.vm.name, '完整模板'); assert.equal(f.vm.sections[0].guidance, '完整指引')
  assert.match(f.reads.at(-1)!, /review_templates\/detail\?knowledge_base_id=one&template_id=template/)
  f.vm.name = '改名'; f.setStored({ is_default: true }); await f.vm.save()
  assert.deepEqual(f.writes[0], { method: 'PUT', path: 'knowledge/review_templates?knowledge_base_id=one&template_id=template', body: { name: '改名' } })
})
test('read-only callers can inspect detail but cannot create, save or delete', async t => {
  const f = await setup(t, { canEdit: false })
  await f.vm.edit(); assert.equal(f.vm.visible, false)
  await f.vm.edit(f.vm.templates[0]); assert.equal(f.vm.visible, true); f.vm.name = '不能写'
  await f.vm.save(); await f.vm.remove(f.vm.templates[0]); assert.equal(f.writes.length, 0)
})
test('deleted template details and externally changed content cannot be overwritten', async t => {
  let missing = true
  const f = await setup(t, { get: async path => ({ data: path.includes('/detail') ? missing ? null : record() : [record()] }) })
  await f.vm.edit(f.vm.templates[0]); f.vm.name = '错误草稿'; await f.vm.save()
  assert.equal(f.writes.length, 0); assert.match(f.vm.error, /已不存在/)
  missing = false; await f.vm.edit(f.vm.templates[0]); f.vm.name = '草稿'
  missing = true; await f.vm.save(); assert.equal(f.writes.length, 0); assert.equal(f.vm.name, '草稿')
})
test('changes to the same remote template field block overwriting and preserve the local draft', async t => {
  const f = await setup(t)
  await f.vm.edit(f.vm.templates[0]); f.vm.name = '我的草稿'; f.setStored({ name: '他人修改' })
  await f.vm.save(); assert.equal(f.writes.length, 0); assert.match(f.vm.error, /已被更新/); assert.equal(f.vm.name, '我的草稿')
})
test('late library lists and template details cannot overwrite the current library editor', async t => {
  let finishList!: (value: any) => void, finishDetail!: (value: any) => void, first = true
  const f = await setup(t, { get: async path => {
    const kb = new URL(path, 'http://fixture.invalid').searchParams.get('knowledge_base_id')!
    if (path.includes('/detail')) return new Promise(resolve => { finishDetail = resolve })
    if (first) { first = false; return new Promise(resolve => { finishList = resolve }) }
    return { data: [record(kb)] }
  } })
  f.props.kbId = 'two'; await flush(); finishList({ data: [record('one')] }); await flush()
  assert.equal(f.vm.templates[0].knowledge_base_id, 'two')
  const editing = f.vm.edit(f.vm.templates[0]); f.props.kbId = 'three'; await flush()
  finishDetail({ data: record('two') }); await editing
  assert.equal(f.vm.visible, false); assert.equal(f.vm.editorKbId, ''); assert.equal(f.vm.templates[0].knowledge_base_id, 'three')
})
test('invalid template boundaries never reach the API and delete clicks cannot submit twice', async t => {
  let finish!: (value: any) => void
  const f = await setup(t, { del: () => new Promise(resolve => { finish = resolve }) })
  await f.vm.edit(); f.vm.name = '知'.repeat(129); await f.vm.save(); assert.equal(f.writes.length, 0)
  f.vm.name = '模板'; f.vm.sections = [{ level: 4, title: '标题', guidance: '指引' }]; await f.vm.save()
  f.vm.sections = [{ level: 1, title: '标题\n换行', guidance: '指引' }]; await f.vm.save()
  f.vm.sections = [{ level: 1, title: '标题', guidance: '段一\n\n段二' }]; await f.vm.save(); assert.equal(f.writes.length, 0)
  f.vm.visible = false; await flush(); const row = f.vm.templates[0]
  const pending = f.vm.remove(row); await f.vm.remove(row); assert.equal(f.writes.length, 1)
  finish({ data: { deleted: true } }); await pending
})
