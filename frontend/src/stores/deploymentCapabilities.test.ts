import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createPinia, defineStore } from 'pinia'
import * as capabilities from '../config/deploymentCapabilities'
import { fixture } from '../test-utils/vueFixture'

for (const response of [undefined, false, true, 'failed'] as const) {
  test(`execution capabilities follow the actual probe (${response})`, async t => {
    const f = fixture(t)
    const { useDeploymentCapabilitiesStore } = f.evaluate(
      readFileSync(new URL('./deploymentCapabilities.ts', import.meta.url), 'utf8'), {
        vue: await import('vue'), pinia: { defineStore },
        '@/api/system': { getDeploymentCapabilities: async () => {
          if (response === 'failed') throw new Error('probe offline')
          return { data: { capabilities: response === undefined ? {} : {
            'agents.steering': { supported: response }, 'agents.browser': { supported: response },
          } } }
        } },
        '@/stores/auth': { useAuthStore: () => ({ isLiteMode: false }) },
        '@/config/deploymentCapabilities': capabilities,
      },
    )
    const store = useDeploymentCapabilitiesStore(createPinia())
    assert.equal(store.isSupported('agents.browser'), false, 'no execution before a successful probe')
    await store.ensureLoaded()
    assert.equal(store.loaded, true)
    assert.equal(store.isSupported('agents.browser'), response === true)
    assert.equal(store.isSupported('agents.steering'), response === true)
    assert.equal(store.isSupported('agents'), true, 'other menu defaults remain unchanged')
    if (response === 'failed') assert.match(store.loadError, /probe offline/)
  })
}
