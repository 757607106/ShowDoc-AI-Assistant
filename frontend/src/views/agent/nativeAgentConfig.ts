import type { CustomAgentConfig } from '@/api/agent';

export type NativeConfigIssue = { field: string; key: string };
const object = (value: unknown): value is Record<string, any> => !!value && typeof value === 'object' && !Array.isArray(value);
const only = (value: object, keys: string[]) => Object.keys(value).every(key => keys.includes(key));
const string = (value: unknown, max: number) => typeof value === 'string' && value.length <= max;
const issue = (field: string, key: string): NativeConfigIssue => ({ field, key: `nativeAgent.${key}` });

// Fast form checks; the server remains authoritative for full JSON Schema semantics.
function schemaIssue(schema: unknown, field: string): NativeConfigIssue | null {
  if (schema == null) return null;
  if (!object(schema)) return issue(field, 'invalidSchema');
  const serialized = JSON.stringify(schema);
  const bytes = Array.from(serialized).reduce((size, char) => size + (char.codePointAt(0)! > 0xffff ? 4 : char.charCodeAt(0) > 0x7ff ? 3 : char.charCodeAt(0) > 0x7f ? 2 : 1), 0);
  if (bytes > 64000) return issue(field, 'invalidSchema');
  const types = ['null', 'boolean', 'object', 'array', 'number', 'integer', 'string'];
  if (schema.type !== undefined && !(Array.isArray(schema.type)
    ? schema.type.length > 0 && schema.type.every(type => types.includes(type))
    : types.includes(schema.type))) return issue(field, 'invalidSchema');
  if (schema.required !== undefined && (!Array.isArray(schema.required) || schema.required.some(key => typeof key !== 'string'))) return issue(field, 'invalidSchema');
  if (schema.properties !== undefined && !object(schema.properties)) return issue(field, 'invalidSchema');
  function safe(value: unknown, depth = 0): boolean {
    if (depth > 30) return false;
    if (Array.isArray(value)) return value.every(item => safe(item, depth + 1));
    if (!object(value)) return true;
    if ('$id' in value && (typeof value.$id !== 'string' || !value.$id.startsWith('#'))) return false;
    for (const key of ['$ref', '$dynamicRef', '$recursiveRef']) {
      const reference = value[key];
      if (reference == null) continue;
      if (typeof reference !== 'string' || (reference !== '#' && !reference.startsWith('#/'))) return false;
      let target: any = schema;
      for (const part of reference === '#' ? [] : reference.slice(2).split('/')) {
        const key = part.replace(/~1/g, '/').replace(/~0/g, '~');
        if (!target || typeof target !== 'object' || !Object.hasOwn(target, key)) return false;
        target = target[key];
      }
    }
    return Object.values(value).every(item => safe(item, depth + 1));
  }
  return safe(schema) ? null : issue(field, 'invalidSchema');
}

function policyIssue(value: Record<string, any>, prefix = '', child = false): NativeConfigIssue | null {
  const rules = value.permissions ?? [];
  if (value.permissions === null || !Array.isArray(rules) || rules.length > 100) return issue(`${prefix}permissions`, 'invalidPermissions');
  for (const rule of rules) {
    if (!object(rule) || !only(rule, ['operations', 'paths', 'mode'])
      || !(child ? ['deny'] : ['allow', 'deny', 'interrupt']).includes(rule.mode ?? 'allow')
      || !Array.isArray(rule.operations) || !rule.operations.length || rule.operations.some(op => !['read', 'write'].includes(op))
      || !Array.isArray(rule.paths) || !rule.paths.length || rule.paths.length > 100
      || rule.paths.some(path => !string(path, 1000) || !path.startsWith('/') || path.includes('\\') || path.includes('\0') || path.split('/').includes('..'))) {
      return issue(`${prefix}permissions`, child ? 'childDenyOnly' : 'invalidPermissions');
    }
  }
  const interrupts = value.interrupt_on ?? {};
  if (value.interrupt_on === null || !object(interrupts) || Object.keys(interrupts).length > 200) return issue(`${prefix}interrupt_on`, 'invalidInterrupts');
  for (const [name, setting] of Object.entries(interrupts)) {
    if (!name || name.length > 300) return issue(`${prefix}interrupt_on`, 'invalidInterrupts');
    if (typeof setting === 'boolean') continue;
    if (!object(setting) || !only(setting, ['allowed_decisions', 'description'])
      || !Array.isArray(setting.allowed_decisions) || !setting.allowed_decisions.length
      || setting.allowed_decisions.some(decision => !['approve', 'edit', 'reject', 'respond'].includes(decision))
      || setting.description !== undefined && !string(setting.description, 8000)) return issue(`${prefix}interrupt_on.${name}`, 'invalidInterrupts');
  }
  return null;
}

export function validateNativeAgentConfig(value: CustomAgentConfig, asyncSupported?: boolean): NativeConfigIssue | null {
  const rootError = schemaIssue(value.response_format, 'response_format') || policyIssue(value);
  if (rootError) return rootError;
  const children = value.subagents === undefined ? [] : value.subagents;
  if (!Array.isArray(children) || children.length > 20) return issue('subagents', 'invalidSubagents');
  const names = new Set<string>();
  for (const [index, child] of children.entries()) {
    const prefix = `subagents[${index}].`;
    if (!object(child) || !only(child, ['name', 'description', 'model_id', 'system_prompt', 'allowed_tools', 'selected_skills', 'access_level', 'response_format', 'permissions', 'interrupt_on', 'execution_mode', 'update_strategy', 'mode'])) return issue(prefix.slice(0, -1), 'invalidSubagents');
    const executionMode = child.execution_mode === undefined ? 'sync' : child.execution_mode;
    if (!['sync', 'async'].includes(executionMode)) return issue(`${prefix}execution_mode`, 'invalidExecutionMode');
    for (const [field, choices] of [['update_strategy', ['interrupt', 'enqueue']], ['mode', ['isolated', 'fork']]] as const) {
      if (Object.hasOwn(child, field) && (executionMode !== 'async' || !(choices as readonly unknown[]).includes(child[field]))) return issue(`${prefix}${field}`, 'invalidAsyncOptions');
    }
    if (executionMode === 'async' && asyncSupported === false) return issue(`${prefix}execution_mode`, 'asyncUnavailable');
    if (!string(child.name, 64) || !/^[A-Za-z0-9_-]{1,64}$/.test(child.name) || child.name === 'general-purpose' || names.has(child.name)) return issue(`${prefix}name`, 'invalidChildName');
    names.add(child.name);
    if (!string(child.description, 8000) || !child.description.trim()) return issue(`${prefix}description`, 'invalidChildDescription');
    if (child.model_id !== undefined && !string(child.model_id, 300) || child.system_prompt !== undefined && !string(child.system_prompt, 100000)) return issue(prefix.slice(0, -1), 'invalidSubagents');
    if (child.access_level !== undefined && !['read_only', 'confirm', 'auto_write'].includes(child.access_level)) return issue(`${prefix}access_level`, 'invalidSubagents');
    for (const field of ['allowed_tools', 'selected_skills'] as const) {
      const selected = child[field];
      if (selected != null && (!Array.isArray(selected) || selected.length > 200 || selected.some(item => !string(item, 300) || !item))) return issue(`${prefix}${field}`, 'invalidSelections');
    }
    const error = schemaIssue(child.response_format, `${prefix}response_format`) || policyIssue(child, prefix, true);
    if (error) return error;
  }
  return null;
}
