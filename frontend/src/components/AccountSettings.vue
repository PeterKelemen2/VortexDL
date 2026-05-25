<script setup>
import { ref, reactive, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import PasswordInput from '@/components/PasswordInput.vue'
import TextInput from '@/components/TextInput.vue'

const auth = useAuthStore()

const profileForm = reactive({
  username: auth.user?.username ?? '',
  currentPassword: '',
})
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  newPasswordConfirm: '',
})

const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const profileSubmitting = ref(false)
const passwordSubmitting = ref(false)

function resetProfileFeedback() {
  profileError.value = ''
  profileSuccess.value = ''
}

function resetPasswordFeedback() {
  passwordError.value = ''
  passwordSuccess.value = ''
}

watch(
  () => auth.user?.username,
  (username) => {
    if (username) {
      profileForm.username = username
    }
  },
)

async function updateProfile() {
  resetProfileFeedback()
  if (!auth.user) {
    profileError.value = 'Unable to update profile: not authenticated.'
    return
  }

  const trimmedUsername = profileForm.username.trim()
  if (trimmedUsername === auth.user.username) {
    profileError.value = 'No changes were made.'
    return
  }

  profileSubmitting.value = true
  try {
    const updatedUser = await api.updateCurrentUser(
      {
        username: trimmedUsername,
        current_password: profileForm.currentPassword,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    auth.user = updatedUser
    profileSuccess.value = 'Username updated successfully.'
    profileForm.currentPassword = ''
  } catch (e) {
    profileError.value = e.message
  } finally {
    profileSubmitting.value = false
  }
}

async function updatePassword() {
  resetPasswordFeedback()
  if (!passwordForm.newPassword) {
    passwordError.value = 'Enter a new password.'
    return
  }

  passwordSubmitting.value = true
  try {
    await api.updateCurrentUser(
      {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
        new_password_confirm: passwordForm.newPasswordConfirm,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    passwordSuccess.value = 'Password updated successfully.'
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.newPasswordConfirm = ''
  } catch (e) {
    passwordError.value = e.message
  } finally {
    passwordSubmitting.value = false
  }
}
</script>

<template>
  <section class="space-y-6">
    <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Account</h2>
      <p class="text-sm text-slate-600 mb-5">
        Update your account name and confirm changes with your current password.
      </p>
      <div class="space-y-4">
        <TextInput
          v-model="profileForm.username"
          label="Username"
          autocomplete="username"
          required
        />
        <PasswordInput
          v-model="profileForm.currentPassword"
          label="Password"
          autocomplete="current-password"
          required
        />

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600">
            Your current username is <strong>{{ auth.user?.username }}</strong
            >.
          </p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="profileSubmitting"
            @click="updateProfile"
          >
            {{ profileSubmitting ? 'Saving…' : 'Save changes' }}
          </button>
        </div>
        <div
          v-if="profileError"
          class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {{ profileError }}
        </div>
        <div
          v-if="profileSuccess"
          class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {{ profileSuccess }}
        </div>
      </div>
    </section>

    <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Change password</h2>
      <p class="text-sm text-slate-600 mb-5">
        Use a strong, unique password for your account. Password changes require your current
        password.
      </p>
      <div class="space-y-4">
        <PasswordInput
          v-model="passwordForm.currentPassword"
          label="Current password"
          autocomplete="password-current-password"
          required
        />
        <PasswordInput
          v-model="passwordForm.newPassword"
          label="New password"
          autocomplete="password-new-password"
          required
        />
        <PasswordInput
          v-model="passwordForm.newPasswordConfirm"
          label="Confirm new password"
          autocomplete="password-confirm-new"
          required
        />

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600">Password strength must meet the backend policy.</p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="passwordSubmitting"
            @click="updatePassword"
          >
            {{ passwordSubmitting ? 'Updating…' : 'Update password' }}
          </button>
        </div>
        <div
          v-if="passwordError"
          class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {{ passwordError }}
        </div>
        <div
          v-if="passwordSuccess"
          class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {{ passwordSuccess }}
        </div>
      </div>
    </section>
  </section>
</template>
