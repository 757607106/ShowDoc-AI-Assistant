<template>
  <Teleport to="body">
    <Transition name="settings-modal-shell">
      <div v-if="visible" class="settings-modal-shell settings-overlay" :class="[overlayClass, { 'has-compact-nav': compactNavLabel }]" :style="{ zIndex }"
        @click.self="emit('close')">
        <div ref="dialog" class="settings-modal" role="dialog" aria-modal="true" :aria-label="title"
          @keydown.tab="cycleDialogFocus">
          <div v-if="loading" class="editor-initializing" role="status" :aria-label="$t('common.loading')">
            <t-loading size="medium" :text="$t('common.loading')" />
          </div>

          <button ref="closeButton" class="close-btn" type="button" @click="emit('close')" :aria-label="$t('common.close')">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
          </button>

          <div class="settings-container">
            <aside class="settings-sidebar">
              <div class="sidebar-header">
                <h2 class="sidebar-title">{{ title }}</h2>
                <slot name="sidebar-header-extra" />
              </div>
              <button v-if="compactNavLabel" ref="compactToggle" class="compact-nav-toggle" type="button"
                :aria-label="`${compactNavLabel} · ${activeLabel}`" :aria-expanded="compactOpen" :aria-controls="navId"
                @click="compactOpen = !compactOpen" @keydown.esc="collapseCompactNav">
                {{ compactNavLabel }}
                <t-icon :name="compactOpen ? 'chevron-up' : 'chevron-down'" aria-hidden="true" />
              </button>
              <nav :id="navId" class="settings-nav" :class="{ 'compact-open': compactOpen }"
                :data-guide="navGuide || undefined" @keydown.esc="collapseCompactNav">
                <slot name="nav">
                  <template v-for="group in navGroups" :key="group.key">
                    <div class="nav-group-title">{{ group.label }}</div>
                    <button v-for="item in group.items" :key="item.key" type="button"
                      :class="['nav-item', { active: modelValue === item.key }]"
                      :data-guide="navItemGuidePrefix ? `${navItemGuidePrefix}-${item.key}` : undefined"
                      :aria-current="modelValue === item.key ? 'true' : undefined"
                      @click="selectNavItem(item.key)">
                      <slot name="nav-icon" :item="item" :active="modelValue === item.key">
                        <t-icon :name="item.icon" class="nav-icon" />
                      </slot>
                      <span class="nav-label">{{ item.label }}</span>
                      <span v-if="showBadge(item)" :class="['nav-badge', item.badgeClass]">{{ item.badge }}</span>
                    </button>
                  </template>
                </slot>
              </nav>
            </aside>

            <div class="settings-content">
              <div class="settings-body">
                <slot />
              </div>
              <div v-if="$slots.footer || $slots['footer-note']" class="settings-footer">
                <slot name="footer-note" />
                <div class="settings-footer-actions">
                  <slot name="footer" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { cycleDialogFocus } from '@/utils/dialogFocus'

/**
 * 全屏"设置类"弹窗壳：遮罩 + 1080×780 面板 + 左侧分组导航 + 右侧内容 + 可选底栏。
 * 被 Settings / AgentEditorModal / OrganizationSettingsModal / KnowledgeBaseEditorModal 共用，
 * 关闭行为（Esc / 遮罩 / 未保存守卫）由消费方通过 useModalShell 决定，本组件只发出 `close`。
 *
 * 样式为非 scoped、以 `.settings-modal-shell` 为根前缀，这样通过 `nav` 插槽自定义导航的消费方
 * 也能复用 .nav-item / .nav-icon 等基础样式。
 */
export interface SettingsModalNavItem {
  key: string
  label: string
  icon?: string
  badge?: number | string | null
  /** 额外的徽标 class，例如 'nav-badge-count' */
  badgeClass?: string
  /** 徽标为 0 时是否仍显示 */
  showZeroBadge?: boolean
  [extra: string]: unknown
}

export interface SettingsModalNavGroup {
  key: string
  label: string
  items: SettingsModalNavItem[]
}

const props = withDefaults(
  defineProps<{
    visible: boolean
    title: string
    /** 当前分区 key（v-model） */
    modelValue?: string
    navGroups?: SettingsModalNavGroup[]
    loading?: boolean
    zIndex?: number
    overlayClass?: string
    navGuide?: string
    navItemGuidePrefix?: string
    compactNavLabel?: string
  }>(),
  {
    modelValue: '',
    navGroups: () => [],
    loading: false,
    zIndex: 1100,
    overlayClass: '',
    navGuide: '',
    navItemGuidePrefix: '',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', key: string): void
  (e: 'close'): void
}>()

const dialog = ref<HTMLElement>()
const closeButton = ref<HTMLButtonElement>()
const compactToggle = ref<HTMLButtonElement>()
const compactOpen = ref(false)
const navId = useId()
const activeLabel = computed(() => props.navGroups.flatMap(group => group.items)
  .find(item => item.key === props.modelValue)?.label || props.compactNavLabel)
let opener: HTMLElement | null = null

function selectNavItem(key: string) {
  if (key === props.modelValue && compactOpen.value && compactToggle.value?.getClientRects().length) {
    compactOpen.value = false
    compactToggle.value.focus()
  }
  emit('update:modelValue', key)
}

function collapseCompactNav(event: KeyboardEvent) {
  if (!compactOpen.value || !compactToggle.value?.getClientRects().length) return
  event.stopPropagation()
  compactOpen.value = false
  compactToggle.value.focus()
}

function restoreFocus() {
  if (opener?.isConnected && !opener.closest('[inert]')) opener.focus({ preventScroll: true })
  opener = null
}

watch([() => props.visible, () => props.modelValue], async ([visible, value], [wasVisible, previous]) => {
  if (!visible) {
    compactOpen.value = false
    restoreFocus()
    return
  }
  if (!wasVisible) opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  if (!props.visible) return
  if (!wasVisible) closeButton.value?.focus({ preventScroll: true })
  if (props.compactNavLabel && value !== previous) {
    const returnToToggle = compactOpen.value && compactToggle.value?.getClientRects().length
    compactOpen.value = false
    dialog.value?.querySelector('.settings-body')?.scrollTo(0, 0)
    if (returnToToggle) compactToggle.value?.focus({ preventScroll: true })
  }
  dialog.value?.querySelector('.settings-nav .nav-item.active')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}, { immediate: true })
onBeforeUnmount(restoreFocus)

function showBadge(item: SettingsModalNavItem): boolean {
  if (item.badge == null || item.badge === '') return false
  if (typeof item.badge === 'number' && item.badge <= 0) return !!item.showZeroBadge
  return true
}
</script>

<style lang="less">
.settings-modal-shell.settings-overlay {
  position: fixed;
  // Stops at a docked assistant panel.
  inset: 0 var(--assistant-dock-width, 0px) 0 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
  overscroll-behavior: none;
}

.settings-modal-shell {
  .compact-nav-toggle {
    display: none;
  }

  .settings-modal {
    position: relative;
    width: 100%;
    // 1080×780：给成员表 / 系统设置这类多列内容留足空间；外层 20px padding 后 1120，
    // 1280+ 的笔记本都放得下；更窄的视口由 width: 100% 收缩。
    max-width: 1080px;
    height: 780px;
    max-height: calc(100vh - 40px);
    background: var(--td-bg-color-container);
    border-radius: var(--app-radius-xl);
    box-shadow: var(--td-shadow-3);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .editor-initializing {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--td-bg-color-container);
  }

  .close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    border-radius: var(--app-radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--td-text-color-secondary);
    transition: background var(--app-motion-base) ease, color var(--app-motion-base) ease;
    z-index: 10;

    &:hover {
      background: var(--td-bg-color-container-hover);
      color: var(--td-text-color-primary);
    }
  }

  .settings-container {
    display: flex;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .settings-sidebar {
    width: 208px;
    background-color: var(--td-bg-color-settings-modal);
    border-right: 1px solid var(--td-component-stroke);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 16px 14px 12px;
    border-bottom: 1px solid var(--td-component-stroke);
    flex-shrink: 0;
  }

  .sidebar-title {
    margin: 0;
    font-size: var(--app-text-xl);
    font-weight: 600;
    color: var(--td-text-color-primary);
  }

  .settings-nav {
    flex: 1;
    padding: 8px 8px 12px;
    overflow-y: auto;
    min-height: 0;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: var(--td-bg-color-secondarycontainer);
    }

    &::-webkit-scrollbar-thumb {
      background: var(--td-gray-color-5);
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb:hover {
      background: var(--td-gray-color-6);
    }
  }

  .nav-group-title {
    padding: 8px 14px 2px;
    color: var(--td-text-color-placeholder);
    font-size: var(--app-text-sm);
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .settings-nav > .nav-group-title:first-child {
    padding-top: 2px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    margin-bottom: 2px;
    border-radius: var(--app-radius-sm);
    cursor: pointer;
    transition: background-color var(--app-motion-base) ease, color var(--app-motion-base) ease;
    font-size: var(--app-text-base);
    color: var(--td-text-color-primary);
    user-select: none;

    &:hover {
      background-color: var(--td-bg-color-container-hover);
      color: var(--td-text-color-primary);
    }

    &.active {
      background-color: var(--td-bg-color-secondarycontainer);
      color: var(--td-brand-color);
      font-weight: 500;
    }
  }

  button.nav-item {
    width: 100%;
    border: 0;
    background: transparent;
    text-align: start;
    font-family: inherit;

    &:focus-visible {
      outline: 2px solid var(--td-brand-color);
      outline-offset: -2px;
    }
  }

  .nav-icon {
    margin-right: 9px;
    font-size: var(--app-text-xl);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;

    &.nav-icon-img {
      width: 16px;
      height: 16px;
    }

    &.nav-icon-emoji {
      font-size: var(--app-text-base);
      line-height: 1;
    }
  }

  .nav-label {
    flex: 1;
  }

  .nav-badge {
    flex-shrink: 0;
    margin-left: 2px;
    padding: 0 6px;
    border-radius: var(--app-radius-md);
    background: var(--td-bg-color-secondarycontainer);
    color: var(--td-text-color-secondary);
    font-size: var(--app-text-xs);
    line-height: 16px;
    font-weight: 500;
    text-align: center;

    &.nav-badge-count {
      min-width: 20px;
    }
  }

  .settings-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background-color: var(--td-bg-color-container);
  }

  // 既是滚动容器，也是 flex 列：消费方的 .content-wrapper 想自己滚动时设 flex:1 + overflow:auto，
  // 想让整块内容随页面滚动时保持自然高度即可。
  .settings-body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: var(--td-bg-color-container);
    }

    &::-webkit-scrollbar-thumb {
      background: var(--td-gray-color-5);
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb:hover {
      background: var(--td-gray-color-6);
    }
  }

  .settings-footer {
    padding: 12px 40px;
    border-top: 1px solid var(--td-component-stroke);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 16px;
    flex-shrink: 0;
    background-color: var(--td-bg-color-container);
  }

  .settings-footer-note {
    margin: 0;
    margin-right: auto;
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: var(--app-text-md);
    line-height: 20px;
    color: var(--td-text-color-secondary);

    strong {
      margin-right: 4px;
      color: var(--td-text-color-primary);
      font-weight: 500;
    }

    &__icon {
      flex-shrink: 0;
      margin-top: 2px;
      font-size: var(--app-text-base);
      color: var(--td-success-color);
    }
  }

  .settings-footer-actions {
    display: flex;
    gap: 12px;
    flex-shrink: 0;
  }
}

.settings-modal-shell-leave-active {
  transition: opacity var(--app-motion-base) ease;

  .settings-modal {
    transition: transform var(--app-motion-base) ease, opacity var(--app-motion-base) ease;
  }
}

.settings-modal-shell-leave-to {
  opacity: 0;

  .settings-modal {
    transform: scale(0.95);
    opacity: 0;
  }
}

@media (max-width: 760px) {
  .settings-modal-shell.settings-overlay {
    inset: 0;
    padding: 0;
  }

  .settings-modal-shell {
    .settings-modal {
      height: 100%;
      max-height: 100%;
      border-radius: 0;
      box-sizing: border-box;
      padding: env(safe-area-inset-top) env(safe-area-inset-right)
        env(safe-area-inset-bottom) env(safe-area-inset-left);
    }

    .close-btn {
      top: calc(8px + env(safe-area-inset-top));
      right: calc(8px + env(safe-area-inset-right));
      width: 40px;
      height: 40px;
    }

    .settings-container {
      flex-direction: column;
    }

    .settings-sidebar {
      width: 100%;
      border: 0;
      border-bottom: 1px solid var(--td-component-stroke);
    }

    .sidebar-header {
      padding-right: 56px;
    }

    .settings-nav {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 8px;
      overflow: auto;
    }

    .settings-nav .nav-group-title,
    .settings-nav > .nav-group-title:first-child {
      padding: 0 6px;
      white-space: nowrap;
    }

    .settings-nav .nav-item {
      flex: none;
      width: auto;
      min-height: 36px;
      margin-bottom: 0;
      white-space: nowrap;
    }

    .settings-footer {
      flex-wrap: wrap;
      padding: 12px 16px;
    }
  }

  .settings-modal-shell.has-compact-nav {
    .sidebar-header {
      display: none;
    }

    .compact-nav-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 56px;
      max-width: calc(100% - 56px);
      padding: 0 16px;
      border: 0;
      background: transparent;
      color: var(--td-text-color-primary);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }

    .settings-nav {
      display: none;
      max-height: min(50dvh, 420px);
      overflow: auto;
    }

    .settings-nav.compact-open {
      display: block;
    }

    .settings-nav .nav-group-title {
      padding: 8px 12px 2px;
    }

    .settings-nav .nav-item {
      width: 100%;
    }
  }
}
</style>
