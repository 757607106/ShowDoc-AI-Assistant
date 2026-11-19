<script setup lang="ts">
import { ref, useId } from 'vue'

defineProps<{ label: string; options: { value: string; content: string; theme?: string }[]; iconOnly?: boolean; text?: string; disabled?: boolean }>()
const emit = defineEmits<{ select: [value: string] }>()
const triggerId = useId()
const open = ref(false)
const menu = ref<HTMLElement | null>(null)
let focusLast = false

function focusItem() {
  const items = menu.value?.querySelectorAll<HTMLButtonElement>('button')
  const item = focusLast ? items?.[items.length - 1] : items?.[0]
  item?.focus({ preventScroll: true })
}

function setOpen(visible: boolean, last = false) {
  focusLast = last
  if (visible && open.value) focusItem()
  open.value = visible
}

function close() {
  open.value = false
  document.getElementById(triggerId)?.focus({ preventScroll: true })
}

function navigate(event: KeyboardEvent) {
  if (event.key === 'Escape' || event.key === 'Tab') {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation() }
    // Move focus back before the browser handles Tab from the trigger's position.
    close()
    return
  }
  if (!menu.value || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const items = Array.from(menu.value.querySelectorAll<HTMLButtonElement>('button'))
  const index = items.indexOf(event.target as HTMLButtonElement)
  const step = event.key === 'ArrowDown' ? 1 : -1
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + step + items.length) % items.length
  items[next]?.focus({ preventScroll: true })
}
</script>

<template>
  <div class="knowledge-action-menu" @click.stop>
    <t-popup trigger="click" placement="bottom-right" overlay-class-name="card-more knowledge-action-popup"
      :visible="open" :disabled="disabled" @visible-change="(visible: boolean) => setOpen(visible)">
      <t-button :id="triggerId" variant="text" :shape="iconOnly ? 'square' : 'rectangle'" :size="iconOnly ? 'medium' : 'small'"
        :disabled="disabled" :aria-label="label" aria-haspopup="menu" :aria-expanded="open"
        @keydown.down.prevent="setOpen(true)" @keydown.up.prevent="setOpen(true, true)">
        <t-icon v-if="iconOnly" name="more" />
        <template v-else>{{ text || '更多' }}<t-icon name="chevron-down" /></template>
      </t-button>
      <template #content>
        <div v-if="open" ref="menu" class="card-menu" role="menu" :aria-labelledby="triggerId"
          @vue:mounted="focusItem" @keydown="navigate">
          <button v-for="item in options" :key="item.value" type="button" role="menuitem" tabindex="-1"
            class="card-menu-item" :class="{ danger: item.theme === 'error' }" @click="close(); emit('select', item.value)">
            {{ item.content }}
          </button>
        </div>
      </template>
    </t-popup>
  </div>
</template>

<style scoped lang="less">
.card-menu-item:focus-visible { outline: 2px solid var(--td-brand-color); outline-offset: -2px; }
// TDesign normally hides the entering overlay before its first frame.
:global(.knowledge-action-popup.t-popup--animation-enter-from) { visibility: visible; }
</style>
