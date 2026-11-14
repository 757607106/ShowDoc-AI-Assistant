import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { ref, watch } from 'vue'
import ts from 'typescript'

const source = readFileSync(new URL('./KnowledgeView.vue', import.meta.url), 'utf8')
const code = ts.transpileModule(source.slice(source.indexOf('function resetDocumentEditor()'), source.indexOf('async function loadGraph()')) + '\nreturn { openDocumentEditor, saveDocument }', {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText

function fixture(read: (kb: string, id: string) => Promise<any>, write?: (...args: any[]) => Promise<any>) {
  const writes: any[] = []
  const state = { docDialog: ref(false), docRow: ref<any>(null), docText: ref(''), docReady: ref(false), docLoading: ref(false), docError: ref(''), docKbId: ref(''), activeBaseId: ref('kb-a'), reviewDrawer: ref(false) }
  const dependencies = { ...state, watch,
    api: { kbDocumentText: read, async kbDocumentUpdate(...args: any[]) { writes.push(args); return write ? write(...args) : { document: { id: args[0] } } } },
    loadKbDocuments: async () => {}, loadReviews: async () => {},
  }
  const functions = new Function('dependencies', `const {${Object.keys(dependencies).join(',')}} = dependencies; let docRequest = 0; ${code}`)(dependencies)
  return { ...state, ...functions, writes }
}

test('late document A cannot supply content for a save to document B', async () => {
  const pending = new Map<string, (value: any) => void>()
  const f = fixture((_kb, id) => new Promise(resolve => pending.set(id, resolve)))
  const a = f.openDocumentEditor({ id: 'A' }), b = f.openDocumentEditor({ id: 'B' })
  pending.get('B')!({ text: 'B_CONTENT' }); await b
  pending.get('A')!({ text: 'A_CONTENT' }); await a
  assert.equal(f.docText.value, 'B_CONTENT')
  await f.saveDocument()
  assert.deepEqual(f.writes, [['B', 'B_CONTENT', 'kb-a']])
})

test('pending or failed/incomplete content reads cannot be saved', async () => {
  let finish!: (value: any) => void
  const f = fixture(() => new Promise(resolve => { finish = resolve }))
  const reading = f.openDocumentEditor({ id: 'A' })
  f.docText.value = 'manually typed before load'
  await f.saveDocument()
  assert.deepEqual(f.writes, [])
  finish({}); await reading
  await f.saveDocument()
  assert.deepEqual(f.writes, [])
  assert.equal(f.docReady.value, false)
})

test('closing and reopening the same document rejects its earlier response', async () => {
  const pending: ((value: any) => void)[] = []
  const f = fixture(() => new Promise(resolve => pending.push(resolve)))
  const old = f.openDocumentEditor({ id: 'A' })
  f.docDialog.value = false
  assert.equal(f.docRow.value, null)
  const current = f.openDocumentEditor({ id: 'A' })
  pending[1]({ text: 'current' }); await current
  pending[0]({ text: 'old' }); await old
  assert.equal(f.docText.value, 'current')
  assert.equal(f.docReady.value, true)
})

test('switching knowledge bases clears the editor and prevents a save using the new base', async () => {
  const f = fixture(async () => ({ text: 'A_CONTENT' }))
  await f.openDocumentEditor({ id: 'A' })
  f.activeBaseId.value = 'kb-b'
  assert.equal(f.docDialog.value, false)
  assert.equal(f.docReady.value, false)
  assert.equal(f.docText.value, '')
  await f.saveDocument()
  assert.deepEqual(f.writes, [])
})

test('save captures its document and base and late completion cannot close a newer editor', async () => {
  let finish!: (value: any) => void
  const f = fixture(async (_kb, id) => ({ text: `${id}_CONTENT` }), () => new Promise(resolve => { finish = resolve }))
  await f.openDocumentEditor({ id: 'A' })
  const saving = f.saveDocument()
  f.activeBaseId.value = 'kb-b'
  await f.openDocumentEditor({ id: 'B' })
  finish({ document: { id: 'A' } }); await saving
  assert.deepEqual(f.writes, [['A', 'A_CONTENT', 'kb-a']])
  assert.equal(f.docDialog.value, true)
  assert.equal(f.docRow.value.id, 'B')
  assert.equal(f.docText.value, 'B_CONTENT')
  assert.equal(f.docLoading.value, false)
})
