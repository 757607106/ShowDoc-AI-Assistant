import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { runInNewContext } from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import { createRenderer, defineComponent, h, nextTick, ref } from 'vue'

test('closed image preview does not mount the viewer default thumbnail', async () => {
  const require = createRequire(import.meta.url)
  const source = readFileSync(new URL('./picture-preview.vue', import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = ts.transpile(compileScript(descriptor, { id: 'preview-test', inlineTemplate: true }).content, { module: ts.ModuleKind.CommonJS })
  const exports: Record<string, any> = {}
  runInNewContext(compiled, { exports, require })
  const visible = ref(false)
  const url = ref('')
  let viewerMounts = 0
  const renderer = createRenderer<any, any>({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
    insert() {}, remove() {}, setElementText() {}, setText() {}, patchProp() {},
    parentNode: () => null, nextSibling: () => null,
  })
  const app = renderer.createApp(defineComponent({
    setup: () => () => h(exports.default, { reviewImg: visible.value, reviewUrl: url.value }),
  }))
  app.component('t-image-viewer', defineComponent({ setup() { viewerMounts++; return () => h('div') } }))
  app.mount({})
  try {
    assert.equal(viewerMounts, 0)
    visible.value = true
    await nextTick()
    assert.equal(viewerMounts, 0, 'an empty URL cannot open the viewer')
    url.value = 'data:image/png;base64,example'
    await nextTick()
    assert.equal(viewerMounts, 1)
  } finally { app.unmount() }
})
