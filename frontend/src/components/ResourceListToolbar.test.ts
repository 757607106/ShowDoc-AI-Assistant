import assert from 'node:assert/strict'
import test from 'node:test'
import {fixture,flush} from '../test-utils/vueFixture.ts'

for(const supported of [false,true])test(`organization selector follows deployment capability (${supported})`,async t=>{
  const fetchOrganizations=t.mock.fn(async()=>{})
  const {vm}=fixture(t).component(new URL('./ResourceListToolbar.vue',import.meta.url),{
    'vue-i18n':{useI18n:()=>({t:(key:string)=>key})},
    '@/stores/organization':{useOrganizationStore:()=>({organizations:[{id:'org-a',name:'协作空间'}],fetchOrganizations})},
    '@/stores/deploymentCapabilities':{useDeploymentCapabilitiesStore:()=>({isSupported:(key:string)=>key==='organizations'&&supported})},
  },{modelValue:'all',query:'',countByOrg:{'org-a':1}})
  await flush()
  assert.equal(fetchOrganizations.mock.callCount(),supported?1:0)
  assert.equal(vm.spaceOptions.length,supported?1:0)
  assert.deepEqual([...vm.scopes].map((item:any)=>item.value),['all','favorites','recents','mine'])
})
