import type { InjectionKey } from 'vue'

/**
 * Provided by a chat view: re-attaches to a suspended run after its prompt was
 * answered and the server resumed it. Takes the prompt's pending id.
 */
export const resumeSuspendedRunKey: InjectionKey<(pendingId: string) => void> = Symbol('resumeSuspendedRun')

/** A nested conversation submits its cards to its own thread. */
export const promptSubmissionTransportKey: InjectionKey<(
  pendingId: string, kind: 'tool_approval' | 'ask_user' | 'native_interrupt', response: unknown,
) => Promise<{ resumed: boolean; stale?: boolean }>> = Symbol('promptSubmissionTransport')
