import type { Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getChunkByIdOnly } from '@/api/knowledge-base'
import { getEmbedChunkById } from '@/api/embed'
import type { CitationKnowledgeRef } from '@/utils/citationMarkdown'
import { useCitationPopover } from './useCitationPopover'
import { IS_CONTEXTDB } from '@/config/contextdb'

export { clearCitationChunkCache } from '@/utils/citationChunkCache'
export type { CitationFloatState } from './useCitationPopover'

export type ChatCitationPopoverOptions = {
  getKnowledgeReferences?: () => CitationKnowledgeRef[] | null | undefined
  embedChannelId?: () => string | undefined
  embedToken?: () => string | undefined
  sessionId?: () => string | undefined
}

export function useChatCitationPopover(rootRef: Ref<HTMLElement | null>, options?: ChatCitationPopoverOptions) {
  const { t } = useI18n()
  return useCitationPopover(rootRef, {
    mode: 'chat',
    getKnowledgeReferences: options?.getKnowledgeReferences,
    getCacheScope: () => {
      const channel = options?.embedChannelId?.()
      const token = options?.embedToken?.()
      return channel && token ? `embed:${channel}:${token}` : options?.sessionId?.() || 'default'
    },
    fetchChunk: (chunkId, kbId) => {
      const channel = options?.embedChannelId?.()
      const token = options?.embedToken?.()
      const reference = options?.getKnowledgeReferences?.()?.find(item => item.id === chunkId
        && (!IS_CONTEXTDB || item.knowledge_base_id === kbId))
      if (channel && token) return getEmbedChunkById(channel, token, chunkId)
      return reference?.knowledge_id ? getChunkByIdOnly(chunkId, reference.knowledge_id) : getChunkByIdOnly(chunkId)
    },
    notFoundError: () => t('agentStream.citation.notFound'),
    loadError: () => t('agentStream.citation.loadFailed'),
  })
}
