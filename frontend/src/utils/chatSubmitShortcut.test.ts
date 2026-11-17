import assert from 'node:assert/strict'
import test from 'node:test'
import { chatSubmitShortcut } from './chatSubmitShortcut'

const enter = { key: 'Enter', keyCode: 13, isComposing: false, shiftKey: false, ctrlKey: false, altKey: false, metaKey: false }
test('Enter and Cmd+Enter submit a normal chat message', () => {
  assert.equal(chatSubmitShortcut(enter), true)
  assert.equal(chatSubmitShortcut({ ...enter, metaKey: true }), true)
})
test('newlines, modifier shortcuts and IME confirmation never submit', () => {
  for (const modifiers of [{ shiftKey: true }, { ctrlKey: true }, { altKey: true }, { isComposing: true }, { keyCode: 229 }]) {
    assert.equal(chatSubmitShortcut({ ...enter, ...modifiers }), false)
  }
  assert.equal(chatSubmitShortcut({ ...enter, key: 'a', keyCode: 65 }), false)
})
