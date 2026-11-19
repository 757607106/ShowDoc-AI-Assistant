import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./Login.vue', import.meta.url), 'utf8')
const tabletStyles = source.slice(
  source.indexOf('@media (max-width: 1150px)'),
  source.indexOf('@media (max-width: 520px)'),
)
const phoneStyles = source.slice(source.indexOf('@media (max-width: 520px)'))

test('tablet login uses one grid column with the form first and room for the logo', () => {
  assert.match(tabletStyles, /\.login-content\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\);/)
  assert.match(tabletStyles, /\.login-content\s*\{[^}]*padding:\s*125px\s+36px\s+60px;/)
  assert.match(tabletStyles, /\.form-section\s*\{[^}]*grid-row:\s*1;/)
})

test('phone login keeps the original logo clear of the form', () => {
  assert.match(phoneStyles, /\.login-content\s*\{[^}]*padding:\s*88px\s+20px\s+42px;/)
  assert.match(phoneStyles, /\.header-logo\s*\{[^}]*top:\s*12px;[^}]*left:\s*20px;/)
  assert.match(phoneStyles, /\.logo-image\s*\{[^}]*width:\s*180px;[^}]*height:\s*28px;/)
  assert.match(phoneStyles, /\.form-card\s*\{[^}]*padding:\s*28px\s+20px;/)
})
