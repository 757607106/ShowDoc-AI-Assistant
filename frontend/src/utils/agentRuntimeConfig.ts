import type { AgentRuntimeDefaults, CustomAgentConfig } from '../api/agent'

export interface AgentRuntimeChange {
  field: string
  before: unknown
  after?: unknown
}

// Mirrors the backend's value checks: false switches and model fallback are valid.
function unsupportedQuickValue(field: string, value: unknown): boolean {
  if (field === 'enable_query_expansion' || field === 'enable_rewrite') return value === true
  if (field === 'fallback_strategy') return value != null && value !== '' && value !== 'model'
  if (['embedding_top_k', 'keyword_threshold', 'vector_threshold', 'rerank_top_k', 'rerank_threshold', 'rerank_model_id'].includes(field)) {
    return value != null && value !== ''
  }
  if (value && typeof value === 'object') return Object.keys(value).length > 0
  return !!value
}

/** Only incompatible values change; supported user selections survive adoption. */
export function agentRuntimeChanges(
  config: CustomAgentConfig,
  defaults: AgentRuntimeDefaults | null,
  unsupportedQuickFields: string[] | null,
): AgentRuntimeChange[] {
  if (!defaults || !unsupportedQuickFields) return []
  const changes: AgentRuntimeChange[] = []
  const mode = config.agent_mode || 'smart-reasoning'
  const current = config as Record<string, unknown>
  if (config.sandbox_config_id && !['state-backend', 'opensandbox-local'].includes(config.sandbox_config_id)) {
    changes.push({ field: 'sandbox_config_id', before: config.sandbox_config_id, after: defaults[mode].sandbox_config_id })
  }
  for (const field of ['web_search_enabled', 'reflection_enabled']) {
    if (current[field] === true) changes.push({ field, before: true, after: false })
  }
  if (config.retain_retrieval_history === false) {
    changes.push({ field: 'retain_retrieval_history', before: false, after: defaults[mode].retain_retrieval_history })
  }
  if (mode === 'quick-answer') {
    if (config.multi_turn_enabled === false) {
      changes.push({ field: 'multi_turn_enabled', before: false, after: defaults[mode].multi_turn_enabled })
    }
    if ((config.history_turns ?? 0) > 0) {
      changes.push({ field: 'history_turns', before: config.history_turns, after: defaults[mode].history_turns })
    }
    for (const field of unsupportedQuickFields) {
      if (unsupportedQuickValue(field, current[field])) changes.push({ field, before: current[field] })
    }
  }
  return changes
}

export function applyAgentRuntimeChanges(config: CustomAgentConfig, changes: AgentRuntimeChange[]): void {
  const target = config as Record<string, unknown>
  for (const { field, after } of changes) {
    if (after === undefined) delete target[field]
    else target[field] = after
  }
}
