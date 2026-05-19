<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../utils/api'
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

async function onLogin() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.login(form.value)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
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
    <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
      <h2 class="text-2xl font-bold mb-6 text-center text-blue-700">Login</h2>
      <form @submit.prevent="onLogin" class="space-y-5">
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Username</label>
          <input
            class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-400 focus:outline-none bg-gray-50"
            v-model="form.username"
            required
            autocomplete="username"
          />
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Password</label>
          <div class="relative">
            <input
              class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-400 focus:outline-none bg-gray-50 pr-10"
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
        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition disabled:opacity-60"
        >
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <div v-if="error" class="text-red-600 text-center font-medium">{{ error }}</div>
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
