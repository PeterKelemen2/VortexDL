<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../utils/api'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', email: '', password: '', password_confirm: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')
const showPassword = ref(false)
const showPasswordConf = ref(false)

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

async function onRegister() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (form.value.password !== form.value.password_confirm) {
      throw new Error('Passwords do not match')
    }
    await api.register(form.value)
    const deviceData = await getDeviceData()
    await auth.login(form.value.username, form.value.password, deviceData.deviceName, deviceData.userAgent)
    success.value = 'Registration successful! Redirecting...'
    await new Promise((resolve) => setTimeout(resolve, 1000))
    await router.push('/')
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
      <h2>Register</h2>
      <form @submit.prevent="onRegister" class="space-y-5">
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Username</label>
          <input v-model="form.username" required autocomplete="username" />
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Email</label>
          <input v-model="form.email" type="email" autocomplete="email" />
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Password</label>
          <div class="relative">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              autocomplete="current-password"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 p-1"
              tabindex="-1"
              aria-label="Toggle password visibility"
            >
              <component :is="showPassword ? EyeOff : Eye" class="w-5 h-5" />
            </button>
          </div>
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Confirm Password</label>
          <div class="relative">
            <input
              v-model="form.password_confirm"
              :type="showPasswordConf ? 'text' : 'password'"
              required
              autocomplete="new-password"
            />
            <button
              type="button"
              @click="showPasswordConf = !showPasswordConf"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 p-1"
              tabindex="-1"
              aria-label="Toggle password visibility"
            >
              <component :is="showPasswordConf ? EyeOff : Eye" class="w-5 h-5" />
            </button>
          </div>
        </div>

        <button type="submit" :disabled="loading" class="btn w-full">
          {{ loading ? 'Registering...' : 'Register' }}
        </button>
        <div v-if="success" class="text-green-600 text-center font-medium">{{ success }}</div>
        <div v-if="error" class="text-red-600 text-center font-medium">{{ error }}</div>
        <div class="text-center mt-2">
          <router-link to="/login" class="text-blue-600 hover:underline"
            >Already have an account? Login</router-link
          >
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped></style>
