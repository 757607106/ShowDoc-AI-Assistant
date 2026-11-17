import assert from 'node:assert/strict'
import test from 'node:test'
import { newPasswordRules } from './passwordPolicy'

test('ordinary platform passwords retain letters and digits within the 8–1024 boundary', () => {
  const rules = newPasswordRules(key => key, false)
  assert.equal(rules.find(rule => rule.min)?.min, 8)
  assert.equal(rules.find(rule => rule.max)?.max, 1024)
  const patterns = rules.filter(rule => rule.pattern).map(rule => rule.pattern as RegExp)
  assert.equal(patterns.length, 2)
  assert.equal(patterns.every(pattern => pattern.test('admin123')), true)
  assert.equal(patterns.every(pattern => pattern.test('password')), false)
  assert.equal(patterns.every(pattern => pattern.test('12345678')), false)
})

test('an enabled complex password policy and caller validation remain enforced', () => {
  const extra = { validator: (value: string) => value !== 'old-password' }
  const rules = newPasswordRules(key => key, true, [extra])
  assert.equal(rules.filter(rule => rule.pattern).length, 4)
  assert.equal(rules.at(-1), extra)
  assert.equal(newPasswordRules(key => key, false, [extra]).at(-1), extra)
})
