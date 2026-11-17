import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test, { type TestContext } from 'node:test'
import * as pinia from 'pinia'
import * as vue from 'vue'
import * as capabilities from '../config/deploymentCapabilities.ts'
import * as localized from './localizedResourceCache.ts'
import * as organizationState from './organizationState.ts'
import * as versioned from './versionedRequest.ts'
import { fixture, flush } from '../test-utils/vueFixture.ts'

function setup(t: TestContext, probe: Promise<capabilities.DeploymentCapabilityMap>) {
  const f = fixture(t)
  const root = pinia.createPinia()
  pinia.setActivePinia(root)
  t.after(() => pinia.disposePinia(root))
  const auth = vue.reactive({ user: { id: 'user-a' }, effectiveTenantId: 1, isLiteMode: false })
  const getCapabilities = t.mock.fn(async () => ({ data: { capabilities: await probe } }))
  const deployment = f.evaluate(readFileSync(new URL('./deploymentCapabilities.ts', import.meta.url), 'utf8'), {
    vue, pinia, '@/api/system': { getDeploymentCapabilities: getCapabilities },
    '@/stores/auth': { useAuthStore: () => auth }, '@/config/deploymentCapabilities': capabilities,
  })
  const api = {
    listMyOrganizations: t.mock.fn(async () => ({ success: true, data: { organizations: [{ id: 'org' }] } })),
    listSharedAgents: t.mock.fn(async () => ({ success: true, data: [{ agent: { id: 'shared' } }] })),
    get: t.mock.fn(async () => ({ success: true, data: {
      display_name: `Assistant ${auth.effectiveTenantId}`, max_access_level: 'read_only',
    } })),
  }
  const assistantApi = f.evaluate(readFileSync(new URL('../api/assistant.ts', import.meta.url), 'utf8'), {
    '@/utils/request': { get: api.get },
  })
  const { useOrganizationStore } = f.evaluate(readFileSync(new URL('./organization.ts', import.meta.url), 'utf8'), {
    vue, pinia, '@/api/organization': api, '@/utils/request': { getCurrentLanguage: () => 'zh-CN' },
    './versionedRequest': versioned, './localizedResourceCache': localized, './organizationState': organizationState,
    './deploymentCapabilities': deployment, '@/stores/deploymentCapabilities': deployment,
  })
  const { useAssistantStore } = f.evaluate(readFileSync(new URL('./assistant.ts', import.meta.url), 'utf8'), {
    vue, pinia, '@/api/assistant': assistantApi, './auth': { useAuthStore: () => auth },
    './deploymentCapabilities': deployment, '@/stores/deploymentCapabilities': deployment,
  })
  return { api, auth, getCapabilities, organization: useOrganizationStore(), assistant: useAssistantStore() }
}

test('unsupported optional endpoints are skipped on startup and forced reload', async t => {
  const { api, organization, assistant } = setup(t, Promise.resolve({
    organizations: { supported: false }, 'settings.assistant': { supported: false },
  }))
  for (const force of [false, true]) {
    await Promise.all([
      organization.fetchOrganizations({ force }), organization.fetchSharedAgents({ force }),
      assistant.loadWorkspaceConfig(),
    ])
  }
  assert.equal(api.listMyOrganizations.mock.callCount(), 0)
  assert.equal(api.listSharedAgents.mock.callCount(), 0)
  assert.equal(api.get.mock.callCount(), 0)
  assert.equal(organization.organizations.length, 0)
  assert.equal(organization.sharedAgents.length, 0)
  assert.equal(organization.loading, false)
  assert.equal(assistant.workspaceConfig, null)
  assert.equal(assistant.accessCeiling, 'confirm')
})

for (const map of [{ organizations: { supported: true }, 'settings.assistant': { supported: true } }, {}]) {
  test(`supported and older deployments keep optional reads (${Object.keys(map).length ? 'enabled' : 'missing keys'})`, async t => {
    const { api, organization, assistant } = setup(t, Promise.resolve(map))
    await flush()
    await Promise.all([organization.fetchOrganizations(), organization.fetchSharedAgents()])
    assert.equal(api.get.mock.callCount(), 1)
    assert.equal(assistant.displayName, 'Assistant 1')
    assert.equal(assistant.accessCeiling, 'read_only')
    assert.equal(organization.organizations[0].id, 'org')
    assert.equal(organization.sharedAgents[0].agent.id, 'shared')
    await Promise.all([
      organization.fetchOrganizations({ force: true }), organization.fetchSharedAgents({ force: true }),
      assistant.loadWorkspaceConfig(),
    ])
    assert.equal(api.listMyOrganizations.mock.callCount(), 2)
    assert.equal(api.listSharedAgents.mock.callCount(), 2)
    assert.equal(api.get.mock.callCount(), 2)
  })
}

test('startup waits for the capability probe before issuing optional requests', async t => {
  let resolve!: (value: capabilities.DeploymentCapabilityMap) => void
  const { api, getCapabilities, organization } = setup(t, new Promise(value => { resolve = value }))
  const pending = Promise.all([organization.fetchOrganizations(), organization.fetchSharedAgents()])
  await flush()
  assert.equal(getCapabilities.mock.callCount(), 1)
  assert.equal(api.listMyOrganizations.mock.callCount(), 0)
  assert.equal(api.listSharedAgents.mock.callCount(), 0)
  assert.equal(api.get.mock.callCount(), 0)
  resolve({ organizations: { supported: false }, 'settings.assistant': { supported: false } })
  await pending
  await flush()
  assert.equal(api.listMyOrganizations.mock.callCount(), 0)
  assert.equal(api.listSharedAgents.mock.callCount(), 0)
  assert.equal(api.get.mock.callCount(), 0)
})

test('an assistant load superseded while waiting for capabilities does not fetch the old workspace', async t => {
  let resolve!: (value: capabilities.DeploymentCapabilityMap) => void
  const { api, auth, assistant } = setup(t, new Promise(value => { resolve = value }))
  auth.effectiveTenantId = 2
  await vue.nextTick()
  resolve({ 'settings.assistant': { supported: true } })
  await flush()
  assert.equal(api.get.mock.callCount(), 1)
  assert.equal(assistant.displayName, 'Assistant 2')
})
