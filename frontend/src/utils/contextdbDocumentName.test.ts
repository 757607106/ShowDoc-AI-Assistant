import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import ts from 'typescript'
import { documentDisplayName, documentDownloadName, graphDocumentLabel } from './contextdbDocumentName.ts'

const storedName = `doc-${'a'.repeat(64)}.html`

test('document names use captured titles and original filenames while retaining the source extension', () => {
  assert.equal(documentDisplayName({ name: storedName, metadata: { title: '  采购明细  ' } }), '采购明细.html')
  assert.equal(documentDisplayName({ name: 'doc-hash.PDF', metadata: { title: '使用手册.pdf' } }), '使用手册.pdf')
  assert.equal(documentDisplayName({ name: 'doc-hash.docx', metadata: { title: '手册', filename: '原始手册（修订）.docx' } }), '原始手册（修订）.docx')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: { title: ' ' } }), '原件.md')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: null }), '原件.md')
  assert.equal(documentDisplayName({ name: '原件.md', metadata: { title: 123, filename: false } }), '原件.md')
})

test('enriched document and review names remain readable without changing their native names', () => {
  const document = { name: storedName, display_name: '采购明细.html' }
  const review = { document_name: storedName, document_display_name: '采购明细.html' }
  assert.equal(documentDisplayName(document), '采购明细.html')
  assert.equal(documentDisplayName(review), '采购明细.html')
  assert.equal(document.name, storedName)
  assert.equal(review.document_name, storedName)
  assert.equal(documentDisplayName({ document_name: storedName }), storedName)
  assert.equal(documentDisplayName({ name: storedName, display_name: ' ', metadata: { title: '历史标题' } }), '历史标题.html')
  assert.equal(documentDisplayName(null), '')
})

test('download names preserve business stems and match the actual file extension after conversion', () => {
  const converted = { name: 'doc-hash.md', display_name: '原始手册.html', metadata: { filename: '原始手册.html' } }
  assert.equal(documentDownloadName(converted), '原始手册.md')
  assert.equal(documentDisplayName(converted), '原始手册.html')
  assert.equal(converted.name, 'doc-hash.md')
  assert.equal(documentDownloadName({ name: 'doc-hash.docx', metadata: { filename: '原始手册.docx' } }), '原始手册.docx')
  assert.equal(documentDownloadName({ name: 'doc-hash.pdf', metadata: { filename: '手册.PDF' } }), '手册.PDF')
  assert.equal(documentDownloadName({ name: 'source.md', document_display_name: '业务标题' }), '业务标题.md')
  assert.equal(documentDownloadName(null), '')
})

test('graph labels replace exact source names and leave entity identities and unrelated text intact', () => {
  const document = { name: storedName, metadata: { title: '采购明细' } }
  assert.equal(graphDocumentLabel(storedName, [document]), '采购明细')
  assert.equal(graphDocumentLabel('采购单', [document]), '采购单')
  assert.equal(graphDocumentLabel(`包含 ${storedName}`, [document]), `包含 ${storedName}`)
  assert.equal(graphDocumentLabel(storedName, [{ ...document, display_name: '采购明细.html', metadata: { title: '001-采购明细' } }]), '采购明细.html')
  assert.equal(graphDocumentLabel(storedName, [{ ...document, display_name: ' ' }]), '采购明细')
  assert.equal(document.name, storedName)
})

test('document view supplies readable names to list, preview and single-file downloads without changing the native identity', () => {
  const source = readFileSync(new URL('../api/contextdb.ts', import.meta.url), 'utf8')
  const script = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports: any = {}
  vm.runInNewContext(script, { exports, require: (name: string) => name === '@/utils/contextdbDocumentName' ? { documentDisplayName, documentDownloadName } : {} })
  const doc = exports.documentView({ id: 'official-id', name: storedName, metadata: { title: '采购明细' }, ingest_status: 'succeeded' })
  assert.equal(doc.name, storedName)
  assert.equal(doc.id, 'official-id')
  assert.equal(doc.file_name, '采购明细.html')
  assert.equal(doc.original_file_name, '采购明细.html')
  assert.equal(doc.file_type, 'html')
  assert.equal(doc.parse_status, 'completed')
  const converted = exports.documentView({ id: 'official-id', name: 'doc-hash.md', metadata: { filename: '原件.html' } })
  assert.equal(converted.file_name, '原件.html')
  assert.equal(converted.download_file_name, '原件.md')
  assert.equal(converted.name, 'doc-hash.md')
})

test('directory rows show source names but retain explicit user renames and folder names', async () => {
  const source = readFileSync(new URL('../views/knowledge/ContextDBDocuments.vue', import.meta.url), 'utf8')
  const start = source.indexOf('const title=')
  const script = ts.transpileModule(source.slice(start, source.indexOf('async function readNodes', start)) + '\nreturn title', {}).outputText
  const items = [
    { node_type: 'file', display_name: storedName, metadata: { title: '采购明细' } },
    { node_type: 'file', display_name: storedName, document_display_name: '云端标题.html' },
    { node_type: 'file', display_name: '用户重命名.html', document_display_name: '采购明细.html', metadata: { title: '采购明细' } },
    { node_type: 'folder', display_name: '资料目录', metadata: { title: '不覆盖目录' } },
  ]
  const original = structuredClone(items)
  const title = new Function('documentDisplayName', script)(documentDisplayName)
  assert.deepEqual(items.map(item => title(item)), ['采购明细.html', '云端标题.html', '用户重命名.html', '资料目录'])
  assert.deepEqual(items, original)
})

test('semantic results show readable names while retaining source names and IDs', async () => {
  const source = readFileSync(new URL('../api/knowledge-base/index.ts', import.meta.url), 'utf8')
  const start = source.indexOf('export async function knowledgeSemanticSearch(')
  const script = ts.transpileModule(source.slice(start, source.indexOf('export function batchReparseKnowledge', start)).replace('export ', '') + '\nreturn knowledgeSemanticSearch', {}).outputText
  const search = new Function('contextdb', script)({ nativeAPI: { post: async () => ({ data: { chunks: [
    { document_id: 'doc-1', document_name: storedName, document_display_name: '采购明细.html', content: '原文' },
    { document_id: 'doc-2', docnm_kwd: '历史原件.md', content: '旧原文' },
  ] } }) } })
  const result = await search({ query: '采购' })
  assert.equal(result.data[0].knowledge_title, '采购明细.html')
  assert.equal(result.data[0].document_name, storedName)
  assert.equal(result.data[0].knowledge_id, 'doc-1')
  assert.equal(result.data[1].knowledge_title, '历史原件.md')
})
