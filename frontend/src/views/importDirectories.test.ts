import assert from 'node:assert/strict'
import test from 'node:test'
import { directoryPreview, importDirectories } from './importDirectories.ts'

test('directory preview keeps source ancestors, root pages and literal slash characters in directory names', () => {
  const tree = directoryPreview('云辉煌知识库', [
    { page_id: 'root', page_title: '简介', directory_path: [] },
    { page_id: 'nested', page_title: '统计', directory_path: ['进货管理', '报表/统计'] },
  ])
  assert.equal(tree[0].label, '云辉煌知识库')
  assert.deepEqual(tree[0].children?.map(item => item.label), ['简介', '进货管理'])
  assert.equal(tree[0].children?.[1].children?.[0].label, '报表/统计')
  assert.equal(tree[0].children?.[1].children?.[0].children?.[0].label, '统计')
})
test('only landed directory references produce links, retaining each distinct root once', () => {
  const root = { knowledge_base_id: 'kb', node_id: 'node', root_name: '云辉煌知识库' }
  assert.deepEqual(importDirectories([root, root, { ...root, node_id: '' }, { ...root, knowledge_base_id: null }, { ...root, node_id: 'second' }]), [root, { ...root, node_id: 'second' }])
  assert.deepEqual(importDirectories(undefined), [])
})
