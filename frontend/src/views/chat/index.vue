<template>
    <div class="chat" :class="{
        'is-embedded': embeddedMode,
        'has-references-panel': referencesDrawerVisible,
        'has-sandbox-panel': sandboxPanel.visible.value,
    }" :style="{
        '--sandbox-panel-width': `${sandboxPanel.width.value}px`,
        '--references-panel-width': `${referencesPanelWidth}px`,
    }">
        <div v-if="!embeddedMode" class="chat-topbar">
            <ChatHeader :session="currentSession" />
            <div v-if="!sandboxPanel.visible.value" class="sandbox-header-toggle">
                <t-tooltip placement="bottom">
                    <template #content>{{ t('chatHeader.toggleSandboxPanel') }}</template>
                    <button type="button" class="sandbox-header-toggle__btn"
                        :aria-label="t('chatHeader.toggleSandboxPanel')" @click="sandboxPanel.open()">
                        <svg viewBox="0 0 20 20" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg"
                            aria-hidden="true">
                            <rect x="1.5" y="1.5" width="17" height="17" rx="3" stroke="currentColor" stroke-width="1.2" />
                            <line x1="12.5" y1="1.5" x2="12.5" y2="18.5" stroke="currentColor" stroke-width="1.2" />
                            <line x1="16" y1="7.5" x2="16" y2="12.5" stroke="currentColor" stroke-width="1.2"
                                stroke-linecap="round" />
                        </svg>
                    </button>
                </t-tooltip>
            </div>
        </div>
        <ChildAgentTabBar v-if="!inheritedChildTabs && childTabs.tabs.value.length" :tabs="childTabs.tabs.value"
            :active-id="childTabs.activeId.value" :attention="promptDock.prompts.value.length > 0" @select="childTabs.select" @close="childTabs.close" />
        <div v-show="!childTabs.activeId.value" class="chat_thread" :style="{ '--chat-composer-height': `${composerHeight}px`, '--chat-scrollbar-gutter': `${scrollbarGutter}px` }">
            <div ref="scrollContainer" class="chat_scroll_box" @scroll="handleScroll">
                <div class="chat_scroll_content">
                    <div class="msg_list" :class="{ 'is-embedded': embeddedMode }">
                        <t-alert v-if="historyStatus === 'failed'" class="history-load-error" theme="error">
                            <span role="alert">{{ t('chat.historyLoadFailed') }}</span>
                            <template #operation>
                                <t-button size="small" variant="text" :loading="historyLoading"
                                    @click="retryHistory">{{ t('common.retry') }}</t-button>
                            </template>
                        </t-alert>
                        <div v-else-if="historyLoading && messagesList.length === 0" class="msg-skeleton-list">
                            <div class="msg-skeleton msg-skeleton-user">
                                <t-skeleton animation="gradient"
                                    :row-col="[{ width: '45%', height: '36px', type: 'rect' }]" />
                            </div>
                            <div class="msg-skeleton msg-skeleton-bot">
                                <t-skeleton animation="gradient"
                                    :row-col="[{ width: '80%', height: '16px' }, { width: '100%', height: '16px' }, { width: '60%', height: '16px' }]" />
                            </div>
                            <div class="msg-skeleton msg-skeleton-user">
                                <t-skeleton animation="gradient"
                                    :row-col="[{ width: '35%', height: '36px', type: 'rect' }]" />
                            </div>
                            <div class="msg-skeleton msg-skeleton-bot">
                                <t-skeleton animation="gradient"
                                    :row-col="[{ width: '70%', height: '16px' }, { width: '90%', height: '16px' }]" />
                            </div>
                        </div>
                        <!-- 推荐问题卡片 - 仅在新会话（无消息）时展示 -->
                        <div v-if="canSuggestQuestions && currentSession && !isAutomationSession && !loading"
                            class="suggested-questions-container"
                            :class="{ 'has-questions': suggestedQuestions.length > 0 || suggestedQuestionsLoading }">
                            <!-- 骨架屏占位 -->
                            <div v-if="suggestedQuestionsLoading && suggestedQuestions.length === 0"
                                class="suggested-questions-inner">
                                <div class="suggested-questions-title"><t-skeleton animation="gradient"
                                        :row-col="[{ width: '120px', height: '14px' }]" /></div>
                                <div class="suggested-questions-grid">
                                    <div v-for="n in 6" :key="'sq-skel-' + n"
                                        class="suggested-question-card sq-card-skeleton">
                                        <t-skeleton animation="gradient"
                                            :row-col="[{ width: '100%', height: '14px', type: 'rect' }]" />
                                    </div>
                                </div>
                            </div>
                            <transition v-else appear name="sq-fade">
                                <div v-if="suggestedQuestions.length > 0" class="suggested-questions-inner">
                                    <div class="suggested-questions-title-row">
                                        <p class="suggested-questions-caption">
                                            <span class="suggested-questions-title">{{ t('chat.suggestedQuestions')
                                                }}</span>
                                            <button type="button" class="suggested-questions-refresh"
                                                :disabled="suggestedQuestionsLoading"
                                                :title="t('chat.refreshSuggestedQuestions')"
                                                :aria-label="t('chat.refreshSuggestedQuestions')"
                                                @click="fetchSuggestedQuestions">
                                                <t-icon :name="suggestedQuestionsLoading ? 'loading' : 'refresh'"
                                                    :class="{ 'sq-refresh-spin': suggestedQuestionsLoading }" />
                                            </button>
                                        </p>
                                    </div>
                                    <div class="suggested-questions-grid">
                                        <button v-for="item in suggestedQuestions" :key="item.question" type="button"
                                            class="suggested-question-card"
                                            @click="handleSuggestedQuestionClick(item)">
                                            <span class="suggested-question-text">{{ item.question }}</span>
                                            <span v-if="item.source === 'faq'"
                                                class="suggested-question-badge faq">FAQ</span>
                                        </button>
                                    </div>
                                </div>
                            </transition>
                        </div>
                        <!--
                      关键：必须用 session.id 作为 key，不能用 v-for 的索引。
                      向上滚动加载历史时会插入一批消息（push/unshift）到列表，
                      若用索引作 key 会让所有已渲染消息的 key 漂移，触发整个列表的销毁重建
                      （botmsg / AgentStreamDisplay 全部重新挂载、markdown 重新渲染），
                      这是历史加载时白屏 + layout shift 蔓延到 session 列表的根因。
                      仅对极少数尚未拿到 id 的本地占位消息 fallback 到 role+created_at+index。
                    -->
                        <div v-for="(session, index) in messagesList"
                            :key="session.id || `${session.role}-${session.created_at}-${index}`" class="msg-item-wrapper"
                            :class="{ 'is-steer-prefix': session.steerForked, 'is-empty-segment': session.role === 'assistant' && !shouldRenderAssistantMessage(session) }">
                            <MessageTimestamp v-if="shouldShowConversationTimestamp(messagesList, index)"
                                :value="session.created_at" />

                            <div v-if="session.role == 'user'" class="message-row"
                                :data-message-id="session.id || undefined">
                                <usermsg :content="session.content" :mentioned_items="session.mentioned_items"
                                    :images="session.images" :attachments="session.attachments" :embeddedMode="embeddedMode"
                                    :session-id="session_id"
                                    :message-id="session.id"
                                    :created-at="session.created_at"
                                    :can-fork="!embeddedMode && forkAffordanceOf(session.id).canFork"
                                    :can-rewind="canRewindMessage(session.id)"
                                    @fork="handleFork"
                                    @rewind="handleRewind">
                                </usermsg>
                            </div>
                            <div v-if="session.role == 'assistant' && shouldRenderAssistantMessage(session)"
                                class="message-row"
                                :data-message-id="session.id || undefined">
                                <botmsg :content="session.content" :session="session" :session-id="session_id"
                                    :user-query="getUserQuery(index)" @scroll-bottom="scrollToBottom"
                                    :isFirstEnter="isFirstEnter" :embeddedMode="embeddedMode"
                                    :can-fork="!embeddedMode && forkAffordanceOf(session.id).canFork"
                                    :can-rewind="canRewindMessage(session.id)"
                                    :can-ask-assistant="!embeddedMode"
                                    @fork="handleFork"
                                    @rewind="handleRewind"
                                    @ask-assistant="handleAskAssistant"
                                    @render-complete-change="(ready) => handleAnswerRenderComplete(session, ready)">
                                </botmsg>
                            </div>
                        </div>
                        <div v-if="showGlobalTypingIndicator" class="chat-global-wait" role="status"
                            :aria-label="t('chat.thinkingAlt')">
                            <span class="chat-global-wait__spinner" aria-hidden="true"></span>
                        </div>
                    </div>
                </div>
            </div>
            <div ref="composerElement" class="chat_composer">
                <div v-if="composerApprovals.length" class="host-approval-pop">
                    <HostApprovalCard v-for="approval in composerApprovals" :key="approval.pending_id"
                        :pending-id="approval.pending_id"
                        :host="approval.host || { reason: approval.kind === 'host_command' ? 'delete' : '' }"
                        :timeout-seconds="approval.timeout_seconds"
                        :requested-at="approval.requested_at"
                        :resolved="approval.resolved"
                        :approved="approval.approved"
                        :resolve-reason="approval.resolve_reason"
                        :resolve-scope="approval.resolve_scope" />
                </div>
                <div class="input-container" :class="{ 'is-embedded': embeddedMode }">
                    <transition name="scroll-btn-fade">
                        <button v-show="userHasScrolledUp" type="button" class="scroll-to-bottom-btn"
                            :aria-label="t('chat.scrollToLatest')" @click="onClickScrollToBottom">
                            <t-icon name="chevron-down" size="18px" />
                        </button>
                    </transition>
                    <PendingPromptDock :embedded-mode="embeddedMode" />
                    <div v-if="isAutomationSession" class="automation-session-notice" role="note">
                        <t-icon name="time" size="14px" />
                        <span>{{ t('automation.conversationNotice') }}</span>
                    </div>
                    <InputField v-else-if="embeddedMode || currentSession" ref="inputFieldRef" :key="embeddedMode ? undefined : session_id" :auto-focus="focusComposerOnMount" compact
                        @send-msg="(query, modelId, mentionedItems, imageFiles, attachmentFiles, options) => sendMsg(query, modelId, mentionedItems, imageFiles, attachmentFiles, options)"
                        @stop-generation="handleStopGeneration"
                        @stop-confirmed="handleStopConfirmed"
                        @stop-failed="handleStopFailed" :isReplying="isReplying" :composer-locked="composerLocked" :sessionId="session_id"
                        :assistantMessageId="currentAssistantMessageId" :embeddedMode="embeddedMode"
                        :model-id="modelId" :default-model-id="defaultModelId"
                        @update:model-id="(id) => emit('update:modelId', id)"
>
                        <template v-if="$slots['composer-chips']" #chips>
                            <slot name="composer-chips" />
                        </template>
                        <template v-if="backgroundItems.length" #background-work>
                            <BackgroundWorkChip :items="backgroundItems" :cancel-work="onCancelWork"
                                :scope-key="backgroundOwnerKey + ':' + String(session_id || '')" @view="openWorkOutput" />
                        </template>
                        <template v-if="$slots['composer-controls']" #controls><slot name="composer-controls" /></template>
                    </InputField>
                </div>
            </div>
            <div v-if="!embeddedMode" class="chat_overlays">
                <ChatQuestionMinimap :scroll-container="scrollContainer" :messages="messagesList"
                    @jump="jumpToQuestion" />
            </div>
        </div>
        <div v-for="tab in childTabs.tabs.value" :key="tab.id" v-show="childTabs.activeId.value === tab.id" class="chat-child-detail" role="tabpanel" :aria-label="tab.task.displayName">
            <ChildAgentStream :key="tab.task.sessionId + ':' + tab.task.runId" :task="tab.task" :active="childTabs.activeId.value === tab.id" />
        </div>
    </div>
    <KnowledgeBaseEditorModal v-if="!embeddedMode" :visible="uiStore.showKBEditorModal" :mode="uiStore.kbEditorMode"
        :kb-id="uiStore.currentKBId || undefined" :initial-type="uiStore.kbEditorType"
        @update:visible="(val) => val ? null : uiStore.closeKBEditor()" @success="handleKBEditorSuccess" />
    <ChatReferencesDrawer />
    <ChatAttachmentPreviewDrawer />
    <SandboxSidePanel v-if="!embeddedMode" :session-id="session_id"
        :agent-id="useSettingsStoreInstance.selectedAgentId"
        :agent-source-tenant-id="useSettingsStoreInstance.selectedAgentSourceTenantId"
        :shifted="referencesDrawerVisible"
        :shift-width="referencesPanelWidth"
        :artifacts="sessionArtifacts" :artifacts-collecting="sessionArtifactsCollecting"
        @artifact-deleted="handleArtifactDeleted" />
    <t-dialog v-model:visible="workOutputVisible" :header="viewingWorkTitle" :footer="false" width="720px">
        <BackgroundWorkResults v-if="workOutputVisible && viewingWorkId && session_id" :session-id="String(session_id)"
            :work-id="viewingWorkId" :owner-key="backgroundOwnerKey" @changed="refreshBackgroundWork" />
    </t-dialog>
</template>
<script setup>
import ChildAgentTabBar from './components/ChildAgentTabBar.vue';
import ChildAgentStream from './components/ChildAgentStream.vue';
import { createChildAgentTabs, childAgentTabsKey, childAgentTaskLookupKey, findChildAgentTask } from '@/composables/useChildAgentTabs';
import { storeToRefs } from 'pinia';
import { inject, ref, onMounted, onBeforeMount, onUnmounted, nextTick, watch, reactive, computed, provide } from 'vue';
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import InputField from '../../components/Input-field.vue';
import HostApprovalCard from './components/HostApprovalCard.vue';
import {
    clearComposerApproval,
    isHostApprovalEvent,
    pendingComposerApprovals,
} from './components/hostApproval';
import botmsg from './components/botmsg.vue';
import usermsg from './components/usermsg.vue';
import { getMessageList, getSession, forkSession, rewindSession } from "@/api/chat/index";
import { resolveForkAffordance } from './forkPoint';
import { rewindSkipMessage } from './rewindNotice';
import { rewindPrefillText, rewindBlockedByOutgoingWork, canReplaceRewindTranscript, shouldApplyRewindLocally, rewindHistoryHasMore, keepMessagesThroughRewindPoint, rewindableMessageIds, rewindHttpConflictCode, rewindConflictI18nKey } from './rewindView';
import { getSuggestedQuestions } from "@/api/agent/index";
import { questionOriginFromSuggestion } from '@/utils/questionOrigin';
import { deleteTemporaryAttachment, uploadTemporaryAttachment } from '@/api/chat/temporary-attachments';
import { useStream } from '../../api/chat/streame'
import { persistedAssistantId } from '@/utils/steerStreamFork';
import { resumeSuspendedRunKey } from '@/utils/suspendedRun';
import { useMenuStore } from '@/stores/menu';
import { useSettingsStore } from '@/stores/settings';
import { useAuthStore } from '@/stores/auth';
import { useDeploymentCapabilitiesStore } from '@/stores/deploymentCapabilities';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { useUIStore } from '@/stores/ui';
import KnowledgeBaseEditorModal from '@/views/knowledge/KnowledgeBaseEditorModal.vue';
import { useKnowledgeBaseCreationNavigation } from '@/hooks/useKnowledgeBaseCreationNavigation';
import { useChatStreamHandler, isAwaitingInput, isPromptCard } from '@/composables/useChatStreamHandler';
import { useChatScrollFollow } from '@/composables/useChatScrollFollow';
import { clearCitationChunkCache } from '@/utils/citationChunkCache';
import ChatReferencesDrawer from '@/components/ChatReferencesDrawer.vue';
import ChatAttachmentPreviewDrawer from '@/components/ChatAttachmentPreviewDrawer.vue';
import MessageTimestamp from '@/components/chat/MessageTimestamp.vue';
import ChatQuestionMinimap from '@/components/chat/ChatQuestionMinimap.vue';
import { shouldShowConversationTimestamp } from '@/utils/messageTimestamp';
import { historyHasMoreAfterAttempt } from '@/utils/historyPagination';
import ChatHeader from '@/components/ChatHeader.vue';
import {
    notifySessionMutation,
    SESSION_MUTATION_EVENT,
} from '@/components/sessionMutations';
import { provideChatReferencesDrawer } from '@/composables/useChatReferencesDrawer';
import { provideChatAttachmentPreviewDrawer } from '@/composables/useChatAttachmentPreviewDrawer';
import { useSessionActivityStore } from '@/stores/sessionActivity';
import { useAssistantStore } from '@/stores/assistant';
import { useAssistantPageContext } from '@/composables/useAssistantPageContext';
import { respondToPageAction } from '@/utils/pageActionResponder';
import { provideChatSandboxPanel } from '@/composables/useChatSandboxPanel';
import SandboxSidePanel from '@/components/chat/SandboxSidePanel.vue';
import PendingPromptDock from './components/PendingPromptDock.vue';
import BackgroundWorkChip from './components/BackgroundWorkChip.vue';
import BackgroundWorkResults from './components/BackgroundWorkResults.vue';
import { cancelBackgroundWork, listBackgroundWork } from '@/api/chat/background-work';
import { createBackgroundWorkPoller, mergeBackgroundWork } from '@/utils/backgroundWork';
import { providePromptDock } from '@/composables/usePromptDock';
import { collectSessionArtifacts, markSessionArtifactDeleted } from '@/utils/sessionArtifacts';
import { isCollectingSkillArtifacts } from '@/utils/skillArtifacts';
const inheritedChildTabs = inject(childAgentTabsKey, null);
const childTabs = inheritedChildTabs || createChildAgentTabs();
provide(childAgentTabsKey, childTabs);
const referencesDrawer = provideChatReferencesDrawer();
provideChatAttachmentPreviewDrawer();
const sandboxPanel = provideChatSandboxPanel();
const { visible: referencesDrawerVisible, panelWidth: referencesPanelWidth } = referencesDrawer;

const props = defineProps({
    session_id: { type: String, default: '' },
    agentId: { type: String, default: '' },
    embeddedMode: { type: Boolean, default: false },
    // Embedded only: sent once on mount, instead of the menu store's firstQuery
    // that belongs to the main chat.
    initialQuery: { type: String, default: '' },
    // Embedded only: returns { knowledgeBaseIds, pageContext } for each send,
    // read at send time so the host can follow the page the user is on.
    hostScope: { type: Function, default: null },
    // Embedded only: the host's model choice (v-model:model-id), '' to
    // follow defaultModelId.
    modelId: { type: String, default: '' },
    defaultModelId: { type: String, default: '' },
});
const emit = defineEmits(['update:modelId']);

const usemenuStore = useMenuStore();
const useSettingsStoreInstance = useSettingsStore();
const deploymentCapabilities = useDeploymentCapabilitiesStore();
const authStore = useAuthStore();
const backgroundOwnerKey = computed(() => `${authStore.currentUserId || ''}:${authStore.effectiveTenantId || ''}`);

// Whether the active chat session is using the Agent pipeline (not quick-answer).
const isAgentStreamSession = () => {
    if (props.embeddedMode) {
        return !!(props.agentId && props.agentId !== 'builtin-quick-answer');
    }
    return useSettingsStoreInstance.isAgentStreamMode;
};

const uiStore = useUIStore();
const { navigateToKnowledgeBaseList } = useKnowledgeBaseCreationNavigation();
const { t } = useI18n();
const { firstQuery, firstMentionedItems, firstModelId, firstImageFiles, firstAttachmentFiles, firstQuestionOrigin } = storeToRefs(usemenuStore);
// Capture before the initial send consumes firstQuery; the child focuses after mounting.
const focusComposerOnMount = Boolean(props.embeddedMode ? props.initialQuery : firstQuery.value);
const { onChunk, error, isStreaming, startStream, stopStream, lastStreamRequest } = useStream();
/** Snapshot of the in-flight HTTP request for attaching to the next assistant message. */
const pendingStreamDebug = ref(null);

const buildStreamDebugPayload = () => {
    const meta = lastStreamRequest.value;
    if (!meta) return null;
    return {
        requestId: meta.requestId,
        url: meta.url,
        method: meta.method,
        body: meta.body,
        sentAt: meta.sentAt,
        sessionId: session_id.value,
    };
};

const attachStreamDebugToMessage = (message) => {
    if (!message) return;
    const payload = pendingStreamDebug.value || buildStreamDebugPayload();
    if (!payload) return;
    if (payload.requestId && !message.request_id) {
        message.request_id = payload.requestId;
    }
    message.debugRequest = payload;
};
const route = useRoute();
const router = useRouter();
const session_id = ref(props.session_id || route.params.chatid);
watch(session_id, () => childTabs.reset(), { flush: 'sync' });
const currentSession = ref(null);
// A session ID can be revisited while requests from its previous visit are still pending.
let chatLoadVersion = 0;
const isAutomationSession = computed(() => currentSession.value?.kind === 'automation');
const backgroundItems = ref([]);
let backgroundGeneration = 0;
const viewingWorkId = ref('');
const workOutputVisible = ref(false);
const viewingWorkTitle = computed(() => {
    const item = backgroundItems.value.find((row) => row.work_id === viewingWorkId.value);
    return item?.title || viewingWorkId.value || '';
});

function replaceBackgroundItems(incoming) {
    const merged = mergeBackgroundWork(backgroundItems.value, incoming);
    const ids = new Set(incoming.map((item) => item.work_id));
    const next = merged.filter((item) => ids.has(item.work_id));
    if (
        next.length === backgroundItems.value.length
        && next.every((item, index) => item === backgroundItems.value[index])
    ) {
        return;
    }
    backgroundItems.value = next;
}

const backgroundPoller = createBackgroundWorkPoller({
    sessionId: () => String(session_id.value || ''),
    list: (id, signal) => listBackgroundWork(id, signal),
    onUpdate: replaceBackgroundItems,
});

function startBackgroundWork() {
    if (!session_id.value) {
        backgroundItems.value = [];
        return;
    }
    backgroundPoller.start();
}

async function refreshBackgroundWork() {
    if (!session_id.value) return;
    await backgroundPoller.refresh();
}

function openWorkOutput(workId) {
    viewingWorkId.value = workId;
    workOutputVisible.value = true;
}

async function onCancelWork(workId) {
    const id = String(session_id.value || '');
    const item = backgroundItems.value.find(row => row.work_id === workId);
    if (!id || !item || item.kind !== 'async_subagent' || item.read_only !== false || item.can_cancel !== true) return;
    const generation = backgroundGeneration;
    let failure;
    try {
        await cancelBackgroundWork(id, workId);
    } catch (error) {
        failure = error;
    }
    try {
        if (generation === backgroundGeneration) await refreshBackgroundWork();
    } catch {
        // Keep the last chip. A non-empty list is still on the 5s poller.
    }
    if (failure) throw failure;
}

watch([session_id, backgroundOwnerKey], ([id]) => {
    backgroundGeneration++;
    backgroundPoller.stop();
    backgroundItems.value = [];
    viewingWorkId.value = '';
    workOutputVisible.value = false;
    if (id) backgroundPoller.start();
}, { flush: 'sync' });

// 拉 session 详情，并按其 last_request_state 把输入栏状态恢复到当时的发起态。
// 嵌入式（embeddedMode）由宿主页面注入 agent/KB，所以跳过整套恢复逻辑，
// 避免污染宿主的 settings store。
const loadSessionAndHydrate = async (sid) => {
    if (!sid || props.embeddedMode) return;
    // Capture before awaiting: onMounted sends and clears firstQuery while this
    // request is in flight. A new session must retain the createChat draft.
    const preserveDraft = Boolean(firstQuery.value);
    const version = chatLoadVersion;
    try {
        const sessionRes = await getSession(sid);
        if (sessionRes?.data && version === chatLoadVersion && sid === session_id.value) {
            currentSession.value = sessionRes.data;
            const lastState = sessionRes.data.last_request_state;
            useSettingsStoreInstance.hydrateSessionInputState(lastState, preserveDraft);
        }
    } catch (error) {
        if (version !== chatLoadVersion || sid !== session_id.value) return;
        console.error('Failed to load session data:', error);
    }
};
const inputFieldRef = ref();
const created_at = ref('');
const limit = ref(20);
const messagesList = reactive([]);
provide(childAgentTaskLookupKey, task => findChildAgentTask(messagesList, task));
const promptDock = providePromptDock(messagesList);
watch(promptDock.focusRequest, () => childTabs.select(''), { flush: 'sync' });
watch(promptDock.prompts, prompts => { childTabs.attention.value = prompts.length > 0; }, { immediate: true });

// The answer the user asked the assistant about, until they leave the session.
const assistant = useAssistantStore();
const askedMessage = ref({ sessionId: '', messageId: '' });
useAssistantPageContext(() => {
    const asked = askedMessage.value;
    if (props.embeddedMode || !asked.messageId || asked.sessionId !== props.session_id) return null;
    return { page: 'chat', chatSessionId: asked.sessionId, messageId: asked.messageId };
});
function handleAskAssistant(messageId) {
    askedMessage.value = { sessionId: props.session_id, messageId };
    assistant.restorePageContext();
    assistant.open();
}

const backgroundWorkStamp = computed(() => messagesList.map((message) => {
    const work = message?.background_work;
    if (!work || typeof work !== 'object') return '';
    return Object.entries(work).map(([id, row]) => `${id}:${row?.state || ''}:${row?.payload?.run_id || ''}`).join(',');
}).join('|'));
watch(backgroundWorkStamp, (stamp, previous) => {
    if (!stamp || stamp === previous) return;
    refreshBackgroundWork().catch(() => {});
});

function forkAffordanceOf(messageId) {
    if (isAutomationSession.value || !messageId) return { canFork: false }
    return resolveForkAffordance(messagesList, messageId)
}

// One pass over the transcript per render instead of two per rendered row:
// the template asks this for every message and re-asks on every streamed token.
const rewindableIds = computed(() => rewindableMessageIds(messagesList, {
    embeddedMode: props.embeddedMode,
    outgoingWork: outgoingWorkBlocksRewind.value,
}))

function canRewindMessage(messageId) {
    return !isAutomationSession.value && Boolean(messageId) && rewindableIds.value.has(String(messageId))
}

const FORK_PREFILL_KEY = 'weknora:fork-prefill'
let forkInFlight = false
const rewindInFlight = ref(false)
const rewindLockSessionId = ref('')
const composerApprovals = computed(() =>
    pendingComposerApprovals.value.filter((item) => item && !item.resolved && isHostApprovalEvent(item))
)

const composerLocked = computed(() =>
    isAutomationSession.value || (rewindInFlight.value && String(session_id.value || '') === rewindLockSessionId.value)
)

function stashForkLanding(sessionId, text) {
    const payload = JSON.stringify({ sessionId, text })
    try {
        sessionStorage.setItem(FORK_PREFILL_KEY, payload)
    } catch {
        // sessionStorage can throw in private mode; landing still navigates.
    }
}

function readForkLanding() {
    try {
        const raw = sessionStorage.getItem(FORK_PREFILL_KEY)
        if (!raw) return null
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== 'object') return null
        return {
            sessionId: String(parsed.sessionId || ''),
            text: String(parsed.text || ''),
        }
    } catch {
        return null
    }
}

function clearForkLanding() {
    try {
        sessionStorage.removeItem(FORK_PREFILL_KEY)
    } catch {
        // ignore
    }
}

function applyForkLanding() {
    const landed = readForkLanding()
    if (!landed || landed.sessionId !== String(session_id.value || '')) {
        return false
    }
    clearForkLanding()
    inputFieldRef.value?.prefill(landed.text)
    return true
}

async function handleFork(messageId) {
    if (props.embeddedMode) return
    if (forkInFlight || composerLocked.value) return
    if (!messageId || !session_id.value) return
    const source = messagesList.find((m) => m.id === messageId)
    if (!source) return
    const sourceSessionId = session_id.value

    forkInFlight = true
    try {
        const res = await forkSession(sourceSessionId, { message_id: messageId })
        const data = res?.data
        if (!data?.session_id) return

        // Carry the question across navigation in sessionStorage: the chat view
        // is reused across chat/:chatid, and history reload / composer reset
        // would clobber an in-memory prefill if we applied it too early.
        const prefill = source.role === 'user' ? String(source.content ?? '') : ''
        stashForkLanding(data.session_id, prefill)

        const now = new Date().toISOString()
        const sourceTitle = currentSession.value?.title || t('menu.newSession')
        usemenuStore.updataMenuChildren({
            id: data.session_id,
            path: `chat/${data.session_id}`,
            title: `${sourceTitle}（分支）`,
            parent_session_id: sourceSessionId,
            isMore: false,
            isNoTitle: false,
            created_at: now,
            updated_at: now,
        })

        await router.push(`/platform/chat/${data.session_id}`)
    } catch (err) {
        if (err?.status === 409 || err?.$httpStatus === 409) {
            MessagePlugin.warning('请等本轮回答结束后再分叉')
            return
        }
        MessagePlugin.error('分叉失败，请重试')
    } finally {
        forkInFlight = false
    }
}

async function handleRewind(messageId) {
    if (props.embeddedMode) return
    if (forkInFlight || composerLocked.value) return
    if (rewindBlockedByOutgoingWork({
        isReplying: isReplying.value,
        isStreaming: isStreaming.value,
        isRecovering: isImRecovering.value,
    })) return
    if (!messageId || !session_id.value) return
    const source = messagesList.find((m) => m.id === messageId || persistedAssistantId(m) === messageId)
    if (!source) return
    const sourceSessionId = session_id.value
    const sourceRole = source.role
    const sourceContent = source.content

    rewindInFlight.value = true
    rewindLockSessionId.value = sourceSessionId
    try {
        const res = await rewindSession(sourceSessionId, { message_id: messageId })
        const data = res?.data
        if (!data) return
        if (!shouldApplyRewindLocally(String(session_id.value || ''), sourceSessionId)) return

        let batch
        let reloadFailed = false
        try {
            const history = await fetchMessageList({
                session_id: sourceSessionId,
                created_at: '',
                limit: limit.value,
            })
            batch = history?.data
            if (!Array.isArray(batch)) {
                throw new Error('rewind history reload returned no list')
            }
        } catch {
            reloadFailed = true
        }
        if (!shouldApplyRewindLocally(String(session_id.value || ''), sourceSessionId)) return

        historyLoading.value = false
        if (reloadFailed) {
            const kept = keepMessagesThroughRewindPoint(
                [...messagesList],
                messageId,
                sourceRole,
                (m) => m.id === messageId || persistedAssistantId(m) === messageId,
            )
            messagesList.splice(0, messagesList.length, ...kept)
            // created_at still points at the oldest message we actually hold.
            // Clearing it here would send the next scroll-up back to the newest
            // page, which this prefix already contains, instead of older ones.
            MessagePlugin.warning(t('chat.rewind.reloadFailed'))
        } else {
            if (!canReplaceRewindTranscript(String(session_id.value || ''), sourceSessionId, undefined)) return
            messagesList.splice(0)
            created_at.value = ''
            if (batch.length) {
                created_at.value = batch[0].created_at
                hasMoreHistory.value = rewindHistoryHasMore(batch.length, limit.value)
                await handleMsgList(batch, false)
            } else {
                hasMoreHistory.value = false
            }
        }

        const prefill = rewindPrefillText(sourceRole, sourceContent)
        if (prefill) {
            inputFieldRef.value?.prefill(prefill)
        }

        if (reloadFailed) {
            return
        }
        if (data.workspace_reset) {
            MessagePlugin.success(t('chat.rewind.success'))
            return
        }
        const skip = rewindSkipMessage(String(data.reason || ''), t)
        if (skip) {
            MessagePlugin.info(skip)
        }
    } catch (err) {
        const conflictCode = rewindHttpConflictCode(err)
        if (conflictCode || err?.status === 409 || err?.$httpStatus === 409) {
            MessagePlugin.warning(t(rewindConflictI18nKey(conflictCode)))
            return
        }
        MessagePlugin.error(t('chat.rewind.failed'))
    } finally {
        rewindInFlight.value = false
        rewindLockSessionId.value = ''
    }
}

const sessionArtifacts = computed(() => collectSessionArtifacts(messagesList));
// The panel already deleted the file server side; flag it in the loaded
// history so the computed drops it without reloading the conversation.
function handleArtifactDeleted({ messageId, index }) {
    markSessionArtifactDeleted(messagesList, messageId, index);
}
const sessionArtifactsCollecting = computed(() =>
    messagesList.some((message) => isCollectingSkillArtifacts(message)),
);
const isReplying = ref(false);
const currentAssistantMessageId = ref(''); // 当前正在生成的 assistant message ID
// True only while attaching to an in-flight *IM-originated* reply via continue-stream.
// Such replies are generated on the IM side and never stream through this server, so
// continue-stream always fails even though the answer is coming — recover by polling
// instead of erroring. Web/api replies are left on the original error path.
const isAttachingImStream = ref(false);

// A session change drops the stack; continue-stream replay adds back the
// cards that are still waiting. Clearing on every isReplying change hid a
// card that replay had just restored.
watch(session_id, () => {
    clearComposerApproval();
});
watch(isReplying, (replying) => {
    if (!replying) clearComposerApproval();
});
let recoverPollTimer = null;
// True while polling to recover an in-flight IM reply we couldn't stream. Drives
// the same "generating" typing indicator the normal reply path shows, so the wait
// isn't a silent gap. IM-only: false everywhere else, so other flows are unchanged.
const isImRecovering = ref(false);
const outgoingWorkBlocksRewind = computed(() => rewindBlockedByOutgoingWork({
    isReplying: isReplying.value,
    isStreaming: isStreaming.value,
    isRecovering: isImRecovering.value,
}))
const scrollLock = ref(false);
const isFirstEnter = ref(true);
const loading = ref(false);
const sessionActivity = useSessionActivityStore();
const activitySessionId = ref('');
watch([activitySessionId, isReplying, isImRecovering, currentAssistantMessageId], () => {
    if (props.embeddedMode || !activitySessionId.value) return;
    // SSE may stay connected after a stop/complete event. The sidebar tracks
    // generation, not the transport, just like the composer's Stop button.
    sessionActivity.update(activitySessionId.value, isReplying.value || isImRecovering.value, currentAssistantMessageId.value);
}, { flush: 'sync' });
const historyLoading = ref(true);
const historyStatus = ref('idle');
watch(activitySessionId, (id) => {
    if (!props.embeddedMode) sessionActivity.setViewing(id);
}, { flush: 'sync' });
const historyLoadingMore = ref(false);
const hasMoreHistory = ref(true);

// Prefill after THIS session's history load settles. A messagesList watch
// would fire on the splice-to-empty that starts a session switch and then
// get clobbered by composer reset / history mount.
watch(historyLoading, (loading) => {
    if (loading) return
    applyForkLanding()
}, { flush: 'post' })
let fullContent = ref('')
const scrollContainer = ref(null)
const composerElement = ref(null)
const composerHeight = ref(0)
const scrollbarGutter = ref(0)
// Reserve space for the independent composer and keep it aligned with the
// message column when drawers, multiline input or attachments change its size.
watch([composerElement, scrollContainer], ([element, scroller], _, onCleanup) => {
    if (!element || !scroller) return
    const measure = () => {
        composerHeight.value = element.offsetHeight
        scrollbarGutter.value = scroller.offsetWidth - scroller.clientWidth
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    observer.observe(scroller)
    onCleanup(() => observer.disconnect())
}, { flush: 'post' })
const userHasScrolledUp = ref(false)
const SCROLL_BOTTOM_THRESHOLD = 80


const jumpToQuestion = (id) => {
    const root = scrollContainer.value
    if (!root || !id) return
    const el = root.querySelector(`[data-message-id="${CSS.escape(id)}"]`)
    if (!el) return

    const offset = el.getBoundingClientRect().top - root.getBoundingClientRect().top + root.scrollTop
    const nearEnd = root.scrollHeight - offset < root.clientHeight + SCROLL_BOTTOM_THRESHOLD
    userHasScrolledUp.value = !nearEnd

    el.scrollIntoView({ block: 'start', behavior: 'smooth' })

}

const handleKBEditorSuccess = (kbId) => {
    navigateToKnowledgeBaseList(kbId)
}

// ===== 推荐问题 =====
const suggestedQuestions = ref([]);
const suggestedQuestionsLoading = ref(false);
const canSuggestQuestions = computed(() =>
    !props.embeddedMode && historyStatus.value === 'loaded' && !historyLoading.value && messagesList.length === 0,
);
let suggestedQuestionsFetchId = 0; // 用于取消过时的请求
let suggestedDebounceTimer = null;

const cancelSuggestedQuestionsFetch = () => {
    suggestedQuestionsFetchId++;
    suggestedQuestionsLoading.value = false;
    suggestedQuestions.value = [];
    if (suggestedDebounceTimer) {
        clearTimeout(suggestedDebounceTimer);
        suggestedDebounceTimer = null;
    }
};

const fetchSuggestedQuestionsIfNeeded = async () => {
    if (messagesList.length > 0) cancelSuggestedQuestionsFetch();
    else await fetchSuggestedQuestions();
};

const fetchSuggestedQuestions = async () => {
    if (!canSuggestQuestions.value) return;
    const fetchId = ++suggestedQuestionsFetchId;
    suggestedQuestionsLoading.value = true;
    // 加载期间保留旧数据，不清空，避免布局抖动
    try {
        const agentId = useSettingsStoreInstance.selectedAgentId;
        if (!agentId) return;
        const res = await getSuggestedQuestions(agentId, useSettingsStoreInstance.getSuggestedQuestionsParams());
        if (fetchId === suggestedQuestionsFetchId) {
            suggestedQuestions.value = res?.data?.questions || [];
        }
    } catch (err) {
        console.warn('[SuggestedQuestions] Failed to fetch:', err);
        if (fetchId === suggestedQuestionsFetchId) {
            suggestedQuestions.value = [];
        }
    } finally {
        if (fetchId === suggestedQuestionsFetchId) {
            suggestedQuestionsLoading.value = false;
        }
    }
};

const handleSuggestedQuestionClick = (item) => {
    inputFieldRef.value?.prefillSuggestion(item.question, questionOriginFromSuggestion(item));
};

const handleAnswerRenderComplete = (message, ready) => {
    message.answerFullyRendered = Boolean(ready);
};

// 防抖包装，切换知识库/文件时300ms内不重复请求
const debouncedFetchSuggestions = () => {
    if (!canSuggestQuestions.value) return;
    if (suggestedDebounceTimer) clearTimeout(suggestedDebounceTimer);
    suggestedDebounceTimer = setTimeout(() => { fetchSuggestedQuestionsIfNeeded(); }, 300);
};

// 监听 Agent / 知识库 / 文件 / 标签 / MCP / Skill @mention，重新获取推荐问题
watch(
    () => ({
        agentId: useSettingsStoreInstance.selectedAgentId,
        kbs: useSettingsStoreInstance.settings.selectedKnowledgeBases,
        files: useSettingsStoreInstance.settings.selectedFiles,
        tags: useSettingsStoreInstance.settings.selectedTags,
        mcps: useSettingsStoreInstance.settings.selectedMCPServices,
        skills: useSettingsStoreInstance.settings.selectedSkills,
    }),
    debouncedFetchSuggestions,
    { deep: true },
);

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

const getUserQuery = (index) => {
    if (index <= 0) {
        return '';
    }
    const previous = messagesList[index - 1];
    if (previous && previous.role === 'user') {
        return previous.content || '';
    }
    return '';
};

watch([() => route.params], async (newvalue) => {
    // The host owns an embedded view's session; the route belongs to the page behind it.
    if (props.embeddedMode) return;
    isFirstEnter.value = true;
    if (newvalue[0].chatid) {
        if (!firstQuery.value) {
            scrollLock.value = false;
        }
        messagesList.splice(0);
        session_id.value = newvalue[0].chatid;
        currentSession.value = null;
        const version = ++chatLoadVersion;
        const sid = session_id.value;
        clearCitationChunkCache();
        cancelSuggestedQuestionsFetch();

        // 切换会话时，重置状态
        historyLoading.value = true;
        historyStatus.value = 'idle';
        historyLoadingMore.value = false;
        hasMoreHistory.value = true;
        created_at.value = '';
        loading.value = false;
        isReplying.value = false;
        currentAssistantMessageId.value = '';
        userHasScrolledUp.value = false;

        // 跨会话切换：先把旧会话覆盖前的全局默认还原，再让新会话重新拍快照
        // 并应用自己的 last_request_state（在 loadSessionAndHydrate 内部完成）。
        useSettingsStoreInstance.restoreDefaultsIfSnapshotted();

        await loadSessionAndHydrate(sid);
        if (version !== chatLoadVersion) return;
        loadInitialHistory();
    }
});
const scrollFollow = useChatScrollFollow(scrollContainer, userHasScrolledUp, computed(() => !childTabs.activeId.value));
const scrollToBottom = scrollFollow.scrollToBottom;
const onClickScrollToBottom = scrollFollow.resume;

let parentTabScrollTop = 0;
watch(childTabs.activeId, (active, previous) => {
    if (!previous && active) parentTabScrollTop = scrollContainer.value?.scrollTop || 0;
    if (!active) nextTick(() => {
        if (scrollContainer.value) {
            scrollContainer.value.scrollTop = parentTabScrollTop;
            scrollFollow.rememberPosition();
        }
    });
});

const debounce = (fn, delay) => {
    let timer
    return (...args) => {
        clearTimeout(timer)
        timer = setTimeout(() => fn(...args), delay)
    }
}
const onChatScrollTop = () => {
    if (childTabs.activeId.value) return;
    if (scrollLock.value || historyLoadingMore.value || !hasMoreHistory.value) return;
    if (!scrollContainer.value) return;
    const { scrollTop, scrollHeight } = scrollContainer.value;
    isFirstEnter.value = false
    if (scrollTop <= 0) {
        let data = {
            session_id: session_id.value,
            created_at: created_at.value,
            limit: limit.value
        }
        getmsgList(data, true, scrollHeight);
    }
}
const debouncedScrollTop = debounce(onChatScrollTop, 500);
const handleScroll = () => {
    if (childTabs.activeId.value) return;
    scrollFollow.onScroll();
    debouncedScrollTop();
};

const fetchMessageList = (data) => getMessageList(data);

const {
    findLastMessage,
    shouldRenderAssistantMessage,
    shouldShowGlobalTypingIndicator,
    handleMsgList,
    processStreamChunk,
    prepareForNewOutgoingMessage,
    prepareResumedMessage,
    markInFlightAssistantStopped,
} = useChatStreamHandler({
    messagesList,
    loading,
    isReplying,
    currentAssistantMessageId,
    fullContent,
    isAgentStreamSession,
    scrollToBottom,
    onError: (msg) => MessagePlugin.error(msg),
    onPageAction: (prompt) => void respondToPageAction(
        prompt,
        !props.embeddedMode ? 'unavailable' : assistant.pageAccess ? 'enabled' : 'disabled',
        { current: () => router.currentRoute.value.fullPath, push: (location) => router.push(location) },
    ),
    preserveIncompleteStreamReactive: true,
    isFirstEnter,
    scrollContainer,
    debug: import.meta.env.DEV,
    onAfterMsgList: async () => {
        const version = chatLoadVersion;
        activitySessionId.value = String(session_id.value);
        if (version !== chatLoadVersion) return;
        // Resume the trailing *assistant*, not simply the last row: a turn
        // that absorbed a mid-run message ends with the injected user bubble
        // in some orderings, and keying off that row would skip the resume
        // entirely, leaving a running agent with no visible output.
        const lastMessage = findLastMessage(
            (message) => message.role === 'assistant' && !message.is_completed
        );
        const locallyRunning = isReplying.value || isImRecovering.value;
        // History reload can finish after sendMsg already marked this session
        // running. Do not clear that marker just because the snapshot's last
        // message still looks completed. A scanned incomplete assistant counts: a
        // turn that absorbed a mid-run message leaves such a row in history even
        // when the tail row is a user bubble.
        if (!props.embeddedMode && !locallyRunning && !lastMessage) {
            sessionActivity.update(activitySessionId.value, false);
        }
        if (lastMessage && !locallyRunning) {
            isReplying.value = true;
            // Such a turn renders as several assistant segments; only the
            // persisted id addresses the row continue-stream and stop
            // actually operate on.
            const resumeId = persistedAssistantId(lastMessage);
            currentAssistantMessageId.value = resumeId;
            console.log('[Continue Stream] Set assistant message ID:', resumeId);
            // Only IM-originated replies (channel === 'im') get the quiet poll-to-recover
            // path: their answer is generated on the IM side and never streams through
            // this server, so continue-stream always 404s even though the reply *is*
            // coming. Web/api replies keep the original behaviour (a real failure to
            // resume the stream still surfaces as an error) — we don't touch them.
            isAttachingImStream.value = lastMessage.channel === 'im';
            await startStream({
                session_id: session_id.value,
                query: resumeId,
                method: 'GET',
                url: '/api/v1/sessions/continue-stream',
            });
            // On success the stream resumed normally; on failure the error watcher
            // already took over (quiet recovery for IM), so only clear the flag here.
            if (version === chatLoadVersion && !error.value) isAttachingImStream.value = false;
        }
    },
    onAgentQuery: (data, existingMessage) => {
        pendingStreamDebug.value = buildStreamDebugPayload();
        if (existingMessage) attachStreamDebugToMessage(existingMessage);
    },
    onMessageCreated: (message) => attachStreamDebugToMessage(message),
    onMessageUpdated: (message, payload) => {
        attachStreamDebugToMessage(message);
        if (payload?.is_completed) pendingStreamDebug.value = null;
    },
    onAgentAnswerDone: (message) => {
        attachStreamDebugToMessage(message);
        pendingStreamDebug.value = null;
    },
    onAgentChunkBound: (message) => {
        attachStreamDebugToMessage(message);
        pendingStreamDebug.value = null;
    },
    onTurnComplete: () => {
        clearSendDraft();
    },
});

const showGlobalTypingIndicator = computed(() =>
    shouldShowGlobalTypingIndicator(messagesList, loading.value, isImRecovering.value),
);

const getmsgList = (data, isScrollType = false, scrollHeight) => {
    const sid = String(data?.session_id || session_id.value || '');
    const version = chatLoadVersion;
    const isCurrent = () => version === chatLoadVersion && sid === String(session_id.value || '');
    if (!isCurrent()) return;
    const retryingInitialHistory = !isScrollType && historyStatus.value === 'failed';
    if (isScrollType) {
        if (historyStatus.value === 'failed' || (historyLoading.value && messagesList.length === 0) ||
            historyLoadingMore.value || !hasMoreHistory.value) return;
        historyLoadingMore.value = true;
    }
    return fetchMessageList(data).then(async (res) => {
        if (!isCurrent()) {
            return
        }
        const batch = res?.data;
        if (res?.success === false || !Array.isArray(batch)) throw new Error('Invalid conversation history response');
        if (!isScrollType) historyStatus.value = 'loaded';
        if (!batch.length) {
            if (isScrollType) {
                hasMoreHistory.value = historyHasMoreAfterAttempt(hasMoreHistory.value, {
                    status: 'loaded',
                    itemCount: 0,
                    pageSize: limit.value,
                    cursorAdvanced: false,
                });
            }
            return;
        }
        if (!isScrollType) {
            cancelSuggestedQuestionsFetch();
        }
        const nextCursor = batch[0].created_at;
        const cursorAdvanced = !(isScrollType && created_at.value && nextCursor === created_at.value);
        hasMoreHistory.value = historyHasMoreAfterAttempt(hasMoreHistory.value, {
            status: 'loaded',
            itemCount: batch.length,
            pageSize: limit.value,
            cursorAdvanced,
        });
        if (!cursorAdvanced) {
            return;
        }
        created_at.value = nextCursor;
        // A live turn can arrive while the initial history is unavailable.
        await handleMsgList(batch, isScrollType || (retryingInitialHistory && messagesList.length > 0), scrollHeight);
    }).catch((err) => {
        if (!isCurrent()) return;
        console.error('Failed to load messages:', err);
        if (isScrollType) {
            hasMoreHistory.value = historyHasMoreAfterAttempt(hasMoreHistory.value, {
                status: 'failed',
            });
        } else {
            historyStatus.value = 'failed';
        }
    }).finally(() => {
        if (!isCurrent()) return;
        historyLoading.value = false;
        historyLoadingMore.value = false;
        if (!isScrollType && historyStatus.value === 'loaded' && messagesList.length === 0) {
            fetchSuggestedQuestionsIfNeeded();
        }
    })
}

const loadInitialHistory = () => {
    historyLoading.value = true;
    return getmsgList({ session_id: session_id.value, created_at: '', limit: limit.value });
};

const retryHistory = () => {
    if (historyStatus.value === 'failed' && !historyLoading.value) return loadInitialHistory();
};

// 发送消息
let sendDraft = '';
let sendImages = [];
let sendAttachments = [];
const clearSendDraft = () => {
    sendDraft = '';
    sendImages = [];
    sendAttachments = [];
};
const restoreSendDraft = (draft) => {
    if (!draft || sendDraft !== draft) return;
    const images = sendImages;
    const attachments = sendAttachments;
    clearSendDraft();
    inputFieldRef.value?.restoreDraft(draft, images, attachments);
};

// 处理停止生成事件 - 立即清除 loading 状态
const handleStopGeneration = () => {
    console.log('[Stop Generation] Immediately clearing loading state');
    clearSendDraft();
    stopStream();
    loading.value = false;
    isReplying.value = false;
    if (recoverPollTimer) { clearTimeout(recoverPollTimer); recoverPollTimer = null; }
    isImRecovering.value = false;
    markInFlightAssistantStopped(currentAssistantMessageId.value);
};

const handleStopConfirmed = () => {
};

const handleStopFailed = async () => {
    const messageId = currentAssistantMessageId.value;
    const message = findLastMessage((item) =>
        item.role === 'assistant' && persistedAssistantId(item) === messageId
    );
    if (!messageId || !message) {
        loading.value = false;
        isReplying.value = false;
        currentAssistantMessageId.value = '';
        return;
    }
    prepareResumedMessage(message, '');
    isReplying.value = true;
    loading.value = true;
    await startStream({
        session_id: session_id.value,
        query: messageId,
        method: 'GET',
        url: '/api/v1/sessions/continue-stream',
    });
};

const sendMsg = async (value, modelId = '', mentionedItems = [], imageFiles = [], attachmentFiles = [], options = {}) => {
    sendDraft = value;
    sendImages = imageFiles;
    sendAttachments = attachmentFiles;
    if (!props.embeddedMode && !currentSession.value) {
        const version = chatLoadVersion;
        await loadSessionAndHydrate(session_id.value);
        if (version !== chatLoadVersion || !currentSession.value) {
            if (version === chatLoadVersion) restoreSendDraft(value);
            return;
        }
    }
    if (composerLocked.value) {
        restoreSendDraft(value);
        return;
    }
    const reasoningEffort = props.embeddedMode ? undefined : (useSettingsStoreInstance.reasoningEffortOverride || undefined);
    stopStream();
    prepareForNewOutgoingMessage();
    activitySessionId.value = String(session_id.value);
    isReplying.value = true;
    loading.value = true;
    const selectedAgentId = props.embeddedMode ? props.agentId : (useSettingsStoreInstance.selectedAgentId || '');
    const selectedAgentSourceTenantId = props.embeddedMode
        ? undefined
        : (useSettingsStoreInstance.selectedAgentSourceTenantId || undefined);

    // Images are unified with the attachment pipeline: on the authenticated web
    // client they upload as temporary documents (understood in the background by
    // the VLM) and are sent as attachment_ids. The inline base64 `images`
    // payload is kept only for the embedded/public API path. A base64 fallback
    // is used per-image if the async upload fails.
    let imageAttachments = [];
    let userImages = [];
    const imageAttachmentIds = [];
    if (imageFiles && imageFiles.length > 0) {
        for (const file of imageFiles) {
            let dataURI;
            try {
                dataURI = await fileToBase64(file);
            } catch (e) {
                console.error('[Image] Failed to read images:', e);
                loading.value = false;
                isReplying.value = false;
                restoreSendDraft(value);
                return;
            }
            userImages.push({ url: dataURI });
            if (props.embeddedMode) {
                imageAttachments.push({ data: dataURI });
                continue;
            }
            try {
                const upload = await uploadTemporaryAttachment(
                    session_id.value, file, selectedAgentId, selectedAgentSourceTenantId, 'auto'
                );
                imageAttachmentIds.push(upload.data.id);
            } catch (e) {
                console.error('[Image] Temporary image upload failed, falling back to inline:', e);
                imageAttachments.push({ data: dataURI });
            }
        }
    }

    // The create-chat page cannot upload before its session exists. Once it
    // navigates here, move those local files through the same asynchronous
    // upload/parse flow before starting the first stream.
    const localAttachments = (attachmentFiles || []).filter(attachment => !attachment.documentId);
    if (!props.embeddedMode && localAttachments.length > 0) {
        try {
            // Only upload to obtain a document ID; parsing continues in the
            // background and is awaited by the backend (shown on the timeline).
            await Promise.all(localAttachments.map(async (attachment) => {
                attachment.status = 'uploading';
                const upload = await uploadTemporaryAttachment(
                    session_id.value, attachment.file, selectedAgentId, selectedAgentSourceTenantId, 'auto'
                );
                attachment.documentId = upload.data.id;
                attachment.status = upload.data.status;
            }));
        } catch (error) {
            console.error('[Attachment] Temporary document upload failed:', error);
            await Promise.all(localAttachments
                .filter(attachment => attachment.documentId)
                .map(attachment => deleteTemporaryAttachment(session_id.value, attachment.documentId).catch(() => undefined)));
            for (const attachment of localAttachments) {
                attachment.documentId = undefined;
                attachment.status = 'local';
            }
            MessagePlugin.error(error?.message || t('chat.attachmentParseFailed'));
            loading.value = false;
            isReplying.value = false;
            restoreSendDraft(value);
            return;
        }
    }

    // Send any successfully uploaded attachment (parsing may still be running);
    // the backend waits for readiness and reports progress on the timeline.
    const attachmentIds = (attachmentFiles || [])
        .filter(attachment => attachment.documentId && attachment.status !== 'failed')
        .map(attachment => attachment.documentId);
    attachmentIds.push(...imageAttachmentIds);
    // Embedded public routes do not expose the authenticated session upload API;
    // keep their existing inline payload for compatibility.
    const legacyAttachmentFiles = props.embeddedMode
        ? (attachmentFiles || []).filter(attachment => !attachment.documentId)
        : [];
    let attachmentUploads = [];
    if (legacyAttachmentFiles.length > 0) {
        try {
            for (const attachment of legacyAttachmentFiles) {
                const reader = new FileReader();
                const base64Promise = new Promise((resolve, reject) => {
                    reader.onload = () => {
                        const result = reader.result;
                        // Extract base64 content (remove data:...;base64, prefix)
                        const base64 = result.split(',')[1];
                        resolve(base64);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(attachment.file);
                });
                const base64Data = await base64Promise;
                attachmentUploads.push({
                    data: base64Data,
                    file_name: attachment.name,
                    file_size: attachment.size
                });
            }
        } catch (e) {
            console.error('[Attachment] Failed to read attachments:', e);
            loading.value = false;
            isReplying.value = false;
            restoreSendDraft(value);
            return;
        }
    }

    // 将@提及的知识库和文件信息存入用户消息
    messagesList.push({ content: value, role: 'user', mentioned_items: mentionedItems, images: userImages, attachments: attachmentFiles.map(a => ({ id: a.documentId, file_name: a.name, file_size: a.size, file_type: '.' + a.name.split('.').pop()?.toLowerCase() })), channel: 'web', created_at: new Date().toISOString() });
    userHasScrolledUp.value = false;
    scrollToBottom(true);

    // Get agent mode status from settings store (prefer selectedAgentId for builtins)
    const agentEnabled = props.embeddedMode
        ? (props.agentId && props.agentId !== 'builtin-quick-answer')
        : useSettingsStoreInstance.isAgentStreamMode;

    // Get web search status from settings store. The embedded assistant has no
    // toggle of its own; its agent config decides on the server.
    const webSearchEnabled = props.embeddedMode ? true : useSettingsStoreInstance.isWebSearchEnabled;

    // Get knowledge_base_ids from settings store (selected by user via KnowledgeBaseSelector)
    // Merge @mentioned KB/file IDs so retrieval uses the same targets user @mentioned (including shared KBs)
    const hostScope = props.embeddedMode && props.hostScope ? props.hostScope() : null;
    const sidebarKbIds = props.embeddedMode ? (hostScope?.knowledgeBaseIds || []) : (useSettingsStoreInstance.settings.selectedKnowledgeBases || []);
    const sidebarFileIds = props.embeddedMode ? [] : (useSettingsStoreInstance.settings.selectedFiles || []);
    const kbIdSet = new Set(sidebarKbIds);
    const fileIdSet = new Set(sidebarFileIds);
    for (const item of mentionedItems || []) {
        if (!item?.id) continue;
        if (item.type === 'kb' && !kbIdSet.has(item.id)) {
            kbIdSet.add(item.id);
        } else if (item.type === 'file' && !fileIdSet.has(item.id)) {
            fileIdSet.add(item.id);
        }
    }
    const kbIds = [...kbIdSet];
    const knowledgeIds = [...fileIdSet];
    const tagIds = [...new Set((mentionedItems || []).filter(item => item.type === 'tag' && item.id).map(item => item.id))];
    const mcpServiceIds = [...new Set((mentionedItems || []).filter(item => item.type === 'mcp' && item.id).map(item => item.id))];
    const skillNames = [...new Set((mentionedItems || []).filter(item => item.type === 'skill' && item.id).map(item => item.skill_name || item.id))];

    const endpoint = agentEnabled ? '/api/v1/agent-chat' : '/api/v1/knowledge-chat';

    const requestMcpServiceIds = agentEnabled ? mcpServiceIds : [];
    const requestSkillNames = agentEnabled ? skillNames : [];

    await startStream({
        session_id: session_id.value,
        knowledge_base_ids: kbIds,
        knowledge_ids: knowledgeIds,
        agent_enabled: agentEnabled,
        agent_id: selectedAgentId,
        agent_source_tenant_id: selectedAgentSourceTenantId,
        web_search_enabled: webSearchEnabled,
        summary_model_id: modelId,
        reasoning_effort: reasoningEffort,
        mcp_service_ids: requestMcpServiceIds,
        skill_names: requestSkillNames,
        tag_ids: tagIds,
        mentioned_items: mentionedItems,
        images: imageAttachments.length > 0 ? imageAttachments : undefined,
        attachment_uploads: attachmentUploads.length > 0 ? attachmentUploads : undefined,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
        query: value,
        question_origin: options?.questionOrigin,
        page_context: agentEnabled ? (hostScope?.pageContext || undefined) : undefined,
        assistant_access: agentEnabled ? (hostScope?.assistantAccess || undefined) : undefined,
        method: 'POST',
        url: endpoint,
    });
}

// Quietly recover an in-flight IM reply we couldn't attach to (it's generated on
// the IM side, so it never streamed through this server). Poll until it completes,
// then reload the thread so it renders via the normal path. Bounded so an IM reply
// that genuinely died (e.g. the bot crashed) doesn't spin forever — on timeout we
// surface the original error so the failure isn't hidden.
const RECOVER_POLL_INTERVAL = 2500;
const RECOVER_POLL_MAX_ATTEMPTS = 48; // ~2 min
const recoverIncompleteMessage = () => {
    const targetSession = session_id.value;
    const targetMessageId = currentAssistantMessageId.value;
    if (recoverPollTimer) { clearTimeout(recoverPollTimer); recoverPollTimer = null; }
    if (!targetMessageId) { isReplying.value = false; isImRecovering.value = false; return; }
    isImRecovering.value = true; // show the "generating" indicator while we poll
    let attempts = 0;
    const poll = async () => {
        recoverPollTimer = null;
        if (session_id.value !== targetSession) { isReplying.value = false; isImRecovering.value = false; return; } // navigated away
        attempts++;
        try {
            const res = await getMessageList({ session_id: targetSession, limit: limit.value, created_at: '' });
            const target = (res?.data || []).find((m) => m.id === targetMessageId);
            if (target && target.is_completed) {
                created_at.value = '';
                messagesList.splice(0);
                getmsgList({ session_id: targetSession, limit: limit.value, created_at: '' });
                isReplying.value = false;
                isImRecovering.value = false;
                currentAssistantMessageId.value = '';
                return;
            }
        } catch (e) {
            console.warn('[Continue Stream] recovery poll failed:', e);
        }
        if (attempts >= RECOVER_POLL_MAX_ATTEMPTS) {
            // The IM reply never completed — don't hide it; surface the standard
            // stream-failure message (reuses the existing i18n key, no raw HTTP code).
            MessagePlugin.error(t('error.streamFailed'));
            isReplying.value = false;
            isImRecovering.value = false;
            currentAssistantMessageId.value = '';
            return;
        }
        recoverPollTimer = setTimeout(poll, RECOVER_POLL_INTERVAL);
    };
    recoverPollTimer = setTimeout(poll, RECOVER_POLL_INTERVAL);
};

// Watch for stream errors and show message
// Answering a suspended prompt resumes its run on the server; follow it on
// the same assistant message. The resumed stream may not exist yet when the
// answer returns, so attaching retries briefly.
let attachingResumedRun = false;
const resumeSuspendedRun = async (pendingId) => {
    const sessionId = session_id.value;
    const message = findLastMessage((m) => m.role === 'assistant' && (m.agentEventStream || []).some(
        (e) => isPromptCard(e) && e.pending_id === pendingId,
    ));
    if (!message || !sessionId || isReplying.value) return;
    const resumeId = persistedAssistantId(message);
    prepareResumedMessage(message, pendingId);
    isReplying.value = true;
    currentAssistantMessageId.value = resumeId;
    attachingResumedRun = true;
    try {
        for (let attempt = 0; attempt < 60; attempt++) {
            await new Promise((resolve) => setTimeout(resolve, 500));
            if (session_id.value !== sessionId) return;
            await startStream({
                session_id: sessionId,
                query: resumeId,
                method: 'GET',
                url: '/api/v1/sessions/continue-stream',
                resume_pending_id: pendingId,
            });
            if (!error.value) return;
        }
    } finally {
        attachingResumedRun = false;
    }
    if (error.value && session_id.value === sessionId) {
        MessagePlugin.error(error.value);
        isReplying.value = false;
        loading.value = false;
        currentAssistantMessageId.value = '';
    }
};
provide(resumeSuspendedRunKey, resumeSuspendedRun);

// The assistant panel's conversation takes messages asked from the page (the
// selection bubble, the editor toolbar) once its history is in.
if (props.embeddedMode) {
    watch([() => assistant.queuedMessage, historyLoading], ([message, pending]) => {
        if (!message || pending) return;
        assistant.takeQueuedMessage();
        if (isReplying.value || loading.value) {
            // Mid-reply it waits in the input box for the user to send.
            inputFieldRef.value?.prefill?.(message.query);
            return;
        }
        sendMsg(message.query, inputFieldRef.value?.getComposerModelId?.() || props.modelId);
    }, { immediate: true });
    watch(() => assistant.focusRequest, () => {
        inputFieldRef.value?.focusInput?.();
    });
}

watch(error, (newError) => {
    if (!newError) return;
    if (attachingResumedRun) return;
    // A failed attach to an in-flight IM reply isn't a real error — the answer is
    // produced on the IM side and never streams here. Recover quietly by polling to
    // completion instead of flashing a "stream failed" toast. Web/api replies fall
    // through to the normal error toast below, unchanged.
    if (isAttachingImStream.value) {
        isAttachingImStream.value = false;
        recoverIncompleteMessage();
        return;
    }
    MessagePlugin.error(newError);
    isReplying.value = false;
    loading.value = false;
    restoreSendDraft(sendDraft);
    // 清空当前 assistant message ID
    currentAssistantMessageId.value = '';
});

onChunk((data) => {
    if (data.response_type === 'session_title') {
        const title = data.content || data.data?.title;
        if (title && data.data?.session_id) {
            console.log('[Session Title Update]', {
                session_id: data.data.session_id,
                title: title,
            });
            usemenuStore.updatasessionTitle(data.data.session_id, title);
            usemenuStore.changeIsFirstSession(false);
            notifySessionMutation({
                sessionId: data.data.session_id,
                patch: { title },
            });
        }
        return;
    }
    processStreamChunk(data);
});

const handleSessionMutation = (event) => {
    const detail = event.detail;
    if (detail?.sessionId !== session_id.value) return;

    if (detail.patch) {
        currentSession.value = {
            ...(currentSession.value || { id: session_id.value }),
            ...detail.patch,
        };
    }
    if (detail.messagesCleared) {
        chatLoadVersion++;
        historyLoading.value = false;
        historyStatus.value = 'loaded';
        messagesList.splice(0);
        created_at.value = '';
        hasMoreHistory.value = true;
        historyLoadingMore.value = false;
        fetchSuggestedQuestionsIfNeeded();
    }
};

onBeforeMount(async () => {
    // 嵌入式的 agent / 知识库由宿主随请求传入，不能写进主对话的 settings store。
    if (props.embeddedMode) return;
    // 若从智能体列表点击共享智能体进入，URL 带 agent_id 与 source_tenant_id，同步到 store
    const agentIdFromQuery = route.query.agent_id && String(route.query.agent_id);
    const sourceTenantIdFromQuery = route.query.source_tenant_id && String(route.query.source_tenant_id);
    if (agentIdFromQuery && sourceTenantIdFromQuery) {
        useSettingsStoreInstance.selectAgent(agentIdFromQuery, sourceTenantIdFromQuery);
    } else if (agentIdFromQuery) {
        useSettingsStoreInstance.selectAgent(agentIdFromQuery, null);
    }

    // 必须在 Input-field onMounted 之前完成：按 session.last_request_state 恢复输入栏
    await loadSessionAndHydrate(session_id.value);
});

onMounted(async () => {
    window.addEventListener(SESSION_MUTATION_EVENT, handleSessionMutation);
    messagesList.splice(0);

    // 初始化状态：加载历史消息时不应显示loading
    loading.value = false;
    isReplying.value = false;
    startBackgroundWork();

    if (props.embeddedMode && props.initialQuery) {
        scrollLock.value = true;
        historyLoading.value = false;
        sendMsg(props.initialQuery, inputFieldRef.value?.getComposerModelId?.() || props.modelId);
    } else if (!props.embeddedMode && firstQuery.value) {
        scrollLock.value = true;
        historyLoading.value = false;
        if (firstModelId.value) {
            useSettingsStoreInstance.updateConversationModels({
                summaryModelId: firstModelId.value,
                selectedChatModelId: firstModelId.value,
                rerankModelId: '',
            });
        }
        sendMsg(firstQuery.value, firstModelId.value || '', firstMentionedItems.value || [], firstImageFiles.value || [], firstAttachmentFiles.value || [], { questionOrigin: firstQuestionOrigin.value || undefined });
        usemenuStore.changeFirstQuery('', [], '', [], []);
    } else {
        scrollLock.value = false;
        hasMoreHistory.value = true;
        historyLoadingMore.value = false;
        loadInitialHistory();
    }
})
const clearData = () => {
    chatLoadVersion++;
    clearSendDraft();
    if (!props.embeddedMode) sessionActivity.detach(activitySessionId.value);
    activitySessionId.value = '';
    stopStream();
    referencesDrawer.close();
    isReplying.value = false;
    fullContent.value = '';
    // Stop any IM-reply recovery poll for the session we're leaving/switching.
    if (recoverPollTimer) { clearTimeout(recoverPollTimer); recoverPollTimer = null; }
    isImRecovering.value = false;
}
onUnmounted(() => {
    chatLoadVersion++;
    if (!props.embeddedMode) sessionActivity.detach(activitySessionId.value);
    activitySessionId.value = '';
    window.removeEventListener(SESSION_MUTATION_EVENT, handleSessionMutation);
    if (recoverPollTimer) { clearTimeout(recoverPollTimer); recoverPollTimer = null; }
    backgroundPoller.dispose();
    clearComposerApproval();
});
// An embedded view outlives the page behind it: a route change must not stop
// its stream or restore the main chat's defaults.
onBeforeRouteLeave((to, from, next) => {
    if (props.embeddedMode) return next()
    clearData()
    // 离开聊天会话 → 还原"用户全局默认"，避免旧会话的请求态泄漏到新建对话。
    useSettingsStoreInstance.restoreDefaultsIfSnapshotted();
    next()
})
onBeforeRouteUpdate((to, from, next) => {
    if (props.embeddedMode) return next()
    clearData()
    // 仅"会话 → 会话"会落到这里；跨会话覆盖的还原放到 route.params 的 watch 里，
    // 因为新会话的 getSession 也在那边触发，便于保证 restore→snapshot→apply 顺序。
    next()
})
</script>
<style lang="less" scoped>
@import '../../components/css/chat-scrollbar.less';
.chat {
    // 水平方向不留 padding，让滚动条贴到内容区最右缘；
    // 消息列与输入列各自用 --chat-content-inset 做左右对称的留白（窄屏时才可见）。
    padding: 0;
    --chat-content-inset: 20px;
    box-sizing: border-box;
    flex: 1;
    // The parent .platform-route-outlet is a flex column with min-height:0
    // and overflow:hidden — we also need min-height:0 here so that our
    // own flex:1 child (.chat_thread) can shrink below its content height.
    min-height: 0;
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    max-width: 100%;
    min-width: 0;

    @media (max-width: 760px) {
        --chat-content-inset: 12px;
    }

    &.is-embedded {
        max-width: 100%;
        min-width: 100%;
        padding: 0;
        overflow-x: hidden;
    }

    &:not(.is-embedded) {
        @media (min-width: 960px) {
            transition: padding-right var(--app-motion-slow) cubic-bezier(0.22, 0.61, 0.36, 1);
        }
    }

    &.has-references-panel:not(.is-embedded) {
        @media (min-width: 960px) {
            padding-right: var(--references-panel-width, 420px);
            box-sizing: border-box;

            .chat_scroll_box {
                padding-top: 0;
            }
        }
    }

    // 沙箱可视化右侧面板：宽度可拖拽调整（--sandbox-panel-width 由
    // composable 持久化），聊天区 padding 跟随面板宽度让位。
    &.has-sandbox-panel:not(.is-embedded) {
        @media (min-width: 960px) {
            padding-right: var(--sandbox-panel-width, 420px);
            box-sizing: border-box;
        }
    }

    &.has-sandbox-panel.has-references-panel:not(.is-embedded) {
        @media (min-width: 1400px) {
            padding-right: calc(var(--references-panel-width, 420px) + var(--sandbox-panel-width, 420px));
        }

        @media (max-width: 1399.98px) and (min-width: 960px) {
            padding-right: var(--sandbox-panel-width, 420px);
        }
    }

    &.is-embedded :deep(.answers-input) {
        position: relative;
        transform: translateX(0);
        width: 100%;
        left: 0;
        bottom: auto;
        display: flex;
        justify-content: center;
    }

    &.is-embedded :deep(.control-bar) {
        justify-content: flex-end;
    }

    &:not(.is-embedded) :deep(.answers-input) {
        position: static;
        transform: translateX(0);

        .t-textarea__inner {
            width: 100% !important;
        }
    }

    &.is-embedded :deep(.answers-input) .t-textarea__inner {
        width: 100% !important;
    }
}

.chat-child-detail { flex: 1; min-height: 0; width: 100%; overflow: hidden; }

.chat_thread {
    position: relative;
    flex: 1;
    min-height: 0;
    width: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.chat-topbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 0 0 var(--app-chat-header-height);
    width: 100%;
    min-width: 0;
    padding: 0 12px 0 var(--chat-content-inset, 20px);
    box-sizing: border-box;
    border-bottom: 1px solid var(--td-component-stroke);
    background: var(--td-bg-color-container);
}

.sandbox-header-toggle {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    margin-left: auto;
}

.sandbox-header-toggle__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: 0;
    border-radius: 5px;
    color: var(--td-text-color-placeholder);
    background: transparent;
    cursor: pointer;
    transition: background-color var(--app-motion-fast) ease, color var(--app-motion-fast) ease;

    &:hover {
        color: var(--td-text-color-primary);
        background: var(--td-bg-color-container-hover);
    }

    &:active {
        background: var(--td-bg-color-container-active);
    }
}

.chat_scroll_box {
    flex: 1;
    min-height: 0;
    width: 100%;
    padding: 8px 0 0;
    box-sizing: border-box;
    overflow-y: auto;
    // Keep native message bounce without chaining scroll to the outer page.
    overscroll-behavior-y: contain;
    scroll-padding-bottom: var(--chat-composer-height, 0px);
    .chat-scrollbar();
}

// Keep the full-height message scrollbar and reserve space below the last
// message for the composer, which sits outside the bouncing scroll viewport.
.chat_scroll_content {
    display: flex;
    flex-direction: column;
    min-height: 100%;

    // Use an in-flow spacer so the content ResizeObserver also detects composer
    // height changes and keeps the last message visible when following replies.
    &::after {
        content: '';
        flex: 0 0 var(--chat-composer-height, 0px);
    }
}

.host-approval-pop {
    width: 100%;
    max-width: 800px;
    margin: 0 auto 8px;
    padding: 0 16px;
    box-sizing: border-box;
}

.chat_composer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: var(--chat-scrollbar-gutter, 0px);
    z-index: 12;
    padding: 16px 0 max(8px, env(safe-area-inset-bottom));
    background: var(--td-bg-color-container);
}

.is-embedded .chat_composer {
    padding: 0;
}

.chat_overlays {
    position: absolute;
    inset: 0 0 var(--chat-composer-height, 0px);
    pointer-events: none;

    :deep(.browser-task-preview) {
        pointer-events: auto;
    }
}

.scroll-to-bottom-btn {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: calc(100% + 8px);
    z-index: 10;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--td-bg-color-container);
    border: 1px solid var(--td-component-stroke);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--td-text-color-secondary);
    transition: background-color var(--app-motion-base) ease, color var(--app-motion-base) ease, box-shadow var(--app-motion-base) ease;

    &:hover {
        background: var(--td-bg-color-container-hover);
        color: var(--td-text-color-primary);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    &:active {
        transform: translateX(-50%) scale(0.92);
    }
}

.scroll-btn-fade-enter-active,
.scroll-btn-fade-leave-active {
    transition: opacity var(--app-motion-base) ease, transform var(--app-motion-base) ease;
}

.scroll-btn-fade-enter-from,
.scroll-btn-fade-leave-to {
    opacity: 0;
    transform: translateX(-50%) translateY(8px);
}

@keyframes contentFadeIn {
    from {
        opacity: 0;
        transform: translateY(6px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.history-load-error {
    margin-top: 16px;
}

.msg-skeleton-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 960px;
    padding: 16px 0;
    animation: contentFadeIn 0.3s ease-out;
}

.msg-skeleton-user {
    display: flex;
    justify-content: flex-end;
}

.msg-skeleton-bot {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-left: 4px;
}

.input-container {
    min-height: 0;
    flex-shrink: 0;
    margin: 0 auto;
    width: 100%;
    max-width: 960px;
    box-sizing: border-box;
    position: relative;

    &:not(.is-embedded) {
        padding: 0 var(--chat-content-inset, 20px);
        max-width: calc(960px + 2 * var(--chat-content-inset, 20px));
    }

    &.is-embedded {
        max-width: 100%;
        width: 100%;
        margin: 0;
        padding: 12px 16px 16px;
        min-height: auto;
        box-sizing: border-box;
        overflow-x: clip;
    }
}

.automation-session-notice {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px 0;
    color: var(--td-text-color-secondary);
    font-size: var(--app-text-sm);
    line-height: 1.6;

    > .t-icon { flex-shrink: 0; }
}

.msg_list {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 960px;
    flex: 1;
    margin: 0 auto;
    width: 100%;
    box-sizing: border-box;

    &:not(.is-embedded) {
        padding: 0 var(--chat-content-inset, 20px);
        max-width: calc(960px + 2 * var(--chat-content-inset, 20px));
    }

    // Matches the composer's inset, and keeps text clear of the scrollbar,
    // which overlays content where the platform uses overlay scrollbars.
    &.is-embedded {
        padding: 0 16px;
    }

    /*
      给每条消息加 layout/style containment：
      - 一条消息的内部布局变化不再让浏览器去 invalidate 整个文档，
        这是修掉"hover 到 session 列表也变白"那个问题的关键。
      - 不要再用 content-visibility: auto / contain-intrinsic-size：
        agent 消息真实高度差异巨大（几百 ~ 数千 px），估的占位高度会让消息进入视口时
        反复发生"占位 -> 真实高度"的大幅 layout shift + 首次 paint 滞后，
        反而在向上滚动时制造"未画完"的白屏闪烁。
        当前 handleMsgList 全流程 ~50ms，根本无需跳过渲染，老老实实正常渲染最稳。
      - 不开 contain: paint：AgentStreamDisplay 里有 tooltip / popover 等会溢出的浮层，
        paint containment 会把它们裁掉。
    */
    .msg-item-wrapper {
        contain: layout style;
        &.is-empty-segment { display: none; }
        &.is-steer-prefix { margin-bottom: -4px; }
    }

    .message-row {
        display: flex;
        flex-direction: column;
        width: 100%;

    }

    .botanswer_laoding_gif {
        width: 24px;
        height: 18px;
        margin-left: 16px;
    }

    .chat-global-wait {
        display: flex;
        align-items: center;
        min-height: 28px;
        padding-left: 4px;
    }

    .chat-global-wait__spinner {
        width: 12px;
        height: 12px;
        box-sizing: border-box;
        border: 1.5px solid var(--td-component-stroke);
        border-top-color: var(--td-text-color-secondary);
        border-radius: 50%;
        animation: wk-spin 0.8s linear infinite;
    }
}

@media (prefers-reduced-motion: reduce) {
    .chat-global-wait__spinner {
        animation: none;
    }
}

@import '../../components/css/suggested-questions.less';

.suggested-questions-container {
    transition: min-height var(--app-motion-slow) @suggested-ease;
}

.suggested-questions-inner {
    animation: contentFadeIn 0.3s ease-out;
}

.sq-fade-enter-active,
.sq-fade-leave-active {
    transition: opacity 0.25s @suggested-ease;
}

.sq-fade-enter-from,
.sq-fade-leave-to {
    opacity: 0;
}
</style>

<style lang="less">
.chat-rewind-popconfirm {
    .t-popconfirm__content {
        width: 280px;
        max-width: calc(100vw - 24px);
        padding: 14px 16px 12px;
        box-sizing: border-box;
    }

    .t-popconfirm__body {
        gap: 8px;
    }

    .t-popconfirm__body > .t-icon {
        flex-shrink: 0;
        margin: 0;
        padding: 3px 0 0;
        font-size: var(--app-text-xl);
    }

    .t-popconfirm__inner {
        flex: 1;
        min-width: 0;
        max-width: none;
        white-space: normal;
    }

    .chat-rewind-confirm__title {
        font-size: var(--app-text-base);
        font-weight: 500;
        line-height: 22px;
        color: var(--td-text-color-primary);
    }

    .chat-rewind-confirm__body {
        margin-top: 2px;
        font-size: var(--app-text-md);
        line-height: 20px;
        color: var(--td-text-color-secondary);
    }

    .t-popconfirm__buttons {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 12px;

        .t-popconfirm__confirm {
            margin-left: 0;
        }
    }
}
</style>
