/**
 * Tool Icons Utility
 * Maps match types to icons and tool names to display labels.
 */
import i18n from '@/i18n'

const t = (key: string) => i18n.global.t(key)

// Match type internal keys for icon mapping
const matchTypeIconKeys: Record<string, string> = {
    vector: '🎯',
    keyword: '🔤',
    adjacent: '📌',
    history: '📜',
    parent: '⬆️',
    relation: '🔗',
    graph: '🕸️',
};

// Match type to icon mapping (keys match backend API response)
export const matchTypeIcons: Record<string, string> = {
    'Vector Match': '🎯',
    'Keyword Match': '🔤',
    'Adjacent Chunk Match': '📌',
    'History Match': '📜',
    'Parent Chunk Match': '⬆️',
    'Relation Chunk Match': '🔗',
    'Graph Match': '🕸️',
};

// Get icon for a match type
export function getMatchTypeIcon(matchType: string): string {
    return matchTypeIcons[matchType] || matchTypeIconKeys[matchType] || '📍';
}

// Tool name to i18n key mapping
const toolDisplayNameKeys: Record<string, string> = {
    multi_kb_search: 'tools.multiKbSearch',
    search_knowledge: 'tools.searchKnowledge',
    read_document: 'tools.readDocument',
    list_documents: 'tools.listDocuments',
    get_chunk_detail: 'tools.getChunkDetail',
    list_knowledge_bases: 'tools.listKnowledgeBases',
    query_knowledge_graph: 'tools.queryKnowledgeGraph',
    think: 'tools.think',
    todo_write: 'tools.todoWrite',
    // Retired names (still present in stored chat history)
    knowledge_search: 'tools.knowledgeSearch',
    grep_chunks: 'tools.grepChunks',
    list_knowledge_chunks: 'tools.listKnowledgeChunks',
    get_document_info: 'tools.getDocumentInfo',
};

// Get tool display name (user-friendly, localized)
export function getToolDisplayName(toolName: string): string {
    const key = toolDisplayNameKeys[toolName];
    if (key) return t(key);

    // Format MCP tool names: "mcp_service_tool" → "Service Tool"
    if (toolName.startsWith('mcp_')) {
        const parts = toolName.slice(4).split('_');
        return parts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
    }

    return toolName;
}

