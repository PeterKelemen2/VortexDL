<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Modal from '@/components/Modal.vue'
import TwoFactorSettings from '@/components/TwoFactorSettings.vue'
import ApiKeysSettings from '@/components/ApiKeysSettings.vue'

const auth = useAuthStore()

const sessions = ref([])
const loading = ref(false)
const error = ref('')
const successMessage = ref('')
const revokingSessionId = ref(null)
const pendingRevokeSession = ref(null)
const showConfirmModal = ref(false)

async function loadSessions() {
  loading.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const token = auth.accessToken
    sessions.value = await api.getSessions(token, auth.setAccessToken)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function openRevokeModal(session) {
  pendingRevokeSession.value = session
  showConfirmModal.value = true
}

async function revokeSession(session) {
  if (!auth.accessToken) {
    error.value = 'Unable to revoke session: not authenticated.'
    return
  }

  const sessionId = session.id
  const isCurrentSession = Boolean(session.current)

  revokingSessionId.value = sessionId
  error.value = ''
  successMessage.value = ''

  try {
    await api.revokeSession(sessionId, auth.accessToken, auth.setAccessToken)
    if (isCurrentSession) {
      await auth.logout()
      window.location.href = '/login'
      return
    }
    successMessage.value = 'Session revoked successfully.'
    await loadSessions()
  } catch (e) {
    error.value = e.message
  } finally {
    revokingSessionId.value = null
    pendingRevokeSession.value = null
    showConfirmModal.value = false
  }
}

async function confirmRevokeSession() {
  if (!pendingRevokeSession.value) return
  await revokeSession(pendingRevokeSession.value)
}

function cancelRevoke() {
  pendingRevokeSession.value = null
  showConfirmModal.value = false
}

onMounted(loadSessions)
</script>

<template>
  <div>
    <TwoFactorSettings />
    <ApiKeysSettings />
    <div
      class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden"
    >
      <div class="px-5 py-5 sm:px-8 border-b border-slate-200 dark:border-slate-800">
        <p
          class="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500"
        >
          Active sessions
        </p>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
          Manage your active refresh token sessions and revoke any you no longer use.
        </p>
      </div>
      <div class="px-5 py-5 sm:px-8">
        <div v-if="loading" class="text-center py-8 text-slate-600 dark:text-slate-400">
          Loading sessions…
        </div>
        <div v-else-if="error" class="text-center text-red-600 dark:text-red-400 font-medium">
          {{ error }}
        </div>
        <div
          v-else-if="successMessage"
          class="text-center text-green-600 dark:text-green-400 font-medium"
        >
          {{ successMessage }}
        </div>
        <div
          v-else-if="sessions.length === 0"
          class="text-center text-gray-600 dark:text-slate-400"
        >
          No active sessions found.
        </div>

        <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800">
          <li v-for="session in sessions" :key="session.id" class="py-4 first:pt-1 last:pb-0">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div class="flex items-center gap-4">
                  <p class="text-lg font-semibold text-gray-900 dark:text-slate-100">
                    {{ session.resolved_name || 'Unknown host' }}
                  </p>
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="text-sm text-gray-500 dark:text-slate-400">
                      {{ session.device_name || 'Unknown device' }}
                    </p>
                    <span
                      v-if="session.current"
                      class="rounded-full bg-green-100 dark:bg-green-900/40 px-2 py-1 text-xs font-semibold text-green-700 dark:text-green-400"
                    >
                      Current session
                    </span>
                  </div>
                </div>
              </div>
              <div class="text-sm text-gray-500 dark:text-slate-400 text-right">
                <p>Created: {{ new Date(session.created_at).toLocaleString() }}</p>
                <p>
                  Last used:
                  {{
                    session.last_used_at ? new Date(session.last_used_at).toLocaleString() : 'Never'
                  }}
                </p>
              </div>
            </div>
            <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-sm text-gray-600 dark:text-slate-400 wrap-break-word">
                <span class="font-medium">User Agent:</span>
                {{ session.user_agent || 'Not available' }}
              </p>
              <button
                class="inline-flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-50 dark:hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="revokingSessionId === session.id"
                @click="openRevokeModal(session)"
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
    </div>

    <Modal v-model="showConfirmModal" title="Revoke session" @close="cancelRevoke">
      <div class="space-y-4">
        <p class="text-sm text-slate-700 dark:text-slate-300">
          Are you sure you want to revoke this session?
        </p>
        <p class="text-sm text-slate-600 dark:text-slate-400">
          <strong>Host:</strong> {{ pendingRevokeSession?.resolved_name || 'Unknown host' }}<br />
          <strong>Device:</strong> {{ pendingRevokeSession?.device_name || 'Unknown device' }}
        </p>
        <p
          v-if="pendingRevokeSession?.current"
          class="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 px-4 py-3 text-sm text-amber-800 dark:text-amber-300"
        >
          Revoking your current session will sign you out immediately.
        </p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="cancelRevoke"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-red-600 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 focus:ring-red-300"
            :disabled="revokingSessionId === pendingRevokeSession?.id"
            @click="confirmRevokeSession"
          >
            {{ revokingSessionId === pendingRevokeSession?.id ? 'Revoking…' : 'Confirm revoke' }}
          </button>
        </div>
      </div>
    </Modal>
  </div>
</template>
