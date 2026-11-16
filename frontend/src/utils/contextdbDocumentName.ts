type DocumentName = { name?: string; document_name?: string; display_name?: unknown; document_display_name?: unknown;
  metadata?: { title?: unknown; filename?: unknown } | null }

export function documentDisplayName(doc?: DocumentName | null): string {
  if (!doc) return ''
  for (const value of [doc.document_display_name, doc.display_name]) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  const filename = typeof doc.metadata?.filename === 'string' ? doc.metadata.filename.trim() : ''
  if (filename) return filename
  const title = typeof doc.metadata?.title === 'string' ? doc.metadata.title.trim() : ''
  const name = doc.name || doc.document_name || ''
  if (!title) return name
  const extension = name.match(/\.[a-z\d]{1,12}$/i)?.[0] || ''
  return extension && !title.toLowerCase().endsWith(extension.toLowerCase()) ? title + extension : title
}

export function graphDocumentLabel(label: string, documents: DocumentName[]): string {
  const document = documents.find(item => item.name === label)
  const display = [document?.document_display_name, document?.display_name].find(value => typeof value === 'string' && value.trim())
  const title = typeof document?.metadata?.title === 'string' ? document.metadata.title.trim() : ''
  return typeof display === 'string' ? display.trim() : document ? title || documentDisplayName(document) : label
}
