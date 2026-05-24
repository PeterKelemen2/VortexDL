<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'

const router = useRouter()
const auth = useAuthStore()
const sessions = ref([])
const loading = ref(false)
const error = ref('')
const revokingSessionId = ref(null)
const successMessage = ref('')

async function loadSessions() {
  loading.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const token = auth.accessToken
    sessions.value = await api.getSessions(token)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function revokeSession(sessionId) {
  if (!auth.accessToken) {
    error.value = 'Unable to revoke session: not authenticated.'
    return
  }

  const session = sessions.value.find((item) => item.id === sessionId)
  const isCurrentSession = Boolean(session?.current)

  revokingSessionId.value = sessionId
  error.value = ''
  successMessage.value = ''

  try {
    await api.revokeSession(sessionId, auth.accessToken)
    if (isCurrentSession) {
      await auth.logout()
      router.push({ name: 'login' })
      return
    }
    successMessage.value = 'Session revoked successfully.'
    await loadSessions()
  } catch (e) {
    error.value = e.message
  } finally {
    revokingSessionId.value = null
  }
}

onMounted(loadSessions)
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-center text-primary mb-6">Active Sessions</h1>

    <div class="mb-6 text-center text-sm text-gray-600">
      This page shows your currently active refresh token sessions and the device metadata
      associated with each.
    </div>

    <div v-if="loading" class="text-center py-8">Loading sessions…</div>
    <div v-else-if="error" class="text-center text-red-600 font-medium">{{ error }}</div>
    <div v-else-if="successMessage" class="text-center text-green-600 font-medium">
      {{ successMessage }}
    </div>
    <div v-else-if="sessions.length === 0" class="text-center text-gray-600">
      No active sessions found.
    </div>

    <ul v-else class="space-y-4">
      <li
        v-for="session in sessions"
        :key="session.id"
        class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div class="flex items-center gap-4">
              <p class="text-lg font-semibold text-gray-900">
                {{ session.resolved_name || 'Unknown host' }}
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <p class="text-sm text-gray-500">
                  {{ session.device_name || 'Unknown device' }}
                </p>
                <span v-if="session.current" class="rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-700">
                  Current session
                </span>
              </div>
            </div>
          </div>
          <div class="text-sm text-gray-500 text-right">
            <p>Created: {{ new Date(session.created_at).toLocaleString() }}</p>
            <p>
              Last used:
              {{ session.last_used_at ? new Date(session.last_used_at).toLocaleString() : 'Never' }}
            </p>
          </div>
        </div>
        <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-gray-600 wrap-break-word">
            <span class="font-medium">User Agent:</span>
            {{ session.user_agent || 'Not available' }}
          </p>
          <button
            class="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="revokingSessionId === session.id"
            @click="revokeSession(session.id)"
          >
            <span v-if="revokingSessionId === session.id">Revoking…</span>
            <span v-else>
              {{ session.current ? 'Revoke current session' : 'Revoke session' }}
            </span>
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped></style>
