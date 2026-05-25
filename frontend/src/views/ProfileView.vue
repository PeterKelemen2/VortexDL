<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Modal from '@/components/Modal.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const menuItems = [
  { id: 'profile', label: 'Profile', route: 'profile', query: { tab: 'profile' } },
  { id: 'security', label: 'Security', route: 'profile', query: { tab: 'security' } },
]

const selectedItem = computed(() => {
  const currentTab = String(route.query.tab ?? '')
  return menuItems.find((item) => item.id === currentTab) ?? menuItems[0]
})

const selectedTab = computed(() => selectedItem.value.id)

const profileForm = reactive({
  username: auth.user?.username ?? '',
  currentPassword: '',
})
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  newPasswordConfirm: '',
})

const profileSuccess = ref('')
const profileError = ref('')
const passwordSuccess = ref('')
const passwordError = ref('')
const profileSubmitting = ref(false)
const passwordSubmitting = ref(false)

const sessions = ref([])
const loading = ref(false)
const error = ref('')
const revokingSessionId = ref(null)
const successMessage = ref('')
const showConfirmModal = ref(false)
const pendingRevokeSession = ref(null)

function resetProfileFeedback() {
  profileError.value = ''
  profileSuccess.value = ''
}

function resetPasswordFeedback() {
  passwordError.value = ''
  passwordSuccess.value = ''
}

async function updateProfile() {
  resetProfileFeedback()
  if (!auth.user) {
    profileError.value = 'Unable to update profile: not authenticated.'
    return
  }

  const trimmedUsername = profileForm.username.trim()
  if (trimmedUsername === auth.user.username) {
    profileError.value = 'No changes were made.'
    return
  }

  profileSubmitting.value = true
  try {
    const updatedUser = await api.updateCurrentUser(
      {
        username: trimmedUsername,
        current_password: profileForm.currentPassword,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    auth.user = updatedUser
    profileSuccess.value = 'Username updated successfully.'
    profileForm.currentPassword = ''
  } catch (e) {
    profileError.value = e.message
  } finally {
    profileSubmitting.value = false
  }
}

async function updatePassword() {
  resetPasswordFeedback()
  if (!passwordForm.newPassword) {
    passwordError.value = 'Enter a new password.'
    return
  }

  passwordSubmitting.value = true
  try {
    await api.updateCurrentUser(
      {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
        new_password_confirm: passwordForm.newPasswordConfirm,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    passwordSuccess.value = 'Password updated successfully.'
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.newPasswordConfirm = ''
  } catch (e) {
    passwordError.value = e.message
  } finally {
    passwordSubmitting.value = false
  }
}

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
      router.push({ name: 'login' })
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

watch(
  () => route.query.tab,
  (value) => {
    if (value === 'security' && sessions.value.length === 0) {
      loadSessions()
    }
  },
)

watch(
  () => auth.user?.username,
  (username) => {
    if (username) {
      profileForm.username = username
    }
  },
)

onMounted(() => {
  profileForm.username = auth.user?.username ?? ''
  if (selectedTab.value === 'security') {
    loadSessions()
  }
})

function selectMenuItem(item) {
  router.push({ name: item.route, query: item.query })
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4">
    <div class="grid gap-6 lg:grid-cols-[200px_1fr] items-start">
      <aside class="border-r-2 border-gray-200 bg-white px-3 py-6 h-[calc(100vh-8rem)]">
        <nav class="space-y-2">
          <button
            v-for="item in menuItems"
            :key="item.id"
            @click="selectMenuItem(item)"
            class="w-full rounded-lg px-3 py-2 text-left font-medium transition hover:bg-blue-50 hover:text-blue-700"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="space-y-6 h-[calc(100vh-8rem)] overflow-auto">
        <div class="flex mt-6">
          <h1>{{ selectedItem.label }} settings</h1>
        </div>

        <section v-if="selectedTab === 'profile'" class="space-y-6">
          <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 class="text-xl font-semibold text-slate-900 mb-3">Change username</h2>
            <p class="text-sm text-slate-600 mb-5">
              Update your display username. For security, confirm with your current password.
            </p>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-800 mb-2" for="username">
                  Username
                </label>
                <input
                  id="username"
                  v-model="profileForm.username"
                  type="text"
                  class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-slate-800 mb-2"
                  for="username-current-password"
                >
                  Current password
                </label>
                <input
                  id="username-current-password"
                  v-model="profileForm.currentPassword"
                  type="password"
                  class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p class="text-sm text-slate-600">
                  Your current username is <strong>{{ auth.user?.username }}</strong
                  >.
                </p>
                <button
                  type="button"
                  class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="profileSubmitting"
                  @click="updateProfile"
                >
                  {{ profileSubmitting ? 'Saving…' : 'Save changes' }}
                </button>
              </div>
              <div
                v-if="profileError"
                class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {{ profileError }}
              </div>
              <div
                v-if="profileSuccess"
                class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
              >
                {{ profileSuccess }}
              </div>
            </div>
          </section>

          <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 class="text-xl font-semibold text-slate-900 mb-3">Change password</h2>
            <p class="text-sm text-slate-600 mb-5">
              Use a strong, unique password for your account. Password changes require your current
              password.
            </p>
            <div class="space-y-4">
              <div>
                <label
                  class="block text-sm font-medium text-slate-800 mb-2"
                  for="password-current-password"
                >
                  Current password
                </label>
                <input
                  id="password-current-password"
                  v-model="passwordForm.currentPassword"
                  type="password"
                  class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-800 mb-2" for="new-password">
                  New password
                </label>
                <input
                  id="new-password"
                  v-model="passwordForm.newPassword"
                  type="password"
                  class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-slate-800 mb-2"
                  for="confirm-new-password"
                >
                  Confirm new password
                </label>
                <input
                  id="confirm-new-password"
                  v-model="passwordForm.newPasswordConfirm"
                  type="password"
                  class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p class="text-sm text-slate-600">
                  Password strength must meet the backend policy.
                </p>
                <button
                  type="button"
                  class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="passwordSubmitting"
                  @click="updatePassword"
                >
                  {{ passwordSubmitting ? 'Updating…' : 'Update password' }}
                </button>
              </div>
              <div
                v-if="passwordError"
                class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {{ passwordError }}
              </div>
              <div
                v-if="passwordSuccess"
                class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
              >
                {{ passwordSuccess }}
              </div>
            </div>
          </section>
        </section>

        <section v-else class="space-y-6">
          <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 class="text-xl font-semibold text-slate-900 mb-3">Active sessions</h2>
            <p class="text-sm text-slate-600 mb-5">
              Manage your active refresh token sessions and revoke any device sessions you no longer
              use.
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
                        session.last_used_at
                          ? new Date(session.last_used_at).toLocaleString()
                          : 'Never'
                      }}
                    </p>
                  </div>
                </div>
                <div
                  class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
                >
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
        </section>
      </main>
    </div>

    <Modal v-model="showConfirmModal" title="Revoke session" @close="cancelRevoke">
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
  </div>
</template>

<style scoped></style>
