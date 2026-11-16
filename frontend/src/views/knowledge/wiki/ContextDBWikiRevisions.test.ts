import assert from 'node:assert/strict'
import test from 'node:test'
import { fixture, flush } from '../../../test-utils/vueFixture.ts'

test('revision selection sends page IDs and opaque cursors, and automatically compares the selected revision with its base', async t => {
  const f = fixture(t), calls: any[] = []
  const { vm } = f.component(new URL('./ContextDBWikiRevisions.vue', import.meta.url), {
    '@/utils/platformPresentation': { contextdbDateTime: String, stateLabel: String },
    '@/api/contextdbWiki': {
      listWikiRevisions: async (kb: string, page: string, params: any) => {
        calls.push({ kb, page, ...params })
        return { items: [{ revision_id: params.cursor ? 'older' : 'latest' }], next_cursor: params.cursor ? null : 'opaque==' }
      },
      getWikiRevisionDiff: async (kb: string, revision: string, baseline?: string) => {
        calls.push({ kb, revision, baseline })
        return { revision_id: revision, diff: { hunks: [{ op: 'add', text: '<script>not HTML</script>' }], added_count: 1, removed_count: 0, truncated: true } }
      },
    },
  }, { kbId: 'kb', pageId: 'page', visible: true })
  await flush(); await vm.load(true); await flush()
  assert.equal(calls.find(row => row.cursor)?.cursor, 'opaque==')
  assert.equal(calls[0].page, 'page')
  vm.target = 'older'; await flush()
  assert.equal(calls.at(-1).revision, 'older')
  assert.equal(calls.at(-1).baseline, undefined)
  assert.equal(vm.diff.diff.truncated, true)
  assert.equal(vm.diff.diff.hunks[0].text, '<script>not HTML</script>')
})

test('closing or switching the history drawer discards slow earlier responses', async t => {
  const f = fixture(t)
  let resolve!: (value: any) => void
  const delayed = new Promise(yes => { resolve = yes })
  const { vm } = f.component(new URL('./ContextDBWikiRevisions.vue', import.meta.url), {
    '@/utils/platformPresentation': { contextdbDateTime: String, stateLabel: String },
    '@/api/contextdbWiki': { listWikiRevisions: () => delayed, getWikiRevisionDiff: assert.fail },
  }, { kbId: 'kb', pageId: 'page', visible: true })
  vm.$.props.visible = false
  resolve({ items: [{ revision_id: 'stale' }], next_cursor: 'old' })
  await flush()
  assert.equal(vm.revisions.length, 0)
  assert.equal(vm.cursor, '')
  assert.equal(vm.diff, null)
})
