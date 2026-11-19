import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

test('knowledge navigation has one list while scope, document and citation links keep their routes', () => {
  const source=readFileSync(new URL('./index.ts',import.meta.url),'utf8')
  const start=source.indexOf('const router = createRouter('), end=source.indexOf('// 持久化 auto-setup',start)
  const code=ts.transpileModule(source.slice(start,end).replaceAll('import.meta.env.BASE_URL',"'/'").replaceAll('import.meta.env.DEV','false')+'\nreturn router.routes',{
    compilerOptions:{target:ts.ScriptTarget.ES2022},
  }).outputText
  const routes=new Function('createRouter','createWebHistory','SettingsRouteOutlet',code)((options:any)=>options,()=>({}),{})
  const children=routes.find((route:any)=>route.name==='Platform').children
  const route=(name:string)=>children.find((item:any)=>item.name===name)
  assert.match(route('knowledgeBaseList').component.toString(),/ContextDBSpaces\.vue/)
  assert.equal(route('knowledgeSpaceList').redirect,'/platform/knowledge-bases')
  assert.equal(route('knowledgeSpaceDetail').path,'knowledge-spaces/:scope')
  assert.equal(route('knowledgeBaseDetail').path,'knowledge-bases/:kbId')
  assert.match(route('knowledgeBaseDetail').component.toString(),/ContextDBKnowledge\.vue/)
  assert.equal(route('kbCreateChat').path,'knowledge-bases/:kbId/createChat')
  assert.equal(route('captures').redirect,'/platform/knowledge-bases')

  const menuStore=readFileSync(new URL('../stores/menu.ts',import.meta.url),'utf8')
  assert.doesNotMatch(menuStore, /path: 'captures'/)
  assert.match(menuStore, /title: '知识评审'[^\n]+path: 'governance'/)

  const menu=readFileSync(new URL('../components/menu.vue',import.meta.url),'utf8')
  const menuStart=menu.indexOf('const isMenuItemActive ='), menuEnd=menu.indexOf('// 统一的图标激活状态判断',menuStart)
  const menuCode=ts.transpileModule(menu.slice(menuStart,menuEnd)+'\nreturn isMenuItemActive',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const active=new Function('route','currentpath',menuCode)({name:'knowledgeSpaceDetail'},{value:'knowledge-spaces'})
  assert.equal(active('knowledge-bases'),true)
})

test('KB chat deep links replace stale references, switches select the new KB, and global chats clear scope', () => {
  const source=readFileSync(new URL('./index.ts',import.meta.url),'utf8')
  const start=source.indexOf('router.beforeResolve('), end=source.indexOf('router.afterEach(',start)
  const code=ts.transpileModule(source.slice(start,end),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  let guard!: (to:any,from:any)=>void
  let pending: {kbIds:string[];fileIds:string[]}|null=null
  const selected={kbIds:['stale-kb'],fileIds:['stale-file']}
  const settings={
    consumeNewChatReferences(){const result=pending;pending=null;return result},
    setNewChatReferences(kbIds:string[],fileIds:string[]){Object.assign(selected,{kbIds:[...kbIds],fileIds:[...fileIds]})},
    clearChatReferences(){Object.assign(selected,{kbIds:[],fileIds:[]})},
  }
  new Function('router','useSettingsStore',code)({beforeResolve:(callback:typeof guard)=>{guard=callback}},()=>settings)
  const enter=(name:string,kbId:any,fullPath:string,previous='')=>guard({name,params:{kbId},fullPath},{fullPath:previous})
  enter('kbCreateChat','kb-a','/platform/knowledge-bases/kb-a/createChat')
  assert.deepEqual(selected,{kbIds:['kb-a'],fileIds:[]})
  enter('kbCreateChat','kb-b','/platform/knowledge-bases/kb-b/createChat','/platform/knowledge-bases/kb-a/createChat')
  assert.deepEqual(selected,{kbIds:['kb-b'],fileIds:[]})
  pending={kbIds:['search-kb'],fileIds:['search-file']}
  enter('kbCreateChat','kb-b','/platform/knowledge-bases/kb-b/createChat')
  assert.deepEqual(selected,{kbIds:['search-kb'],fileIds:['search-file']})
  enter('globalCreateChat',undefined,'/platform/createChat')
  assert.deepEqual(selected,{kbIds:[],fileIds:[]})
  for(const invalid of ['',[], ' '.repeat(3), 'x'.repeat(201)]) {
    enter('kbCreateChat',invalid,'/platform/knowledge-bases/invalid/createChat')
    assert.deepEqual(selected,{kbIds:[],fileIds:[]})
  }
})
