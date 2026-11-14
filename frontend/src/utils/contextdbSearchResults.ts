export function splitKnowledgeResults(items: any[]) {
  const graph: any[] = [], documents: any[] = []
  for (const item of items) {
    if (item.tag_kwd?.includes('graphrag') || String(item.chunk_id || '').startsWith('graph:') || item.type === 'graph_context') {
      graph.push(item)
    } else {
      documents.push({...item, content:item.content ?? item.content_with_weight ?? '',
        doc_name:item.doc_name || item.document_name || item.docnm_kwd,
        doc_id:item.doc_id || item.document_id})
    }
  }
  return {graph, documents}
}
