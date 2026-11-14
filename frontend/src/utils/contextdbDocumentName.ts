type DocumentName = { name?: string; metadata?: { title?: unknown; filename?: unknown } | null }

export function documentDisplayName(doc: DocumentName): string {
  const filename = typeof doc.metadata?.filename === 'string' ? doc.metadata.filename.trim() : ''
  if (filename) return filename
  const title = typeof doc.metadata?.title === 'string' ? doc.metadata.title.trim() : ''
  if (!title) return doc.name || ''
  const extension = doc.name?.match(/\.[a-z\d]{1,12}$/i)?.[0] || ''
  return extension && !title.toLowerCase().endsWith(extension.toLowerCase()) ? title + extension : title
}

export function graphDocumentLabel(label: string, documents: DocumentName[]): string {
  const document = documents.find(item => item.name === label)
  const title = typeof document?.metadata?.title === 'string' ? document.metadata.title.trim() : ''
  return document ? title || documentDisplayName(document) : label
}
