import assert from 'node:assert/strict'
import test from 'node:test'
import { stateLabel, stateTheme, permissionLabel, spaceName, memberRoleLabel, contextdbToolLabel } from './platformPresentation.ts'

test('the same API state keeps its stage-specific business meaning', () => {
  assert.equal(stateLabel('completed', 'task'), '检查完成')
  assert.equal(stateLabel('completed', 'upload'), '提交完成')
  assert.equal(stateLabel('succeeded', 'ingest'), '已入库')
  assert.equal(stateLabel('succeeded', 'wiki'), '生成完成')
  assert.equal(stateLabel('approved', 'review'), '人工通过')
})

test('missing and unknown states never appear as success or failure', () => {
  assert.equal(stateLabel(null, 'ingest'), '未返回')
  assert.equal(stateLabel('future_state', 'ingest'), '未知状态')
  assert.equal(stateTheme('future_state'), 'default')
  assert.equal(stateTheme('submitted'), 'default')
  assert.equal(permissionLabel('kb_manage'), '管理')
  assert.equal(permissionLabel(null), '未返回')
  assert.equal(permissionLabel('none'), '无权限')
  assert.equal(memberRoleLabel('editor'), '编辑者')
  assert.equal(spaceName('space-123', [{scope:'space-123',name:'产品知识'}]), '产品知识')
  assert.equal(spaceName('missing', []), '名称未获取')
  assert.equal(spaceName('default', []), '默认知识库')
  assert.equal(spaceName('default', [{scope:'default',name:'默认知识空间'}]), '默认知识库')
  assert.equal(spaceName('default', [{scope:'default',name:'产品文档'}]), '产品文档')
  assert.equal(spaceName('custom', [{scope:'custom',name:'默认知识空间'}]), '默认知识空间')
})

test('known ContextDB tools describe their actual action and preserve unknown operation names', () => {
  assert.equal(contextdbToolLabel('knowledge.search'),'检索知识')
  assert.equal(contextdbToolLabel('knowledge.delete_base'),'删除知识库')
  assert.equal(contextdbToolLabel('knowledge.list_entity_chunks'),'查看实体来源')
  assert.equal(contextdbToolLabel('remember_fact'),undefined)
  assert.equal(contextdbToolLabel('search_memories'),undefined)
  assert.equal(contextdbToolLabel('knowledge.future_operation'),undefined)
  assert.equal(contextdbToolLabel('constructor'),undefined)
})
