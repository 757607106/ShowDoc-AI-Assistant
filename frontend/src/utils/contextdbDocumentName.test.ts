import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import ts from 'typescript'
import { documentDisplayName, graphDocumentLabel } from './contextdbDocumentName.ts'

const storedName = `doc-${'a'.repeat(64)}.html`

test('document names use captured titles and original filenames while retaining the source extension', () => {
  assert.equal(documentDisplayName({ name: storedName, metadata: { title: '  采购明细  ' } }), '采购明细.html')
  assert.equal(documentDisplayName({ name: 'doc-hash.PDF', metadata: { title: '使用手册.pdf' } }), '使用手册.pdf')
  assert.equal(documentDisplayName({ name: 'doc-hash.docx', metadata: { title: '手册', filename: '原始手册（修订）.docx' } }), '原始手册（修订）.docx')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: { title: ' ' } }), '原件.md')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: null }), '原件.md')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: { title: 123, filename: false } }), '原件.md')
})

test('graph labels replace exact source names and leave entity identities and unrelated text intact', () => {
  const document = { name: storedName, metadata: { title: '采购明细' } }
  assert.equal(graphDocumentLabel(storedName, [document]), '采购明细')
  assert.equal(graphDocumentLabel('采购单', [document]), '采购单')
  assert.equal(graphDocumentLabel(`包含 ${storedName}`, [document]), `包含 ${storedName}`)
  assert.equal(document.name, storedName)
})

test('document view supplies readable names to list, preview and single-file downloads without changing the native identity', () => {
  const source = readFileSync(new URL('../api/contextdb.ts', import.meta.url), 'utf8')
  const script = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports: any = {}
  vm.runInNewContext(script, { exports, require: (name: string) => name === '@/utils/contextdbDocumentName' ? { documentDisplayName } : {} })
  const doc = exports.documentView({ id: 'official-id', name: storedName, metadata: { title: '采购明细' }, ingest_status: 'succeeded' })
  assert.equal(doc.name, storedName)
  assert.equal(doc.id, 'official-id')
  assert.equal(doc.file_name, '采购明细.html')
  assert.equal(doc.original_file_name, '采购明细.html')
  assert.equal(doc.file_type, 'html')
  assert.equal(doc.parse_status, 'completed')
})

test('directory rows show source names but retain explicit user renames and folder names', async () => {
  const source = readFileSync(new URL('../views/knowledge/ContextDBKnowledge.vue', import.meta.url), 'utf8')
  const start = source.indexOf('async function loadNodes()')
  const script = ts.transpileModule(source.slice(start, source.indexOf('async function enterNode', start)) + '\nreturn loadNodes', {}).outputText
  const nodes = { value: [] as any[] }, breadcrumbs = { value: [] }, nodeTotal = { value: 0 }
  const items = [
    { node_type: 'file', display_name: storedName, metadata: { title: '采购明细' } },
    { node_type: 'file', display_name: '用户重命名.html', metadata: { title: '采购明细' } },
    { node_type: 'folder', display_name: '资料目录', metadata: { title: '不覆盖目录' } },
  ]
  const load = new Function('nativeAPI', 'kbId', 'parent', 'nodePage', 'nodes', 'breadcrumbs', 'nodeTotal', 'documentDisplayName', script)(
    { get: async () => ({ data: { items, total: 3 } }) }, { value: 'kb' }, { value: '' }, { value: 1 }, nodes, breadcrumbs, nodeTotal, documentDisplayName,
  )
  await load()
  assert.deepEqual(nodes.value.map(item => item.label), ['采购明细.html', '用户重命名.html', '资料目录'])
  assert.equal(nodes.value[0].display_name, storedName)
})
