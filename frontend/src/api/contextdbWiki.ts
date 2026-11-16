import { nativeAPI } from './contextdb'

export type WikiPageType = 'entity' | 'concept' | 'synthesis' | 'comparison' | 'category' | 'summary'
export interface WikiLink { page_id: string; title?: string; display_title?: string; slug?: string; page_type?: WikiPageType }
export interface WikiPage extends WikiLink {
  title: string
  page_type: WikiPageType
  version: number
  content?: string
  summary?: string
  published?: boolean
  run_state?: string
  head_revision_id?: string
  parent_page_id?: string | null
  category_path?: string[]
  ancestors?: WikiLink[]
  links?: WikiLink[]
  backlinks?: WikiLink[]
  links_total?: number
  backlinks_total?: number
  links_truncated?: boolean
  backlinks_truncated?: boolean
  source_document_ids?: string[]
  updated_at?: string
  created_at?: string
}
export interface WikiCursorPage<T> { items: T[]; next_cursor?: string | null; limit?: number; total?: number }
export interface WikiIndexGroup extends WikiCursorPage<WikiPage> { type: WikiPageType; total: number }
export interface WikiIndex { intro: string; version: number; groups: WikiIndexGroup[] }
export interface WikiRevision {
  revision_id: string
  page_id: string
  base_revision_id?: string
  edit_source?: string
  review_status?: string
  review_reason?: string
  created_at?: string
}
export interface WikiRevisionDiff {
  revision_id: string
  base_revision_id?: string
  page_id: string
  review_status?: string
  diff: { hunks: { op: 'eq' | 'add' | 'del'; text: string }[]; added_count: number; removed_count: number; truncated: boolean }
}
export interface WikiMutation { page_id?: string; version?: number; event_id?: string; revision_id?: string; [key: string]: unknown }
export interface WikiEvent { event_id?: string; status?: string; error_message?: string; error?: unknown; [key: string]: unknown }
export interface WikiCompileRun {
  document_id: string
  document_name?: string
  name?: string
  run_state: string
  event_id?: string
  updated_at?: string
  [key: string]: unknown
}
export type WikiCompileSummary = Record<string, number>
export interface WikiCompileRuns extends WikiCursorPage<WikiCompileRun> {
  summary: WikiCompileSummary
  wiki_compile_paused: boolean
}
export interface WikiIssue {
  issue_id: string
  page_id: string
  version: number
  status: string
  severity?: string
  issue_type?: string
  description?: string
  title?: string
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}
export interface WikiEvidence { side?: string; quote?: string; document_id?: string; chunk_id?: string; scope?: unknown }
export type WikiIssueChoice = 'use_old' | 'use_new' | 'keep_both' | 'fix' | 'manual_edit' | 'rerun_merge'
export interface WikiIssueDetail extends WikiIssue {
  body?: Record<string, unknown> & { recheck_uncertain?: boolean }
  evidence?: Record<string, WikiEvidence[]>
  recommended_action?: string
  task_items?: Record<string, unknown>[]
  recheck_status?: string
}
export interface WikiIssueTaskItem {
  issue_id: string
  expected_version: number
  choice: WikiIssueChoice
  side?: 'old' | 'new' | 'both'
  note?: string
  manual_content?: string
}
export interface WikiIssueTask {
  event_id: string
  status?: string
  total_items?: number
  succeeded_items?: number
  failed_items?: number
  items?: { issue_id: string; status: string; error_code?: string; error_message?: string; resolution_revision_id?: string }[]
}
type Cursor = { cursor?: string; limit?: number }
const path = (resource: string) => `knowledge/wiki/${resource}`

export async function listWikiPages(kbId: string, params: Cursor & { parent_page_id?: string; page_type?: 'category' } = {}): Promise<WikiCursorPage<WikiPage>> {
  return (await nativeAPI.get(path('pages'), { knowledge_base_id: kbId, ...params })).data
}
export async function getWikiIndex(kbId: string, params: Cursor & { types?: string } = {}): Promise<WikiIndex> {
  return (await nativeAPI.get(path('index'), { knowledge_base_id: kbId, ...params })).data
}
export async function getWikiPage(kbId: string, pageId: string): Promise<WikiPage> {
  return (await nativeAPI.get(path('pages/detail'), { knowledge_base_id: kbId, page_id: pageId })).data
}
export async function getWikiPageByReference(kbId: string, reference: string): Promise<WikiPage> {
  if (/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(reference)) return getWikiPage(kbId, reference)
  const search = await searchWikiPages(kbId, reference, { limit: 50 })
  const match = search.items.find(page => page.slug === reference)
  if (match) return getWikiPage(kbId, match.page_id)
  // Legacy citations contain slugs; a capped search is not a complete slug lookup.
  for (const type of ['entity', 'concept', 'synthesis', 'comparison']) {
    let cursor: string | undefined
    const seen = new Set<string>()
    do {
      const index = await getWikiIndex(kbId, { types: type, limit: 200, cursor })
      const group = index.groups.find(group => group.type === type)
      const page = group?.items.find(page => page.slug === reference)
      if (page) return getWikiPage(kbId, page.page_id)
      cursor = group?.next_cursor || undefined
      if (cursor && seen.has(cursor)) throw new Error('页面索引分页异常，请刷新后重试')
      if (cursor) seen.add(cursor)
    } while (cursor)
  }
  throw new Error('该页面已不可读或链接已失效，请在 Wiki 索引中核对')
}
export async function searchWikiPages(kbId: string, query: string, params: { mode?: 'keyword' | 'regex'; limit?: number } = {}): Promise<WikiCursorPage<WikiPage>> {
  return (await nativeAPI.get(path('search'), { knowledge_base_id: kbId, query, ...params })).data
}
export async function getWikiSummary(kbId: string, documentId: string): Promise<WikiPage | null> {
  return (await nativeAPI.get(path('summary'), { knowledge_base_id: kbId, document_id: documentId })).data
}
export async function createWikiPage(kbId: string, data: { title: string; content: string; page_type?: 'entity' | 'concept'; parent_page_id?: string; comment?: string }): Promise<WikiMutation> {
  return (await nativeAPI.post(path('pages'), { knowledge_base_id: kbId, ...data })).data
}
export async function updateWikiPage(kbId: string, pageId: string, data: { content: string; expected_version: number; comment?: string }): Promise<WikiMutation> {
  return (await nativeAPI.put(path('pages'), { knowledge_base_id: kbId, page_id: pageId, ...data })).data
}
export async function createWikiDirectory(kbId: string, data: { title: string; parent_page_id?: string }): Promise<WikiMutation> {
  return (await nativeAPI.post(path('directories'), { knowledge_base_id: kbId, ...data })).data
}
type Organize = { expected_version: number; title?: string; parent_page_id?: string; expected_parent_version?: number }
export async function organizeWikiPage(kbId: string, pageId: string, data: Organize & { action: 'rename' | 'move' | 'archive' }): Promise<WikiMutation> {
  return (await nativeAPI.post(path('pages/actions'), { knowledge_base_id: kbId, page_id: pageId, ...data })).data
}
export async function organizeWikiDirectory(kbId: string, directoryId: string, data: Organize & { action: 'rename' | 'move' | 'delete' }): Promise<WikiMutation> {
  return (await nativeAPI.post(path('directories/actions'), { knowledge_base_id: kbId, directory_id: directoryId, ...data })).data
}
export async function deleteWikiPage(kbId: string, pageId: string): Promise<WikiMutation> {
  const query = new URLSearchParams({ knowledge_base_id: kbId, page_id: pageId })
  return (await nativeAPI.del(`${path('pages')}?${query}`)).data
}
export async function listWikiRevisions(kbId: string, pageId: string, params: Cursor = {}): Promise<WikiCursorPage<WikiRevision>> {
  return (await nativeAPI.get(path('revisions'), { knowledge_base_id: kbId, page_id: pageId, ...params })).data
}
export async function getWikiRevisionDiff(kbId: string, revisionId: string, baseRevisionId?: string): Promise<WikiRevisionDiff> {
  return (await nativeAPI.get(path('revisions/diff'), { knowledge_base_id: kbId, revision_id: revisionId, base_revision_id: baseRevisionId })).data
}
export async function listWikiCompileRuns(kbId: string, params: Cursor & { status?: string } = {}): Promise<WikiCompileRuns> {
  return (await nativeAPI.get(path('compile-runs'), { knowledge_base_id: kbId, ...params })).data
}
export async function controlWikiCompileRuns(kbId: string, data: { action: 'pause' | 'resume' | 'recompile_affected' | 'retry_failed'; document_id?: string; event_id?: string }): Promise<Record<string, unknown> & { event_id?: string }> {
  return (await nativeAPI.post(path('compile-runs/actions'), { knowledge_base_id: kbId, ...data })).data
}
export async function listWikiIssues(kbId: string, params: Cursor & { page_id?: string; status?: string; severity?: string; issue_type?: string } = {}): Promise<WikiCursorPage<WikiIssue>> {
  return (await nativeAPI.get(path('issues'), { knowledge_base_id: kbId, ...params })).data
}
export async function getWikiIssue(kbId: string, issueId: string): Promise<WikiIssueDetail> {
  return (await nativeAPI.get(path('issues/detail'), { knowledge_base_id: kbId, issue_id: issueId })).data
}
export async function actOnWikiIssue(kbId: string, data: { issue_id: string; expected_version: number; action: 'ignore' | 'close_not_issue' | 'reopen'; reason?: string }): Promise<WikiIssue> {
  return (await nativeAPI.post(path('issues/actions'), { knowledge_base_id: kbId, ...data })).data
}
export async function createWikiIssueTask(kbId: string, data: { idempotency_key: string; items: WikiIssueTaskItem[] }): Promise<WikiIssueTask> {
  return (await nativeAPI.post(path('issues/tasks'), { knowledge_base_id: kbId, ...data })).data
}
export async function getWikiIssueTask(kbId: string, eventId: string): Promise<WikiIssueTask> {
  return (await nativeAPI.get(path('issue-tasks/detail'), { knowledge_base_id: kbId, event_id: eventId })).data
}
export async function getWikiEvent(eventId: string): Promise<WikiEvent> {
  return (await nativeAPI.get(`event/${encodeURIComponent(eventId)}`)).data
}
