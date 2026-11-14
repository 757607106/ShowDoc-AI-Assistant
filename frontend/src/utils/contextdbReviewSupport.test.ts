import assert from 'node:assert/strict'
import test from 'node:test'
import { supportsOfficialReview } from './contextdbReviewSupport.ts'

test('only officially documented review formats are presented as supported', () => {
  for (const name of ['manual.TXT', 'manual.md', 'manual.markdown', 'manual.PDF', 'manual.doc', 'manual.docx']) {
    assert.equal(supportsOfficialReview({ name, source_type: 'file' }), true, name)
  }
  for (const name of ['page.html', 'slides.pptx', 'table.xlsx', 'image.png', 'audio.mp3', 'video.mp4', 'data.json', 'unknown']) {
    assert.equal(supportsOfficialReview({ name, source_type: 'file' }), false, name)
  }
  assert.equal(supportsOfficialReview({ source_type: 'text' }), true)
  assert.equal(supportsOfficialReview({ file_name: 'import.html', source_type: 'text' }), false)
  assert.equal(supportsOfficialReview({ document_name: 'source.pdf' }), true)
  assert.equal(supportsOfficialReview({}), false)
})
