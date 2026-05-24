<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'

const auth = useAuthStore()
const sessions = ref([])
const loading = ref(false)
const error = ref('')

async function loadSessions() {
  loading.value = true
  error.value = ''
  try {
    const token = auth.accessToken
    sessions.value = await api.getSessions(token)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
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
            <p class="text-lg font-semibold text-gray-900">
              {{ session.device_name || 'Unknown device' }}
            </p>
            <p class="text-sm text-gray-500">{{ session.device_os || 'Unknown OS' }}</p>
          </div>
          <div class="text-sm text-gray-500 text-right">
            <p>Created: {{ new Date(session.created_at).toLocaleString() }}</p>
            <p>
              Last used:
              {{ session.last_used_at ? new Date(session.last_used_at).toLocaleString() : 'Never' }}
            </p>
          </div>
        </div>
        <p class="mt-3 text-sm text-gray-600 wrap-break-word">
          <span class="font-medium">User Agent:</span>
          {{ session.user_agent || 'Not available' }}
        </p>
      </li>
    </ul>
  </div>
</template>

<style scoped></style>
