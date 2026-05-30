<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Loader2, CheckCircle2, XCircle } from 'lucide-vue-next'
import { api } from '@/utils/api'

const route = useRoute()
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))

// 'loading' | 'success' | 'error'
const status = ref('loading')
const message = ref('Verifying your email...')

onMounted(async () => {
  if (!token.value) {
    status.value = 'error'
    message.value = 'This verification link is invalid or incomplete.'
    return
  }
  try {
    const res = await api.verifyEmail(token.value)
    status.value = 'success'
    message.value = res?.msg || 'Email verified successfully. You can now log in.'
  } catch (e) {
    status.value = 'error'
    message.value = e.message || 'Verification failed. The link may have expired.'
  }
})
</script>

<template>
  <div
    class="flex min-h-screen items-center justify-center bg-linear-to-br from-blue-100 to-blue-300 dark:bg-none dark:bg-[#0a0e17]"
  >
    <div class="card text-center">
      <h2>Email verification</h2>

      <div class="flex flex-col items-center gap-4 py-2">
        <Loader2 v-if="status === 'loading'" class="h-12 w-12 animate-spin text-blue-500" />
        <CheckCircle2 v-else-if="status === 'success'" class="h-12 w-12 text-green-500" />
        <XCircle v-else class="h-12 w-12 text-red-500" />

        <p
          class="text-slate-700 dark:text-slate-200"
          :class="{
            'text-green-600 dark:text-green-400': status === 'success',
            'text-red-600 dark:text-red-400': status === 'error',
          }"
        >
          {{ message }}
        </p>

        <router-link v-if="status !== 'loading'" to="/login" class="btn mt-2">
          Continue to login
        </router-link>
      </div>
    </div>
  </div>
</template>
