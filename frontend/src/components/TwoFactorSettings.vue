<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import Modal from '@/components/Modal.vue'
import TextInput from '@/components/TextInput.vue'
import PasswordInput from '@/components/PasswordInput.vue'
import { ShieldCheck, ShieldOff, Copy, Check } from 'lucide-vue-next'

const auth = useAuthStore()
const toast = useToast()

const loading = ref(true)
const enabled = ref(false)

// Enrollment state
const showSetup = ref(false)
const setupData = ref(null) // { secret, otpauth_uri, qr_code, backup_codes }
const verifyCode = ref('')
const verifying = ref(false)
const setupError = ref('')

// Disable state
const showDisable = ref(false)
const disablePassword = ref('')
const disabling = ref(false)
const disableError = ref('')

const copied = ref(false)

function tokenArgs() {
  return [auth.accessToken, auth.setAccessToken]
}

async function loadStatus() {
  loading.value = true
  try {
    const res = await api.getTwoFactorStatus(...tokenArgs())
    enabled.value = Boolean(res.enabled)
  } catch (e) {
    toast.error(e.message || 'Failed to load 2FA status')
  } finally {
    loading.value = false
  }
}

async function beginSetup() {
  setupError.value = ''
  verifyCode.value = ''
  try {
    setupData.value = await api.setupTwoFactor(...tokenArgs())
    showSetup.value = true
  } catch (e) {
    toast.error(e.message || 'Failed to start 2FA setup')
  }
}

async function confirmSetup() {
  if (!verifyCode.value.trim()) {
    setupError.value = 'Enter the 6-digit code from your authenticator app.'
    return
  }
  verifying.value = true
  setupError.value = ''
  try {
    await api.verifyTwoFactor(verifyCode.value.trim(), ...tokenArgs())
    enabled.value = true
    showSetup.value = false
    toast.success('Two-factor authentication enabled')
  } catch (e) {
    setupError.value = e.message || 'Invalid code'
  } finally {
    verifying.value = false
  }
}

async function confirmDisable() {
  if (!disablePassword.value) {
    disableError.value = 'Enter your password to disable 2FA.'
    return
  }
  disabling.value = true
  disableError.value = ''
  try {
    await api.disableTwoFactor(disablePassword.value, ...tokenArgs())
    enabled.value = false
    showDisable.value = false
    disablePassword.value = ''
    toast.success('Two-factor authentication disabled')
  } catch (e) {
    disableError.value = e.message || 'Failed to disable 2FA'
  } finally {
    disabling.value = false
  }
}

async function copyBackupCodes() {
  if (!setupData.value?.backup_codes) return
  try {
    await navigator.clipboard.writeText(setupData.value.backup_codes.join('\n'))
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    toast.error('Could not copy to clipboard')
  }
}

onMounted(loadStatus)
</script>

<template>
  <div
    class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden mb-6"
  >
    <div class="px-5 py-5 sm:px-8 border-b border-slate-200 dark:border-slate-800">
      <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
        Two-factor authentication
      </p>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
        Add an extra layer of security using a time-based one-time password (TOTP) app.
      </p>
    </div>

    <div class="px-5 py-5 sm:px-8">
      <div v-if="loading" class="text-slate-600 dark:text-slate-400">Loading…</div>

      <div v-else class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-3">
          <component
            :is="enabled ? ShieldCheck : ShieldOff"
            :class="['w-6 h-6', enabled ? 'text-green-600 dark:text-green-400' : 'text-slate-400']"
          />
          <div>
            <p class="font-semibold text-slate-900 dark:text-slate-100">
              {{ enabled ? 'Enabled' : 'Disabled' }}
            </p>
            <p class="text-sm text-slate-500 dark:text-slate-400">
              {{
                enabled
                  ? 'A code from your authenticator app is required at login.'
                  : 'Protect your account with an authenticator app.'
              }}
            </p>
          </div>
        </div>

        <button
          v-if="!enabled"
          type="button"
          class="btn bg-blue-600 hover:bg-blue-700 text-white"
          @click="beginSetup"
        >
          Enable 2FA
        </button>
        <button
          v-else
          type="button"
          class="btn bg-red-600 hover:bg-red-700 text-white"
          @click="showDisable = true"
        >
          Disable 2FA
        </button>
      </div>
    </div>

    <!-- Setup modal -->
    <Modal v-model="showSetup" title="Set up two-factor authentication" @close="showSetup = false">
      <div v-if="setupData" class="space-y-5">
        <div>
          <p class="text-sm text-slate-700 dark:text-slate-300 mb-3">
            1. Scan this QR code with your authenticator app (Google Authenticator, Authy,
            1Password…).
          </p>
          <div class="flex justify-center">
            <img
              :src="setupData.qr_code"
              alt="2FA QR code"
              class="w-44 h-44 rounded-lg border border-slate-200 dark:border-slate-700 bg-white"
            />
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-2 text-center">
            Or enter this secret manually:
            <span class="font-mono break-all">{{ setupData.secret }}</span>
          </p>
        </div>

        <div>
          <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            2. Save your backup codes
          </p>
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
            Each code can be used once if you lose access to your authenticator. Store them safely —
            they won't be shown again.
          </p>
          <div
            class="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 grid grid-cols-2 gap-1.5 font-mono text-sm"
          >
            <span
              v-for="code in setupData.backup_codes"
              :key="code"
              class="text-slate-700 dark:text-slate-200"
              >{{ code }}</span
            >
          </div>
          <button
            type="button"
            class="mt-2 inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            @click="copyBackupCodes"
          >
            <component :is="copied ? Check : Copy" class="w-4 h-4" />
            {{ copied ? 'Copied' : 'Copy codes' }}
          </button>
        </div>

        <div>
          <TextInput
            v-model="verifyCode"
            label="3. Enter the 6-digit code to confirm"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="8"
            placeholder="123456"
            class="font-mono tracking-widest"
            @keyup.enter="confirmSetup"
          />
          <p v-if="setupError" class="text-sm text-red-600 dark:text-red-400 mt-2">
            {{ setupError }}
          </p>
        </div>

        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="showSetup = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-blue-600 hover:bg-blue-700 text-white"
            :disabled="verifying"
            @click="confirmSetup"
          >
            {{ verifying ? 'Verifying…' : 'Enable' }}
          </button>
        </div>
      </div>
    </Modal>

    <!-- Disable modal -->
    <Modal
      v-model="showDisable"
      title="Disable two-factor authentication"
      @close="showDisable = false"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-700 dark:text-slate-300">
          Enter your password to turn off two-factor authentication. Your account will be less
          secure.
        </p>
        <PasswordInput
          v-model="disablePassword"
          label="Current password"
          autocomplete="current-password"
          placeholder="Current password"
          @keyup.enter="confirmDisable"
        />
        <p v-if="disableError" class="text-sm text-red-600 dark:text-red-400">{{ disableError }}</p>
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="showDisable = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-red-600 hover:bg-red-700 text-white"
            :disabled="disabling"
            @click="confirmDisable"
          >
            {{ disabling ? 'Disabling…' : 'Disable 2FA' }}
          </button>
        </div>
      </div>
    </Modal>
  </div>
</template>
