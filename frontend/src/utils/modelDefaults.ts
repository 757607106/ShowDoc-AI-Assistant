export interface ModelDefaultCandidate {
  id?: string
  type: string
  status?: string
  is_default?: boolean
  default_for?: string[]
  parameters?: { supports_vision?: boolean }
  capabilities?: { input?: string[] }
}

export function modelSupportsType(model: ModelDefaultCandidate, modelType: string): boolean {
  if (modelType !== 'VLLM') return model.type === modelType
  if (model.type !== 'VLLM' && model.type !== 'KnowledgeQA') return false
  return model.capabilities?.input?.includes('image')
    ?? (model.type === 'VLLM' || model.parameters?.supports_vision === true)
}

export function isDefaultModelForType(model: ModelDefaultCandidate, modelType: string): boolean {
  return Boolean(model.default_for?.includes(modelType) || (model.type === modelType && model.is_default))
}

/**
 * Pick a creation-time model: prefer the declared default, fall back to the
 * first active model.
 */
export function selectInitialModelId(
  models: readonly ModelDefaultCandidate[],
  modelType: string,
): string | null {
  const active = models.filter(
    model => Boolean(model.id?.trim())
      && modelSupportsType(model, modelType)
      && (!model.status || model.status === 'active'),
  )
  const chosen = active.find(model => model.default_for?.includes(modelType))
    ?? active.find(model => isDefaultModelForType(model, modelType))
    ?? active[0]
  return chosen?.id?.trim() ?? null
}
