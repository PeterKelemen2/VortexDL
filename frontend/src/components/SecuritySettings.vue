<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Modal from '@/components/Modal.vue'

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
  <section class="space-y-6">
    <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Active sessions</h2>
      <p class="text-sm text-slate-600 mb-5">
        Manage your active refresh token sessions and revoke any device sessions you no longer use.
      </p>

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
                  <span
                    v-if="session.current"
                    class="rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-700"
                  >
                    Current session
                  </span>
                </div>
              </div>
            </div>
            <div class="text-sm text-gray-500 text-right">
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
            <p class="text-sm text-gray-600 wrap-break-word">
              <span class="font-medium">User Agent:</span>
              {{ session.user_agent || 'Not available' }}
            </p>
            <button
              class="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
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
    </section>

    <Modal
      :model-value="showConfirmModal"
      title="Revoke session"
      @update:modelValue="
        (value) => {
          showConfirmModal.value = value
          if (!value) cancelRevoke()
        }
      "
      @close="cancelRevoke"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-700">Are you sure you want to revoke this session?</p>
        <p class="text-sm text-slate-600">
          <strong>Host:</strong> {{ pendingRevokeSession?.resolved_name || 'Unknown host' }}<br />
          <strong>Device:</strong> {{ pendingRevokeSession?.device_name || 'Unknown device' }}
        </p>
        <p
          v-if="pendingRevokeSession?.current"
          class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          Revoking your current session will sign you out immediately.
        </p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="btn bg-white text-slate-700 border border-slate-300 hover:bg-slate-100"
            @click="cancelRevoke"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-primary text-white hover:bg-primary-dark"
            :disabled="revokingSessionId === pendingRevokeSession?.id"
            @click="confirmRevokeSession"
          >
            {{ revokingSessionId === pendingRevokeSession?.id ? 'Revoking…' : 'Confirm revoke' }}
          </button>
        </div>
      </div>
    </Modal>
  </section>
</template>
