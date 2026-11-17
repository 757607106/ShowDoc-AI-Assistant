import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

test('one material route retains legacy add/history URLs with context and auth requirements', () => {
  const source=readFileSync(new URL('./index.ts',import.meta.url),'utf8')
  const start=source.indexOf('const router = createRouter('),end=source.indexOf('// 持久化 auto-setup',start)
  const code=ts.transpileModule(source.slice(start,end).replaceAll('import.meta.env.BASE_URL',"'/'").replaceAll('import.meta.env.DEV','false')+'\nreturn router.routes',{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
  const routes=new Function('createRouter','createWebHistory','SettingsRouteOutlet',code)((options:any)=>options,()=>({}),{})
  const children=routes.find((route:any)=>route.name==='Platform').children
  const route=(name:string)=>children.find((entry:any)=>entry.name===name)
  const query={kb_id:'a',space:'scope-a',mode:'file',url:'https://example.com'}
  assert.deepEqual(route('collect').redirect({query,hash:'#source'}),{path:'/platform/tasks',query:{...query,view:'tasks',add:'1'},hash:'#source'})
  assert.deepEqual(route('releases').redirect({query:{space:'a'},hash:''}),{path:'/platform/tasks',query:{space:'a',view:'history'},hash:''})
  assert.match(route('tasks').component.toString(),/TasksView\.vue/)
  for (const name of ['collect','tasks','releases']) assert.deepEqual(route(name).meta,{requiresAuth:true,requiresInit:true})
  const menu=readFileSync(new URL('../stores/menu.ts',import.meta.url),'utf8')
  assert.match(menu,/title: '资料任务'[^\n]+path: 'tasks'/)
  assert.doesNotMatch(menu,/path: '(collect|releases)'/)
})
