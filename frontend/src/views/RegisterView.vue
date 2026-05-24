<script setup>
import { computed, ref } from 'vue'
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
const confirmFocused = ref(false)
const confirmTouched = ref(false)

const strengthCriteria = computed(() => {
  const password = form.value.password || ''
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)
  return [
    { label: 'At least 12 characters', valid: password.length >= 12, mandatory: true },
    { label: 'No spaces', valid: /^\S+$/.test(password), mandatory: true },
    { label: 'An uppercase letter', valid: /[A-Z]/.test(password), mandatory: true },
    { label: 'A lowercase letter', valid: /[a-z]/.test(password), mandatory: false },
    { label: 'A number', valid: hasNumber, mandatory: false },
    { label: 'A special character', valid: hasSpecial, mandatory: false },
  ]
})

const passwordStrengthScore = computed(() => {
  const password = form.value.password || ''
  const lengthValid = password.length >= 12
  const noSpacesValid = /^\S+$/.test(password)
  const hasUppercase = /[A-Z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)

  if (!lengthValid || !noSpacesValid || !hasUppercase) return 0
  if (hasNumber && hasSpecial) return 3
  if (hasNumber || hasSpecial) return 2
  return 1
})

const passwordStrengthLabel = computed(() => {
  const password = form.value.password || ''
  if (!password) return 'Enter password'

  const lengthValid = strengthCriteria.value[0].valid
  const noSpacesValid = strengthCriteria.value[1].valid
  const hasUppercase = strengthCriteria.value[2].valid
  const hasNumber = strengthCriteria.value[4].valid
  const hasSpecial = strengthCriteria.value[5].valid
  const score = passwordStrengthScore.value

  if (!lengthValid) return 'Too short'
  if (!noSpacesValid) return 'No spaces allowed'
  if (!hasUppercase) return 'Add an uppercase letter'
  if (!hasNumber && !hasSpecial) return 'Add a number or special character'
  if (score === 1) return 'Weak'
  if (score === 2) return 'Acceptable'
  return 'Strong'
})

const mandatoryCriteria = computed(() => strengthCriteria.value.filter((item) => item.mandatory))
const isPasswordValid = computed(
  () => mandatoryCriteria.value.every((item) => item.valid) && passwordStrengthScore.value >= 2,
)
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
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Username</label>
          <input v-model="form.username" required autocomplete="username" />
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Email</label>
          <input v-model="form.email" type="email" required autocomplete="email" />
        </div>
        <div>
          <label class="block text-gray-700 mb-1 font-medium">Password</label>
          <div class="relative">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              autocomplete="new-password"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 p-1"
              aria-label="Toggle password visibility"
            >
              <component :is="showPassword ? EyeOff : Eye" class="w-5 h-5" />
            </button>
          </div>
          <div class="mt-3">
            <div class="flex items-center justify-between text-sm text-gray-600 mb-1">
              <span>Password strength</span>
              <span
                class="font-semibold transition-colors"
                :class="{
                  'text-red-600': !isPasswordValid,
                  'text-green-600': isPasswordValid,
                }"
                >{{ passwordStrengthLabel }}</span
              >
            </div>
            <div
              class="h-2 w-full border border-slate-300 bg-slate-200 rounded-full overflow-hidden"
            >
              <div
                class="h-full rounded-full transition-all"
                :style="{
                  width: `${(passwordStrengthScore / 3) * 100}%`,
                  backgroundColor: isPasswordValid
                    ? '#16a34a'
                    : passwordStrengthScore === 2
                      ? '#eab308'
                      : '#ef4444',
                }"
              />
            </div>
            <ul class="mt-2 space-y-1 text-xs text-gray-600">
              <li
                v-for="(rule, index) in strengthCriteria"
                :key="index"
                :class="rule.valid ? 'text-green-700' : 'text-gray-500'"
              >
                <span class="mr-2" :aria-hidden="true">{{ rule.valid ? '✓' : '•' }}</span>
                {{ rule.label }}
              </li>
            </ul>
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
              @focus="confirmFocused = true"
              @blur="confirmTouched = true"
            />
            <button
              type="button"
              @click="showPasswordConf = !showPasswordConf"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 p-1"
              aria-label="Toggle password visibility"
            >
              <component :is="showPasswordConf ? EyeOff : Eye" class="w-5 h-5" />
            </button>
          </div>
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
