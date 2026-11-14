export const CONTEXTDB_REVIEW_FORMAT_NOTICE = 'ContextDB 官方确认的知识评审格式为 TXT、Markdown、PDF、DOC、DOCX；HTML、PPT、Excel、图片和音视频等资料的治理支持尚未确认。上传或入库成功不代表已完成知识治理。'

export function supportsOfficialReview(document: { name?: string; file_name?: string; document_name?: string; source_type?: string }): boolean {
  const name = document.name || document.file_name || document.document_name || ''
  const extension = name.match(/\.([^.]+)$/)?.[1]?.toLowerCase()
  if (extension) return ['txt', 'md', 'markdown', 'pdf', 'doc', 'docx'].includes(extension)
  return ['text', 'memory_promotion'].includes(document.source_type || '')
}
