export const CONTEXTDB_REVIEW_FORMAT_NOTICE = 'TXT、Markdown、PDF、DOC、DOCX 使用官方知识评审；开启评审时 HTML 先转换为 Markdown。其他不支持评审的格式会被阻止提交；关闭评审时按官方支持的格式入库。上传或入库成功不代表评审和编译均已完成。'

export function supportsOfficialReview(document: { name?: string; file_name?: string; document_name?: string; source_type?: string }): boolean {
  const name = document.name || document.file_name || document.document_name || ''
  const extension = name.match(/\.([^.]+)$/)?.[1]?.toLowerCase()
  if (extension) return ['txt', 'md', 'markdown', 'pdf', 'doc', 'docx'].includes(extension)
  return ['text', 'memory_promotion'].includes(document.source_type || '')
}
