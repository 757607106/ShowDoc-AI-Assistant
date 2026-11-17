import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const inputField = readFileSync(new URL('./Input-field.vue', import.meta.url), 'utf8')

test('mention button matches icon controls and leaves the count to the selected chips', () => {
  const css = inputField.slice(inputField.indexOf('.kb-btn {'), inputField.indexOf('.kb-btn-text'))
  assert.match(css, /width: 28px/)
  assert.match(css, /&:hover:not\(\.disabled\):not\(\.active\)/)
  assert.doesNotMatch(css, /box-shadow: inset/)
  assert.doesNotMatch(inputField, /class="kb-count"/)
})
