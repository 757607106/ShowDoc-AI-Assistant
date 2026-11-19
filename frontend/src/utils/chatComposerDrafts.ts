import type { AttachmentFile } from '../components/AttachmentUpload.vue'
import type { QuestionOrigin } from './questionOrigin'

interface ChatComposerDraft {
  text: string
  images: File[]
  attachments: AttachmentFile[]
  questionOrigin?: QuestionOrigin
}

// shortcut: drafts live in this tab, add persistent storage only if reload recovery is required
const drafts = new Map<string, ChatComposerDraft>()

export function saveChatDraft(key: string, draft: ChatComposerDraft) {
  if (draft.text || draft.images.length || draft.attachments.length) drafts.set(key, draft)
  else drafts.delete(key)
}

export function takeChatDraft(key: string) {
  const draft = drafts.get(key)
  drafts.delete(key)
  return draft
}

export function clearChatDrafts() {
  drafts.clear()
}
