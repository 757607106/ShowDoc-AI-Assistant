import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const source=readFileSync(new URL('./ContextDBSettings.vue',import.meta.url),'utf8')
const script=source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)![1]!
const ast=ts.createSourceFile('Settings.ts',script,ts.ScriptTarget.Latest,true)
const closeHandler=ast.statements.find(statement=>ts.isFunctionDeclaration(statement)&&statement.name?.text==='close')
assert.ok(closeHandler)
const compiled=ts.transpileModule(closeHandler.getText(ast),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText

function closeSettings(back:unknown,name='settings'){
  const actions:string[]=[]
  runInNewContext(compiled+'\nclose()',{
    route:{name},ui:{closeSettings:()=>actions.push('close')},
    router:{options:{history:{state:{back}}},push:(path:string)=>actions.push('push:'+path),back:()=>actions.push('back')},
  })
  return actions
}

test('closing a directly opened settings route stays within the application',()=>{
  for(const back of [null,undefined,'','https://example.com/','//example.com/','/login']){
    assert.deepEqual(closeSettings(back),['close','push:/platform/knowledge-bases'])
  }
})

test('closing settings restores a known app route but leaves an overlay route unchanged',()=>{
  for(const back of ['/platform/knowledge-bases','/platform/chat/session-123'])assert.deepEqual(closeSettings(back),['close','back'])
  assert.deepEqual(closeSettings(null,'chat'),['close'])
})
