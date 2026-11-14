// Review pages contain parsed text, including for PDF and Office source files.
export async function reviewEditableContent(review: any, readPage: (id: string, page: number) => Promise<any>) {
  if (typeof review.rewritten_content === 'string' && review.rewritten_content) return review.rewritten_content
  const parts: string[] = []
  let totalPages = 1, totalChars: number | undefined
  for (let page = 1; page <= totalPages; page++) {
    const detail = (await readPage(review.review_id, page)).review
    const content = detail?.original_content
    if (['review_id', 'document_id', 'knowledge_base_id'].some(key => !review[key] || detail?.[key] !== review[key]) ||
        !content || content.page !== page || !Number.isInteger(content.total_pages) || content.total_pages < 1 ||
        !Number.isInteger(content.total_chars) || content.total_chars < 1 || typeof content.text !== 'string' || !content.text.length ||
        (page > 1 && (content.total_pages !== totalPages || content.total_chars !== totalChars))) {
      throw new Error('评审原文分页不完整或已变化，请重新读取评审后再编辑')
    }
    totalPages = content.total_pages
    totalChars = content.total_chars
    parts.push(content.text)
  }
  const text = parts.join('')
  if (Array.from(text).length !== totalChars) throw new Error('评审原文不完整，请重试读取后再编辑')
  return text
}
