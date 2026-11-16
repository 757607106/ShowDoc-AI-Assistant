<script setup lang="ts">
import KbTypeAvatar from './KbTypeAvatar.vue'
defineProps<{title:string; currentId:string; tabs:{key:string;label:string;icon?:string}[]; modelValue:string; modeLabel?:string; description?:string; permissionMode?:string}>()
const emit=defineEmits<{'update:modelValue':[value:string];navigate:[]}>()
</script>
<template>
  <header class="knowledge-header">
    <div class="knowledge-heading"><t-button variant="text" shape="square" aria-label="返回知识库列表" @click="emit('navigate')"><t-icon name="chevron-left" /></t-button><KbTypeAvatar type="document" /><div class="knowledge-name"><div><h2>{{title}}</h2><t-tag v-if="modeLabel" variant="light">{{modeLabel}}</t-tag><span class="permission-mode">{{permissionMode}}</span></div><p v-if="description">{{description}}</p></div><div class="knowledge-actions"><slot name="actions" /></div></div>
    <div class="knowledge-view-tabs" role="tablist" aria-label="知识库视图"><button v-for="tab in tabs" :key="tab.key" role="tab" type="button" :aria-selected="modelValue===tab.key" @click="emit('update:modelValue',tab.key)">{{tab.label}}</button></div>
  </header>
</template>
<style scoped lang="less">
.knowledge-header{font-family:var(--app-font-family);font-size:var(--app-text-base);flex:none;padding:16px 20px 0}.knowledge-heading{display:flex;align-items:center;gap:12px;min-height:40px}.knowledge-name{min-width:0;flex:1}.knowledge-name>div{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.knowledge-name h2{font-size:var(--app-text-3xl);font-weight:600;line-height:28px;margin:0;overflow-wrap:anywhere}.knowledge-name p{font-size:var(--app-text-md);color:var(--td-text-color-secondary);margin:4px 0 0}.permission-mode{color:var(--td-text-color-secondary);font-size:var(--app-text-sm)}.knowledge-actions{margin-left:auto;flex:none}.knowledge-view-tabs{display:inline-flex;gap:2px;margin-top:16px;padding:3px;background:var(--td-bg-color-secondarycontainer);border-radius:var(--app-radius-lg)}.knowledge-view-tabs button{border:0;border-radius:var(--app-radius-md);height:28px;padding:0 16px;background:transparent;color:var(--td-text-color-secondary);font:inherit;font-size:var(--app-text-base);cursor:pointer}.knowledge-view-tabs button[aria-selected=true]{background:var(--app-selection-bg);color:var(--app-selection-text);box-shadow:0 1px 3px color-mix(in srgb,var(--td-text-color-primary) 5%,transparent)}.knowledge-view-tabs button:focus-visible{outline:2px solid var(--td-brand-color)}@media(max-width:900px){.knowledge-heading{flex-wrap:wrap}.knowledge-actions{margin-left:44px;width:100%}}
</style>
