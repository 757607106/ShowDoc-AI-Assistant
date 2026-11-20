import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import { createI18n } from 'vue-i18n'
import { fixture, flush } from '../../test-utils/vueFixture'
import * as passwordPolicy from '../../utils/passwordPolicy'
import zh from '../../i18n/locales/zh-CN'
import en from '../../i18n/locales/en-US'

async function setup(t: TestContext, accepted = true) {
  const calls: any[] = [], errors: string[] = [], sessions: any[] = [], routes: string[] = []
  const auth = { isLoggedIn: false, hasValidTenant: true,
    setUser: (value: any) => sessions.push({ user: value }), setToken: (value: string) => sessions.push({ token: value }),
    setRefreshToken() {}, setTenant() {}, setMemberships() {}, setSelectedTenant() {},
    refreshFromAuthMe: async () => true }
  const { vm } = fixture(t).component(new URL('./Login.vue', import.meta.url), {
    'vue-router': { useRoute: () => ({ query: {} }), useRouter: () => ({ replace: (value: string) => routes.push(value) }) },
    'tdesign-vue-next': { MessagePlugin: { error: (value: string) => errors.push(value), success() {} } },
    '@/composables/useRoleLabel': { useRoleLabel: () => ({ formatRole() {}, roleIcon() {} }) },
    '@/utils/loginNotify': { notifyLoginSuccess() {} }, '@/utils/passwordPolicy': passwordPolicy,
    '@/api/auth': {
      login: async (value: any) => { calls.push(value); return accepted
        ? { success: true, user: { id: 'admin-id', account: 'admin', username: '管理员', tenant_id: 1 }, token: 'session', tenant: { id: 1 } }
        : { success: false, message: '账号或密码错误' } },
      autoSetup: async () => ({ success: false }), getOIDCConfig: async () => ({ success: true, enabled: false }),
      getAuthConfig: async () => ({ success: true, registration_mode: 'invite_only', complex_password_enabled: false }),
      userInfoFromApi: (user: any) => user,
    },
    '@/stores/auth': { useAuthStore: () => auth },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key, tm: () => [] }) },
    '@/utils/api-base': { getApiBaseUrl: () => '' },
  })
  await flush()
  vm.formRef = { validate: async () => {
    const account = vm.formData.account, password = vm.formData.password
    return vm.formRules.account.every((rule: any) => !rule.validator || rule.validator(account)) &&
      vm.formRules.password.every((rule: any) => (!rule.required || !!password) &&
        (!rule.min || password.length >= rule.min) && (!rule.max || password.length <= rule.max))
  } }
  return { vm, calls, errors, sessions, routes }
}

test('plain account login submits account and password without requiring an email', async t => {
  const f = await setup(t)
  assert.equal(f.vm.formRules.email, undefined)
  f.vm.formData.account = ' admin '; f.vm.formData.password = 'admin123'
  await f.vm.handleLogin()
  assert.deepEqual(JSON.parse(JSON.stringify(f.calls)), [{ account: 'admin', password: 'admin123' }])
  assert.equal(f.sessions.find(value => value.user)?.user.account, 'admin')
  assert.deepEqual(f.routes, ['/platform/knowledge-bases'])
  const source = readFileSync(new URL('./Login.vue', import.meta.url), 'utf8')
  const start = source.indexOf('<t-form ref="formRef"')
  const login = source.slice(start, source.indexOf('</t-form>', start))
  assert.match(login, /name="account"/)
  assert.match(login, /autocomplete="username"/)
  assert.doesNotMatch(login, /formData\.email|autocomplete="email"/)
})

test('empty account and passwords outside 8–1024 characters cannot call login', async t => {
  const f = await setup(t)
  f.vm.formData.account = ' '; f.vm.formData.password = 'admin123'; await f.vm.handleLogin()
  assert.equal(f.calls.length, 0)
  f.vm.formData.account = 'admin'; f.vm.formData.password = 'short12'; await f.vm.handleLogin()
  assert.equal(f.calls.length, 0)
  f.vm.formData.password = 'x'.repeat(1025); await f.vm.handleLogin(); assert.equal(f.calls.length, 0)
  f.vm.formData.password = 'x'.repeat(1024); await f.vm.handleLogin(); assert.equal(f.calls.length, 1)
})

test('an incorrect password does not persist a session or redirect', async t => {
  const f = await setup(t, false)
  f.vm.formData.account = 'admin'; f.vm.formData.password = 'wrong123'; await f.vm.handleLogin()
  assert.equal(f.calls.length, 1)
  assert.deepEqual(f.errors, ['账号或密码错误'])
  assert.deepEqual(f.sessions, []); assert.deepEqual(f.routes, [])
})

test('the auth client preserves account identities and sends the account login contract', async t => {
  const calls: any[] = []
  const api = fixture(t).evaluate(readFileSync(new URL('../../api/auth/index.ts', import.meta.url), 'utf8'), {
    '@/utils/request': { post: async (path: string, body: any) => { calls.push({ path, body }); return { success: true } } },
    '@/i18n': { default: { global: { t: (key: string) => key } } },
  })
  await api.login({ account: 'admin', password: 'admin123' })
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [{ path: '/api/v1/auth/login', body: { account: 'admin', password: 'admin123' } }])
  assert.equal(api.userInfoFromApi({ id: 'same-id', account: 'admin', email: 'legacy@example.com' }).account, 'admin')
  assert.equal(api.userInfoFromApi({ id: 'legacy-id', email: 'legacy-account' }).account, 'legacy-account')
})

test('the login account label resolves from the real auth locale namespace', () => {
  const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zh, 'en-US': en } })
  assert.equal(i18n.global.t('auth.account'), '账号')
  assert.equal(i18n.global.t('auth.accountPlaceholder'), '请输入账号')
  i18n.global.locale.value = 'en-US'
  assert.equal(i18n.global.t('auth.account'), 'Account')
  assert.match(i18n.global.t('auth.passwordMaxLength'), /1024/)
})
