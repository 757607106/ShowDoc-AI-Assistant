// Native ContextDB transport and WeKnora view-field mapping; no local knowledge state.
import { get, post, put, del, patch, getDown } from '@/utils/request'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { updateSpace } from '@/api/knowledgeSpaces'

export const nativeAPI = {
  get: (path: string, params?: Record<string, any>) => get(`/api/contextdb/v1/${path}`, { params }),
  post: (path: string, data: any) => post(`/api/contextdb/v1/${path}`, data),
  put: (path: string, data: any) => put(`/api/contextdb/v1/${path}`, data),
  patch: (path: string, data: any) => patch(`/api/contextdb/v1/${path}`, data),
  del: (path: string, data?: any) => del(`/api/contextdb/v1/${path}`, data),
}

export async function listMembers() {
  const members: any[] = []
  for (let page = 1; ; page++) {
    const res = await nativeAPI.get('workspaces/members', {page, page_size:500})
    const batch = res.data.members || []
    members.push(...batch)
    if (batch.length < 500 || members.length >= res.data.total) return members
  }
}

export function kbView(base: any) {
  const displayName = typeof base.display_name === 'string' ? base.display_name.trim() : ''
  return { ...base, name: displayName || base.name, original_name: base.original_name ?? base.name,
    tenant_id: 1, type: 'document',
    capabilities: { vector: true, keyword: true, wiki: !!base.wiki_enabled,
      graph: !!base.graph_enabled, faq: false, ...base.capabilities },
    indexing_strategy: { wiki_enabled: base.wiki_enabled, graph_enabled: base.graph_enabled },
    document_count: base.document_count,
    knowledge_count: base.document_count,
    extract_config: {enabled:!!base.graph_enabled},
  }
}

export function documentView(doc: any) {
  const statuses: Record<string, string> = { succeeded: 'completed', processing: 'processing',
    pending: 'pending', uploading: 'processing', ai_reviewing: 'processing',
    pending_review: 'pending_review', failed: 'failed', deleting: 'deleting', deleted: 'deleted' }
  return { ...doc, file_name: documentDisplayName(doc), original_file_name: documentDisplayName(doc), file_type: String(doc.name || '').split('.').pop(),
    type: 'file',
    file_size: doc.size_bytes, parse_status: statuses[doc.ingest_status] || doc.ingest_status,
    source: doc.file_path, custom_metadata: doc.metadata, knowledge_base_id: doc.knowledge_base_id,
  }
}

export async function listBases() {
  const items: any[] = []
  for (let page = 1; ; page++) {
    const res = await nativeAPI.get('knowledge/knowledge_bases', { page, page_size: 100 })
    const batch = res.data.knowledge_bases || []
    items.push(...batch)
    if (batch.length < 100 || (Number.isFinite(res.data.total) && items.length >= res.data.total)) break
  }
  return { success: true, data: items.filter((b: any) => b.name !== '_governance').map(kbView) }
}

export async function getBase(id: string) {
  const res = await nativeAPI.get('knowledge/knowledge_bases/detail', { knowledge_base_id: id })
  return { success: true, data: kbView(res.data) }
}

export async function createBase(data: any) {
  const flags = data.indexing_strategy || {}
  const res = await nativeAPI.post('knowledge/knowledge_bases', { name: data.name, description: data.description,
    wiki_enabled: !!flags.wiki_enabled, graph_enabled: !!flags.graph_enabled, review_enabled: data.review_enabled ?? true })
  return { success: true, data: kbView(res.data) }
}

export async function updateBase(id: string, data: any) {
  const current = (await getBase(id)).data
  if (current.space_scope) {
    const descriptionChanged = data.description !== undefined && data.description !== (current.description || '')
    if (descriptionChanged) {
      await nativeAPI.put('knowledge/knowledge_bases', {
        knowledge_base_id: id, name: current.original_name, description: data.description })
    }
    if (data.name !== undefined && data.name !== (current.space_name || current.name)) {
      try { await updateSpace(current.space_scope, { name: data.name }) }
      catch (error) {
        if (descriptionChanged) throw new Error(`知识库说明已保存，但名称更新失败：${error instanceof Error ? error.message : String(error)}`)
        throw error
      }
    }
    return getBase(id)
  }
  const res = await nativeAPI.put('knowledge/knowledge_bases', {
    knowledge_base_id: id, name: data.name, description: data.description })
  return { success: true, data: kbView(res.data) }
}

export async function listDocuments(kbId: string, params: any = {}) {
  const res = await nativeAPI.get('knowledge/documents', { knowledge_base_id: kbId,
    page: params.page || 1, page_size: Math.min(params.page_size || 35,100) })
  return { success: true, data: (res.data.documents || []).map(documentView), total: res.data.total }
}

export async function getDocument(id: string) {
  const res = await nativeAPI.get('knowledge/documents/detail', { document_id: id })
  return { success: true, data: documentView(res.data) }
}
export function downloadDocument(id: string) {
  return getDown(`/api/contextdb/documents/${encodeURIComponent(id)}/download`)
}

