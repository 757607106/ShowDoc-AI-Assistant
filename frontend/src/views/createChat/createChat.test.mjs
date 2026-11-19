import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('./createChat.vue', import.meta.url), 'utf8')

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

for (const [failure, response] of [['request error', null], ['invalid response', { data: {} }], ['aborted navigation', { data: { id: 'new-session' } }]]) {
  test(`new-session failure leaves the draft in place (${failure})`, async () => {
    const start = source.indexOf('async function createNewSession')
    const end = source.indexOf('const navigateToSession', start)
    const creatingSession = { value: false }, errors = []
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
      navigateToSession: async () => false,
      inputFieldRef: { value: { clearDraft: () => assert.fail('the draft must remain until navigation succeeds') } },
      creatingSession,
      MessagePlugin: { error: message => errors.push(message) },
      console: { error() {} },
      t: key => key,
    })
    const image = { name: 'image.png' }, attachment = { id: 'attachment-a' }
    await createNewSession('keep this question', 'model', [], [image], [attachment])
    assert.equal(errors.length, 1)
    assert.equal(creatingSession.value, false)
  })
}
