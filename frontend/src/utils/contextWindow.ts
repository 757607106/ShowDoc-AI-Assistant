import type { ModelConfig } from '../api/model/index'

export function modelHasContextWindow(type?: string): boolean {
  return type === 'KnowledgeQA' || type === 'VLLM' || type === 'chat' || type === 'vllm'
}

export function effectiveContextWindow(tokens?: number | null): number | null {
  return typeof tokens === 'number' && Number.isFinite(tokens) && tokens > 0 ? tokens : null
}

/** Read-only views use the backend's resolved limits; editor inputs stay raw. */
export function modelContextWindow(model?: Pick<ModelConfig, 'capabilities' | 'parameters'> | null): number | null {
  return effectiveContextWindow(model?.capabilities?.context_window
    ?? model?.parameters?.spec?.context_window ?? model?.parameters?.context_window)
}

export function isUnknownContextWindow(tokens?: number | null): boolean {
  return effectiveContextWindow(tokens) === null
}

/** Compact label: 128000 → 128K, 200000 → 200K, 1048576 → 1M. */
export function formatTokenCount(tokens: number): string {
  if (!Number.isFinite(tokens) || tokens <= 0) {
    return ''
  }
  const n = Math.round(tokens)
  if (n >= 1_000_000 && n % 1_000_000 === 0) {
    return `${n / 1_000_000}M`
  }
  if (n >= 1000 && n % 1000 === 0) {
    return `${n / 1000}K`
  }
  if (n >= 1024 && n % 1024 === 0) {
    const k = n / 1024
    if (k >= 1024 && k % 1024 === 0) {
      return `${k / 1024}M`
    }
    return `${k}K`
  }
  return String(n)
}

export function formatContextWindow(tokens?: number | null, unknownLabel = '—'): string {
  const known = effectiveContextWindow(tokens)
  return known === null ? unknownLabel : formatTokenCount(known)
}
