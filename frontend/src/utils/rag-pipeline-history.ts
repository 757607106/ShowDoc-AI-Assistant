export const RAG_PIPELINE_TOOL_NAMES = new Set(['query_understand', 'knowledge_search', 'knowledge.search'])

/** Retrieval tools that can produce citations. `search_knowledge` is the legacy alias. */
export const RAG_RETRIEVAL_TOOL_NAMES = new Set(['knowledge_search', 'search_knowledge', 'knowledge.search'])

/** Tools rendered on the quick-answer timeline (includes pre-RAG attachment prep). */
export const RAG_TIMELINE_TOOL_NAMES = new Set([
  ...RAG_PIPELINE_TOOL_NAMES,
  'attachment_parsing',
  'image_analysis',
])

type RagHistoryReference = {
  chunk_type?: string
  knowledge_id?: string
  knowledge_title?: string
}

type RagHistoryMessage = {
  knowledge_references?: RagHistoryReference[]
  agentEventStream?: Array<Record<string, unknown>>
}

export function hasRagPipelineToolEvents(stream: Array<Record<string, unknown>> | undefined): boolean {
  if (!stream?.length) return false
  return stream.some((event) => {
    return (
      event.type === 'tool_call' &&
      typeof event.tool_name === 'string' &&
      RAG_PIPELINE_TOOL_NAMES.has(event.tool_name)
    )
  })
}

export function ensureRagPipelineHistoryStream(item: RagHistoryMessage & {
  content?: string
  is_completed?: boolean
  isAgentMode?: boolean
  hideContent?: boolean
}): void {
  if (!item.is_completed) return

  const stream = Array.isArray(item.agentEventStream)
    ? [...item.agentEventStream]
    : []

  if (hasRagPipelineToolEvents(stream)) return

  const hasRestorablePayload =
  Boolean(item.content?.trim()) ||
  Boolean(item.knowledge_references?.length)
  if (!hasRestorablePayload) return

  // Citations prove sources, not which pipeline steps executed. Restore only persisted events.
  const preserved = stream
  item.agentEventStream = preserved

  const hasAnswer = preserved.some((event) => {
    if (event.type !== 'answer' || event.superseded) return false
    const content = event.content
    return typeof content === 'string' && content.trim().length > 0
  })

  if (!hasAnswer && item.content?.trim()) {
    item.agentEventStream.push({
      type: 'answer',
      content: item.content,
      done: true,
    })
  }

  item.isAgentMode = true
  item.hideContent = true
}
