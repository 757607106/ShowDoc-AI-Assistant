import assert from 'node:assert/strict'
import test from 'node:test'
import { knowledgeNeedsStatusPolling } from './wikiStatusRefresh.ts'

test('document polling continues for parsing and pending summaries, and stops at terminal states', () => {
  for (const parse_status of ['pending', 'processing', 'finalizing']) assert.equal(knowledgeNeedsStatusPolling({parse_status}), true)
  assert.equal(knowledgeNeedsStatusPolling({parse_status:'completed',summary_status:'processing'}), true)
  assert.equal(knowledgeNeedsStatusPolling({parse_status:'completed',summary_status:'completed'}), false)
  assert.equal(knowledgeNeedsStatusPolling({parse_status:'failed'}), false)
})
