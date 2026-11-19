<template>
  <div class="user-profile">
    <div class="section-header">
      <h2>{{ $t('userProfile.title') }}</h2>
      <p class="section-description">{{ $t('userProfile.description') }}</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-inline">
      <t-loading size="small" />
      <span>{{ $t('tenant.loadingInfo') }}</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-inline">
      <t-alert theme="error" :message="error">
        <template #operation>
          <t-button size="small" @click="loadInfo">{{ $t('tenant.retry') }}</t-button>
        </template>
      </t-alert>
    </div>

    <!-- Content -->
    <div v-else class="settings-group">
      <!-- 用户 ID -->
      <div class="setting-row">
        <div class="setting-info">
          <label>{{ $t('tenant.api.userIdLabel') }}</label>
          <p class="desc">{{ $t('tenant.api.userIdDescription') }}</p>
        </div>
        <div class="setting-control">
          <span class="info-value">{{ userInfo?.id || '-' }}</span>
        </div>
      </div>

      <!-- 用户名 -->
      <div class="setting-row">
        <div class="setting-info">
          <label>{{ $t('tenant.api.usernameLabel') }}</label>
          <p class="desc">{{ $t('tenant.api.usernameDescription') }}</p>
        </div>
        <div class="setting-control">
          <span class="info-value">{{ userInfo?.username || '-' }}</span>
        </div>
      </div>

      <!-- 登录账号 -->
      <div class="setting-row">
        <div class="setting-info">
          <label>{{ $t('auth.account') }}</label>
          <p class="desc">{{ $t('auth.accountDescription') }}</p>
        </div>
        <div class="setting-control">
          <span class="info-value">{{ userInfo?.account || userInfo?.email || '-' }}</span>
        </div>
      </div>

      <!-- 注册时间 -->
      <div class="setting-row">
        <div class="setting-info">
          <label>{{ $t('tenant.api.createdAtLabel') }}</label>
          <p class="desc">{{ $t('tenant.api.createdAtDescription') }}</p>
        </div>
        <div class="setting-control">
          <span class="info-value">{{ formatDate(userInfo?.created_at) }}</span>
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>{{ $t('userProfile.changePassword.label') }}</label>
          <p class="desc">
            {{ oidcOnlyLogin
              ? $t('userProfile.changePassword.oidcOnlyDescription')
              : $t('userProfile.changePassword.description') }}
          </p>
        </div>
        <div class="setting-control">
          <template v-if="oidcOnlyLogin">
            <span class="info-value info-value--muted">—</span>
          </template>
          <template v-else>
            <span class="info-value password-mask" aria-hidden="true">••••••••</span>
            <t-button
              theme="default"
              variant="text"
              shape="square"
              size="small"
              class="edit-btn"
              :title="$t('userProfile.changePassword.label')"
              :aria-label="$t('userProfile.changePassword.label')"
              aria-haspopup="dialog"
              @click="openPasswordDialog"
            >
              <template #icon>
                <t-icon name="edit" />
              </template>
            </t-button>
          </template>
        </div>
      </div>
    </div>

    <t-dialog
      v-model:visible="passwordDialogVisible"
      attach="body"
      placement="center"
      width="min(480px, calc(100vw - 32px))"
      :header="$t('userProfile.changePassword.label')"
      role="dialog"
      aria-modal="true"
      :aria-label="$t('userProfile.changePassword.label')"
      :close-btn="false"
      :cancel-btn="{ content: $t('common.cancel'), disabled: passwordSubmitting }"
      :confirm-btn="$t('userProfile.changePassword.submit')"
      :confirm-loading="passwordSubmitting"
      :close-on-overlay-click="!passwordSubmitting"
      :close-on-esc-keydown="!passwordSubmitting"
      @confirm="submitPasswordChange"
      @keydown.tab="cycleDialogFocus"
      @closed="restorePasswordFocus"
    >
      <div ref="passwordDialogBody">
        <p class="password-dialog-hint">{{ $t('userProfile.changePassword.description') }}</p>
        <t-form ref="passwordFormRef" :data="passwordForm" :rules="passwordRules" label-align="top"
          :disabled="passwordSubmitting" @submit.prevent>
          <t-form-item :label="$t('userProfile.changePassword.currentLabel')" name="oldPassword" :for="`${passwordFormId}-oldPassword`">
            <t-input v-model="passwordForm.oldPassword" name="oldPassword" type="password" autocomplete="current-password"
              :placeholder="$t('userProfile.changePassword.currentPlaceholder')" />
          </t-form-item>
          <t-form-item :label="$t('userProfile.changePassword.newLabel')" name="newPassword" :for="`${passwordFormId}-newPassword`">
            <t-input v-model="passwordForm.newPassword" name="newPassword" type="password" autocomplete="new-password"
              :placeholder="$t('userProfile.changePassword.newPlaceholder')" />
          </t-form-item>
          <t-form-item :label="$t('userProfile.changePassword.confirmLabel')" name="confirmPassword" :for="`${passwordFormId}-confirmPassword`">
            <t-input v-model="passwordForm.confirmPassword" name="confirmPassword" type="password" autocomplete="new-password"
              :placeholder="$t('userProfile.changePassword.confirmPlaceholder')" @enter="submitPasswordChange" />
          </t-form-item>
        </t-form>
      </div>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, useId, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import type { FormInstanceFunctions, FormRule } from 'tdesign-vue-next'
import {
  getCurrentUser,
  getAuthConfig,
  changePassword,
  logout as logoutApi,
  type UserInfo,
} from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import { newPasswordRules } from '@/utils/passwordPolicy'
import { cycleDialogFocus } from '@/utils/dialogFocus'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const userInfo = ref<UserInfo | null>(null)
const complexPasswordEnabled = ref(false)
const loading = ref(true)
const error = ref('')

const passwordDialogVisible = ref(false)
const passwordDialogBody = ref<HTMLElement>()
const passwordFormId = useId()
let passwordOpener: HTMLElement | null = null
const passwordFormRef = ref<FormInstanceFunctions | null>(null)
const passwordSubmitting = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const loadPasswordPolicy = async () => {
  try {
    const resp = await getAuthConfig()
    complexPasswordEnabled.value = !!resp.complex_password_enabled
  } catch {
    complexPasswordEnabled.value = false
  }
}

const oidcOnlyLogin = computed(
  () => userInfo.value?.preferences?.oidc_only_login === true,
)

watch(passwordDialogVisible, (open) => {
  if (!open) resetPasswordForm()
})

const passwordRules = computed<Record<string, FormRule[]>>(() => ({
  oldPassword: [
    { required: true, message: t('userProfile.changePassword.currentRequired'), type: 'error' },
  ],
  newPassword: newPasswordRules(t, complexPasswordEnabled.value, [
    {
      validator: (val: string) => val !== passwordForm.oldPassword,
      message: t('userProfile.changePassword.sameAsCurrent'),
      type: 'error',
    },
  ]),
  confirmPassword: [
    { required: true, message: t('auth.confirmPasswordRequired'), type: 'error' },
    {
      validator: (val: string) => val === passwordForm.newPassword,
      message: t('auth.passwordMismatch'),
      type: 'error',
      trigger: 'blur',
    },
  ],
}))

const loadInfo = async () => {
  try {
    loading.value = true
    error.value = ''
    const resp = await getCurrentUser()
    if ((resp as any).success && resp.data) {
      userInfo.value = resp.data.user
    } else {
      error.value = resp.message || t('tenant.messages.fetchFailed')
    }
  } catch (err: any) {
    error.value = err?.message || t('tenant.messages.networkError')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return t('tenant.unknown')
  try {
    const d = new Date(dateStr)
    const fmt = new Intl.DateTimeFormat(locale.value || 'zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
    return fmt.format(d)
  } catch {
    return t('tenant.formatError')
  }
}

const resetPasswordForm = () => {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  passwordFormRef.value?.clearValidate?.()
}

const openPasswordDialog = async (event: MouseEvent) => {
  passwordOpener = event.currentTarget as HTMLElement
  resetPasswordForm()
  void loadPasswordPolicy()
  passwordDialogVisible.value = true
  await nextTick()
  passwordDialogBody.value?.querySelectorAll<HTMLInputElement>('input[name]').forEach(input => {
    input.id = `${passwordFormId}-${input.name}`
  })
  passwordDialogBody.value?.querySelector<HTMLElement>('input[name="oldPassword"]')?.focus({ preventScroll: true })
}

const restorePasswordFocus = () => {
  passwordOpener?.focus({ preventScroll: true })
  passwordOpener = null
}

const submitPasswordChange = async () => {
  if (passwordSubmitting.value) return
  const result = await passwordFormRef.value?.validate?.()
  if (result !== true) return

  passwordSubmitting.value = true
  try {
    const resp = await changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    })
    if (!resp.success) {
      MessagePlugin.error(resp.message || t('userProfile.changePassword.failed'))
      return
    }

    passwordDialogVisible.value = false
    MessagePlugin.success(t('userProfile.changePassword.success'))
    resetPasswordForm()

    // Backend revokes all sessions on success; mirror that locally and
    // force a fresh login with the new credential.
    try {
      await logoutApi()
    } catch {
      /* ignore — local cleanup still proceeds */
    }
    authStore.logout()
    router.push('/login')
  } catch (err: any) {
    MessagePlugin.error(err?.message || t('userProfile.changePassword.failed'))
  } finally {
    passwordSubmitting.value = false
  }
}

onMounted(loadInfo)
</script>

<style lang="less" scoped>
@import (reference) '@/components/css/settings-section.less';

.user-profile {
  width: 100%;
  container-type: inline-size;
}

.section-header {
  .settings-section-header();
}

.loading-inline {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  justify-content: center;
  color: var(--td-text-color-secondary);
  font-size: var(--app-text-base);
}

.error-inline {
  padding: 20px 0;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.setting-row {
  .setting-row();
}

.setting-info {
  .setting-info();
}

.setting-control {
  .setting-control();

  .info-value {
    font-size: var(--app-text-base);
    color: var(--td-text-color-primary);
    text-align: right;
    word-break: break-word;
  }

  .info-value--muted {
    color: var(--td-text-color-placeholder);
  }

  .edit-btn {
    flex-shrink: 0;
  }
}

.password-mask {
  letter-spacing: 0.12em;
  color: var(--td-text-color-secondary);
}

@container (max-width: 520px) {
  .stacked-setting-rows();

  .setting-control .info-value {
    text-align: start;
    overflow-wrap: anywhere;
  }
}

.password-dialog-hint {
  margin: 0 0 12px;
  font-size: var(--app-text-md);
  line-height: 1.55;
  color: var(--td-text-color-secondary);
}
</style>
