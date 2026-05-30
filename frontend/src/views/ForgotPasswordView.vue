<script setup>
import { computed, ref } from 'vue'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import TextInput from '@/components/TextInput.vue'

const toast = useToast()
const email = ref('')
const loading = ref(false)
const submitted = ref(false)

const canSubmit = computed(() => !loading.value && /.+@.+\..+/.test(email.value))

async function onSubmit() {
  loading.value = true
  try {
    const res = await api.requestPasswordReset(email.value.trim())
    submitted.value = true
    toast.success(res?.msg || 'If that email exists, a reset link has been sent.')
  } catch (e) {
    toast.error(e.message || 'Something went wrong. Please try again.')
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
      <h2>Forgot password</h2>

      <div v-if="submitted" class="space-y-5 text-center">
        <p class="text-slate-600 dark:text-slate-300">
          If an account exists for <span class="font-medium">{{ email }}</span
          >, we've sent a password reset link. Please check your inbox.
        </p>
        <router-link to="/login" class="text-blue-600 hover:underline">Back to login</router-link>
      </div>

      <form v-else @submit.prevent="onSubmit" class="space-y-5">
        <p class="text-sm text-slate-600 dark:text-slate-300">
          Enter your account email and we'll send you a link to reset your password.
        </p>
        <TextInput v-model="email" label="Email" type="email" autocomplete="email" required />
        <button type="submit" :disabled="!canSubmit" class="btn w-full">
          {{ loading ? 'Sending...' : 'Send reset link' }}
        </button>
        <div class="text-center mt-2">
          <router-link to="/login" class="text-blue-600 hover:underline">Back to login</router-link>
        </div>
      </form>
    </div>
  </div>
</template>
