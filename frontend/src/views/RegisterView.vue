<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../utils/api'
import { useAuthStore } from '@/stores/auth'
import PasswordInput from '@/components/PasswordInput.vue'
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter.vue'
import TextInput from '@/components/TextInput.vue'
import { usePasswordStrength } from '@/composables/usePasswordStrength'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', email: '', password: '', password_confirm: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')
const confirmFocused = ref(false)
const confirmTouched = ref(false)
const passwordFocused = ref(false)
const { isPasswordValid } = usePasswordStrength(computed(() => form.value.password))

const showConfirmMismatch = computed(
  () =>
    isPasswordValid.value &&
    (confirmFocused.value || confirmTouched.value) &&
    form.value.password_confirm &&
    form.value.password !== form.value.password_confirm,
)
const canSubmit = computed(() => {
  return (
    !loading.value &&
    form.value.username &&
    form.value.email &&
    form.value.password &&
    form.value.password_confirm &&
    form.value.password === form.value.password_confirm &&
    isPasswordValid.value
  )
})

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
    await auth.login(
      form.value.username,
      form.value.password,
      deviceData.deviceName,
      deviceData.userAgent,
    )
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
        <TextInput v-model="form.username" label="Username" autocomplete="username" required />
        <TextInput v-model="form.email" label="Email" type="email" autocomplete="email" required />
        <div>
          <PasswordInput
            v-model="form.password"
            label="Password"
            autocomplete="new-password"
            required
            @focus="passwordFocused = true"
            @blur="passwordFocused = false"
          />

          <div
            class="overflow-hidden transition-all duration-300 ease-out bg-slate-100 rounded-lg mt-2"
            :class="passwordFocused ? 'max-h-[30rem]' : 'max-h-0'"
          >
            <PasswordStrengthMeter
              :password="form.password"
              help-text="Password strength must meet the policy."
              class="px-3 py-3"
            />
          </div>
        </div>
        <div>
          <PasswordInput
            v-model="form.password_confirm"
            label="Confirm Password"
            autocomplete="new-password"
            required
            @focus="confirmFocused = true"
            @blur="confirmTouched = true"
          />
          <div v-if="showConfirmMismatch" class="text-sm font-semibold text-red-600 mt-2">
            Passwords do not match.
          </div>
        </div>

        <button type="submit" :disabled="!canSubmit" class="btn w-full">
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
