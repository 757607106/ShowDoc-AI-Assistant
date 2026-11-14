import axios from 'axios'
import {useAuthStore} from '@/stores/auth'

const http = axios.create({ baseURL: '/', timeout: 120_000 })

http.interceptors.request.use(config=>{const token=useAuthStore().token;if(token)config.headers.Authorization=`Bearer ${token}`;return config})

http.interceptors.response.use((response) => response, (error) => {
  const message = error?.response?.data?.message || error.message || '请求失败'
  return Promise.reject(new Error(message))
})

async function unwrap<T = any>(promise: Promise<{ data: any }>): Promise<T> {
  const { data } = await promise
  if (data && typeof data === 'object' && data.success === false) {
    throw new Error(data.message || '请求失败')
  }
  return data as T
}

export const api = {
  downloadFile: async (url: string, name: string) => {
    const response=await http.get(url,{responseType:'blob'})
    const href=URL.createObjectURL(response.data)
    const link=document.createElement('a');link.href=href;link.download=name;link.click()
    setTimeout(()=>URL.revokeObjectURL(href),1000)
  },
  // ---------- 治理域(原有 27 路由) ----------
  entries: () => unwrap(http.get('/api/entries')),
  showdocProjects: () => unwrap(http.get('/showdoc/projects')),
  startTask: (entry: string, payload: any) => unwrap(http.post(`/entries/${entry}/start`, payload)),
  entryDocuments: (entry: string, params: any) => unwrap(http.get(`/entries/${entry}/documents`, { params })),
  taskStatus: (taskId: string) => unwrap(http.get(`/task_status/${taskId}`)),
  tasks: (spaceScope?: string) => unwrap(http.get('/api/tasks', { params: { space_scope: spaceScope } })),
  cancelTask: (taskId: string) => unwrap(http.post(`/tasks/${taskId}/cancel`)),
  retryTask: (taskId: string) => unwrap(http.post(`/tasks/${taskId}/retry`)),
  publishTask: (taskId: string) => unwrap(http.post(`/tasks/${taskId}/publish`)),
  submitTask: (taskId: string) => unwrap(http.post(`/tasks/${taskId}/submit`)),
  uploadFiles: (files: File[], spaceScope: string) => {
    const form = new FormData()
    form.append('space_scope', spaceScope)
    files.forEach(file => form.append('files', file))
    return unwrap(http.post('/api/uploads', form))
  },
  documents: (taskId?: string) => unwrap(http.get('/api/documents', { params: taskId ? { task_id: taskId } : {} })),
  documentDetail: (versionId: string) => unwrap(http.get(`/api/documents/${versionId}`)),
  documentSourceUrl: (versionId: string) => `/api/documents/${versionId}/source`,
  reviseDocument: (versionId: string, content: string, reason: string) =>
    unwrap(http.post(`/api/documents/${versionId}/revisions`, { content, reason })),
  releases: () => unwrap(http.get('/api/releases')),
  activateRelease: (releaseId: string) => unwrap(http.post(`/api/releases/${releaseId}/activate`)),
  releaseDownloadUrl: (releaseId: string) => `/api/releases/${releaseId}/download`,
  taskDownloadUrl: (taskId: string) => `/download/${taskId}`,
  health: () => unwrap(http.get('/api/health')),

  // ---------- 知识域(ContextDB) ----------
  kbBases: () => unwrap(http.get('/api/kb/bases')),
  kbSearch: (question: string, kbIds: string[], options: any = {}) =>
    unwrap(http.post('/api/kb/search', { question, kb_ids: kbIds, ...options })),
  kbGraph: (kbId: string, options: any = {}) =>
    unwrap(http.get('/api/kb/graph', { params: { kb_id: kbId, ...options } })),
  kbReviewSettings: (kbId: string) => unwrap(http.get('/api/kb/review-settings', { params: { kb_id: kbId } })),
  kbReviewSettingsUpdate: (kbId: string, settings: any) =>
    unwrap(http.put('/api/kb/review-settings', { kb_id: kbId, ...settings })),
  kbEvents: (params: any = {}) => unwrap(http.get('/api/kb/events', { params })),
  kbDocumentRetry: (documentId: string) =>
    unwrap(http.post(`/api/kb/documents/${documentId}/retry`)),
  kbDocuments: (kbId: string, params: any = {}) =>
    unwrap(http.get('/api/kb/documents', { params: { kb_id: kbId, ...params } })),
  kbDocumentText: (kbId: string, documentId: string) =>
    unwrap(http.get(`/api/kb/documents/${documentId}/text`, { params: { kb_id: kbId } })),
  kbDocumentUpdate: (documentId: string, text: string, kbId: string) =>
    unwrap(http.put(`/api/kb/documents/${documentId}`, { text, kb_id: kbId })),
  kbReviews: (kbId?: string, params: any = {}) =>
    unwrap(http.get('/api/kb/reviews', { params: { kb_id: kbId, ...params } })),
  kbReviewDetail: (reviewId: string, contentPage?: number) =>
    unwrap(http.get(`/api/kb/reviews/${reviewId}`, { params: contentPage ? { content_page: contentPage } : {} })),
  kbReviewAction: (reviewId: string, action: string, options: { editedContent?: string; conflictResolutions?: any[] } = {}) =>
    unwrap(http.post(`/api/kb/reviews/${reviewId}/action`, {
      action, edited_content: options.editedContent, conflict_resolutions: options.conflictResolutions,
    })),
  kbReviewBatch: (reviewIds: string[], action: string) =>
    unwrap(http.post('/api/kb/reviews/batch', { ids: reviewIds, action })),
  kbReviewConflicts: (reviewId: string, resolutions: any[]) =>
    unwrap(http.post(`/api/kb/reviews/${reviewId}/conflicts`, { resolutions })),
  kbSyncStatus: (jobId: string) => unwrap(http.get('/api/kb/sync-status', { params: { job_id: jobId } })),

  // ---------- Agent 域 ----------
  agentSessions: () => unwrap(http.get('/api/agent/sessions')),
  agentSessionCreate: (title: string) => unwrap(http.post('/api/agent/sessions', { title })),
  agentSessionMessages: (sessionId: string) => unwrap(http.get(`/api/agent/sessions/${sessionId}`)),
  agentSessionDelete: (sessionId: string) => unwrap(http.delete(`/api/agent/sessions/${sessionId}`)),
}
export default api
