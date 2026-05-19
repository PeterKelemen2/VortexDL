<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')
const showPassword = ref(false)

async function onLogin() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    success.value = 'Login successful! Redirecting...'
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
      <h2>Login</h2>
      <form @submit.prevent="onLogin" class="space-y-5">
        <div>
          <label>Username</label>
          <input v-model="form.username" required autocomplete="username" />
        </div>
        <div>
          <label>Password</label>
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
        <button type="submit" :disabled="loading" class="btn w-full">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <div v-if="success" class="text-green-600 text-center font-medium">{{ success }}</div>
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
