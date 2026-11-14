<script setup lang="ts">
import KBSwitcherDropdown from '@/components/KBSwitcherDropdown.vue'

defineProps<{
  title: string
  currentId: string
  choices?: {id:string;name:string;type?:string}[]
  tabs: {key:string;label:string;icon:string}[]
  modelValue: string
  canManage?: boolean
}>()
const emit=defineEmits<{
  'update:modelValue':[value:string]
  navigate:[]
  select:[id:string]
  settings:[]
}>()
</script>

<!-- Header structure and styles transplanted from WeKnora KnowledgeBase.vue. -->
<template>
  <div class="document-header">
    <div class="document-header-title">
      <div class="document-title-row">
        <h2 class="document-breadcrumb">
          <button type="button" class="breadcrumb-link" @click="emit('navigate')">知识库</button>
          <t-icon name="chevron-right" class="breadcrumb-separator" />
          <KBSwitcherDropdown v-if="choices?.length" :kb-list="choices" :current-kb-id="currentId" @select="id=>emit('select',id)">
            <button type="button" class="breadcrumb-link dropdown" :disabled="!currentId"><span>{{title}}</span><t-icon name="chevron-down" /></button>
          </KBSwitcherDropdown>
          <span v-else class="breadcrumb-current">{{title}}</span>
          <t-icon name="chevron-right" class="breadcrumb-separator" />
          <div class="kb-view-tabs" role="tablist" aria-label="知识库视图">
            <button v-for="tab in tabs" :key="tab.key" type="button" role="tab" class="kb-view-tab" :class="{active:modelValue===tab.key}" :aria-selected="modelValue===tab.key" @click="emit('update:modelValue',tab.key)">
              <t-icon :name="tab.icon" size="16px" /><span>{{tab.label}}</span>
            </button>
          </div>
        </h2>
        <div class="kb-title-actions">
          <t-tooltip v-if="canManage" content="设置" placement="top">
            <button type="button" class="kb-settings-button" aria-label="知识库设置" :disabled="!currentId" @click="emit('settings')"><t-icon name="setting" size="16px" /></button>
          </t-tooltip>
        </div>
      </div>
    </div>
    <slot name="actions" />
  </div>
</template>

<style scoped lang="less">
.kb-view-tabs {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 2px;
  padding: 3px;
  border-radius: var(--app-radius-lg);
  background: var(--td-bg-color-secondarycontainer);
}

.kb-view-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--app-radius-md);
  background: transparent;
  color: var(--td-text-color-secondary);
  font-family: var(--app-font-family);
  font-size: var(--app-text-base);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--app-motion-fast) ease, background-color var(--app-motion-fast) ease;

  &:hover {
    color: var(--td-text-color-primary);
  }

  &.active {
    background: var(--td-bg-color-container);
    color: var(--td-brand-color);
    font-weight: 600;
    box-shadow: 0 1px 3px rgb(0 0 0 / 8%);
  }

  &:focus-visible {
    outline: 2px solid var(--app-focus-border);
    outline-offset: 1px;
  }

  &__indicator {
    display: inline-flex;
    color: var(--td-brand-color);
  }
}

.document-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  flex-shrink: 0;

  .document-header-title {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .document-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .kb-title-actions {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    margin-left: 4px;
  }

  .document-breadcrumb {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    row-gap: 8px;
    margin: 0;
    font-size: var(--app-text-3xl);
    font-weight: 600;
    color: var(--td-text-color-primary);
  }

  .breadcrumb-link {
    border: none;
    background: transparent;
    padding: 4px 8px;
    margin: -4px -8px;
    font: inherit;
    color: var(--td-text-color-secondary);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
    border-radius: var(--app-radius-sm);
    transition: color var(--app-motion-instant) ease, background-color var(--app-motion-instant) ease;

    &:hover:not(:disabled) {
      color: var(--td-success-color);
      background: var(--td-bg-color-container);
    }

    &:disabled {
      cursor: not-allowed;
      color: var(--td-text-color-placeholder);
    }

    &.dropdown {
      padding-right: 6px;

      :deep(.t-icon) {
        font-size: var(--app-text-base);
        transition: transform var(--app-motion-instant) ease;
      }

      &:hover:not(:disabled) {
        :deep(.t-icon) {
          transform: translateY(1px);
        }
      }
    }
  }

  .breadcrumb-separator {
    font-size: var(--app-text-base);
    color: var(--td-text-color-placeholder);
  }

  .breadcrumb-current {
    color: var(--td-text-color-primary);
    font-weight: 600;
  }

  h2 {
    margin: 0;
    color: var(--td-text-color-primary);
    font-family: var(--app-font-family);
    font-size: var(--app-text-4xl);
    font-weight: 600;
    line-height: 32px;
  }

  .document-subtitle {
    margin: 0;
    color: var(--td-text-color-placeholder);
    font-family: var(--app-font-family);
    font-size: var(--app-text-base);
    font-weight: 400;
    line-height: 20px;
  }

}
.kb-settings-button {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: var(--td-bg-color-secondarycontainer);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--td-text-color-secondary);
  cursor: pointer;
  transition: color var(--app-motion-base) ease, background-color var(--app-motion-base) ease, box-shadow var(--app-motion-base) ease;
  padding: 0;

  &:hover:not(:disabled) {
    background: var(--td-success-color-light);
    color: var(--td-brand-color);
    box-shadow: none;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  :deep(.t-icon) {
    font-size: var(--app-text-2xl);
  }
}

</style>
