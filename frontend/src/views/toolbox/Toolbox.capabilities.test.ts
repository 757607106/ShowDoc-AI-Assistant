import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive } from 'vue'
import { fixture, flush } from '../../test-utils/vueFixture'
import { isDeploymentCapabilitySupported, type DeploymentCapabilityMap } from '../../config/deploymentCapabilities'
import * as toolbox from '../../config/toolbox'

test('an unsupported browser bookmark neither selects its panel nor refreshes its account', async t => {
  const requests: string[] = [], routes: unknown[] = []
  const map = reactive<{ value: DeploymentCapabilityMap }>({ value: {} })
  const { vm } = fixture(t).component(new URL('./Toolbox.vue', import.meta.url), {
    'vue-router': { useRoute: () => ({ params: { section: 'browserconnection' }, query: {} }),
      useRouter: () => ({ replace: (location: unknown) => routes.push(location) }) },
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    '@/config/toolbox': toolbox,
    '@/stores/auth': { useAuthStore: () => ({ currentTenantRole: 'owner', canAccessAllTenants: false, hasRole: () => true }) },
    '@/stores/deploymentCapabilities': { useDeploymentCapabilitiesStore: () => ({
      isSupported: (key: any) => isDeploymentCapabilitySupported(map.value, key),
    }) },
    '@/stores/browserConnection': { useBrowserConnectionStore: () => ({
      loaded: false, refresh: async () => { requests.push('browser') },
    }) },
    '@/api/skill': { listSkillCatalog: async () => ({ data: [] }) },
    '@/api/mcp-service': { listMCPServices: async () => [] },
  })
  await flush()
  assert.equal(vm.selectedItem, undefined)
  assert.equal(vm.visibleItems.some((item: any) => item.key === 'browserconnection'), false)
  assert.deepEqual(requests, [])
  assert.equal(JSON.stringify(routes[0]), JSON.stringify({path:'/platform/settings',query:{section:'browserconnection'}}))
  map.value = { 'agents.browser': { supported: false } }; await flush()
  assert.deepEqual(requests, [])
  map.value = { 'agents.browser': { supported: true } }; await flush()
  assert.equal(vm.selectedItem,undefined)
  assert.equal(vm.visibleItems.some((item:any)=>item.key==='browserconnection'),false)
  assert.deepEqual(requests,[])
})
