import { get, post } from '../../utils/request'

/** States the UI and the model both see. `unknown` stays on the server. */
export type BackgroundWorkState =
  | 'pending'
  | 'running'
  | 'waiting'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'lost'

/**
 * List rows from GET .../background-work.
 * The handler never fills parent_tool_call_id, so it is not part of this type.
 */
export interface BackgroundWorkItem {
  work_id: string
  kind: string
  title: string
  state: BackgroundWorkState
  started_at?: string
  finished_at?: string
  read_only?: boolean
  can_cancel?: boolean
}

/** Byte windows on service.ShellJobPayload. */
export interface ShellJobByteOffsets {
  stdout: number
  stderr: number
}

/**
 * JSON shape of service.ShellJobPayload, returned as detail `result`.
 * A user-facing read must not send run_id; the server keeps RunID empty so
 * the model's incremental cursor does not move.
 */
export interface ShellJobPayload {
  display_type: string
  work_id: string
  state: string
  session_id: string
  command: string
  work_dir: string
  exit_code?: number
  duration_ms: number
  started_at: string
  stdout: string
  stderr: string
  from_bytes: ShellJobByteOffsets
  total_bytes: ShellJobByteOffsets
  omitted_bytes: ShellJobByteOffsets
  truncated: boolean
  note?: string
}

export interface AsyncSubagentInterrupt {
  id: string
  value: unknown
  response_schema?: Record<string, unknown>
}

export interface AsyncSubagentPayload {
  display_type: 'async_subagent'
  output: string
  structured_response?: unknown
  interrupts: AsyncSubagentInterrupt[]
  error?: string
  view_session_id?: string
  prompts?: AsyncSubagentPrompt[]
}

export interface AsyncSubagentPrompt {
  pending_id: string
  kind: 'tool_approval' | 'ask_user' | 'native_interrupt'
  interrupt_id: string
  action_index?: number
  action_count?: number
  mcp_tool_name?: string
  [key: string]: unknown
}

export interface BackgroundWorkDetail {
  work_id: string
  kind?: string
  state: BackgroundWorkState
  title: string
  read_only?: boolean
  can_cancel?: boolean
  result: ShellJobPayload | AsyncSubagentPayload | null
}

interface ApiData<T> {
  success?: boolean
  data?: T
}

function sessionWorkPath(sessionId: string, workId?: string): string {
  const base = `/api/v1/sessions/${encodeURIComponent(sessionId)}/background-work`
  return workId === undefined ? base : `${base}/${encodeURIComponent(workId)}`
}

export async function listBackgroundWork(
  sessionId: string,
  signal?: AbortSignal,
): Promise<BackgroundWorkItem[]> {
  const res = await get<ApiData<BackgroundWorkItem[]>>(sessionWorkPath(sessionId), signal ? { signal } : undefined)
  return Array.isArray(res?.data) ? res.data : []
}

export async function getBackgroundWork(
  sessionId: string,
  workId: string,
): Promise<BackgroundWorkDetail> {
  const res = await get<ApiData<BackgroundWorkDetail>>(sessionWorkPath(sessionId, workId))
  if (!res?.data) {
    throw new Error('background work not found')
  }
  return res.data
}

export async function updateBackgroundWork(
  sessionId: string,
  workId: string,
  message: string,
): Promise<void> {
  await post(`${sessionWorkPath(sessionId, workId)}/update`, { message })
}

export async function resumeBackgroundWork(
  sessionId: string,
  workId: string,
  responses: Record<string, unknown>,
): Promise<void> {
  await post(`${sessionWorkPath(sessionId, workId)}/resume`, { responses })
}

export async function cancelBackgroundWork(
  sessionId: string,
  workId: string,
): Promise<{ work_id: string; state: string }> {
  const res = await post<ApiData<{ work_id: string; state: string }>>(
    `${sessionWorkPath(sessionId, workId)}/cancel`,
    {},
  )
  if (!res?.data?.work_id) {
    throw new Error('background work not found')
  }
  return res.data
}
