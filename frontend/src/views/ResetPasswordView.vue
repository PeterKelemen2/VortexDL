<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { usePasswordStrength } from '@/composables/usePasswordStrength'
import PasswordInput from '@/components/PasswordInput.vue'
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter.vue'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))
const form = ref({ new_password: '', new_password_confirm: '' })
const loading = ref(false)
const passwordFocused = ref(false)
const { isPasswordValid } = usePasswordStrength(computed(() => form.value.new_password))

const passwordsMatch = computed(
  () => form.value.new_password && form.value.new_password === form.value.new_password_confirm,
)
const canSubmit = computed(
  () => !loading.value && token.value && isPasswordValid.value && passwordsMatch.value,
)

async function onSubmit() {
  loading.value = true
  try {
    const res = await api.resetPassword({
      token: token.value,
      new_password: form.value.new_password,
      new_password_confirm: form.value.new_password_confirm,
    })
    toast.success(res?.msg || 'Password reset successfully. You can now log in.')
    await router.push('/login')
  } catch (e) {
    toast.error(e.message || 'Reset failed. The link may have expired.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="flex min-h-screen items-center justify-center bg-linear-to-br from-blue-100 to-blue-300 dark:bg-none dark:bg-[#0a0e17]"
  >
    <div class="card">
      <h2>Reset password</h2>

      <div v-if="!token" class="space-y-5 text-center">
        <p class="text-red-600 dark:text-red-400 font-medium">
          This reset link is invalid or incomplete.
        </p>
        <router-link to="/forgot-password" class="text-blue-600 hover:underline">
          Request a new link
        </router-link>
      </div>

      <form v-else @submit.prevent="onSubmit" class="space-y-5">
        <div>
          <PasswordInput
            v-model="form.new_password"
            label="New password"
            autocomplete="new-password"
            required
            @focus="passwordFocused = true"
            @blur="passwordFocused = false"
          />
          <div
            class="overflow-hidden transition-all duration-300 ease-out bg-slate-100 dark:bg-slate-800 rounded-lg mt-2"
            :class="passwordFocused ? 'max-h-[30rem]' : 'max-h-0'"
          >
            <PasswordStrengthMeter
              :password="form.new_password"
              help-text="Password strength must meet the policy."
              class="px-3 py-3"
            />
          </div>
        </div>
        <PasswordInput
          v-model="form.new_password_confirm"
          label="Confirm new password"
          autocomplete="new-password"
          required
        />
        <p
          v-if="form.new_password_confirm && !passwordsMatch"
          class="text-sm text-red-600 dark:text-red-400"
        >
          Passwords do not match.
        </p>
        <button type="submit" :disabled="!canSubmit" class="btn w-full">
          {{ loading ? 'Resetting...' : 'Reset password' }}
        </button>
        <div class="text-center mt-2">
          <router-link to="/login" class="text-blue-600 hover:underline">Back to login</router-link>
        </div>
      </form>
    </div>
  </div>
</template>
