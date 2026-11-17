import assert from 'node:assert/strict'
import test from 'node:test'
import { currentTask, foldTaskRows, taskFilter, taskStatusLabel, type MaterialTask } from './materialTasks.ts'

const capture: MaterialTask = {task_id:'capture', scope:'a', kind:'crawl', entry:'showdoc', status:'completed', phase:'submitted', submission_id:'snapshot', sync_task_id:'latest'}
const submission: MaterialTask = {task_id:'latest', scope:'a', kind:'ctxdb_sync', status:'running', phase:'syncing', release_id:'snapshot', source_task_id:'capture', progress:50}

test('only the exact latest associated submission folds into its capture; older attempts remain accessible', () => {
  const older = {...submission, task_id:'older', status:'failed'}
  const rows = foldTaskRows([submission, older, capture])
  assert.deepEqual(rows.map(row => row.task_id), ['older', 'capture'])
  assert.equal(rows[1].submission_task?.task_id, 'latest')
  assert.equal(taskStatusLabel(currentTask(rows[1])), '提交中')
  assert.equal(taskFilter(rows[1]), 'active')
  assert.equal(capture.submission_task, undefined, 'folding must not mutate fetched records')
})

test('scope or release mismatch never hides a submission, and page boundaries keep both records reachable', () => {
  for (const changed of [{...submission, scope:'b'}, {...submission, release_id:'another'}, {...submission, source_task_id:'other'}]) {
    assert.equal(foldTaskRows([capture, changed]).length, 2)
  }
  assert.equal(foldTaskRows([submission])[0].task_id, 'latest')
  const parentOnly = foldTaskRows([{...capture, submission_task:submission}])[0]
  assert.equal(currentTask(parentOnly).progress, 50)
  const unlinked = {...capture, sync_task_id:null}
  assert.equal(currentTask(unlinked), unlinked)
})

test('captured, queued, submission failures, and cloud completion remain different stages', () => {
  assert.equal(taskStatusLabel({...capture, phase:'completed'}), '采集完成')
  assert.equal(taskStatusLabel({...capture, entry:'file', phase:'completed'}), '检查完成')
  assert.equal(taskStatusLabel(capture), '已排队提交')
  assert.equal(taskStatusLabel({...capture, phase:'submission_failed'}), '自动提交失败')
  assert.equal(taskStatusLabel({...submission, status:'completed', phase:'submitted'}), '提交完成')
  assert.equal(taskFilter({...capture, submission_task:{...submission, status:'partial'}}), 'action')
  assert.equal(taskFilter({...capture, status:'partial', submission_task:submission}), 'action')
  assert.equal(taskFilter({...capture, status:'cancelled', submission_task:submission}), 'done')
})
