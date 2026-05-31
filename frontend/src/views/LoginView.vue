<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import PasswordInput from '@/components/PasswordInput.vue'
import TextInput from '@/components/TextInput.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const form = ref({ username: '', password: '', totpCode: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')
const totpRequired = ref(false)

async function getDeviceData() {
  const userAgent = navigator.userAgent || undefined
  let deviceName = navigator.userAgentData?.platform || navigator.platform || undefined

  if (navigator.userAgentData?.getHighEntropyValues) {
    try {
      const data = await navigator.userAgentData.getHighEntropyValues([
        'platform',
        'platformVersion',
        'model',
      ])
      const parts = [data.platform, data.platformVersion, data.model].filter(Boolean)
      if (parts.length) deviceName = parts.join(' ')
    } catch (error) {
      console.debug('[auth] high-entropy hints unavailable', error)
    }
  }

  console.debug('[auth] device data', { deviceName, userAgent })
  return { deviceName, userAgent }
}

async function onLogin() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const deviceData = await getDeviceData()
    await auth.login(
      form.value.username,
      form.value.password,
      deviceData.deviceName,
      deviceData.userAgent,
      totpRequired.value ? form.value.totpCode : null,
    )
    success.value = 'Login successful! Redirecting...'
    await new Promise((resolve) => setTimeout(resolve, 1000))
    await router.push(route.query.redirect || '/')
  } catch (e) {
    if (e.status === 401 && e.message === 'totp_required') {
      totpRequired.value = true
      error.value = 'Enter the code from your authenticator app.'
    } else {
      if (e.message === 'totp_required') error.value = 'Two-factor code required.'
      else error.value = e.message
    }
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
      <h2>Login</h2>
      <form @submit.prevent="onLogin" class="space-y-5">
        <TextInput v-model="form.username" label="Username" autocomplete="username" required />
        <PasswordInput
          v-model="form.password"
          label="Password"
          autocomplete="current-password"
          required
        />
        <TextInput
          v-if="totpRequired"
          v-model="form.totpCode"
          label="Two-factor code"
          autocomplete="one-time-code"
          inputmode="numeric"
          placeholder="123456 or backup code"
          required
        />
        <button type="submit" :disabled="loading" class="btn w-full">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <div v-if="error" class="text-red-600 text-center font-medium">{{ error }}</div>
        <div v-if="success" class="text-green-600 text-center font-medium">{{ success }}</div>
        <div class="text-center mt-2">
          <router-link to="/forgot-password" class="text-blue-600 hover:underline"
            >Forgot your password?</router-link
          >
        </div>
        <div class="text-center mt-2">
          <router-link to="/register" class="text-blue-600 hover:underline"
            >Don't have an account? Register</router-link
          >
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped></style>
