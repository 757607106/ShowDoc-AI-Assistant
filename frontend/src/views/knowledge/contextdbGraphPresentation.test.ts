import assert from 'node:assert/strict'
import test from 'node:test'
import { buildGraphData, graphNodeLabel, graphTypeColor } from './contextdbGraphPresentation.ts'

test('official type palette uses stable unsigned hashes rather than query ordering', () => {
  assert.equal(graphTypeColor('technology'), '#2e6fdb')
  assert.equal(graphTypeColor('concept'), '#237f92')
  assert.equal(graphTypeColor('document'), '#27805c')
  assert.equal(graphTypeColor('person'), '#a26a21')
  assert.equal(graphTypeColor('product'), '#a65877')
  assert.equal(graphTypeColor('a'.repeat(300)), '#8763ab')
  assert.equal(graphTypeColor('中文类型'), '#237f92')
  assert.equal(graphTypeColor(''), '#2e6fdb')
  assert.equal(graphTypeColor(), '#2e6fdb')
})

test('official node labels retain 24 characters and truncate longer labels at 23 plus three dots', () => {
  assert.equal(graphNodeLabel('实体名称'), '实体名称')
  assert.equal(graphNodeLabel('名'.repeat(24)), '名'.repeat(24))
  assert.equal(graphNodeLabel('名'.repeat(25)), '名'.repeat(23) + '...')
})

test('graph data preserves opaque identities and full names while applying official root styling', () => {
  const nodes = [
    { id: '不透明/根:实体', label: '图谱实体名称'.repeat(6), group: 'concept' },
    { id: '不透明:目标', label: '目标实体', group: 'document' },
  ]
  const edges = [{ id: '不透明/关系', from: nodes[0]!.id, to: nodes[1]!.id, label: '关系类型'.repeat(12) }]
  const before = JSON.stringify({ nodes, edges })
  const result = buildGraphData(nodes, edges, nodes[0]!.id)
  assert.equal(result.nodes[0]!.id, nodes[0]!.id)
  assert.equal(result.nodes[0]!.fullLabel, nodes[0]!.label)
  assert.equal(result.nodes[0]!.label, graphNodeLabel(nodes[0]!.label))
  assert.equal(result.nodes[0]!.size, 46)
  assert.deepEqual(result.nodes[0]!.style, { fill: '#237f92', stroke: '#172337', lineWidth: 3 })
  assert.equal(result.nodes[1]!.size, 32)
  assert.deepEqual(result.nodes[1]!.style, { fill: '#27805c', stroke: '#fff', lineWidth: 2 })
  assert.deepEqual(result.edges[0], { ...edges[0], source: nodes[0]!.id, target: nodes[1]!.id })
  assert.equal(result.edges[0]!.label, edges[0]!.label)
  assert.equal(JSON.stringify({ nodes, edges }), before)
})

test('graph data blanks ASCII relation identifiers while retaining Chinese labels', () => {
  const nodes = [{ id: 'a', label: '甲' }, { id: 'b', label: '乙' }]
  const result = buildGraphData(nodes, [
    { id: 'english', from: 'a', to: 'b', label: 'contains_module' },
    { id: 'chinese', from: 'b', to: 'a', label: '包含' },
  ])
  assert.deepEqual(result.edges.map(edge => edge.label), ['', '包含'])
})

test('parallel and self relationships remain available while unknown endpoints are omitted', () => {
  const nodes = [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]
  const edges = [
    { id: 'first', from: 'a', to: 'b', label: '使用' },
    { id: 'second', from: 'a', to: 'b', label: '依赖' },
    { id: 'reverse', from: 'b', to: 'a', label: '属于' },
    { id: 'self', from: 'a', to: 'a', label: '引用' },
    { id: 'missing', from: 'a', to: 'missing', label: '未知' },
  ]
  const result = buildGraphData(nodes, edges)
  assert.deepEqual(result.edges.map(edge => edge.id), ['first', 'second', 'reverse', 'self'])
  assert.ok(result.nodes.every(node => node.size === 32))
  assert.deepEqual(buildGraphData([], []), { nodes: [], edges: [] })
})
