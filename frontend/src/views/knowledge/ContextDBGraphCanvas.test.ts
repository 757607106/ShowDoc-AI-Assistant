import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import * as presentation from './contextdbGraphPresentation.ts'

const source = readFileSync(new URL('./ContextDBGraphCanvas.vue', import.meta.url), 'utf8')
const script = source.slice(source.indexOf('<script setup lang="ts">') + '<script setup lang="ts">'.length, source.indexOf('</script>'))
const compiled = ts.transpileModule(script + '\nexports.state = { stage, error, renderGraph, fit, focus, zoom, keyPan };', {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText
const plain = (value: any) => JSON.parse(JSON.stringify(value))

function fixture(width = 830, height = 406, fail = false) {
  const props = vue.reactive({
    nodes: [{ id: '产品甲', label: '产品甲', group: 'document' }, { id: '组件乙', label: '组件乙', group: 'concept' }],
    edges: [{ id: 'relation', from: '产品甲', to: '组件乙', label: '包含' }],
    rootId: '产品甲', selectedId: '', isRelation: false,
  })
  const events: any[] = [], instances: Engine[] = [], cleanup: (() => void)[] = []
  let mount = () => {}, resize = () => {}, changeAppearance = () => {}, disconnects = 0, appearanceDisconnects = 0
  const theme: Record<string, string> = {
    '--td-brand-color': '#07c05f', '--td-component-border': '#dcdcdc', '--td-bg-color-container': '#fff',
    '--td-bg-color-sidebar': '#f9f9f9', '--td-text-color-primary': 'rgba(0,0,0,0.9)',
    '--td-text-color-secondary': 'rgba(0,0,0,0.6)', '--app-text-base': '14px', '--app-text-sm': '12px', fontFamily: 'WeKnora Sans',
  }
  class Engine {
    listeners = new Map<string, (event?: any) => void>()
    dataValue: any; destroyed = false; scale = 0.75; tx = 100; ty = 40; refreshes = 0
    changes: any[] = []; selections: any[] = []; fits: any[] = []; focuses: any[] = []; translations: any[] = []
    constructor(public options: any) { instances.push(this) }
    data(value: any) { this.dataValue = value; value.nodes.forEach((model: any, i: number) => { model.x = -1000 + i * 4000; model.y = -2000 + i * 7000 }) }
    render() { if (fail) throw new Error('drawing failed') }
    on(name: string, handler: (event?: any) => void) { this.listeners.set(name, handler) }
    trigger(name: string, event?: any) { this.listeners.get(name)?.(event) }
    getNodes() { return this.dataValue.nodes.map((model: any) => ({ id: model.id, getID: () => model.id, getModel: () => model })) }
    getEdges() { return this.dataValue.edges.map((model: any) => ({ id: model.id, getID: () => model.id, getModel: () => model })) }
    clearItemStates(item: any, states: string[]) { this.selections.push(['clear', item.id, states]) }
    setItemState(item: any, state: string, selected: boolean) { this.selections.push(['select', item.id, state, selected]) }
    findById(id: string) { return [...this.getNodes(), ...this.getEdges()].find(item => item.id === id) }
    fitView(padding: number) { this.fits.push(padding); this.scale = 0.5 }
    getZoom() { return this.scale }
    zoomTo(scale: number, point: any) { this.scale = scale; this.changes.push(['zoom', scale, point]) }
    focusItem(id: string) { this.focuses.push(id); const model = this.findById(id).getModel(); this.tx = this.options.width / 2 - model.x * this.scale; this.ty = this.options.height / 2 - model.y * this.scale }
    changeSize(width: number, height: number) { this.options.width = width; this.options.height = height; this.changes.push(['resize', width, height]) }
    translate(x: number, y: number) { this.translations.push([x, y]); this.tx += x; this.ty += y }
    getCanvasByPoint(x: number, y: number) { return { x: x * this.scale + this.tx, y: y * this.scale + this.ty } }
    refreshPositions() { this.refreshes++ }
    updateItem(item: any, update: any) {
      const model = item.getModel()
      Object.assign(model, { ...update, style: { ...model.style, ...update.style }, labelCfg: { ...model.labelCfg, ...update.labelCfg } })
    }
    destroy() { this.destroyed = true }
  }
  const parallel: any[] = [], exports: { state?: any } = {}, scope = vue.effectScope()
  const modules: Record<string, any> = {
    vue: { ...vue, onMounted: (fn: () => void) => { mount = fn }, onUnmounted: (fn: () => void) => cleanup.push(fn) },
    '@antv/g6': { __esModule: true, default: { Graph: Engine, Arrow: { triangle: (...args: any[]) => args.join(',') }, Util: { processParallelEdges: (edges: any[], spacing: number) => parallel.push([plain(edges), spacing]) } } },
    './contextdbGraphPresentation': presentation,
  }
  scope.run(() => vm.runInNewContext(compiled, {
    exports, defineProps: () => props, defineEmits: () => (...args: any[]) => events.push(args), defineExpose() {},
    require: (name: string) => { assert.ok(name in modules, name); return modules[name] },
    ResizeObserver: class { constructor(fn: () => void) { resize = fn } observe() {} disconnect() { disconnects++ } },
    MutationObserver: class { constructor(fn: () => void) { changeAppearance = fn } observe() {} disconnect() { appearanceDisconnects++ } },
    document: { documentElement: {} },
    getComputedStyle: () => ({ fontFamily: theme.fontFamily, getPropertyValue: (key: string) => theme[key] || '' }),
  }))
  const element = { clientWidth: width, clientHeight: height }
  exports.state!.stage.value = element
  mount()
  return { ...exports.state, props, instances, events, element, parallel, resize: () => resize(), disconnects: () => disconnects, appearanceDisconnects: () => appearanceDisconnects,
    changeAppearance: (values: Record<string, string>) => { Object.assign(theme, values); changeAppearance() },
    flush: async () => { await vue.nextTick(); await new Promise(resolve => setImmediate(resolve)) },
    dispose() { cleanup.forEach(fn => fn()); scope.stop() }, fail: (value: boolean) => { fail = value } }
}

test('official renderer uses the measured canvas, G6 force, node sizes, labels and drag interactions', t => {
  const f = fixture(); t.after(f.dispose)
  const engine = f.instances[0]!, options = engine.options
  assert.equal(options.width, 830); assert.equal(options.height, 406)
  assert.equal(options.fitView, false); assert.equal(options.fitViewPadding, 48); assert.equal(options.animate, false)
  assert.deepEqual(plain(options.layout), { type: 'force', preventOverlap: true, nodeSize: 64, nodeStrength: -420, linkDistance: 170, alphaDecay: 0.05 })
  assert.deepEqual(plain(options.modes.default), ['drag-canvas', 'zoom-canvas', 'drag-node'])
  assert.equal(options.defaultNode.labelCfg.style.fontSize, 14); assert.equal(options.defaultNode.labelCfg.offset, 9)
  assert.equal(options.defaultEdge.labelCfg.autoRotate, true); assert.equal(options.defaultEdge.labelCfg.style.fontSize, 12)
  assert.equal(options.defaultNode.labelCfg.style.fontFamily, 'WeKnora Sans')
  assert.equal(options.nodeStateStyles.selected.stroke, '#07c05f')
  assert.deepEqual(engine.dataValue.nodes.map((node: any) => node.size), [46, 32])
  assert.equal(engine.dataValue.edges[0].source, '产品甲'); assert.equal(engine.dataValue.edges[0].target, '组件乙')
  assert.equal(f.parallel[0][1], 24)
})

test('node and edge clicks retain opaque IDs, and selecting details never rebuilds or mutes the graph', async t => {
  const f = fixture(); t.after(f.dispose)
  const engine = f.instances[0]!
  engine.trigger('node:click', { item: { getID: () => '产品甲' } })
  engine.trigger('edge:click', { item: { getID: () => 'relation' } })
  assert.deepEqual(plain(f.events.filter((event: any[]) => event[0] === 'select')), [['select', '产品甲', false], ['select', 'relation', true]])
  f.props.selectedId = 'relation'; f.props.isRelation = true; await f.flush()
  assert.equal(f.instances.length, 1)
  assert.deepEqual(plain(engine.selections.at(-1)), ['select', 'relation', 'selected', true])
  assert.ok(engine.dataValue.nodes.every((node: any) => node.style.opacity === undefined))
})

test('locating preserves zoom, fit uses official padding and zoom anchors the measured canvas center', t => {
  const f = fixture(); t.after(f.dispose); const engine = f.instances[0]!
  f.focus('组件乙'); assert.deepEqual(engine.focuses, ['组件乙']); assert.equal(engine.scale, 0.75)
  f.focus('missing'); assert.equal(engine.focuses.length, 1)
  f.fit(); assert.deepEqual(engine.fits, [48]); assert.equal(engine.scale, 0.5)
  f.zoom(2); assert.deepEqual(plain(engine.changes.at(-1)), ['zoom', 1, { x: 415, y: 203 }])
  engine.trigger('afterlayout'); assert.deepEqual(engine.fits, [48], 'layout completion does not apply a second custom fit')
  assert.equal(engine.refreshes, 0, 'settled force coordinates are not projected or rewritten')
})

test('resize preserves manual zoom and settled coordinates while graph changes destroy the prior engine', async t => {
  const f = fixture(); t.after(f.dispose); const first = f.instances[0]!
  const before = plain(first.dataValue.nodes); first.scale = 1.25
  f.element.clientWidth = 1260; f.element.clientHeight = 700; f.resize()
  assert.deepEqual(first.changes, [['resize', 1260, 700]]); assert.equal(first.scale, 1.25)
  assert.deepEqual(plain(first.dataValue.nodes), before); assert.equal(first.refreshes, 0)
  f.props.nodes = [...f.props.nodes, { id: 'new', label: '新增实体', group: 'concept' }]; await f.flush()
  assert.equal(first.destroyed, true); assert.equal(f.instances.length, 2)
  assert.equal(f.instances[1]!.options.width, 1260); assert.equal(f.instances[1]!.options.height, 700)
})

test('hidden canvases wait for a real size and unmount disconnects and destroys rendering', () => {
  const f = fixture(0, 0)
  assert.equal(f.instances.length, 0)
  f.element.clientWidth = 640; f.element.clientHeight = 480; f.resize(); assert.equal(f.instances.length, 1)
  f.dispose(); assert.equal(f.disconnects(), 1); assert.equal(f.appearanceDisconnects(), 1); assert.equal(f.instances[0]!.destroyed, true)
})

test('render failures remain visible and retry replaces the failed engine', t => {
  const f = fixture(830, 406, true); t.after(f.dispose)
  assert.equal(f.instances[0]!.destroyed, true); assert.match(f.error.value, /绘制失败/)
  f.fail(false); f.renderGraph(); assert.equal(f.error.value, ''); assert.equal(f.instances.length, 2)
})

test('keyboard panning and zooming work without intercepting focused child controls', t => {
  const f = fixture(); t.after(f.dispose); const element = {}
  let prevented = 0
  f.keyPan({ target: element, currentTarget: element, key: 'ArrowRight', preventDefault() { prevented++ } })
  assert.deepEqual(f.instances[0]!.translations.at(-1), [-40, 0])
  f.keyPan({ target: {}, currentTarget: element, key: '+', preventDefault() { prevented++ } })
  assert.equal(f.instances[0]!.scale, 0.75)
  f.keyPan({ target: element, currentTarget: element, key: '+', preventDefault() { prevented++ } })
  assert.equal(f.instances[0]!.scale, 0.9375); assert.equal(prevented, 2)
})


test('zoomed entity locating keeps its chosen zoom when opening details changes the canvas width', async t => {
  const f = fixture(); t.after(f.dispose); const engine = f.instances[0]!
  engine.scale = 2; f.focus('组件乙'); f.props.selectedId = '组件乙'; await f.flush()
  f.element.clientWidth = 470; f.resize()
  assert.equal(engine.scale, 2); assert.deepEqual(engine.focuses, ['组件乙'])
  assert.equal(engine.refreshes, 0, 'opening details only resizes the renderer and does not repack nodes')
})


test('initial camera opens at readable scale around the root while later layout events preserve user zoom', t => {
  const f = fixture(); t.after(f.dispose); const engine = f.instances[0]!
  const positions = plain(engine.dataValue.nodes)
  engine.trigger('afterlayout')
  assert.equal(engine.scale, 1); assert.deepEqual(engine.focuses, ['产品甲'])
  assert.deepEqual(plain(engine.dataValue.nodes), positions); assert.equal(engine.refreshes, 0)
  engine.scale = 2; engine.trigger('afterlayout')
  assert.equal(engine.scale, 2); assert.deepEqual(engine.focuses, ['产品甲'])
  f.fit(); assert.deepEqual(engine.fits, [48])
})

test('whole-library initial camera chooses the most connected returned entity with stable first-node ties', async t => {
  const f = fixture(); t.after(f.dispose)
  f.props.rootId = ''; f.props.nodes = [...f.props.nodes, { id: '叶节点', label: '叶节点', group: 'concept' }]
  f.props.edges = [...f.props.edges, { id: 'extra', from: '组件乙', to: '叶节点', label: '使用' }]
  await f.flush(); const engine = f.instances.at(-1)!
  engine.trigger('afterlayout'); assert.equal(engine.scale, 1); assert.deepEqual(engine.focuses, ['组件乙'])
  f.props.edges = [{ id: 'tie', from: '产品甲', to: '组件乙', label: '包含' }]; await f.flush()
  const tied = f.instances.at(-1)!; tied.trigger('afterlayout'); assert.deepEqual(tied.focuses, ['产品甲'])
})

test('theme and font changes update canvas appearance without changing entity colors, positions or zoom', async t => {
  const f = fixture(); t.after(f.dispose); const engine = f.instances[0]!
  f.props.selectedId = 'relation'; f.props.isRelation = true; await f.flush()
  engine.scale = 2
  const positions = engine.dataValue.nodes.map(({ id, x, y, size, style }: any) => ({ id, x, y, size, fill: style.fill }))
  f.changeAppearance({ '--td-brand-color': '#06b04d', '--td-bg-color-container': '#242424', '--td-bg-color-sidebar': '#181818',
    '--td-text-color-primary': '#eee', '--td-text-color-secondary': '#aaa', '--td-component-border': '#5e5e5e', fontFamily: 'User Sans' })
  assert.equal(f.instances.length, 1); assert.equal(engine.scale, 2); assert.equal(engine.refreshes, 0)
  assert.deepEqual(engine.dataValue.nodes.map(({ id, x, y, size, style }: any) => ({ id, x, y, size, fill: style.fill })), positions)
  assert.equal(engine.dataValue.nodes[0].style.stroke, '#06b04d'); assert.equal(engine.dataValue.nodes[1].style.stroke, '#242424')
  assert.equal(engine.dataValue.nodes[0].labelCfg.style.fill, '#eee'); assert.equal(engine.dataValue.nodes[0].labelCfg.style.fontFamily, 'User Sans')
  assert.equal(engine.dataValue.nodes[0].labelCfg.style.background.fill, '#181818')
  assert.equal(engine.dataValue.edges[0].style.stroke, '#5e5e5e'); assert.equal(engine.dataValue.edges[0].style.endArrow.fill, '#5e5e5e')
  assert.equal(engine.dataValue.edges[0].labelCfg.style.fill, '#aaa'); assert.equal(engine.dataValue.edges[0].stateStyles.selected.stroke, '#06b04d')
  assert.deepEqual(plain(engine.selections.at(-1)), ['select', 'relation', 'selected', true])
})
