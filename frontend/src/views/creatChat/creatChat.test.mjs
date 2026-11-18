import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('./creatChat.vue', import.meta.url), 'utf8')

test('new-session createSessions includes project_dir only through withOptionalProjectDir', () => {
  assert.match(source, /withOptionalProjectDir/)
  assert.match(source, /createSessions\(withOptionalProjectDir/)
  assert.match(source, /selectedProjectDir/)
  assert.match(source, /hostSandboxEnabled/)
  assert.doesNotMatch(source, /approvalMode|GetApprovalMode|SetApprovalMode/)
})

test('new-session page has a single project button flush above the composer', () => {
  assert.match(source, /pickHostProjectDir/)
  assert.match(source, /create-chat-composer/)
  assert.match(source, /createChat\.openProject/)
  assert.doesNotMatch(source, /wailsjs\/go\/main\/App/)
  assert.doesNotMatch(source, /PickProjectFile/)
  assert.doesNotMatch(source, /createChat\.openFile/)
  assert.doesNotMatch(source, /t-select/)
  assert.doesNotMatch(source, /project-dir-picker/)
})

for (const response of [null, { data: {} }]) {
  test(`new-session failure restores the draft (${response ? 'invalid response' : 'request error'})`, async () => {
    const start = source.indexOf('async function createNewSession')
    const end = source.indexOf('const navigateToSession', start)
    const restored = []
    const createNewSession = vm.runInNewContext(ts.transpile(`${source.slice(start, end)}\ncreateNewSession`), {
      settingsStore: {
        settings: { selectedKnowledgeBases: [], selectedFiles: [] },
        agentConfig: {},
      },
      selectedProjectDir: { value: '' },
      withOptionalProjectDir: data => data,
      createSessions: async () => {
        if (!response) throw new Error('offline')
        return response
      },
      inputFieldRef: { value: { restoreDraft: (...args) => restored.push(args) } },
      MessagePlugin: { error() {} },
      console: { error() {} },
      t: key => key,
    })
    const image = { name: 'image.png' }, attachment = { id: 'attachment-a' }
    await createNewSession('keep this question', 'model', [], [image], [attachment])
    assert.deepEqual(restored, [['keep this question', [image], [attachment]]])
  })
}
