import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'
import { ref } from 'vue'

const input = readFileSync(new URL('./Input-field.vue', import.meta.url), 'utf8')
function between(source: string, start: string, end: string) {
  const from = source.indexOf(start), to = source.indexOf(end, from)
  assert.ok(from >= 0 && to > from, start)
  return source.slice(from, to)
}

for (const embeddedMode of [false, true]) {
  test(`a send during an active reply preserves the draft and attachments (${embeddedMode ? 'embedded' : 'ordinary'})`, async () => {
    const query = ref('Keep my draft'), images = ref([{ file: 'image' }]), attachments = ref([{ id: 'file', status: 'ready' }])
    const emitted: unknown[] = [], notices: string[] = []
    const createSession = runInNewContext(ts.transpileModule(
      `${between(input, 'const createSession =', 'const updateAgentModeDropdownPosition =')}\ncreateSession`, {
        compilerOptions: { target: ts.ScriptTarget.ES2022 },
      }).outputText, {
      props: { composerLocked: false, isReplying: true, embeddedMode },
      uploadedImages: images, uploadedAttachments: attachments, allSelectedItems: ref([]),
      MessagePlugin: { info: (key: string) => notices.push(key) }, t: (key: string) => key,
      emit: (...args: unknown[]) => emitted.push(args), clearvalue: () => { query.value = '' },
    })
    await createSession(query.value)
    assert.deepEqual(emitted, [])
    assert.deepEqual(notices, ['input.messages.replying'])
    assert.equal(query.value, 'Keep my draft')
    assert.equal(images.value.length, 1)
    assert.equal(attachments.value.length, 1)
  })
}
