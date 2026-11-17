import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { posix } from 'node:path'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'

const root = new URL('../', import.meta.url)
const baseline = JSON.parse(readFileSync(new URL('UPSTREAM-AGENT-UI.json', root), 'utf8'))
const hash = (text: string) => createHash('sha256').update(text).digest('hex')
const readSource = (path: string) => readFileSync(new URL(path, root), 'utf8')
const reference = 'docs/architecture/agent-repair-alignment-20261117.md'
const finalReference = 'docs/architecture/deepagents-contextdb-final-plan-20261117.md'
const references = new Set([reference, finalReference])
type FileHashes = { template: string; styles: string; source?: string; bindings?: Record<string, string> }
type Adaptation = Partial<Record<'template' | 'styles' | 'source', string>> & {
  local_path?: string; reason: string; reference: string
}
type Adaptations = Record<string, Adaptation>
type Disposition = { status: 'retired'; reason: string; reference: string }
type Dispositions = Record<string, Disposition>
type LocalSource = { source: string; upstream_source?: string; reason: string; reference: string }
const localSourceOrigins: Record<string, string> = {
  'src/composables/usePromptDock.ts': 'c8d7772eb93e7320000401aa70b4583653ecb33cdd6d9acf0e9020db5cf9e38f',
  'src/utils/suspendedRun.ts': 'e572f1d2af3de062b945a81ac55657f155961cedb74f3ca6a20ca267837026a4',
  'src/utils/collaborationDisplay.ts': '1c8c1aa3af53e8ce8fb737bc327b4353defb1e727d35f6f0b53c801b0a354190',
}
const localSourcePaths = [...Object.keys(localSourceOrigins), 'src/views/chat/components/NativeInterruptCard.vue']
const exists = (path: string) => existsSync(new URL(path, root))
let sourceImports: Array<[string, string]> | undefined

function importReferences(target: string) {
  if (!sourceImports) {
    sourceImports = []
    for (const name of readdirSync(new URL('src/', root), { recursive: true, encoding: 'utf8' })) {
      if (!/\.(vue|[cm]?[jt]sx?)$/.test(name)) continue
      const consumer = `src/${name}`
      const source = readSource(consumer)
      for (const match of source.matchAll(/(?:\bfrom\s*|\bimport\s*(?:\(\s*)?|\brequire\s*\(\s*)['"]([^'"]+)['"]/g)) {
        const specifier = match[1]!
        const resolved = specifier.startsWith('@/') ? `src/${specifier.slice(2)}`
          : specifier.startsWith('.') ? posix.normalize(posix.join(posix.dirname(consumer), specifier)) : specifier
        sourceImports.push([resolved, consumer])
      }
    }
  }
  return sourceImports.filter(([resolved]) => resolved === target || resolved === target.replace(/\.(vue|[cm]?[jt]sx?)$/, '')).map(([, consumer]) => consumer)
}

function verifyDisposition(path: string, value: Disposition, present = exists(path), imports = importReferences(path)) {
  assert.ok(path in baseline.files || path in baseline.dependencies, `${path}: unknown disposition`)
  assert.deepEqual(Object.keys(value).sort(), ['reason', 'reference', 'status'], `${path}: unexpected disposition field`)
  assert.equal(value.status, 'retired', `${path}: unsupported disposition`)
  assert.ok(value.reason.trim(), `${path}: reviewed retirement reason`)
  assert.equal(value.reference, finalReference, `${path}: retirement review reference`)
  assert.equal(present, false, `${path}: retired source still exists`)
  assert.deepEqual(imports, [], `${path}: retired source still imported`)
}

test('the original upstream baseline cannot be refreshed to accept local changes', () => {
  assert.equal(baseline.repository, 'https://github.com/Tencent/WeKnora')
  assert.equal(baseline.commit, 'cbdcebabf48c5ee2d6868b370326aa8341703f62')
  assert.equal(hash(JSON.stringify({ repository: baseline.repository, commit: baseline.commit,
    files: baseline.files, dependencies: baseline.dependencies })),
  'c4f0301d5bb109e94000a9342127ae1e2abc256113048b16540e81dc6b2b04a1')
})

test('Tencent license and notices are retained verbatim', () => {
  assert.equal(hash(readSource('UPSTREAM-LICENSE')), '5935f49975d7daf97857d7053b6fe45500a3b2ec31cc92a42a89a5fd98a86cea')
  assert.equal(readSource('LICENSE'), readSource('UPSTREAM-LICENSE'))
})

function verifyAgentUi(read = readSource, adaptations: Adaptations = baseline.adaptations,
  dispositions: Dispositions = baseline.dispositions || {}) {
  for (const [path, disposition] of Object.entries(dispositions)) {
    verifyDisposition(path, disposition)
    assert.ok(!adaptations[path], `${path}: retired source cannot also be adapted`)
  }
  for (const [path, adaptation] of Object.entries(adaptations)) {
    const expected = baseline.files[path] || { source: baseline.dependencies[path] }
    assert.ok(path in baseline.files || path in baseline.dependencies, `${path}: unknown adaptation`)
    assert.ok(adaptation.reason.trim(), `${path}: reviewed reason`)
    assert.ok(references.has(adaptation.reference), `${path}: review reference`)
    assert.ok(existsSync(new URL(`../${adaptation.reference}`, root)), `${path}: missing review document`)
    const fields = path in baseline.files ? ['template', 'styles', 'source'] : ['source']
    assert.ok(Object.keys(adaptation).every(key => [...fields, 'local_path', 'reason', 'reference'].includes(key)), `${path}: unexpected field`)
    if (adaptation.local_path) {
      assert.equal(path, 'src/views/chat/components/tool-results/DocMarkdown.vue')
      assert.equal(adaptation.local_path, 'src/components/DocMarkdown.vue')
    }
    const overrides = fields.filter(field => field in adaptation) as Array<'template' | 'styles' | 'source'>
    assert.ok(overrides.some(field => expected[field] && adaptation[field] !== expected[field]), `${path}: redundant adaptation`)
    for (const field of overrides) {
      assert.match(adaptation[field]!, /^[a-f0-9]{64}$/, `${path}: ${field} hash`)
      assert.notEqual(adaptation[field], expected[field], `${path}: unchanged ${field} must retain upstream hash`)
    }
    if (adaptation.styles) {
      assert.ok(['src/components/Input-field.vue', 'src/views/agent/AgentEditorModal.vue', 'src/views/chat/components/tool-results/DocMarkdown.vue',
        'src/views/settings/Settings.vue', 'src/views/settings/MemorySettings.vue',
        'src/views/settings/SkillSettings.vue', 'src/views/toolbox/Toolbox.vue',
        'src/views/chat/components/BackgroundWorkChip.vue',
        'src/views/chat/components/BackgroundWorkResults.vue'].includes(path), `${path}: unapproved style adaptation`)
    }
  }
  let files = 0, dependencies = 0
  for (const [path, expected] of Object.entries(baseline.files) as Array<[string, FileHashes]>) {
    if (dispositions[path]) continue
    const adaptation = adaptations[path]
    const source = read(adaptation?.local_path || path)
    const { descriptor, errors } = parse(source)
    assert.deepEqual(errors, [], path)
    assert.equal(hash(descriptor.template?.content || ''), adaptation?.template || expected.template, `${path}: template`)
    assert.equal(hash(JSON.stringify(descriptor.styles.map(({ content, lang, scoped, src }) => ({ content, lang, scoped, src })))), adaptation?.styles || expected.styles, `${path}: styles`)
    let upstreamSource = source
    for (const [localBinding, upstreamBinding] of Object.entries(expected.bindings || {})) {
      assert.equal(upstreamSource.split(localBinding).length - 1, 1, `${path}: exact import relocation`)
      upstreamSource = upstreamSource.replace(localBinding, upstreamBinding)
    }
    const sourceHash = adaptation?.source || expected.source
    if (sourceHash) assert.equal(hash(upstreamSource), sourceHash, `${path}: source`)
    files++
  }
  for (const [path, expected] of Object.entries(baseline.dependencies) as Array<[string, string]>) {
    if (dispositions[path]) continue
    assert.equal(hash(read(path)), adaptations[path]?.source || expected, `${path}: dependency`)
    dependencies++
  }
  return { files, dependencies, retired: Object.keys(dispositions).length }
}

function verifyLocalSources(read = readSource, sources: Record<string, LocalSource> = baseline.localSources) {
  assert.deepEqual(Object.keys(sources).sort(), [...localSourcePaths].sort(), 'local sources: unreviewed paths')
  for (const [path, value] of Object.entries(sources)) {
    const upstream = localSourceOrigins[path]
    const fields = upstream ? ['source', 'upstream_source', 'reason', 'reference'] : ['source', 'reason', 'reference']
    assert.deepEqual(Object.keys(value).sort(), fields.sort(), `${path}: local source fields`)
    assert.ok(value.reason.trim(), `${path}: local source review reason`)
    assert.equal(value.reference, finalReference, `${path}: local source review reference`)
    if (upstream) {
      assert.equal(value.upstream_source, upstream, `${path}: original supplemental upstream hash`)
      assert.notEqual(value.source, upstream, `${path}: redundant local adaptation`)
    }
    assert.match(value.source, /^[a-f0-9]{64}$/, `${path}: local source hash`)
    assert.equal(hash(read(path)), value.source, `${path}: local source`)
  }
}

test('retained official sources match upstream or reviewed adaptations, with retired files accounted for', () => {
  const counts = verifyAgentUi()
  assert.equal(counts.files, 132 - Object.keys(baseline.dispositions || {}).filter(path => path in baseline.files).length)
  assert.equal(counts.dependencies, 32 - Object.keys(baseline.dispositions || {}).filter(path => path in baseline.dependencies).length)
  assert.equal(counts.files + counts.dependencies + counts.retired, 164)
})

test('supplemental sources retain their original attribution and exact reviewed local hashes', () => {
  verifyLocalSources()
})

test('supplemental source changes and unreviewed paths fail the gate', () => {
  for (const path of localSourcePaths) {
    assert.throws(() => verifyLocalSources(file => readSource(file) + (file === path ? '\n' : '')),
      new RegExp(`${path}: local source`))
  }
  assert.throws(() => verifyLocalSources(readSource, { ...baseline.localSources,
    'src/not-reviewed.ts': { source: '0'.repeat(64), reason: 'unknown', reference: finalReference } }), /unreviewed paths/)
})

test('a one-character unapproved change fails for original and adapted interactions', () => {
  for (const path of ['src/components/AgentAvatar.vue', 'src/components/Input-field.vue']) {
    assert.throws(() => verifyAgentUi(file => readSource(file) + (file === path ? '\n' : '')),
      new RegExp(`${path}: source`))
  }
})

test('unadapted styles and dependencies remain strictly pinned', () => {
  const path = 'src/components/AgentAvatar.vue'
  const source = readSource(path)
  const style = parse(source).descriptor.styles[0]!.content
  assert.throws(() => verifyAgentUi(file => file === path ? source.replace(style, style + ' ') : readSource(file)), /AgentAvatar.vue: styles/)
  const dependency = Object.keys(baseline.dependencies).find(path => !baseline.adaptations[path])!
  assert.throws(() => verifyAgentUi(file => readSource(file) + (file === dependency ? '\n' : '')), /: dependency/)
})

test('unknown or redundant adaptation entries cannot weaken the gate', () => {
  const entry = { source: '0'.repeat(64), reason: 'unreviewed', reference }
  assert.throws(() => verifyAgentUi(readSource, { ...baseline.adaptations, 'src/not-in-upstream.vue': entry }), /unknown adaptation/)
  assert.throws(() => verifyAgentUi(readSource, { ...baseline.adaptations,
    'src/components/AgentAvatar.vue': { ...entry, source: baseline.files['src/components/AgentAvatar.vue'].source } }), /redundant adaptation/)
})

test('retirement cannot hide an existing source, a remaining import, or an unknown file', () => {
  const entry: Disposition = { status: 'retired', reason: 'Reviewed retirement', reference: finalReference }
  const path = 'src/components/AgentAvatar.vue'
  assert.throws(() => verifyDisposition(path, entry, true, []), /retired source still exists/)
  assert.throws(() => verifyDisposition(path, entry, false, ['src/consumer.vue']), /retired source still imported/)
  assert.throws(() => verifyDisposition('src/not-in-upstream.vue', entry, false, []), /unknown disposition/)
})
