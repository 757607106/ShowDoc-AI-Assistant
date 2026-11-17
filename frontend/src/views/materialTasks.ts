import { stateLabel } from '../utils/platformPresentation'

export interface MaterialTask {
  task_id: string
  scope: string
  kind?: string
  status: string
  phase?: string
  entry?: string
  entry_name?: string
  source_name?: string
  message?: string
  start_time?: string
  progress?: number
  completed_pages?: number
  total_pages?: number
  failed_pages?: number
  skipped_pages?: number
  sync_task_id?: string | null
  source_task_id?: string | null
  release_id?: string | null
  submission_id?: string | null
  submission_task?: MaterialTask | null
  submit_available?: boolean
  download_available?: boolean
  [key: string]: any
}

export type TaskFilter = 'all' | 'active' | 'action' | 'done'

export function foldTaskRows(tasks: MaterialTask[]): MaterialTask[] {
  const parents = new Map(tasks.filter(task => task.kind !== 'ctxdb_sync').map(task => [task.task_id, task]))
  const linked = new Map<string, MaterialTask>()
  for (const task of tasks) {
    if (task.kind !== 'ctxdb_sync' || !task.source_task_id) continue
    const parent = parents.get(task.source_task_id)
    if (parent?.sync_task_id === task.task_id && parent.scope === task.scope && parent.submission_id === task.release_id) {
      linked.set(parent.task_id, task)
    }
  }
  const hidden = new Set([...linked.values()].map(task => task.task_id))
  return tasks.filter(task => !hidden.has(task.task_id)).map(task => {
    const child = linked.get(task.task_id) || task.submission_task
    return child && child.task_id === task.sync_task_id ? {...task, submission_task: child} : task
  })
}

export function currentTask(task: MaterialTask): MaterialTask {
  const child = task.submission_task
  return task.kind !== 'ctxdb_sync' && task.status === 'completed' && child && child.task_id === task.sync_task_id ? child : task
}

export function taskFilter(task: MaterialTask): Exclude<TaskFilter, 'all'> {
  const stage = currentTask(task)
  if (stage.phase === 'submission_failed' || ['failed', 'partial'].includes(stage.status)) return 'action'
  if (stage.status === 'cancelled') return 'done'
  if (['pending', 'running', 'cancelling'].includes(stage.status) || (stage.kind !== 'ctxdb_sync' && stage.phase === 'submitted')) return 'active'
  return 'done'
}

export function taskStatusLabel(task: MaterialTask): string {
  if (task.kind === 'ctxdb_sync') return task.phase === 'submitted' ? '提交完成' : stateLabel(task.status, 'upload')
  if (task.phase === 'submission_failed') return '自动提交失败'
  if (task.phase === 'submitted') return '已排队提交'
  if (task.status === 'completed') return task.entry === 'file' ? '检查完成' : '采集完成'
  return stateLabel(task.status, 'task')
}

export function taskSourceName(task: MaterialTask): string {
  return task.source_name || (task.kind === 'ctxdb_sync' ? '知识库资料提交' : task.entry_name || '资料采集')
}
