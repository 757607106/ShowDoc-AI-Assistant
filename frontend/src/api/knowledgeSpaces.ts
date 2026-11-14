import { get, post, patch } from '@/utils/request'

export interface KnowledgeSpace {
  scope: string
  name: string
  graph_enabled: boolean
  wiki_kb_id: string | null
  graph_kb_id: string | null
  legacy?: boolean
  has_submission?: boolean
  targets?: Record<string, { knowledge_base_id: string | null; enabled: boolean;
    status?: 'available' | 'missing' | 'forbidden' | 'unknown' | 'unbound'; missing_knowledge_base_id?: string; previous_knowledge_base_ids?: string[]; error?: string }>
}

export function spaceTargetStatus(space: KnowledgeSpace, mode: 'wiki' | 'graph') {
  return space.targets?.[mode]?.status || (space[`${mode}_kb_id`] ? 'available' : 'unbound')
}

export function spaceTargetNotice(space: KnowledgeSpace, mode: 'wiki' | 'graph') {
  const name = mode === 'wiki' ? 'Wiki 库' : '图谱库'
  return ({ missing: `${name}在 ContextDB 中不存在`, forbidden: `当前成员无权读取${name}`, unknown: `暂时无法确认${name}状态`, unbound: `${name}尚未建立`, available: '' })[spaceTargetStatus(space, mode)]
}

export function findKnowledgeSpace(spaces: KnowledgeSpace[], kbId: string) {
  for (const space of spaces) {
    for (const mode of ['wiki', 'graph'] as const) {
      if (space[`${mode}_kb_id`] === kbId || space.targets?.[mode]?.missing_knowledge_base_id === kbId) return { space, mode }
    }
  }
  let historical: { space: KnowledgeSpace; mode: 'wiki' | 'graph' } | null = null
  for (const space of spaces) {
    for (const mode of ['wiki', 'graph'] as const) {
      if (!space.targets?.[mode]?.previous_knowledge_base_ids?.includes(kbId)) continue
      if (historical) return null
      historical = { space, mode }
    }
  }
  return historical
}

const spacePath = (scope: string) => `/api/kb/spaces/${encodeURIComponent(scope)}`
export const getSpaces = () => get('/api/kb/spaces')
export const getSpace = (scope: string) => get(spacePath(scope))
export const createSpace = (data: { name: string; graph_enabled: boolean; wiki_kb_id?: string; graph_kb_id?: string }) => post('/api/kb/spaces', data)
export const updateSpace = (scope: string, data: Partial<Pick<KnowledgeSpace, 'name' | 'graph_enabled' | 'wiki_kb_id' | 'graph_kb_id'>>) => patch(spacePath(scope), data)
export const getSpaceProgress = (scope: string, page = 1) => get(`${spacePath(scope)}/progress`, { params: { page, page_size: 50 } })
export const submitSpace = (scope: string, targetModes?: ('wiki' | 'graph')[]) => post(`${spacePath(scope)}/submit`, targetModes ? { target_modes: targetModes } : {})
export const retrySpaceTarget = (scope: string, data: { target_mode: 'wiki' | 'graph'; stage: 'upload' | 'ingest' | 'graph'; task_id?: string; source_id?: string }) => post(`${spacePath(scope)}/retry`, data)
