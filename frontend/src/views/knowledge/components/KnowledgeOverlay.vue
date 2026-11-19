<script lang="ts">
const activeOverlays: string[] = []
</script>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

defineOptions({ inheritAttrs: false })
const props = defineProps<{ visible: boolean; drawer?: boolean }>()
const id = useId()
const marker = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null

const panel = () => marker.value?.closest<HTMLElement>('.t-dialog, .t-drawer')
function focusable(element: HTMLElement) {
  return Array.from(element.querySelectorAll<HTMLElement>('a[href],button,input,select,textarea,[tabindex],[contenteditable="true"]'))
    .filter(item => item.tabIndex >= 0 && !item.matches(':disabled') && !item.closest('[inert]') &&
      item.getClientRects().length > 0 && getComputedStyle(item).visibility === 'visible')
}
function focusInitial() {
  const element = panel()
  if (!props.visible || activeOverlays.at(-1) !== id || !element || element.contains(document.activeElement)) return
  const items = focusable(element)
  const field = items.find(item => item.matches('.t-dialog__body input:not([type="checkbox"]):not([type="radio"]), .t-dialog__body textarea'))
  const cancel = items.find(item => item.closest('.t-dialog__footer, .t-drawer__footer') && /^(取消|关闭)$/.test(item.textContent?.trim() || ''))
  ;(field || cancel || items[0] || element).focus({ preventScroll: true })
}
function keepTabInside(event: KeyboardEvent) {
  if (event.key !== 'Tab' || activeOverlays.at(-1) !== id) return
  const element = panel()
  if (!element) return
  const items = focusable(element)
  const first = items[0], last = items.at(-1)
  if (!items.includes(document.activeElement as HTMLElement) || document.activeElement === (event.shiftKey ? first : last)) {
    event.preventDefault()
    ;(event.shiftKey ? last : first)?.focus()
  }
}
function release() {
  const index = activeOverlays.lastIndexOf(id)
  if (index === -1) return
  const restore = index === activeOverlays.length - 1 ? opener : null
  activeOverlays.splice(index, 1)
  document.removeEventListener('keydown', keepTabInside, true)
  opener = null
  void nextTick(() => {
    if (restore?.isConnected && !restore.closest('[inert]')) restore.focus({ preventScroll: true })
  })
}
watch(() => props.visible, visible => {
  if (!visible) { release(); return }
  opener = document.activeElement as HTMLElement | null
  activeOverlays.push(id)
  document.addEventListener('keydown', keepTabInside, true)
  void nextTick(focusInitial)
}, { immediate: true, flush: 'sync' })
onBeforeUnmount(release)
</script>

<template>
  <component :is="drawer ? 't-drawer' : 't-dialog'" v-bind="$attrs" :visible="visible" :inert="!visible"
    :role="visible ? 'dialog' : undefined" :aria-modal="visible ? 'true' : undefined" :aria-hidden="!visible"
    :aria-label="visible && typeof $attrs.header === 'string' ? $attrs.header : undefined" @opened="focusInitial">
    <template #default><span ref="marker" hidden /><slot /></template>
    <template v-for="name in Object.keys($slots).filter(key => key !== 'default')" #[name]="scope">
      <slot :name="name" v-bind="scope || {}" />
    </template>
  </component>
</template>
