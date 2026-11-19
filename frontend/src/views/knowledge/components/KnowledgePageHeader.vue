<script setup lang="ts">
import { computed } from 'vue'
import KbTypeAvatar from './KbTypeAvatar.vue'
import { navigateKnowledgeTabs } from './knowledgeTabNavigation'
const props = defineProps<{title:string; panelId:string; tabs:{key:string;label:string;icon?:string}[]; modelValue:string; modeLabel?:string; description?:string; permissionMode?:string}>()
const emit=defineEmits<{'update:modelValue':[value:string];navigate:[]}>()
const focusableKey = computed(() => props.tabs.find(tab => tab.key === props.modelValue)?.key ?? props.tabs[0]?.key)

</script>
<template>
  <header class="knowledge-header">
    <div class="knowledge-heading"><t-button variant="text" shape="square" aria-label="返回知识库列表" title="返回知识库列表" @click="emit('navigate')"><t-icon name="chevron-left" /></t-button><KbTypeAvatar type="document" /><div class="knowledge-name"><div><h1>{{title}}</h1><t-tag v-if="modeLabel" variant="light">{{modeLabel}}</t-tag><span v-if="permissionMode" class="permission-mode">{{permissionMode}}</span></div><p v-if="description">{{description}}</p></div><div class="knowledge-actions"><slot name="actions" /></div></div>
    <div class="knowledge-view-tabs" role="tablist" aria-label="知识库视图" @keydown="navigateKnowledgeTabs">
      <button v-for="tab in tabs" :id="`${panelId}-${tab.key}`" :key="tab.key" role="tab" type="button"
        :aria-selected="modelValue === tab.key" :aria-controls="panelId" :tabindex="focusableKey === tab.key ? 0 : -1"
        @click="emit('update:modelValue', tab.key)">{{ tab.label }}</button>
    </div>
  </header>
</template>
<style scoped lang="less">
.knowledge-header{font-family:var(--app-font-family);font-size:var(--app-text-base);flex:none;padding:16px 20px 0;container-type:inline-size}.knowledge-heading{display:flex;align-items:center;gap:12px;min-height:40px}.knowledge-name{min-width:0;flex:1;overflow-wrap:anywhere}.knowledge-name>div{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.knowledge-name h1{font-size:var(--app-text-3xl);font-weight:600;line-height:28px;margin:0;overflow-wrap:anywhere}.knowledge-name p{font-size:var(--app-text-md);color:var(--td-text-color-secondary);margin:4px 0 0}.permission-mode{color:var(--td-text-color-secondary);font-size:var(--app-text-sm)}.knowledge-actions{margin-left:auto;flex:none;max-width:100%}.knowledge-view-tabs{display:inline-flex;gap:2px;margin-top:16px;padding:3px;background:var(--td-bg-color-secondarycontainer);border-radius:var(--app-radius-lg)}.knowledge-view-tabs button{border:0;border-radius:var(--app-radius-md);height:28px;padding:0 16px;background:transparent;color:var(--td-text-color-secondary);font:inherit;font-size:var(--app-text-base);cursor:pointer}.knowledge-view-tabs button[aria-selected=true]{background:var(--app-selection-bg);color:var(--app-selection-text);box-shadow:0 1px 3px color-mix(in srgb,var(--td-text-color-primary) 5%,transparent)}.knowledge-view-tabs button:focus-visible{outline:2px solid var(--td-brand-color)}
@container (max-width: 760px) {
  .knowledge-heading { gap: 6px; }
  .knowledge-name>div { gap: 4px 8px; }
  .knowledge-view-tabs { margin-top: 10px; }
  .knowledge-view-tabs button { padding-inline: 12px; }
}
</style>
