// Native ContextDB transport and WeKnora view-field mapping; no local knowledge state.
import { get, post, put, del, patch, getDown, postUpload } from '@/utils/request'
import { documentDisplayName } from '@/utils/contextdbDocumentName'

export type KnowledgeMode = 'source' | 'graph' | 'wiki'
export interface ContextDBBase {
  id: string
  name: string
  description?: string
  wiki_enabled: boolean
  graph_enabled: boolean
  review_enabled: boolean
  document_count?: number
  created_at?: string
  updated_at?: string
  [key: string]: any
}
export interface CreateBaseInput {
  name: string
  description?: string
  review_enabled?: boolean
  indexing_strategy?: { wiki_enabled?: boolean; graph_enabled?: boolean }
}
export interface BasePermissionProfile {
  member?: { member_id?: string; member_name?: string; role?: string; status?: string; role_permission?: string }
  knowledge_base_permissions?: { knowledge_base_id: string; current_permission?: string }[]
  [key: string]: any
}
export const knowledgeMode = (base: Pick<ContextDBBase, 'wiki_enabled' | 'graph_enabled'>): KnowledgeMode => base.wiki_enabled ? 'wiki' : base.graph_enabled ? 'graph' : 'source'
export const knowledgeModeLabel = (base: Pick<ContextDBBase, 'wiki_enabled' | 'graph_enabled'>) => ({ source: '零编译', graph: '图谱编译', wiki: 'Wiki 编译' })[knowledgeMode(base)]

export function knowledgeAccess(base: { id: string }, profile: BasePermissionProfile | null, contributor: boolean) {
  if (!profile || (profile.evaluation_state && profile.evaluation_state !== 'active') || (profile.member?.status && profile.member.status !== 'active')) return { write: false, manage: false, delete: false }
  const global = ['owner', 'admin'].includes(profile?.member?.role || '')
  const permission = profile?.knowledge_base_permissions?.find(item => item.knowledge_base_id === base.id)?.current_permission
  return { write: contributor && (global || ['write', 'kb_manage', 'all'].includes(permission || '')),
    manage: contributor && (global || (profile.mode === 'personal_compatibility' && permission === 'all') || permission === 'kb_manage'),
    delete: contributor && (global || (profile.mode === 'personal_compatibility' && permission === 'all')) }
}

export async function getBasePermissions(): Promise<BasePermissionProfile> {
  let profile: BasePermissionProfile = {}, items: NonNullable<BasePermissionProfile['knowledge_base_permissions']> = []
  for (let page = 1; ; page++) {
    const response = await nativeAPI.get('workspaces/members/self/permissions', { page, page_size: 100 })
    profile = response.data
    const batch = profile.knowledge_base_permissions || []
    items.push(...batch)
    if (batch.length < 100 || (Number.isFinite(profile.total) && items.length >= profile.total)) break
  }
  return { ...profile, knowledge_base_permissions: items }
}

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
  return { ...base, name: base.name, original_name: base.name,
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
  const res = await nativeAPI.get('knowledge/knowledge_bases')
  return { success: true, data: (res.data.knowledge_bases || []).map(kbView) }
}

export async function getBase(id: string) {
  const res = await nativeAPI.get('knowledge/knowledge_bases/detail', { knowledge_base_id: id })
  return { success: true, data: kbView(res.data) }
}

export async function createBase(data: CreateBaseInput) {
  const flags = data.indexing_strategy || {}
  if (flags.wiki_enabled && flags.graph_enabled) throw new Error('只能选择一种编译模式')
  const res = await nativeAPI.post('knowledge/knowledge_bases', { name: data.name, description: data.description,
    wiki_enabled: !!flags.wiki_enabled, graph_enabled: !!flags.graph_enabled, review_enabled: data.review_enabled ?? false })
  return { success: true, data: kbView(res.data) }
}

export async function updateBase(id: string, data: { name: string; description?: string; review_enabled?: boolean }) {
  const res = await nativeAPI.put('knowledge/knowledge_bases', {
    knowledge_base_id: id, name: data.name, description: data.description, review_enabled: data.review_enabled })
  return { success: true, data: kbView(res.data) }
}

export async function deleteBase(id: string) {
  const result = await nativeAPI.del(`knowledge/knowledge_bases?knowledge_base_id=${encodeURIComponent(id)}`)
  if (result.data?.lifecycle !== 'deleted') throw new Error('官方删除尚未确认完成，请刷新核对知识库状态后再决定是否重试')
  return result
}
export const bindBase = (id: string) => post(`/api/kb/bases/${encodeURIComponent(id)}/binding`, {})
export const deleteDocuments = (kbId: string, ids: string[]) => nativeAPI.del('knowledge/documents/batch', { knowledge_base_id: kbId, ids })
export const retryDocument = (id: string) => nativeAPI.post('knowledge/documents/retry', { document_id: id })
export const updateDocumentMetadata = (id: string, metadata: Record<string, unknown>) => nativeAPI.put('knowledge/documents/metadata', { document_id: id, metadata })

export async function replaceDocumentFile(id: string, file: File) {
  return transferFile(file, { document_id: id })
}
export async function uploadDocumentFile(kbId: string, file: File, options: { parent_node_id?: string; review_enabled?: boolean } = {}) {
  return transferFile(file, { knowledge_base_id: kbId, ...options })
}
async function transferFile(file: File, target: { document_id: string } | { knowledge_base_id: string; parent_node_id?: string; review_enabled?: boolean }) {
  if (!file.size) throw new Error('上传文件不能为空')
  const path = '/api/contextdb/v1/knowledge/files'
  const updating = 'document_id' in target
  if (file.size <= 100 * 1024 * 1024) {
    const form = new FormData(); for (const [key, value] of Object.entries(target)) if (value !== undefined) form.append(key, String(value)); form.append('file', file)
    return updating ? put(path, form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 300000 }) : postUpload(path, form)
  }
  if ('review_enabled' in target) throw new Error('分片上传不支持单次知识评审设置，请先调整知识库默认评审策略')
  const { data: upload } = await (updating ? put : post)(path + '/init-upload', { ...target, file_name: file.name, mime_type: file.type || 'application/octet-stream' })
  if (!upload.upload_ticket || !Number.isInteger(upload.chunk_size) || upload.chunk_size < 1) throw new Error('未收到有效分片上传凭据')
  const headers = { 'X-Upload-Ticket': upload.upload_ticket }, parts: { part_number: number; etag: string }[] = []
  let completing = false
  try {
    for (let offset = 0; offset < file.size; offset += upload.chunk_size) {
      const form = new FormData(), number = parts.length + 1
      form.append('part_number', String(number)); form.append('data', file.slice(offset, offset + upload.chunk_size), file.name)
      const { data: part } = await postUpload(path + '/chunks', form, undefined, { headers })
      if (part.part_number !== number || !part.etag) throw new Error('分片上传回执不完整')
      parts.push({ part_number: number, etag: part.etag })
    }
    completing = true
    return await post(path + '/complete', { parts }, { headers, timeout: 300000 })
  } catch (error) {
    if (!completing) await post(path + '/abort', {}, { headers }).catch(() => {})
    throw error
  }
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

