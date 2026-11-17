import assert from 'node:assert/strict';
import test from 'node:test';
import * as vue from 'vue';
import { fixture, flush } from '../../test-utils/vueFixture';
import { validateNativeAgentConfig } from './nativeAgentConfig';

test('native form emits exact inherited/empty options and keeps malformed JSON in its own draft', async t => {
  const fx = fixture(t);
  const original = { response_format: null, permissions: [], interrupt_on: {}, subagents: [
    { name: 'research', description: 'Research', model_id: 'private-model', allowed_tools: null, selected_skills: [] },
  ] };
  const before = JSON.stringify(original);
  const fields: any[] = [], validations: any[] = [], drafts: string[] = [];
  const mounted = fx.component(new URL('./NativeAgentConfig.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    './nativeAgentConfig': { validateNativeAgentConfig },
  }, {
    config: original, models: [],
    'onUpdate:fields': (value: unknown) => fields.push(value),
    onValidation: (value: unknown) => validations.push(value),
    onDraft: (value: string) => drafts.push(value),
  });
  await flush();
  const state = mounted.vm.$.exposed;
  assert.equal(fields.length, 0, 'hydrating does not rewrite the saved configuration');
  const baseline = drafts.at(-1);
  assert.deepEqual(Array.from(state.modelOptions.value, (model: any) => model.value), ['private-model']);
  state.children.value[0].base.description = 'Edited research';
  await vue.nextTick();
  assert.equal(validations.at(-1), null);
  assert.deepEqual(JSON.parse(JSON.stringify(fields.at(-1).subagents)), [
    { name: 'research', description: 'Edited research', model_id: 'private-model', allowed_tools: null, selected_skills: [] },
  ]);
  state.setPromptInheritance(state.children.value[0], false);
  await vue.nextTick();
  assert.equal(fields.at(-1).subagents[0].system_prompt, '', 'empty custom instructions explicitly clear the parent instruction');
  state.setPromptInheritance(state.children.value[0], true);
  await vue.nextTick();
  assert.equal(Object.hasOwn(fields.at(-1).subagents[0], 'system_prompt'), false, 'inherit omits the field');
  const validCount = fields.length;
  state.texts.value.response_format = '{';
  await vue.nextTick();
  assert.equal(fields.length, validCount, 'invalid JSON is never sent as a config field');
  assert.equal(validations.at(-1).key, 'nativeAgent.invalidJson');
  assert.match(drafts.at(-1)!, /response_format/);
  state.texts.value.response_format = '{"type":"invalid"}';
  await vue.nextTick();
  assert.equal(validations.at(-1).key, 'nativeAgent.invalidSchema');
  state.texts.value.response_format = 'null';
  state.children.value[0].options = '{"allowed_tools":[],"selected_skills":null}';
  await vue.nextTick();
  assert.equal(validations.at(-1), null);
  assert.deepEqual(Array.from(fields.at(-1).subagents[0].allowed_tools), []);
  assert.equal(fields.at(-1).subagents[0].selected_skills, null);
  state.children.value[0].base.description = 'Research';
  state.children.value[0].options = JSON.stringify({ allowed_tools: null, selected_skills: [] }, null, 2);
  await vue.nextTick();
  assert.equal(drafts.at(-1), baseline, 'reverting edits restores the unsaved-change baseline');
  assert.equal(JSON.stringify(original), before);
});

test('native contracts reject child permission expansion, unknown Python options and unused HITL schemas', () => {
  const child = { name: 'review', description: 'Review', permissions: [{ operations: ['write'], paths: ['/state/**'], mode: 'allow' }] };
  assert.equal(validateNativeAgentConfig({ subagents: [child] } as any)?.key, 'nativeAgent.childDenyOnly');
  assert.equal(validateNativeAgentConfig({ subagents: [{ name: 'review', description: 'Review', middleware: [] }] } as any)?.key, 'nativeAgent.invalidSubagents');
  assert.equal(validateNativeAgentConfig({ interrupt_on: { execute: { allowed_decisions: ['approve'], args_schema: { type: 'object' } } } } as any)?.key, 'nativeAgent.invalidInterrupts');
  assert.equal(validateNativeAgentConfig({ response_format: { $defs: { answer: { type: 'string' } }, $ref: '#/$defs/answer' } }), null);
  assert.equal(validateNativeAgentConfig({ response_format: { $ref: '#/$defs/missing' } })?.key, 'nativeAgent.invalidSchema');
});

test('async child contracts validate SDK options and keep transport server controlled', () => {
  const child = { name: 'research', description: 'Research', execution_mode: 'async' };
  assert.equal(validateNativeAgentConfig({ subagents: [child] } as any, true), null);
  assert.equal(validateNativeAgentConfig({ subagents: [child] } as any, false)?.key, 'nativeAgent.asyncUnavailable');
  for (const mode of ['isolated', 'fork']) for (const update_strategy of ['interrupt', 'enqueue']) {
    assert.equal(validateNativeAgentConfig({ subagents: [{ ...child, mode, update_strategy }] } as any, true), null);
  }
  for (const options of [{ execution_mode: null }, { execution_mode: 'background' }]) {
    assert.equal(validateNativeAgentConfig({ subagents: [{ ...child, ...options }] } as any)?.key, 'nativeAgent.invalidExecutionMode');
  }
  for (const options of [{ mode: 'shared' }, { update_strategy: 'parallel' }, { mode: null },
    { execution_mode: 'sync', mode: 'fork' }, { execution_mode: undefined, update_strategy: 'enqueue' }]) {
    assert.equal(validateNativeAgentConfig({ subagents: [{ ...child, ...options }] } as any)?.key, 'nativeAgent.invalidAsyncOptions');
  }
  for (const field of ['url', 'headers', 'graph_id', 'runnable', 'webhook', 'notify_parent']) {
    assert.equal(validateNativeAgentConfig({ subagents: [{ ...child, [field]: 'untrusted' }] } as any)?.key, 'nativeAgent.invalidSubagents');
  }
});

test('an unavailable async capability preserves saved selections and rejects new activation', async t => {
  const fx = fixture(t);
  const original = { subagents: [{ name: 'research', description: 'Research', execution_mode: 'async', mode: 'fork' }] };
  const before = JSON.stringify(original);
  const fields: any[] = [], validations: any[] = [];
  const mounted = fx.component(new URL('./NativeAgentConfig.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    './nativeAgentConfig': { validateNativeAgentConfig },
  }, { config: original, models: [],
    'onUpdate:fields': (value: unknown) => fields.push(value),
    onValidation: (value: unknown) => validations.push(value),
  });
  await flush();
  const state = mounted.vm.$.exposed;
  assert.equal(fields.length, 0, 'loading does not rewrite history');
  assert.equal(state.children.value[0].base.execution_mode, 'async');
  assert.equal(JSON.parse(state.children.value[0].options).mode, 'fork');
  assert.equal(state.executionOptions.value.find((option: any) => option.value === 'async').disabled, true);
  assert.equal(validations.at(-1).key, 'nativeAgent.asyncUnavailable');
  state.addChild();
  state.setExecutionMode(state.children.value[1], 'async');
  assert.equal(state.children.value[1].base.execution_mode, undefined, 'an old or failed capability probe cannot activate async');
  state.children.value.pop();
  state.children.value[0].options = '{';
  await vue.nextTick();
  assert.equal(validations.at(-1).key, 'nativeAgent.invalidJson');
  mounted.vm.$.props.asyncSupported = true;
  await vue.nextTick();
  assert.equal(state.children.value[0].options, '{', 'capability refresh does not overwrite an unsaved JSON draft');
  state.children.value[0].options = '{"mode":"fork"}';
  await vue.nextTick();
  assert.equal(validations.at(-1), null);
  assert.equal(state.executionOptions.value.find((option: any) => option.value === 'async').disabled, false);
  assert.equal(JSON.stringify(original), before);
});

test('switching async to sync requires explicitly removing SDK async options', async t => {
  const fx = fixture(t);
  const fields: any[] = [], validations: any[] = [];
  const mounted = fx.component(new URL('./NativeAgentConfig.vue', import.meta.url), {
    'vue-i18n': { useI18n: () => ({ t: (key: string) => key }) },
    './nativeAgentConfig': { validateNativeAgentConfig },
  }, { config: { subagents: [{ name: 'research', description: 'Research', execution_mode: 'async',
    mode: 'fork', update_strategy: 'enqueue', allowed_tools: [], selected_skills: null }] }, models: [], asyncSupported: true,
    'onUpdate:fields': (value: unknown) => fields.push(value),
    onValidation: (value: unknown) => validations.push(value),
  });
  await flush();
  const state = mounted.vm.$.exposed;
  const child = state.children.value[0];
  child.base.description = 'Edited research';
  await vue.nextTick();
  assert.equal(validations.at(-1), null);
  assert.equal(fields.at(-1).subagents[0].mode, 'fork');
  state.setExecutionMode(child, 'sync');
  await vue.nextTick();
  assert.equal(validations.at(-1).key, 'nativeAgent.invalidAsyncOptions');
  assert.equal(JSON.parse(child.options).mode, 'fork', 'invalid settings remain visible for explicit correction');
  child.options = '{"allowed_tools":[],"selected_skills":null}';
  await vue.nextTick();
  assert.equal(validations.at(-1), null);
  assert.deepEqual(JSON.parse(JSON.stringify(fields.at(-1).subagents)), [{ name: 'research', description: 'Edited research',
    execution_mode: 'sync', allowed_tools: [], selected_skills: null }]);
});
