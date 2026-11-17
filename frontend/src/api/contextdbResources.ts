import { downloadDocument, getDocument, nativeAPI } from './contextdb'
import { chunkAttachments, fileSourceImages, fileSourceLinks, sourceLink, uniqueSourceLinks, type KnowledgeAttachment, type SourceLink } from '@/utils/contextdbResources'
import { documentDisplayName } from '@/utils/contextdbDocumentName'
import { get } from '@/utils/request'

export interface DocumentResources {
  documentId: string
  name: string
  attachments: KnowledgeAttachment[]
  links: SourceLink[]
  warning: string
  sourceFile?: { blob: Blob; name: string; fileType: string }
}

export async function loadDocumentResources(documentId: string, kbId?: string): Promise<DocumentResources> {
  const { data: doc } = await getDocument(documentId)
  if (doc.id !== documentId || (kbId && doc.knowledge_base_id !== kbId)) throw new Error('来源文档不属于当前知识库')
  const result: DocumentResources = { documentId, name: documentDisplayName(doc), attachments: [], links: [], warning: '' }
  const chunks: any[] = []
  try {
    for (let offset = 0; ; ) {
      const { data } = await nativeAPI.get('knowledge/documents/chunks', { document_id: documentId, knowledge_base_id: kbId, offset, limit: 100 })
      if (data.document_id !== documentId) throw new Error('来源切片归属不一致')
      const batch = data.chunks || []
      chunks.push(...batch)
      offset += batch.length
      if (!batch.length || offset >= data.total) break
    }
  } catch (error: any) { result.warning = error?.message || '来源附件暂时无法读取' }
  result.attachments = chunkAttachments(chunks, documentId)
  const originalLink = sourceLink(doc.metadata?.url || '')
  if (originalLink) result.links.push(originalLink)
  const extension = String(doc.name || '').split('.').pop()?.toLowerCase() || ''
  try {
    // Read source links, not generated prose; this also preserves PDF/Office hyperlinks.
    if (['md', 'markdown', 'mdown', 'mkd', 'mdx', 'txt', 'html', 'htm', 'xhtml', 'docx', 'pptx', 'xlsx', 'epub', 'pdf', 'csv', 'tsv', 'json', 'xml'].includes(extension)) {
      const blob = await downloadDocument(documentId)
      if (['pdf', 'docx', 'pptx', 'xlsx', 'epub'].includes(extension)) result.sourceFile = { blob, name: doc.name, fileType: extension }
      try { result.links.push(...await fileSourceLinks(blob, doc.name || '', doc.metadata?.url || '')) }
      catch (e: any) { result.warning = [result.warning, e?.message || '来源链接暂时无法读取'].filter(Boolean).join('；') }
      result.attachments.push(...await fileSourceImages(blob, doc.name || '', documentId))
    }
  } catch (error: any) {
    result.warning = [result.warning, error?.message || '来源链接暂时无法读取'].filter(Boolean).join('；')
  }
  if (['md', 'markdown', 'mdown', 'mkd', 'mdx', 'html', 'htm', 'xhtml'].includes(extension)) {
    try {
      const { data } = await get(`/api/contextdb/documents/${encodeURIComponent(documentId)}/source-images`, { params: { knowledge_base_id: kbId } })
      if (data.document_id !== documentId) throw new Error('原件图片归属不一致')
      result.attachments.push(...(data.images || []).map((image: any, index: number) => {
        if (!/^[a-f\d]{64}$/i.test(image.image_key || '')) throw new Error('原件图片标识无效')
        return { type: 'image', source: 'source_inline', source_image_hash: image.image_key, description: image.description,
          document_id: documentId, chunk_index: -1, attachment_index: index }
      }))
    } catch (e: any) { result.warning = [result.warning, e?.message || '原件图片暂时无法读取'].filter(Boolean).join('；') }
  }
  result.links = uniqueSourceLinks(result.links)
  return result
}
