import assert from 'node:assert/strict'
import test, {type TestContext} from 'node:test'
import {reactive} from 'vue'
import {fixture, flush} from '../test-utils/vueFixture.ts'
import * as presentation from '../utils/platformPresentation.ts'
import * as materialTasks from './materialTasks.ts'

function setup(t: TestContext, options: {
  query?: Record<string, any>; contributor?: boolean;
  tasks?: (scope?: string, pagination?: any) => Promise<any>;
  taskStatus?: (id: string) => Promise<any>;
  cancel?: (id: string) => Promise<any>;
} = {}) {
  const f = fixture(t), reads: string[] = [], lists: any[] = [], writes: any[] = [], routes: any[] = [], guards: (() => boolean)[] = [], warnings: string[] = []
  let poll = () => {}
  Object.assign(f.window, {setInterval:(callback:()=>void) => {poll=callback; return 1}, clearInterval(){}})
  const route = reactive({query:options.query || {}, fullPath:'/platform/tasks'})
  const router = {replace:async (target:any) => {routes.push(target); route.query=target.query}, push:(target:any) => {routes.push(target)}}
  const {vm, close} = f.component(new URL('./TasksView.vue', import.meta.url), {
    'vue-router': {useRoute:()=>route, useRouter:()=>router, onBeforeRouteLeave:(guard:()=>boolean)=>guards.push(guard), onBeforeRouteUpdate:(guard:()=>boolean)=>guards.push(guard)},
    '@/stores/auth': {useAuthStore:()=>({hasRole:()=>options.contributor !== false})},
    'tdesign-vue-next': {MessagePlugin:{success(){}, warning:(message:string)=>warnings.push(message)}},
    '@/api/knowledgeSpaces': {getSpaces:async()=>({spaces:[{scope:'a', name:'A'}, {scope:'b', name:'B'}]})},
    '@/utils/platformPresentation': presentation,
    './materialTasks': materialTasks,
    '@/api/backend': {
      tasks:async (scope:string,pagination:any) => {lists.push({scope,...pagination}); return options.tasks ? options.tasks(scope,pagination) : {tasks:[],total:0}},
      taskStatus:async (id:string) => {reads.push(id); return options.taskStatus ? options.taskStatus(id) : {task_id:id,scope:'a',status:'completed',kind:'crawl',phase:'completed',failure_details:[{title:'视频来源',error:'源正文为空'}]}},
      cancelTask:async (id:string) => {writes.push({action:'cancel',id}); return options.cancel ? options.cancel(id) : {}},
      retryTask:async (id:string) => {writes.push({action:'retry',id}); return {task_id:'new-capture'}},
      submitTask:async (id:string) => {writes.push({action:'submit',id}); return {release_id:'new-release'}},
      retrySubmission:async (scope:string,id:string) => {writes.push({action:'retry-sync',scope,id}); return {success:true,result:{task_id:'new-submission'}}},
      downloadFile:async (url:string,name:string) => writes.push({url,name}), taskDownloadUrl:(id:string)=>'/download/'+id,
    },
  })
  return {vm, close, route, routes, reads, lists, writes, guards, warnings, poll:()=>poll()}
}

test('changing or closing details ignores delayed responses and keeps failure details and separate durations', async t => {
  const pending = new Map<string,(value:any)=>void>()
  const f = setup(t, {taskStatus:async id=>id==='slow'?new Promise(resolve=>pending.set(id,resolve)):{task_id:id,scope:'a',status:'partial',failure_details:[{title:'视频来源',error:'源正文为空'}]}})
  const slow = f.vm.openDetails('slow'); await f.vm.openDetails('current')
  pending.get('slow')!({task_id:'slow'}); await slow
  assert.equal(f.vm.detail.task_id, 'current'); assert.equal(f.vm.detail.failure_details[0].error, '源正文为空')
  const closing = f.vm.openDetails('slow'); f.vm.closeDetails(); pending.get('slow')!({task_id:'slow'}); await closing
  assert.equal(f.vm.detailId, ''); assert.equal(f.vm.detail, null); assert.equal(f.vm.detailPending, false)
  assert.equal(f.vm.duration(1800), '30 分 0 秒'); assert.equal(f.vm.duration(13), '13 秒')
})

test('a linked-detail read failure preserves the capture and its public submission summary', async t => {
  const summary = {task_id:'sync',scope:'a',kind:'ctxdb_sync',status:'running'}
  const f = setup(t, {taskStatus:async id=>{if(id==='sync')throw new Error('提交详情暂不可用');return {task_id:id,scope:'a',status:'completed',kind:'crawl',sync_task_id:'sync',submission_task:summary}}})
  await f.vm.openDetails('capture')
  assert.equal(f.vm.detail.task_id, 'capture'); assert.equal(f.vm.detailSubmission.task_id, 'sync')
  assert.match(f.vm.submissionReadError, /提交详情暂不可用/); assert.equal(f.vm.detailError, '')
})

test('background refresh has at most one in-flight detail request even when it takes longer than polling', async t => {
  let slow = false, resolve!:(value:any)=>void
  const f = setup(t,{taskStatus:async id=>slow?new Promise(yes=>resolve=yes):{task_id:id,scope:'a',status:'running'}})
  await flush(); await f.vm.openDetails('current'); slow=true
  f.poll(); f.poll(); f.poll()
  assert.equal(f.reads.length, 2)
  resolve({task_id:'current',scope:'a',status:'completed'}); await flush()
  assert.equal(f.vm.detail.status, 'completed'); assert.equal(f.vm.detailPending, false)
})

test('scope changes clear old rows and ignore an earlier list response', async t => {
  let resolve!:(value:any)=>void
  const f = setup(t,{query:{space:'a'},tasks:async scope=>scope==='a'?new Promise(yes=>resolve=yes):{tasks:[{task_id:'b-task',scope:'b',status:'pending'}],total:1}})
  f.vm.tasks=[{task_id:'old',scope:'a',status:'pending'}]
  f.route.query={space:'b'}; await flush()
  assert.equal(f.vm.tasks[0].scope,'b')
  resolve({tasks:[{task_id:'late-a',scope:'a'}],total:99}); await flush()
  assert.equal(f.vm.tasks[0].task_id,'b-task'); assert.equal(f.vm.total,1)
  f.vm.changePage(3); await flush(); assert.equal(f.lists.at(-1).scope,'b'); assert.equal(f.lists.at(-1).page,3)
})

test('only current operations refresh details, retrying a sync opens its newly returned task', async t => {
  let resolve!:(value:any)=>void
  const f=setup(t,{cancel:async()=>new Promise(yes=>resolve=yes)})
  await f.vm.openDetails('first')
  const cancelling=f.vm.act({task_id:'first',scope:'a',status:'running'},'cancel')
  await f.vm.openDetails('second'); resolve({}); await cancelling
  assert.equal(f.vm.detailId,'second')
  await f.vm.act({task_id:'old-sync',scope:'a',kind:'ctxdb_sync',status:'failed'},'retry-sync')
  assert.deepEqual(f.writes.at(-1),{action:'retry-sync',scope:'a',id:'old-sync'})
  assert.equal(f.vm.detailId,'new-submission')
})

test('viewer operations are rejected and queued submission is not cloud completion', async t => {
  const f=setup(t,{contributor:false}); await flush()
  await f.vm.act({task_id:'x',scope:'a',status:'running'},'cancel'); assert.equal(f.writes.length,0)
  assert.equal(f.vm.statusLabel({task_id:'x',scope:'a',kind:'crawl',status:'completed',phase:'submitted'}),'已排队提交')
  assert.equal(f.vm.statusLabel({task_id:'x',scope:'a',kind:'ctxdb_sync',status:'completed',phase:'submitted'}),'提交完成')
})

test('adding guards busy navigation and consumes legacy source parameters after it closes', async t => {
  const f=setup(t,{query:{add:'1',kb_id:'old-library',mode:'file',url:'https://example.com',space:'a'}})
  await flush(); f.vm.addingBusy=true
  assert.equal(f.guards.length,2); assert.ok(f.guards.every(guard=>guard()===false))
  f.vm.closeAdd(); assert.equal(f.routes.length,0)
  f.vm.addingBusy=false; assert.ok(f.guards.every(guard=>guard()===true)); f.vm.closeAdd(); await flush()
  assert.equal(f.route.query.kb_id,undefined); assert.equal(f.route.query.mode,undefined); assert.equal(f.route.query.url,undefined)
  await f.vm.changeScope('b'); f.vm.openAdd(); await flush()
  assert.equal(f.route.query.space,'b'); assert.equal(f.route.query.add,'1'); assert.equal(f.route.query.kb_id,undefined)
})

test('creation refreshes in place; show-tasks closes adding and locates the task; deep links work', async t => {
  const f=setup(t,{query:{add:'1',view:'tasks',task:'initial'}}); await flush()
  assert.equal(f.vm.detailId,'initial')
  f.vm.created(); await flush(); assert.equal(f.route.query.add,'1'); assert.equal(f.routes.length,0)
  await f.vm.showTasks({scope:'b',task_id:'new-file'}); await flush()
  assert.equal(f.route.query.add,undefined); assert.equal(f.route.query.view,'tasks'); assert.equal(f.route.query.space,'b')
  assert.equal(f.vm.detailId,'new-file'); assert.equal(f.vm.page,1); assert.equal(f.vm.filter,'all')
  f.vm.dismissDetails(); await flush(); assert.equal(f.route.query.task,undefined)
  f.vm.openKnowledgeBase({scope:'资料 /?#中文'})
  assert.equal(f.routes.at(-1).path,'/platform/knowledge-spaces/'+encodeURIComponent('资料 /?#中文'))
  assert.equal('query' in f.routes.at(-1),false)
})

test('unmount invalidates late list and detail responses', async t => {
  let list!:(value:any)=>void, read!:(value:any)=>void
  const f=setup(t,{tasks:async()=>new Promise(resolve=>list=resolve),taskStatus:async()=>new Promise(resolve=>read=resolve)})
  const detail=f.vm.openDetails('late'); f.close(); list({tasks:[{task_id:'late'}],total:1}); read({task_id:'late'}); await detail; await flush()
  assert.equal(f.vm.tasks.length,0); assert.equal(f.vm.detail,null)
})
