import { get, put } from '@/utils/request'

// RetrievalConfig mirrors the ContextDB official query contract parameters the
// workspace may pass through: top_k (REST limit 1-10), similarity_threshold
// (0-1, official default 0.6), vector_weight (0-1, official default 0.7) and
// query_rewrite (official default off; the platform keeps it on by default).
export interface RetrievalConfig {
  top_k: number
  similarity_threshold: number
  vector_weight: number
  query_rewrite: boolean
}

// Get tenant retrieval config via KV API
export function getTenantRetrievalConfig() {
  return get('/api/v1/tenants/kv/retrieval-config')
}

// Update tenant retrieval config via KV API
export function updateTenantRetrievalConfig(config: RetrievalConfig) {
  return put('/api/v1/tenants/kv/retrieval-config', config)
}
