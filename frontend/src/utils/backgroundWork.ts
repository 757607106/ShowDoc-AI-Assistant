import type { AsyncSubagentPrompt, BackgroundWorkItem, BackgroundWorkState } from '../api/chat/background-work'

export function isBackgroundWorkActive(state: BackgroundWorkState): boolean {
  return state === 'pending' || state === 'running' || state === 'waiting'
}

/** Collect cards without submitting a partial native interrupt batch. */
export function asyncPromptResponses(prompts: AsyncSubagentPrompt[], drafts: Record<string, unknown>): Record<string, unknown> | null {
  if (!prompts.length || prompts.some(prompt => !Object.hasOwn(drafts, prompt.pending_id))) return null
  const responses: Record<string, unknown> = Object.create(null)
  const actionCounts = new Map<string, number>()
  for (const prompt of prompts) {
    const answer = drafts[prompt.pending_id]
    if (prompt.kind === 'tool_approval') {
      const request = answer as { decision: string; modified_args?: Record<string, unknown>; message?: string; reason?: string }
      const decision = request.decision === 'edit'
        ? { type: 'edit', edited_action: { name: prompt.mcp_tool_name, args: request.modified_args } }
        : request.decision === 'reject' ? { type: 'reject', message: request.reason }
        : request.decision === 'respond' ? { type: 'respond', message: request.message }
        : { type: request.decision }
      const batch = responses[prompt.interrupt_id] as { decisions: unknown[] } | undefined
      const value = batch ?? { decisions: [] }
      value.decisions[prompt.action_index ?? 0] = decision
      responses[prompt.interrupt_id] = value
      if (prompt.action_count !== undefined) actionCounts.set(prompt.interrupt_id, prompt.action_count)
    } else responses[prompt.interrupt_id] = answer
  }
  for (const [id, count] of actionCounts) {
    const decisions = (responses[id] as { decisions: unknown[] }).decisions
    if (decisions.length !== count || Object.keys(decisions).length !== count) return null
  }
  return responses
}

function itemTime(item: BackgroundWorkItem): number {
  const parsed = Date.parse(item.started_at ?? item.finished_at ?? '')
  return Number.isFinite(parsed) ? parsed : 0
}

function sameWorkItem(a: BackgroundWorkItem, b: BackgroundWorkItem): boolean {
  return a.work_id === b.work_id
    && a.kind === b.kind
    && a.title === b.title
    && a.state === b.state
    && a.started_at === b.started_at
    && a.finished_at === b.finished_at
    && a.read_only === b.read_only
    && a.can_cancel === b.can_cancel
}

function compareWork(a: BackgroundWorkItem, b: BackgroundWorkItem): number {
  const rank = (item: BackgroundWorkItem) => isBackgroundWorkActive(item.state) ? 0 : 1
  const byState = rank(a) - rank(b)
  if (byState !== 0) return byState
  return itemTime(a) - itemTime(b)
}

/**
 * Merge by work_id. Incoming wins. Unchanged items keep their object identity,
 * and an unchanged list keeps the same array, so a poll tick does not rerender.
 * Active rows stay above terminal ones; within a group, earlier times come first.
 */
export function mergeBackgroundWork(
  existing: BackgroundWorkItem[],
  incoming: BackgroundWorkItem[],
): BackgroundWorkItem[] {
  const byID = new Map<string, BackgroundWorkItem>()
  for (const item of existing) byID.set(item.work_id, item)
  for (const item of incoming) {
    const prev = byID.get(item.work_id)
    if (prev && sameWorkItem(prev, item)) continue
    byID.set(item.work_id, item)
  }
  const sorted = [...byID.values()].sort(compareWork)
  if (sorted.length === existing.length && sorted.every((item, index) => item === existing[index])) {
    return existing
  }
  return sorted
}

export interface PollerOptions {
  /** Current session, or a getter so a switch can drop the in-flight response. */
  sessionId: string | (() => string)
  intervalMs?: number
  list: (
    sessionId: string,
    signal: AbortSignal,
  ) => Promise<BackgroundWorkItem[] | { data?: BackgroundWorkItem[] | null }>
  onUpdate: (items: BackgroundWorkItem[]) => void
  onError?: (message: string) => void
}

function readSessionId(sessionId: PollerOptions['sessionId']): string {
  return typeof sessionId === 'function' ? sessionId() : sessionId
}

function asWorkItems(
  value: BackgroundWorkItem[] | { data?: BackgroundWorkItem[] | null } | null | undefined,
): BackgroundWorkItem[] {
  if (Array.isArray(value)) return value
  if (value && Array.isArray(value.data)) return value.data
  return []
}

export function createBackgroundWorkPoller(options: PollerOptions): {
  start(): void; stop(): void; refresh(): Promise<void>; dispose(): void
} {
  const intervalMs = options.intervalMs ?? 5000
  let timer: ReturnType<typeof setTimeout> | null = null
  let abort: AbortController | null = null
  let running = false
  let disposed = false

  const stop = () => {
    running = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    abort?.abort()
    abort = null
  }

  const tick = async () => {
    if (!running || disposed) return
    const sessionId = readSessionId(options.sessionId)
    const controller = new AbortController()
    abort?.abort()
    abort = controller
    try {
      const raw = await options.list(sessionId, controller.signal)
      if (!running || controller.signal.aborted) return
      if (readSessionId(options.sessionId) !== sessionId) {
        void tick()
        return
      }
      const items = asWorkItems(raw)
      options.onUpdate(items)
      if (!running) return
      if (!items.some(item => isBackgroundWorkActive(item.state))) {
        running = false
        timer = null
        return
      }
      timer = setTimeout(() => { void tick() }, intervalMs)
    } catch (err) {
      if (!running || controller.signal.aborted) return
      options.onError?.(err instanceof Error ? err.message : String(err))
      if (!running) return
      timer = setTimeout(() => { void tick() }, intervalMs)
    }
  }

  return {
    start() {
      if (running || disposed) return
      running = true
      void tick()
    },
    stop,
    async refresh() {
      if (disposed) return
      // Manual refreshes use the same abort/generation boundary as polling.
      // A newer request, session switch or unmount invalidates their results.
      stop()
      running = true
      await tick()
    },
    dispose() {
      disposed = true
      stop()
    },
  }
}
