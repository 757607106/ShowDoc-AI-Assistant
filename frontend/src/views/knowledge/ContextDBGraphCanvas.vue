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
let graph: IGraph | undefined, observer: ResizeObserver | undefined
let mounted = false, canvasWidth = 0, canvasHeight = 0

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
        labelCfg: { position: 'bottom', offset: 9, style: { fill: '#202939', fontSize: 12, background: { fill: '#f6f8fb', padding: [2, 4] } } },
      },
      defaultEdge: {
        type: 'quadratic',
        style: { stroke: '#a2afc1', lineWidth: 1, endArrow: { path: G6.Arrow.triangle(5, 7, 0), fill: '#a2afc1' } },
        labelCfg: { autoRotate: true, style: { fill: '#647086', fontSize: 11 } },
      },
      nodeStateStyles: { selected: { stroke: '#172337', lineWidth: 3 } },
      edgeStateStyles: { selected: { stroke: '#2e6fdb', lineWidth: 3 } },
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
onUnmounted(() => { mounted = false; observer?.disconnect(); disposeGraph() })
defineExpose({ fit, focus, zoom })
</script>

<template>
  <div class="contextdb-graph-canvas" role="group" aria-label="实体关系图谱：拖动画布平移，滚轮缩放，拖动节点调整位置；方向键平移，加减键缩放，0 适应画布。可通过实体定位框选择节点。" tabindex="0" @keydown="keyPan">
    <div ref="stage" class="graph-engine" aria-hidden="true" />
    <t-alert v-if="error" class="graph-render-error" theme="error" :message="error"><template #operation><t-button variant="text" @click="renderGraph">重试绘制</t-button></template></t-alert>
  </div>
</template>

<style scoped lang="less">
.contextdb-graph-canvas { position: relative; width: 100%; height: 100%; min-width: 0; min-height: 0; background: #f6f8fb; }
.contextdb-graph-canvas:focus-visible { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
.graph-engine { position: absolute; inset: 0; width: 100%; height: 100%; }
.graph-render-error { position: absolute; z-index: 1; top: 12px; left: 12px; right: 12px; }
</style>
