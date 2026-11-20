<template>
    <div class="main" ref="dropzone" :style="{ '--sidebar-width': `${uiStore.sidebarDisplayWidth}px` }">
        <div v-if="isNarrow" class="platform-mobile-bar" :inert="navigationOpen">
            <button ref="navigationToggle" class="platform-navigation-button" type="button"
                :aria-label="t('menu.expandSidebar')" :aria-expanded="navigationOpen" aria-controls="platform-navigation"
                aria-haspopup="dialog"
                @click="navigationOpen = true">
                <t-icon name="view-list" size="20px" aria-hidden="true" />
            </button>
        </div>
        <t-drawer v-model:visible="navigationOpen" attach="body" placement="left"
            size="min(300px, 100vw - 32px)" :z-index="950" :header="false" :footer="false" :close-btn="false"
            drawer-class-name="platform-navigation-drawer" :inert="!navigationOpen" role="dialog"
            :aria-modal="navigationOpen" :aria-label="t('menu.expandSidebar')">
            <div id="platform-navigation" class="platform-navigation-panel">
                <button ref="navigationClose" class="platform-navigation-button" type="button"
                    :aria-label="t('menu.collapseSidebar')" @click="navigationOpen = false">
                    <t-icon name="close" size="20px" aria-hidden="true" />
                </button>
            </div>
        </t-drawer>
        <Teleport to="#platform-navigation" :disabled="!isNarrow" defer>
            <Menu :compact="isNarrow" @navigate="navigationOpen = false" />
        </Teleport>
        <div v-if="isRouterAlive" class="platform-route-outlet" :inert="navigationOpen">
            <RouterView />
        </div>
        <!-- WeKnora 助手：停靠时作为布局右栏挤压页面，悬浮时浮在页面上；都不加遮罩，
             跨页面保留会话，从侧栏、右侧边缘按钮或命令面板唤出（设置里可选） -->
        <AssistantPanel />
        <AssistantLauncher />
        <AssistantPageBridge />
        <div class="upload-mask" v-show="ismask">
            <UploadMask></UploadMask>
        </div>
        <!-- 全局设置模态框，供所有 platform 子路由使用 -->
        <Settings />
        <!-- 全局命令面板 (⌘K)，随 platform 路由存活 -->
        <GlobalCommandPalette />
        <!-- 知识库文件上传进度浮层：上传队列放在 store 里，切换页面不中断 -->
        <UploadTasksPanel />
        <!-- 带遮罩层的新手引导：首次进入自动开启，可从用户菜单顶部昵称旁帮助按钮重新打开 -->
        <NewUserGuide v-if="!IS_CONTEXTDB" />
    </div>
</template>
<script setup lang="ts">
import { IS_CONTEXTDB } from '@/config/contextdb'
import Menu from '@/components/menu.vue'
import { ref, onMounted, onUnmounted, nextTick, provide, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router'
import UploadMask from '@/components/upload-mask.vue'
import Settings from '@/views/settings/Settings.vue'
import GlobalCommandPalette from '@/components/GlobalCommandPalette.vue'
import AssistantPanel from '@/components/assistant/AssistantPanel.vue'
import AssistantLauncher from '@/components/assistant/AssistantLauncher.vue'
import AssistantPageBridge from '@/components/assistant/AssistantPageBridge.vue'
import UploadTasksPanel from '@/components/upload-tasks/UploadTasksPanel.vue'
import NewUserGuide from '@/components/NewUserGuide.vue'
import { useCommandPaletteStore } from '@/stores/commandPalette'
import { useChatResourcesStore } from '@/stores/chatResources'
import { useUIStore } from '@/stores/ui'
import { MessagePlugin } from 'tdesign-vue-next'
import { useI18n } from 'vue-i18n'
import { collectDroppedFiles } from './collectDroppedFiles'

const route = useRoute();
const router = useRouter();
const commandPaletteStore = useCommandPaletteStore();
const uiStore = useUIStore();
let ismask = ref(false)
const { t } = useI18n();

const narrowViewport = window.matchMedia('(max-width: 760px)')
const isNarrow = ref(narrowViewport.matches)
const navigationOpen = ref(false)
const navigationToggle = ref<HTMLButtonElement>()
const navigationClose = ref<HTMLButtonElement>()

function syncNavigationLayout() {
    isNarrow.value = narrowViewport.matches
    if (!isNarrow.value) navigationOpen.value = false
}

watch(() => route.fullPath, () => { navigationOpen.value = false })
watch(() => uiStore.showSettingsModal || route.name === 'settings', async (visible) => {
    if (visible || !isNarrow.value || navigationOpen.value) return
    await nextTick()
    const active = document.activeElement
    if (active === document.body || active?.closest('.platform-navigation-drawer[inert], .settings-modal-shell-leave-active')) {
        navigationToggle.value?.focus({ preventScroll: true })
    }
})

watch(navigationOpen, (open) => {
    // TDesign applies drawer visibility on the next timer.
    window.setTimeout(() => {
        if (navigationOpen.value !== open) return
        if (open) navigationClose.value?.focus({ preventScroll: true })
        else if (!uiStore.showSettingsModal && !commandPaletteStore.open) navigationToggle.value?.focus({ preventScroll: true })
    })
}, { flush: 'post' })

const isRouterAlive = ref(true)
const reloadApp = () => {
    isRouterAlive.value = false
    nextTick(() => {
        isRouterAlive.value = true
    })
}
provide('app:reload', reloadApp)

// 仅在 Wails 桌面端运行时拦截 Cmd/Ctrl+R：
// 桌面端没有浏览器地址栏，整页重载会白屏，所以用前端软刷新替代。
// 浏览器（含 Web 版 / 非 Lite 部署）里不拦截，交给浏览器做真正的整页刷新，
// 否则会出现左侧菜单、全局设置、Pinia store 等不随"刷新"一起重置的问题。
// @ts-ignore
const isWailsDesktop = typeof window !== 'undefined' && !!(window as any).runtime?.EventsOn

const handleGlobalKeyDown = (e: KeyboardEvent) => {
    if (!isWailsDesktop) return
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
        e.preventDefault()
        reloadApp()
    }
}

// 用于跟踪拖拽进入/离开的计数器，解决子元素触发 dragleave 的问题
let dragCounter = 0;

const CHAT_DROP_ROUTE_NAMES = new Set(['chat', 'globalCreateChat', 'kbCreateChat']);

const isChatDropRoute = () => {
    return CHAT_DROP_ROUTE_NAMES.has(String(route.name || ''));
}


// isFileDrag distinguishes an OS file drag (the only thing the global upload
// drop zone cares about) from an in-app element drag such as the wiki
// folder/page drag-and-drop. Element drags carry only "text/*" types, never
// "Files", so we bail out and let the originating component handle the drop.
const isFileDrag = (event: DragEvent): boolean => {
    const types = event.dataTransfer?.types
    if (!types) return false
    return Array.from(types).includes('Files')
}

const shouldHandleGlobalFileDrag = (event: DragEvent): boolean => {
    if (!isFileDrag(event)) return false;
    // Keep the browser from opening dropped files, even outside upload pages.
    event.preventDefault();
    // Settings and its teleported skill drawers own their uploads. This runs
    // in document capture, before a local drop handler can stop propagation.
    const enabled = !uiStore.showSettingsModal && isChatDropRoute();
    if (!enabled) {
        dragCounter = 0;
        ismask.value = false;
    }
    return enabled;
}

// 全局拖拽事件处理
const handleGlobalDragEnter = (event: DragEvent) => {
    if (!shouldHandleGlobalFileDrag(event)) return;
    dragCounter++;
    if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'all';
    }
    ismask.value = true;
}

const handleGlobalDragOver = (event: DragEvent) => {
    if (!shouldHandleGlobalFileDrag(event)) return;
    if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'copy';
    }
}

const handleGlobalDragLeave = (event: DragEvent) => {
    if (!shouldHandleGlobalFileDrag(event)) return;
    dragCounter--;
    if (dragCounter === 0) {
        ismask.value = false;
    }
}

const handleGlobalDrop = async (event: DragEvent) => {
    if (!shouldHandleGlobalFileDrag(event)) return;
    dragCounter = 0;
    ismask.value = false;

    const droppedFiles = await collectDroppedFiles(event);
    if (droppedFiles.length === 0) {
        MessagePlugin.warning(t('knowledgeBase.dragFileNotText'));
        return;
    }

    if (isChatDropRoute()) {
        event.stopPropagation();
        window.dispatchEvent(new CustomEvent('weknora:chat-file-drop', {
            detail: { files: droppedFiles }
        }));
        return;
    }
}

// 组件挂载时添加全局事件监听器
onMounted(() => {
    narrowViewport.addEventListener('change', syncNavigationLayout)
    document.addEventListener('dragenter', handleGlobalDragEnter, true);
    document.addEventListener('dragover', handleGlobalDragOver, true);
    document.addEventListener('dragleave', handleGlobalDragLeave, true);
    document.addEventListener('drop', handleGlobalDrop, true);
    if (isWailsDesktop) {
        window.addEventListener('keydown', handleGlobalKeyDown);
        // @ts-ignore
        window.runtime.EventsOn('app:reload', () => {
            reloadApp()
        })
    }
    // 支持通过 URL 查询参数打开全局命令面板，例如旧路径
    // /platform/knowledge-search?q=foo 重定向后携带 ?cmdk=foo
    maybeOpenCmdkFromRoute()
    // 后台预取对话输入栏资源，进入 createChat / chat 时复用缓存
    void useChatResourcesStore().prefetchChatInput()
});

// 监听路由变化，兼容 SPA 内部跳转时的 ?cmdk= 参数
watch(() => route.query.cmdk, () => {
    maybeOpenCmdkFromRoute()
})

function maybeOpenCmdkFromRoute() {
    if (!('cmdk' in route.query)) return
    const q = String(route.query.cmdk ?? '')
    commandPaletteStore.openPalette(q)
    // 清除 query，避免回退/刷新时反复触发
    const newQuery = { ...route.query }
    delete (newQuery as any).cmdk
    router.replace({ path: route.path, query: newQuery, hash: route.hash })
}

// 组件卸载时移除全局事件监听器
onUnmounted(() => {
    narrowViewport.removeEventListener('change', syncNavigationLayout)
    document.removeEventListener('dragenter', handleGlobalDragEnter, true);
    document.removeEventListener('dragover', handleGlobalDragOver, true);
    document.removeEventListener('dragleave', handleGlobalDragLeave, true);
    document.removeEventListener('drop', handleGlobalDrop, true);
    if (isWailsDesktop) {
        window.removeEventListener('keydown', handleGlobalKeyDown);
        // @ts-ignore
        if (window.runtime?.EventsOff) {
            // @ts-ignore
            window.runtime.EventsOff('app:reload')
        }
    }
    dragCounter = 0;
});
</script>
<style lang="less">
:root {
    --platform-workspace-inset: var(--app-space-2);
}

.main {
    display: flex;
    align-items: stretch;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    background: var(--td-bg-color-sidebar);
}

/* 右侧路由区：占满剩余宽度与整列高度，并把 min-height:0 传给子页面以便内部 flex 滚动 */
.platform-route-outlet {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--td-bg-color-container);
}

@media (min-width: 761px) {
    .platform-route-outlet,
    .main > .assistant-panel.is-docked.is-open {
        margin-block: var(--platform-workspace-inset);
        margin-inline-end: var(--platform-workspace-inset);
        border-radius: var(--td-radius-extraLarge);
        box-shadow: 0 0 0 1px var(--td-component-stroke);
    }

    .platform-route-outlet {
        margin-inline-start: var(--platform-workspace-inset);
    }

    .main > .assistant-panel.is-docked.is-open {
        height: auto;
    }
}

@media (min-width: 761px) and (max-width: 1024px) {
    :root {
        --platform-workspace-inset: var(--app-space-1);
    }
}

.platform-mobile-bar,
.platform-navigation-panel {
    background: var(--td-bg-color-sidebar);
}

.platform-mobile-bar {
    flex: none;
    padding: env(safe-area-inset-top) 4px 0 max(4px, env(safe-area-inset-left));
}

.platform-navigation-drawer {
    // Make the panel focusable when it starts sliding in.
    .t-drawer__content-wrapper {
        transition-property: transform;
    }

    .t-drawer__body {
        padding: 0;
        overflow: hidden;
    }
}

.platform-navigation-panel {
    box-sizing: border-box;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom) env(safe-area-inset-left);

    > .platform-navigation-button {
        align-self: flex-end;
        margin: 0 4px;
    }

    > .aside_box {
        flex: 1;
        width: 100%;
        height: auto;
        min-height: 0;
        border-radius: 0;
    }
}

.platform-navigation-button {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: 44px;
    height: 44px;
    border: 0;
    border-radius: var(--app-radius-md);
    background: transparent;
    color: var(--td-text-color-primary);
    cursor: pointer;

    &:hover {
        background: var(--td-bg-color-container-hover);
    }

    &:focus-visible {
        outline: 2px solid var(--td-brand-color);
        outline-offset: -2px;
    }
}

@media (max-width: 760px) {
    .main {
        flex-direction: column;
    }
}

.upload-mask {
    background-color: rgba(255, 255, 255, 0.8);
    position: fixed;
    width: 100%;
    height: 100%;
    z-index: 999;
    display: flex;
    justify-content: center;
    align-items: center;
}

img {
    -webkit-user-drag: none;
    -khtml-user-drag: none;
    -moz-user-drag: none;
    -o-user-drag: none;
    user-drag: none;
}
</style>
