import assert from 'node:assert/strict'
import test from 'node:test'
import { currentTask, materialErrorLabel, taskFilter, taskSourceName, taskStatusLabel, type MaterialTask } from './materialTasks.ts'

const capture: MaterialTask = {task_id:'capture', scope:'a', kind:'crawl', entry:'showdoc', status:'completed', phase:'submitted', submission_id:'snapshot', sync_task_id:'latest'}
const submission: MaterialTask = {task_id:'latest', scope:'a', kind:'ctxdb_sync', status:'running', phase:'syncing', release_id:'snapshot', source_task_id:'capture', progress:50}

test('the displayed stage follows the exact associated submission only', () => {
  const linked = {...capture, submission_task:submission}
  assert.equal(currentTask(linked), submission)
  assert.equal(taskStatusLabel(currentTask(linked)), '提交中')
  assert.equal(taskFilter(linked), 'active')
  const stale = {...linked, submission_task:{...submission, task_id:'older'}}
  assert.equal(currentTask(stale), stale)
  assert.equal(currentTask(submission), submission)
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

test('material labels use business names and never echo unrecognized diagnostics', () => {
  assert.equal(taskSourceName({...capture, entry:'old_internal_crawler', entry_name:'old_internal_crawler'}), '资料采集')
  assert.equal(taskSourceName({...capture, entry_name:'ShowDoc'}), 'ShowDoc')
  assert.equal(materialErrorLabel('wiki/internal-id: COMMON_BAD_REQUEST: node not found (errorCode=1001)'), '找不到对应的资料')
  assert.equal(materialErrorLabel('源正文为空'), '原文为空')
  assert.equal(materialErrorLabel('读取超时'), '处理超时')
  assert.equal(materialErrorLabel('EIO at /runtime/jobs/internal-id'), '')
})
