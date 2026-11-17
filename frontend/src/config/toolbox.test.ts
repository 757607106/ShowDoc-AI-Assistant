import assert from 'node:assert/strict'
import test from 'node:test'
import {readFileSync} from 'node:fs'
import {computed,ref} from 'vue'
import {TOOLBOX_ITEMS,canAccessToolboxSection,isToolboxSection,toolboxLocation} from './toolbox'
import zhCN from '../i18n/locales/zh-CN'

const roles=['viewer','contributor','admin','owner']
const access=(role:string|null,unsupported:string[]=[],superuser=false)=>({
  currentTenantRole:role,canAccessAllTenants:superuser,
  hasRole:(min:string)=>roles.indexOf(role||'')>=roles.indexOf(min),
  isSupported:(capability?:string)=>!capability||!unsupported.includes(capability),
})

test('toolbox contains native skill and external MCP sources without retired browser management',()=>{
  assert.deepEqual(TOOLBOX_ITEMS.map(item=>item.key),['skills','mcp'])
  const lookup=(key:string)=>key.split('.').reduce<any>((node,part)=>node?.[part],zhCN)
  for(const item of TOOLBOX_ITEMS)for(const key of [item.title,item.description,'help' in item?item.help:undefined,item.action])if(key)assert.equal(typeof lookup(key),'string',key)
  for(const key of ['browserconnection','sandbox','websearch','envvars','integration-api',undefined,'unknown'])assert.equal(isToolboxSection(key),false)
})

test('toolbox retains role and deployment gates during account changes',()=>{
  for(const role of ['viewer','contributor']){
    assert.equal(canAccessToolboxSection('skills',access(role)),false)
    assert.equal(canAccessToolboxSection('mcp',access(role)),false)
  }
  assert.equal(canAccessToolboxSection('skills',access('admin')),true)
  assert.equal(canAccessToolboxSection('skills',access('owner',['settings.sandbox'])),false)
  assert.equal(canAccessToolboxSection('mcp',access('owner',['settings.mcp'])),false)
  assert.equal(canAccessToolboxSection('mcp',access(null)),false)
  assert.equal(canAccessToolboxSection('mcp',access(null,[],true)),true)
  const role=ref('admin'),allowed=computed(()=>canAccessToolboxSection('skills',access(role.value)))
  assert.equal(allowed.value,true);role.value='viewer';assert.equal(allowed.value,false)
})

test('legacy skill locations keep sandbox selection without leaking it into MCP',()=>{
  assert.deepEqual(toolboxLocation('skills','sandbox-123'),{path:'/platform/toolbox/skills',query:{sandboxId:'sandbox-123'}})
  assert.deepEqual(toolboxLocation('mcp','sandbox-123'),{path:'/platform/toolbox/mcp',query:{}})
  assert.deepEqual(toolboxLocation(),{path:'/platform/toolbox',query:{}})
  assert.deepEqual(toolboxLocation('browserconnection'),{path:'/platform/settings',query:{section:'browserconnection'}})
})

test('moved tool bookmarks are routed to the toolbox and the retired panel is not imported',()=>{
  const router=readFileSync(new URL('../router/index.ts',import.meta.url),'utf8')
  assert.match(router,/to\.path === '\/platform\/settings' && isToolboxSection\(to\.query\.section\)/)
  assert.match(router,/toolboxLocation\(to\.query\.section/)
  const page=readFileSync(new URL('../views/toolbox/Toolbox.vue',import.meta.url),'utf8')
  assert.doesNotMatch(page,/BrowserConnectionSettings|useBrowserConnectionStore|BrowserIcon/)
  assert.match(page,/if \(!selectedItem\.value && fallback\) void router\.replace\(toolboxLocation\(fallback\.key\)\)/)
})
