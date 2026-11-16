<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import G6, { type IGraph } from '@antv/g6'
import { buildGraphData } from './contextdbGraphPresentation'

const props = defineProps<{
  nodes: { id: string; label: string; group?: string }[]
  edges: { id: string; from: string; to: string; label: string }[]
  rootId: string
  selectedId: string
  isRelation: boolean
}>()
const emit = defineEmits<{
  (e: 'select', id: string, relation: boolean): void
  (e: 'zoom', scale: number): void
}>()
const stage = ref<HTMLDivElement | null>(null), error = ref('')
let graph: IGraph | undefined, observer: ResizeObserver | undefined, appearanceObserver: MutationObserver | undefined
let mounted = false, canvasWidth = 0, canvasHeight = 0

function appearance() {
  const css = getComputedStyle(stage.value!)
  const brand = css.getPropertyValue('--td-brand-color').trim()
  const stroke = css.getPropertyValue('--td-component-border').trim()
  return {
    brand, surface: css.getPropertyValue('--td-bg-color-container').trim(),
    nodeLabel: { fill: css.getPropertyValue('--td-text-color-primary').trim(), fontFamily: css.fontFamily, fontSize: parseFloat(css.getPropertyValue('--app-text-base')), background: { fill: css.getPropertyValue('--td-bg-color-sidebar').trim(), padding: [2, 4] } },
    edgeLabel: { fill: css.getPropertyValue('--td-text-color-secondary').trim(), fontFamily: css.fontFamily, fontSize: parseFloat(css.getPropertyValue('--app-text-sm')) },
    edge: { stroke, lineWidth: 1, endArrow: { path: G6.Arrow.triangle(5, 7, 0), fill: stroke } },
    selected: { stroke: brand, lineWidth: 3 },
  }
}
function updateAppearance() {
  if (!graph || !stage.value) return
  const theme = appearance()
  for (const node of graph.getNodes()) graph.updateItem(node, { style: { stroke: node.getID() === props.rootId ? theme.brand : theme.surface }, stateStyles: { selected: theme.selected }, labelCfg: { style: theme.nodeLabel } })
  for (const edge of graph.getEdges()) graph.updateItem(edge, { style: theme.edge, stateStyles: { selected: theme.selected }, labelCfg: { style: theme.edgeLabel } })
  selectItem()
}
function reportZoom() { if (graph) emit('zoom', graph.getZoom()) }
function selectItem() {
  if (!graph) return
  for (const item of [...graph.getNodes(), ...graph.getEdges()]) graph.clearItemStates(item, ['selected'])
  const selected = props.selectedId && graph.findById(props.selectedId)
  if (selected) graph.setItemState(selected, 'selected', true)
}
function disposeGraph() {
  graph?.destroy(); graph = undefined
}
function renderGraph() {
  if (!mounted || !stage.value) return
  disposeGraph(); error.value = ''
  if (!props.nodes.length || !stage.value.clientWidth || !stage.value.clientHeight) return
  try {
    const data = buildGraphData(props.nodes, props.edges, props.rootId)
    const theme = appearance()
    for (const node of data.nodes) node.style.stroke = node.id === props.rootId ? theme.brand : theme.surface
    G6.Util.processParallelEdges(data.edges, 24)
    canvasWidth = stage.value.clientWidth; canvasHeight = stage.value.clientHeight
    const instance = new G6.Graph({
      container: stage.value,
      width: stage.value.clientWidth,
      height: stage.value.clientHeight,
      // Start at readable node and label sizes; the fit button provides the full overview.
      fitView: false,
      fitViewPadding: 48,
      animate: false,
      layout: { type: 'force', preventOverlap: true, nodeSize: 64, nodeStrength: -420, linkDistance: 170, alphaDecay: 0.05 },
      defaultNode: {
        type: 'circle', size: 32,
        labelCfg: { position: 'bottom', offset: 9, style: theme.nodeLabel },
      },
      defaultEdge: {
        type: 'quadratic',
        style: theme.edge,
        labelCfg: { autoRotate: true, style: theme.edgeLabel },
      },
      nodeStateStyles: { selected: theme.selected },
      edgeStateStyles: { selected: theme.selected },
      modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
    })
    graph = instance
    instance.on('node:click', event => emit('select', String(event.item!.getID()), false))
    instance.on('edge:click', event => emit('select', String(event.item!.getID()), true))
    instance.on('viewportchange', reportZoom)
    let initialCamera = true
    instance.on('afterlayout', () => {
      if (graph !== instance) return
      if (initialCamera) {
        initialCamera = false
        const degrees = new Map<string, number>()
        for (const edge of data.edges) for (const id of [edge.source, edge.target]) degrees.set(id, (degrees.get(id) || 0) + 1)
        const central = data.nodes.reduce((best, node) => (degrees.get(node.id) || 0) > (degrees.get(best.id) || 0) ? node : best)
        instance.zoomTo(1, { x: 0, y: 0 })
        instance.focusItem(instance.findById(props.rootId) ? props.rootId : central.id)
      }
      selectItem(); reportZoom()
    })
    instance.data(data)
    instance.render()
    selectItem(); reportZoom()
  } catch (cause) {
    disposeGraph(); error.value = cause instanceof Error ? cause.message : '图谱绘制失败，请重试。'
  }
}
function fit() { graph?.fitView(48); reportZoom() }
function focus(id: string) {
  if (!graph?.findById(id)) return
  graph.focusItem(id); reportZoom()
}
function zoom(factor: number) {
  if (!graph || !stage.value) return
  const next = Math.max(0.02, Math.min(5, graph.getZoom() * factor))
  graph.zoomTo(next, { x: stage.value.clientWidth / 2, y: stage.value.clientHeight / 2 }); reportZoom()
}
function keyPan(event: KeyboardEvent) {
  if (event.target !== event.currentTarget || !graph) return
  const movement: Record<string, [number, number]> = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] }
  if (movement[event.key]) { event.preventDefault(); graph.translate(...movement[event.key]!) }
  else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(1.25) }
  else if (event.key === '-') { event.preventDefault(); zoom(1 / 1.25) }
  else if (event.key === '0') { event.preventDefault(); fit() }
}
watch(() => [props.nodes, props.edges, props.rootId], renderGraph, { flush: 'post' })
watch(() => [props.selectedId, props.isRelation], selectItem)
onMounted(() => {
  mounted = true
  appearanceObserver = new MutationObserver(updateAppearance)
  appearanceObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['theme-mode', 'style'] })
  observer = new ResizeObserver(() => {
    if (!stage.value?.clientWidth || !stage.value.clientHeight) return
    if (!graph) renderGraph()
    else if (canvasWidth !== stage.value.clientWidth || canvasHeight !== stage.value.clientHeight) {
      canvasWidth = stage.value.clientWidth; canvasHeight = stage.value.clientHeight
      graph.changeSize(canvasWidth, canvasHeight); reportZoom()
    }
  })
  if (stage.value) observer.observe(stage.value)
  renderGraph()
})
onUnmounted(() => { mounted = false; observer?.disconnect(); appearanceObserver?.disconnect(); disposeGraph() })
defineExpose({ fit, focus, zoom })
</script>

<template>
  <div class="contextdb-graph-canvas" role="group" aria-label="实体关系图谱：拖动画布平移，滚轮缩放，拖动节点调整位置；方向键平移，加减键缩放，0 适应画布。可通过实体定位框选择节点。" tabindex="0" @keydown="keyPan">
    <div ref="stage" class="graph-engine" aria-hidden="true" />
    <t-alert v-if="error" class="graph-render-error" theme="error" :message="error"><template #operation><t-button variant="text" @click="renderGraph">重试绘制</t-button></template></t-alert>
  </div>
</template>

<style scoped lang="less">
.contextdb-graph-canvas { position: relative; width: 100%; height: 100%; min-width: 0; min-height: 0; background: var(--td-bg-color-sidebar); }
.contextdb-graph-canvas:focus-visible { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
.graph-engine { position: absolute; inset: 0; width: 100%; height: 100%; }
.graph-render-error { position: absolute; z-index: 1; top: 12px; left: 12px; right: 12px; }
</style>
