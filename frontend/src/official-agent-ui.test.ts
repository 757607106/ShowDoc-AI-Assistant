import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'

const root = new URL('../', import.meta.url)
const baseline = JSON.parse(readFileSync(new URL('UPSTREAM-AGENT-UI.json', root), 'utf8'))
const hash = (text: string) => createHash('sha256').update(text).digest('hex')

test('Agent UI retains the pinned WeKnora templates, styles and interaction modules', () => {
  assert.equal(baseline.commit, 'cbdcebabf48c5ee2d6868b370326aa8341703f62')
  for (const [path, expected] of Object.entries(baseline.files) as Array<[string, { template: string; styles: string; source?: string; bindings?: Record<string, string> }]>) {
    const source = readFileSync(new URL(path, root), 'utf8')
    const { descriptor, errors } = parse(source)
    assert.deepEqual(errors, [], path)
    assert.equal(hash(descriptor.template?.content || ''), expected.template, `${path}: template`)
    assert.equal(hash(JSON.stringify(descriptor.styles.map(({ content, lang, scoped, src }) => ({ content, lang, scoped, src })))), expected.styles, `${path}: styles`)
    let upstreamSource = source
    for (const [localBinding, upstreamBinding] of Object.entries(expected.bindings || {})) {
      assert.equal(upstreamSource.split(localBinding).length - 1, 1, `${path}: exact import relocation`)
      upstreamSource = upstreamSource.replace(localBinding, upstreamBinding)
    }
    if (expected.source) assert.equal(hash(upstreamSource), expected.source, `${path}: official interactions`)
  }
  for (const [path, expected] of Object.entries(baseline.dependencies)) {
    assert.equal(hash(readFileSync(new URL(path, root), 'utf8')), expected, `${path}: typography/layout dependency`)
  }
})
