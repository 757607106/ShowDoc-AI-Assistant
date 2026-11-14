import assert from 'node:assert/strict'
import test from 'node:test'
import { reviewEditableContent } from './reviewContent.ts'

const review = { review_id: 'review-a', document_id: 'source.pdf', knowledge_base_id: 'kb-a' }
const detail = (page: number, text: string, total_pages = 2, total_chars = 6) => ({
  review: { ...review, original_content: { page, text, total_pages, total_chars } },
})

test('parsed review pages join without separators and preserve Unicode from binary sources', async () => {
  const pages: number[] = []
  const text = await reviewEditableContent(review, async (id, page) => {
    assert.equal(id, review.review_id); pages.push(page)
    return detail(page, page === 1 ? '标题🙂' : '\n正文')
  })
  assert.equal(text, '标题🙂\n正文'); assert.deepEqual(pages, [1, 2])
  assert.equal(await reviewEditableContent({ ...review, rewritten_content: '官方完整重写稿' }, async () => assert.fail()), '官方完整重写稿')
})

test('missing, changed or incomplete review pages cannot become a replacement draft', async () => {
  const invalid = [
    { review: { ...review, document_id: 'another-source', original_content: detail(2, '正文').review.original_content } },
    detail(1, '正文'), detail(2, '', 2, 6), detail(2, '正文', 3, 6), detail(2, '正文', 2, 8),
    { review: { ...review, original_content: null } }, detail(2, '文'),
  ]
  for (const second of invalid) {
    await assert.rejects(reviewEditableContent(review, async (_id, page) => page === 1 ? detail(1, '第一段') : second), /原文/)
  }
  await assert.rejects(reviewEditableContent(review, async (_id, page) => {
    if (page === 2) throw new Error('page unavailable')
    return detail(1, '第一段')
  }), /page unavailable/)
})
