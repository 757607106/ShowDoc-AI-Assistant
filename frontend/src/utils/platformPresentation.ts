type Stage = 'task' | 'upload' | 'ingest' | 'review' | 'wiki' | 'graph' | 'revision' | 'issue'

const common: Record<string, string> = {
  pending: '等待处理', queued: '等待处理', running: '处理中', processing: '处理中',
  completed: '已完成', succeeded: '已完成', failed: '处理失败', partial: '部分失败',
  cancelled: '已取消', canceled: '已取消', cancelling: '取消中', submitted: '已提交',
  submitting: '提交中', uncertain: '结果待确认', rejected: '已拒绝', pending_review: '待人工评审',
}
const stages: Record<Stage, Record<string, string>> = {
  task: { completed: '检查完成' },
  upload: { pending: '等待提交', running: '提交中', completed: '提交完成', failed: '提交失败', skipped: '内容未变化' },
  ingest: { pending: '等待入库', uploading: '上传中', processing: '解析入库中', ai_reviewing: '评审中', pending_review: '待人工评审', succeeded: '已入库', failed: '入库失败', deleting: '删除中', deleted: '已删除' },
  review: { pending: '待评审', reviewed: '评审完成', pending_human: '待人工评审', auto_accepted: '自动通过', approved: '人工通过', rejected: '已拒绝', failed: '评审失败', superseded: '已被新评审替代' },
  wiki: { pending: '等待生成', compiling: '生成中', processing: '生成中', succeeded: '生成完成', failed: '生成失败', skipped: '已跳过' },
  graph: { pending: '等待构建', building: '构建中', processing: '构建中', succeeded: '构建完成', failed: '构建失败', disabled: '未启用', skipped: '已跳过' },
  revision: { pending: '待校验', pending_review: '待复核', validating: '校验中', approved: '已通过', published: '已发布', rejected: '已拒绝', superseded: '已替代' },
  issue: { open: '待处理', pending: '待处理', queued: '等待处理', applying: '修订中', resolved: '已解决', ignored: '已忽略', reopened: '已重开', review_required: '待人工复核', dismissed: '已忽略', closed: '已关闭', fixing: '修复中' },
}

export function stateLabel(value: unknown, stage: Stage): string {
  if (value == null || value === '') return '未返回'
  const key = String(value).toLowerCase()
  return stages[stage][key] || common[key] || '未知状态'
}

export function stateTheme(value: unknown): 'danger' | 'success' | 'warning' | 'default' {
  const key = String(value || '').toLowerCase()
  if (['failed', 'rejected'].includes(key)) return 'danger'
  if (['completed', 'succeeded', 'approved', 'auto_accepted', 'published', 'resolved'].includes(key)) return 'success'
  if (['partial', 'pending_review', 'pending_human'].includes(key)) return 'warning'
  return 'default'
}

export function permissionLabel(value: unknown): string {
  if (value == null || value === '') return '未返回'
  if (value === 'none') return '无权限'
  return ({ read: '只读', write: '读写', kb_manage: '管理', manage: '管理', all: '全部权限' } as Record<string, string>)[String(value)] || '未知权限'
}

export function memberRoleLabel(value: unknown): string {
  return ({ owner: '所有者', admin: '管理员', editor: '编辑者', contributor: '编辑者', viewer: '只读成员', member: '普通成员', group_admin: '组管理员' } as Record<string, string>)[String(value)] || '未知角色'
}

export function spaceName(scope: string, spaces: {scope: string; name: string}[]): string {
  const name = spaces.find(space => space.scope === scope)?.name
  return scope === 'default' && (!name || name === '默认知识空间') ? '默认知识库' : name || '名称未获取'
}

export function dateTime(value: unknown): string {
  if (!value) return '—'
  const date = new Date(String(value))
  return Number.isNaN(date.getTime()) ? '时间无效' : new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

export function contextdbDateTime(value: unknown): string {
  if (!value) return '-'
  const date = new Date(String(value))
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('zh-CN', { hour12: false })
}

export const reviewActionLabels: Record<string, string> = {
  confirm: '原样入库', force_accept: '强制接纳原文', accept_rewrite: '采纳重写',
  reject: '拒绝', reject_reupload: '要求重新上传', retract: '撤回', retry_review: '重新评审',
}

const contextdbTools: Record<string,string> = {
  'knowledge.list_bases':'查找知识库', 'knowledge.get_base':'查看知识库',
  'knowledge.create_base':'创建知识库', 'knowledge.update_base':'修改知识库', 'knowledge.delete_base':'删除知识库',
  'knowledge.list_documents':'查找文档', 'knowledge.get_document':'查看文档',
  'knowledge.create_text_document':'创建文档', 'knowledge.delete_document':'删除文档',
  'knowledge.search':'检索知识', 'knowledge.wiki_search':'查找 Wiki 页面',
  'knowledge.list_graph_entities':'查找图谱实体', 'knowledge.get_graph':'查看知识图谱',
  'knowledge.list_entity_chunks':'查看实体来源',
  list_governance_releases:'查看提交记录', get_capture_provenance:'查看资料来源',
  rerun_collection:'重新采集资料',
}
export function contextdbToolLabel(value:string):string|undefined { return Object.hasOwn(contextdbTools,value)?contextdbTools[value]:undefined }
