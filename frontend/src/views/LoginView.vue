<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import PasswordInput from '@/components/PasswordInput.vue'
import TextInput from '@/components/TextInput.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')

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
    )
    success.value = 'Login successful! Redirecting...'
    await new Promise((resolve) => setTimeout(resolve, 1000))
    await router.push(route.query.redirect || '/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="flex min-h-screen items-center justify-center bg-linear-to-br from-blue-100 to-blue-300"
  >
    <div class="card bg-primary-light">
      <h2>Login</h2>
      <form @submit.prevent="onLogin" class="space-y-5">
        <TextInput
          v-model="form.username"
          label="Username"
          autocomplete="username"
          required
        />
        <PasswordInput
          v-model="form.password"
          label="Password"
          autocomplete="current-password"
          required
        />
        <button type="submit" :disabled="loading" class="btn w-full">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <div v-if="error" class="text-red-600 text-center font-medium">{{ error }}</div>
        <div v-if="success" class="text-green-600 text-center font-medium">{{ success }}</div>
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
