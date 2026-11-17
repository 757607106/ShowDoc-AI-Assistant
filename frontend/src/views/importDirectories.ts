export interface ImportDirectory {
  knowledge_base_id: string
  node_id: string
  root_name: string
}
export interface DirectoryPreviewNode { value: string; label: string; children?: DirectoryPreviewNode[] }

export function importDirectories(value: unknown): ImportDirectory[] {
  if (!Array.isArray(value)) return []
  const seen = new Set<string>()
  return value.filter((item): item is ImportDirectory => {
    if (!item || !['knowledge_base_id', 'node_id', 'root_name'].every(key => typeof item[key] === 'string' && item[key].trim())) return false
    const key = `${item.knowledge_base_id}:${item.node_id}`
    if (seen.has(key)) return false
    seen.add(key); return true
  })
}

export function directoryPreview(rootName: string, pages: { page_id: string | number; page_title?: string; directory_path?: string[] }[]): DirectoryPreviewNode[] {
  const root: DirectoryPreviewNode = { value: 'root', label: rootName, children: [] }
  for (const page of pages) {
    let parent = root
    for (const [index, name] of (page.directory_path || []).entries()) {
      const value = `directory:${JSON.stringify(page.directory_path!.slice(0, index + 1))}`
      let child = parent.children!.find(item => item.value === value)
      if (!child) { child = { value, label: name, children: [] }; parent.children!.push(child) }
      parent = child
    }
    parent.children!.push({ value: `page:${page.page_id}`, label: page.page_title || String(page.page_id) })
  }
  return [root]
}
