import { del, get, post, postUpload } from "../../utils/request";
import type { ConfigSkillFileContent, ConfigSkillFileEntry } from "../system";

// Skill信息
export interface SkillInfo {
  name: string;
  description: string;
}

export interface SkillCatalogItem {
  id: string;
  name: string;
  enabled?: boolean;
  version?: string;
  description?: string;
  bundle_sha256?: string;
  created_at: string;
  updated_at: string;
}

export interface SkillCatalogRegisterResult {
  id: string;
  name: string;
  version?: string;
  description?: string;
}

/** Locates a shared agent's source workspace, same parameters as a chat request. */
export interface AgentScope {
  agentId?: string;
  /** Set only for a shared agent; left empty for this workspace's own agents. */
  sourceTenantId?: string | number;
}

// Lists the current user's enabled skill directories for a native backend.
// Directory availability does not establish that script dependencies exist.
export function listSkills(sandboxConfigId?: string, agent?: AgentScope) {
  const params: Record<string, string> = {};
  if (sandboxConfigId) params.sandbox_config_id = sandboxConfigId;
  if (agent?.agentId && agent?.sourceTenantId) {
    params.agent_id = agent.agentId;
    params.agent_source_tenant_id = String(agent.sourceTenantId);
  }
  return get<{ data: SkillInfo[]; skills_available?: boolean }>('/api/v1/skills', { params });
}

export function listSkillCatalog() {
  return get<{ data: SkillCatalogItem[] }>('/api/v1/skills/catalog');
}

export function registerSkillCatalogFromSource(source: string) {
  return post<{ data: SkillCatalogRegisterResult }>('/api/v1/skills/catalog', { source }, {
    timeout: 2 * 60 * 1000,
  });
}

export function registerSkillCatalogFromFile(
  file: File,
  onProgress?: (percent: number) => void,
) {
  const form = new FormData();
  form.append('file', file);
  return postUpload('/api/v1/skills/catalog', form, (e: any) => {
    if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total));
  }, { timeout: 5 * 60 * 1000 }) as Promise<{ data: SkillCatalogRegisterResult }>;
}

export function deleteSkillCatalog(catalogId: string) {
  return del(`/api/v1/skills/catalog/${catalogId}`);
}

export function listCatalogSkillFiles(catalogId: string) {
  return get<{ data: ConfigSkillFileEntry[] }>(`/api/v1/skills/catalog/${catalogId}/files`);
}

export function getCatalogSkillFile(catalogId: string, path: string) {
  return get<{ data: ConfigSkillFileContent }>(`/api/v1/skills/catalog/${catalogId}/files/content`, {
    params: { path },
  });
}
