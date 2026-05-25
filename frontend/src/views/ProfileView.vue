<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import AccountSettings from '@/components/AccountSettings.vue'
import SecuritySettings from '@/components/SecuritySettings.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const menuItems = [
  { id: 'account', label: 'Account', route: 'profile', query: { tab: 'account' } },
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

        <AccountSettings
          v-if="selectedTab === 'account'"
          :profile-form="profileForm"
          :password-form="passwordForm"
          :auth-user="auth.user"
          :profile-error="profileError"
          :profile-success="profileSuccess"
          :profile-submitting="profileSubmitting"
          :password-error="passwordError"
          :password-success="passwordSuccess"
          :password-submitting="passwordSubmitting"
          @update-profile="updateProfile"
          @update-password="updatePassword"
        />

        <SecuritySettings
          v-else
          :sessions="sessions"
          :loading="loading"
          :error="error"
          :success-message="successMessage"
          :revoking-session-id="revokingSessionId"
          :pending-revoke-session="pendingRevokeSession"
          :show-confirm-modal="showConfirmModal"
          @open-revoke-modal="openRevokeModal"
          @confirm-revoke-session="confirmRevokeSession"
          @cancel-revoke="cancelRevoke"
        />
      </main>
    </div>
  </div>
</template>

<style scoped></style>
