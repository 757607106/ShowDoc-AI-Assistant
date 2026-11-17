<template>
  <div class="native-config">
    <section class="settings-group">
      <h3>{{ t('nativeAgent.subagents', 'Subagents') }}</h3>
      <p class="desc">{{ t('nativeAgent.subagentsHelp', 'Delegate to up to 20 named specialists. Omitted options inherit the parent; null tools/skills inherit, and [] disables them.') }}</p>
      <article v-for="(child, index) in children" :key="index" class="native-child">
        <div class="native-child-heading">
          <strong>{{ child.base.name || t('nativeAgent.newSubagent', 'New subagent') }}</strong>
          <t-button variant="text" theme="danger" :disabled="readOnly" @click="children.splice(index, 1)">{{ t('common.delete') }}</t-button>
        </div>
        <label>{{ t('agent.editor.name') }}<t-input v-model="child.base.name" :disabled="readOnly" :maxlength="64" /></label>
        <label>{{ t('agent.editor.description') }}<t-textarea v-model="child.base.description" :disabled="readOnly" :maxlength="8000" /></label>
        <label>{{ t('nativeAgent.executionMode', 'Execution mode') }}
          <t-select :value="child.base.execution_mode || 'sync'" :disabled="readOnly" :options="executionOptions"
            @change="(value: unknown) => setExecutionMode(child, value)" />
        </label>
        <p v-if="!asyncSupported" class="desc">{{ t('nativeAgent.asyncUnavailable', 'Background execution requires a connected Agent Protocol service. Choose synchronous execution to save.') }}</p>
        <label>{{ t('agent.editor.modelConfig') }}
          <t-select v-model="child.base.model_id" :disabled="readOnly" clearable :options="modelOptions"
            :placeholder="t('nativeAgent.inheritParent', 'Inherit parent')" />
        </label>
        <label>{{ t('agent.editor.systemPrompt') }}</label>
        <t-checkbox :checked="!Object.hasOwn(child.base, 'system_prompt')" :disabled="readOnly"
          @change="(value: boolean) => setPromptInheritance(child, value)">{{ t('nativeAgent.inheritParent', 'Inherit parent') }}</t-checkbox>
        <t-textarea v-model="child.base.system_prompt" :disabled="readOnly || !Object.hasOwn(child.base, 'system_prompt')" />
        <details>
          <summary>{{ t('nativeAgent.childOptions', 'Tools, skills and policies (JSON)') }}</summary>
          <p class="desc">{{ t('nativeAgent.childOptionsHelp', 'Optional keys: allowed_tools, selected_skills, access_level, response_format, permissions, interrupt_on. Child file permissions accept deny rules only.') }}</p>
          <p class="desc">{{ t('nativeAgent.asyncOptionsHelp', 'Background execution also accepts update_strategy (interrupt or enqueue; default interrupt) and mode (isolated or fork; default isolated). Fork is experimental and copies conversation history. Remove these keys before switching to synchronous execution.') }}</p>
          <t-textarea v-model="child.options" :disabled="readOnly" :autosize="{ minRows: 4, maxRows: 18 }" />
        </details>
      </article>
      <t-button variant="outline" :disabled="readOnly || children.length >= 20" @click="addChild">{{ t('nativeAgent.addSubagent', 'Add subagent') }}</t-button>
    </section>
    <section class="settings-group">
      <h3>{{ t('nativeAgent.advancedConfig', 'Output and policies') }}</h3>
      <label>{{ t('nativeAgent.responseFormat', 'Structured output (JSON Schema)') }}</label>
      <p class="desc">{{ t('nativeAgent.responseFormatHelp', 'Enter a JSON Schema object, or null for normal output. Only local references are accepted. The server validates the full schema before saving.') }}</p>
      <t-textarea v-model="texts.response_format" :disabled="readOnly" :autosize="{ minRows: 4, maxRows: 18 }" />
      <label>{{ t('nativeAgent.permissions', 'File permission rules (JSON)') }}</label>
      <p class="desc">{{ t('nativeAgent.permissionsHelp', 'Rules use operations [read, write], absolute paths, and mode allow, deny or interrupt. Platform authorization remains the upper limit.') }}</p>
      <t-textarea v-model="texts.permissions" :disabled="readOnly" :autosize="{ minRows: 3, maxRows: 18 }" />
      <label>{{ t('nativeAgent.interruptOn', 'Tool approvals (JSON)') }}</label>
      <p class="desc">{{ t('nativeAgent.interruptOnHelp', 'Map tool names to true/false or an object with allowed_decisions (approve, edit, reject, respond) and optional description. Edited arguments follow the tool schema. Required platform approvals cannot be disabled.') }}</p>
      <t-textarea v-model="texts.interrupt_on" :disabled="readOnly" :autosize="{ minRows: 3, maxRows: 18 }" />
    </section>
    <p v-if="validation" class="native-error" role="alert"><code>{{ validation.field }}</code>: {{ t(validation.key) }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { CustomAgentConfig } from '@/api/agent';
import type { ModelConfig } from '@/api/model';
import { validateNativeAgentConfig, type NativeConfigIssue } from './nativeAgentConfig';

const props = defineProps<{ config: CustomAgentConfig; models: ModelConfig[]; readOnly?: boolean; asyncSupported?: boolean }>();
const emit = defineEmits<{
  (event: 'update:fields', fields: CustomAgentConfig): void;
  (event: 'validation', issue: NativeConfigIssue | null): void;
  (event: 'draft', value: string): void;
}>();
const { t } = useI18n();
type ChildDraft = { base: Record<string, any>; options: string };
const children = ref<ChildDraft[]>([]);
const texts = ref({ response_format: 'null', permissions: '[]', interrupt_on: '{}' });
const validation = ref<NativeConfigIssue | null>(null);
const basicKeys = ['name', 'description', 'model_id', 'system_prompt', 'execution_mode'];
const optionKeys = ['allowed_tools', 'selected_skills', 'access_level', 'response_format', 'permissions', 'interrupt_on', 'update_strategy', 'mode'];
const format = (value: unknown, fallback: unknown) => JSON.stringify(value === undefined ? fallback : value, null, 2);
const draftText = () => JSON.stringify({ texts: texts.value, children: children.value });
let hydrating = false;
let hydrationGeneration = 0;
const executionOptions = computed(() => [
  { value: 'sync', label: t('nativeAgent.executionSync', 'Synchronous') },
  { value: 'async', label: t('nativeAgent.executionAsync', 'Background (async)'), disabled: props.asyncSupported !== true },
]);
const modelOptions = computed(() => {
  const selected = new Set(children.value.map(child => child.base.model_id).filter(Boolean));
  const models = props.models.filter(model => selected.has(model.id) || (!model.status || model.status === 'active') && ['KnowledgeQA', 'VLLM'].includes(model.type));
  const options = models.map(model => ({ value: model.id, label: model.name,
    disabled: !!model.status && model.status !== 'active' || !['KnowledgeQA', 'VLLM'].includes(model.type) }));
  for (const id of selected) if (!models.some(model => model.id === id)) options.push({ value: id, label: id, disabled: true });
  return options;
});

watch(() => props.config, async config => {
  const generation = ++hydrationGeneration;
  hydrating = true;
  texts.value = { response_format: format(config.response_format, null), permissions: format(config.permissions, []), interrupt_on: format(config.interrupt_on, {}) };
  children.value = (Array.isArray(config.subagents) ? config.subagents : []).map(child => ({
    base: Object.fromEntries(Object.entries(child).filter(([key]) => basicKeys.includes(key))),
    options: JSON.stringify(Object.fromEntries(Object.entries(child).filter(([key]) => !basicKeys.includes(key))), null, 2),
  }));
  emit('draft', draftText());
  validation.value = validateNativeAgentConfig(config, props.asyncSupported === true);
  emit('validation', validation.value);
  await nextTick();
  if (generation === hydrationGeneration) hydrating = false;
}, { immediate: true });

function addChild() {
  children.value.push({ base: { name: '', description: '' }, options: '{}' });
}

function setExecutionMode(child: ChildDraft, mode: unknown) {
  if (props.readOnly || !['sync', 'async'].includes(mode as string) || mode === 'async' && props.asyncSupported !== true) return;
  child.base.execution_mode = mode;
}

function setPromptInheritance(child: ChildDraft, inherit: boolean) {
  if (props.readOnly) return;
  if (inherit) delete child.base.system_prompt;
  else child.base.system_prompt ??= '';
}

watch([texts, children, () => props.asyncSupported], () => {
  if (hydrating) return;
  emit('draft', draftText());
  let field = 'response_format';
  try {
    const fields: CustomAgentConfig = {};
    for (const key of ['response_format', 'permissions', 'interrupt_on'] as const) {
      field = key;
      (fields as Record<string, unknown>)[key] = JSON.parse(texts.value[key]);
    }
    fields.subagents = children.value.map((child, index) => {
      field = `subagents[${index}]`;
      const options = JSON.parse(child.options);
      if (!options || typeof options !== 'object' || Array.isArray(options) || Object.keys(options).some(key => !optionKeys.includes(key))) throw new Error('options');
      return { ...options, ...child.base };
    });
    validation.value = validateNativeAgentConfig(fields, props.asyncSupported === true);
    emit('update:fields', fields);
  } catch {
    validation.value = { field, key: 'nativeAgent.invalidJson' };
  }
  emit('validation', validation.value);
}, { deep: true });
</script>

<style scoped>
.settings-group { margin-bottom: 24px; padding: 20px; border: 1px solid var(--td-component-border); border-radius: var(--app-radius-md); }
h3 { margin: 0 0 12px; font-size: 16px; }
.desc { margin: 8px 0 12px; color: var(--td-text-color-secondary); font-size: 12px; line-height: 1.6; }
label { display: block; margin: 16px 0 8px; font-size: 14px; }
label > :deep(.t-input), label > :deep(.t-textarea), label > :deep(.t-select__wrap) { margin-top: 8px; }
.native-child { margin-bottom: 16px; padding: 16px; border: 1px solid var(--td-component-border); border-radius: var(--app-radius-md); }
.native-child-heading { display: flex; justify-content: space-between; align-items: center; }
summary { margin-top: 16px; cursor: pointer; }
.native-error { color: var(--td-error-color); overflow-wrap: anywhere; }
</style>
