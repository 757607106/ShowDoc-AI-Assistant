import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('./contextdb.ts', import.meta.url), 'utf8')
const script = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const api: any = {}
runInNewContext(script, { exports: api, require: () => ({}) })

test('managed knowledge bases remain selectable for native retrieval and expose actual graph/wiki modes', () => {
  const kb = api.kbView({ id: 'kb', name: 'Finance', graph_enabled: true, wiki_enabled: false })
  assert.equal(kb.capabilities.vector, true)
  assert.equal(kb.capabilities.keyword, true)
  assert.equal(kb.capabilities.graph, true)
  assert.equal(kb.capabilities.wiki, false)
  assert.equal(api.kbView({ capabilities: { vector: false } }).capabilities.vector, false)
})
