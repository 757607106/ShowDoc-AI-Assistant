import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')
const inputField = read('../components/Input-field.vue')
const homePage = read('../views/createChat/createChat.vue')
const chatPage = read('../views/chat/index.vue')

test('the composer forwards the origin only for the matching submitted draft', () => {
  const start = inputField.indexOf('const suggestionOriginFor =')
  const end = inputField.indexOf('const createSession =', start)
  const origin = { knowledge_base_id: 'kb-1' }
  const originFor = vm.runInNewContext(ts.transpile(inputField.slice(start, end) + '\nsuggestionOriginFor'), {
    suggestedDraft: { value: { text: 'suggestion', origin } },
  })
  assert.equal(originFor('suggestion'), origin)
  assert.equal(originFor('edited suggestion'), undefined)
  assert.match(inputField, /const options: SendMessageOptions = \{ questionOrigin: suggestionOriginFor\(val\) \}/)
  const emits = inputField.match(/emit\('send-msg',[^\n]*\)/g) || []
  assert.ok(emits.length >= 2)
  for (const call of emits) {
    assert.match(call, /, options\)$/, `send-msg must forward options: ${call}`)
  }
})

test('recommendations prefill the composer and the provenance travels with the later send', () => {
  for (const [name, source] of [['createChat.vue', homePage], ['chat/index.vue', chatPage]]) {
    assert.doesNotMatch(source, /pendingQuestionOrigin/, `${name} must not keep a pending origin`)
    assert.match(source, /prefillSuggestion\(item\.question, questionOriginFromSuggestion\(item\)\)/, name)
  }
  assert.match(homePage, /changeFirstQuery\([^)]*options\.questionOrigin \?\? null\)/)
  assert.match(chatPage, /@send-msg="\([^"]*options\) => sendMsg\([^"]*options\)"/)
  assert.match(chatPage, /question_origin: options\?\.questionOrigin/)
  assert.match(chatPage, /questionOrigin: firstQuestionOrigin\.value \|\| undefined/)
})
