const typeColors = ['#2e6fdb', '#27805c', '#8763ab', '#a26a21', '#237f92', '#a65877']

export function graphTypeColor(group = ''): string {
  let hash = 0
  for (let i = 0; i < group.length; i++) hash = (hash * 31 + group.charCodeAt(i)) >>> 0
  return typeColors[hash % typeColors.length]!
}

export function graphNodeLabel(label: string): string {
  return label.length > 24 ? label.slice(0, 23) + '...' : label
}

interface EntityNode { id: string; label: string; group?: string }
interface EntityEdge { id: string; from: string; to: string; label: string }

export function buildGraphData(nodes: EntityNode[], edges: EntityEdge[], root = '') {
  const ids = new Set(nodes.map(node => node.id))
  return {
    nodes: nodes.map(node => ({
      ...node,
      label: graphNodeLabel(node.label),
      fullLabel: node.label,
      size: node.id === root ? 46 : 32,
      style: { fill: graphTypeColor(node.group), stroke: node.id === root ? '#172337' : '#fff', lineWidth: node.id === root ? 3 : 2 },
    })),
    edges: edges.filter(edge => ids.has(edge.from) && ids.has(edge.to)).map(edge => ({ ...edge, source: edge.from, target: edge.to })),
  }
}
