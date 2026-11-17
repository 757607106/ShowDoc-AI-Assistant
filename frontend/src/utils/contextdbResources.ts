import { Marked } from 'marked'

export interface KnowledgeAttachment {
  type: string
  asset_id?: string
  description?: string
  source?: string
  start_ms?: number | null
  end_ms?: number | null
  document_id: string
  chunk_index: number
  attachment_index: number
  source_image_hash?: string
  embedded_key?: string
  source_blob?: Blob
}

export interface SourceLink { url: string; text: string }

export function attachmentPath(item: KnowledgeAttachment, kbId?: string): string {
  const path = item.source_image_hash
    ? `/api/contextdb/documents/${encodeURIComponent(item.document_id)}/source-images/${item.source_image_hash}`
    : item.type === 'image' && item.asset_id
    ? `/api/contextdb/assets/${encodeURIComponent(item.asset_id)}`
    : `/api/contextdb/documents/${encodeURIComponent(item.document_id)}/attachments/${item.chunk_index}/${item.attachment_index}`
  return kbId ? `${path}?knowledge_base_id=${encodeURIComponent(kbId)}` : path
}

export function chunkAttachments(chunks: any[], documentId: string): KnowledgeAttachment[] {
  const seen = new Set<string>()
  return chunks.flatMap(chunk => (Array.isArray(chunk.attachments) ? chunk.attachments : []).flatMap((item: any, index: number) => {
    if (!['image', 'audio', 'video'].includes(item?.type)) return []
    if (!item.asset_id && (!Number.isInteger(chunk.chunk_index) || chunk.chunk_index < 0)) return []
    const key = item.asset_id || `${item.type}:${chunk.chunk_index}:${index}`
    if (seen.has(key)) return []
    seen.add(key)
    // Signed URLs expire; keep only authenticated official asset coordinates.
    return [{ type: item.type, asset_id: item.asset_id, description: item.description, source: item.source,
      start_ms: item.start_ms, end_ms: item.end_ms, document_id: documentId,
      chunk_index: chunk.chunk_index, attachment_index: index }]
  }))
}

export function sourceLink(url: string, text = '', base = ''): SourceLink | null {
  try {
    url = url.trim()
    const target = base ? new URL(url, base) : new URL(url)
    if (!['https:', 'http:', 'mailto:', 'tel:'].includes(target.protocol)) return null
    if (!url || url.startsWith('#')) return null
    return { url: target.href, text: text.trim() || target.href }
  } catch { return null }
}

export function uniqueSourceLinks(links: SourceLink[]): SourceLink[] {
  return [...new Map(links.map(link => [link.url, link])).values()]
}

export function markdownSourceLinks(text: string, base = ''): SourceLink[] {
  const links: SourceLink[] = []
  const marked = new Marked({ gfm: true })
  marked.walkTokens(marked.lexer(text), token => {
    if (token.type === 'link') {
      // Match the browser's single entity decode of a rendered Markdown href.
      const anchor = new DOMParser().parseFromString(`<a href="${token.href.replace(/"/g, '&quot;')}"></a>`, 'text/html').getElementsByTagName('a')[0]
      const item = sourceLink(anchor?.getAttribute('href') || '', token.text, base)
      if (item) links.push(item)
    } else if (token.type === 'html') {
      links.push(...htmlSourceLinks(token.text, base))
    }
  })
  return uniqueSourceLinks(links)
}

export function htmlSourceLinks(text: string, base = ''): SourceLink[] {
  const doc = new DOMParser().parseFromString(text, 'text/html')
  return uniqueSourceLinks([...doc.querySelectorAll('a[href]')].flatMap(node => {
    const item = sourceLink(node.getAttribute('href') || '', node.textContent || '', base)
    return item ? [item] : []
  }))
}

export async function fileSourceLinks(blob: Blob, fileName: string, base = ''): Promise<SourceLink[]> {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (['md', 'markdown', 'mdown', 'mkd', 'mdx'].includes(ext)) return markdownSourceLinks(await blob.text(), base)
  if (['html', 'htm', 'xhtml'].includes(ext)) return htmlSourceLinks(await blob.text(), base)
  if (['docx', 'pptx', 'xlsx', 'epub'].includes(ext)) {
    const { default: JSZip } = await import('jszip')
    const zip = await JSZip.loadAsync(await blob.arrayBuffer())
    const links: SourceLink[] = []
    for (const entry of Object.values(zip.files)) {
      if (entry.dir) continue
      if (ext === 'epub' && /\.(?:xhtml|html|htm)$/i.test(entry.name)) {
        links.push(...htmlSourceLinks(await entry.async('string'), base))
      }
      if (!entry.name.endsWith('.rels')) continue
      const xml = new DOMParser().parseFromString(await entry.async('string'), 'application/xml')
      for (const node of Array.from(xml.getElementsByTagNameNS('*', 'Relationship'))) {
        if (node.getAttribute('TargetMode') !== 'External' || !node.getAttribute('Type')?.endsWith('/hyperlink')) continue
        const item = sourceLink(node.getAttribute('Target') || '', '', base)
        if (item) links.push(item)
      }
    }
    return uniqueSourceLinks(links)
  }
  if (ext === 'pdf') {
    const { loadPdfJs } = await import('../components/source-preview/pdfjsLoader')
    const pdfjs = await loadPdfJs()
    const task = pdfjs.getDocument({ data: new Uint8Array(await blob.arrayBuffer()) })
    try {
      const pdf = await task.promise
      const links: SourceLink[] = []
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i)
        for (const annotation of await page.getAnnotations()) {
          const item = typeof annotation.url === 'string' ? sourceLink(annotation.url, '', base) : null
          if (item) links.push(item)
        }
        page.cleanup()
      }
      return uniqueSourceLinks(links)
    } finally { await task.destroy() }
  }
  if (blob.type.startsWith('text/') || ['txt', 'csv', 'tsv', 'json', 'xml'].includes(ext)) {
    return uniqueSourceLinks((await blob.text()).match(/https?:\/\/[^\s<>"']+/g)?.flatMap(url => {
      const item = sourceLink(url)
      return item ? [item] : []
    }) || [])
  }
  return []
}

export async function fileSourceImages(blob: Blob, fileName: string, documentId: string): Promise<KnowledgeAttachment[]> {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (!['docx', 'pptx', 'xlsx', 'epub'].includes(ext)) return []
  const { default: JSZip } = await import('jszip')
  const zip = await JSZip.loadAsync(await blob.arrayBuffer()), images: KnowledgeAttachment[] = []
  for (const entry of Object.values(zip.files)) {
    if (entry.dir || !/\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?)$/i.test(entry.name)) continue
    const bytes = await entry.async('uint8array')
    const imageExt = entry.name.split('.').pop()!.toLowerCase().replace(/^jpg$/, 'jpeg').replace(/^tif$/, 'tiff')
    images.push({ type: 'image', source: 'source_embedded', embedded_key: entry.name,
      source_blob: new Blob([new Uint8Array(bytes)], { type: `image/${imageExt === 'svg' ? 'svg+xml' : imageExt}` }),
      document_id: documentId, chunk_index: -1, attachment_index: images.length })
  }
  return images
}
