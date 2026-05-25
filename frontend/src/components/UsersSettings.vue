<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Modal from '@/components/Modal.vue'
import TextInput from '@/components/TextInput.vue'
import PasswordInput from '@/components/PasswordInput.vue'

const auth = useAuthStore()
const users = ref([])
const roles = ref([])
const loadingUsers = ref(false)
const loadingRoles = ref(false)
const pageError = ref('')
const pageSuccess = ref('')

const modalOpen = ref(false)
const currentAction = ref('')
const currentUser = ref(null)
const actionError = ref('')
const actionSuccess = ref('')
const actionSubmitting = ref(false)
const confirmEmailInput = ref('')

const actionForm = reactive({
  username: '',
  newPassword: '',
  newPasswordConfirm: '',
  role: '',
})

const actionDetails = {
  editUsername: {
    title: 'Change username',
    description: 'Update a user’s username and confirm the target email before saving.',
  },
  changePassword: {
    title: 'Change password',
    description: 'Set a new password for a user. This action requires email confirmation.',
  },
  changeRole: {
    title: 'Change role',
    description: 'Assign a new role to a user. This action requires email confirmation.',
  },
  deleteUser: {
    title: 'Delete user',
    description: 'Permanently delete this user account. Type the user email to confirm.',
  },
}

const actionLabel = computed(() => {
  if (currentAction.value === 'deleteUser') return 'Delete user'
  return 'Save changes'
})

const roleOptions = computed(() => {
  if (roles.value.length) return roles.value
  return ['user', 'admin']
})

function resetActionState() {
  actionError.value = ''
  actionSuccess.value = ''
  actionSubmitting.value = false
  confirmEmailInput.value = ''
  actionForm.username = ''
  actionForm.newPassword = ''
  actionForm.newPasswordConfirm = ''
  actionForm.role = currentUser.value?.role ?? ''
}

function openAction(user, actionType) {
  currentUser.value = user
  currentAction.value = actionType
  actionForm.username = user.username
  actionForm.role = user.role
  actionForm.newPassword = ''
  actionForm.newPasswordConfirm = ''
  confirmEmailInput.value = ''
  actionError.value = ''
  actionSuccess.value = ''
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  currentAction.value = ''
  currentUser.value = null
  resetActionState()
}

async function loadUsers() {
  loadingUsers.value = true
  pageError.value = ''
  try {
    users.value = await api.listUsers(auth.accessToken, auth.setAccessToken)
  } catch (error) {
    pageError.value = error.message || 'Unable to load users.'
  } finally {
    loadingUsers.value = false
  }
}

async function loadRoles() {
  loadingRoles.value = true
  try {
    const roleData = await api.getAdminRoles(auth.accessToken, auth.setAccessToken)
    roles.value = roleData.map((role) => role.name)
  } catch {
    roles.value = ['user', 'admin']
  } finally {
    loadingRoles.value = false
  }
}

async function submitAction() {
  if (!currentUser.value) return
  actionError.value = ''
  actionSuccess.value = ''

  const trimmedEmail = confirmEmailInput.value.trim()
  if (!trimmedEmail) {
    actionError.value = 'Enter the user email to confirm.'
    return
  }

  const payload = { confirm_email: trimmedEmail }

  if (currentAction.value === 'editUsername') {
    const username = actionForm.username.trim()
    if (!username) {
      actionError.value = 'Username cannot be empty.'
      return
    }
    payload.username = username
  }

  if (currentAction.value === 'changePassword') {
    if (!actionForm.newPassword) {
      actionError.value = 'Enter a new password.'
      return
    }
    if (actionForm.newPassword !== actionForm.newPasswordConfirm) {
      actionError.value = 'Password confirmation does not match.'
      return
    }
    payload.new_password = actionForm.newPassword
    payload.new_password_confirm = actionForm.newPasswordConfirm
  }

  if (currentAction.value === 'changeRole') {
    if (!actionForm.role) {
      actionError.value = 'Choose a role.'
      return
    }
    payload.role = actionForm.role
  }

  actionSubmitting.value = true
  try {
    if (currentAction.value === 'deleteUser') {
      await api.deleteUserByAdmin(
        currentUser.value.id,
        payload,
        auth.accessToken,
        auth.setAccessToken,
      )
      actionSuccess.value = 'User deleted successfully.'
    } else {
      await api.updateUserByAdmin(
        currentUser.value.id,
        payload,
        auth.accessToken,
        auth.setAccessToken,
      )
      actionSuccess.value = 'User updated successfully.'
    }
    await loadUsers()
    if (currentAction.value === 'deleteUser') {
      closeModal()
      pageSuccess.value = 'User deleted successfully.'
    } else {
      confirmEmailInput.value = ''
    }
  } catch (error) {
    actionError.value = error.message || 'Failed to complete action.'
  } finally {
    actionSubmitting.value = false
  }
}

onMounted(async () => {
  if (!auth.isAdmin) return
  await Promise.all([loadUsers(), loadRoles()])
})
</script>

<template>
  <section class="space-y-6">
    <section class="rounded-3xl border border-gray-200 bg-white p-4 lg:p-6 shadow-sm">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-center">
        <div>
          <h2 class="text-xl font-semibold text-slate-900">User management</h2>
          <p class="text-sm text-slate-600 mt-1">
            View all accounts, change roles, update usernames or passwords, and delete users when
            needed.
          </p>
        </div>
      </div>

      <div
        v-if="pageError"
        class="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        {{ pageError }}
      </div>
      <div
        v-if="pageSuccess"
        class="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
      >
        {{ pageSuccess }}
      </div>

      <div
        v-if="!auth.isAdmin"
        class="mt-6 rounded-2xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800"
      >
        You do not have permission to manage users.
      </div>

      <div v-else class="mt-6">
        <div v-if="loadingUsers" class="text-center py-8 text-slate-600">Loading users…</div>

        <div
          v-else-if="users.length === 0"
          class="rounded-2xl border border-gray-200 bg-gray-50 p-6 text-center text-slate-600"
        >
          No users found.
        </div>

        <div v-else class="space-y-4">
          <div class="overflow-hidden rounded-3xl border border-gray-200">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left text-sm font-semibold text-slate-700">Username</th>
                  <th class="px-4 py-3 text-left text-sm font-semibold text-slate-700">Email</th>
                  <th class="px-4 py-3 text-left text-sm font-semibold text-slate-700">Role</th>
                  <th class="px-4 py-3 text-right text-sm font-semibold text-slate-700">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="user in users" :key="user.id">
                  <td class="px-4 py-3 text-sm text-slate-700">{{ user.username }}</td>
                  <td class="px-4 py-3 text-sm text-slate-500 wrap-break-word">{{ user.email }}</td>
                  <td class="px-4 py-3 text-sm text-slate-700">{{ user.role }}</td>
                  <td class="px-4 py-3 text-sm text-right text-slate-700">
                    <div class="flex flex-wrap justify-end gap-2">
                      <button
                        type="button"
                        class="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        @click="openAction(user, 'editUsername')"
                      >
                        Edit name
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        @click="openAction(user, 'changePassword')"
                      >
                        Change password
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        @click="openAction(user, 'changeRole')"
                      >
                        Change role
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center rounded-xl border border-red-200 bg-red-50 px-3 py-1 text-xs font-medium text-red-700 transition hover:bg-red-100"
                        @click="openAction(user, 'deleteUser')"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <Modal
      :model-value="modalOpen"
      :title="actionDetails[currentAction]?.title || 'Manage user'"
      @update:modelValue="
        (value) => {
          modalOpen = value
          if (!value) closeModal()
        }
      "
      @close="closeModal"
    >
      <div v-if="currentUser" class="space-y-4">
        <p class="text-sm text-slate-600">{{ actionDetails[currentAction]?.description }}</p>

        <div v-if="currentAction === 'editUsername'" class="space-y-4">
          <TextInput
            v-model="actionForm.username"
            label="New username"
            autocomplete="username"
            required
          />
        </div>

        <div v-if="currentAction === 'changePassword'" class="space-y-4">
          <PasswordInput
            v-model="actionForm.newPassword"
            label="New password"
            autocomplete="new-password"
            required
          />
          <PasswordInput
            v-model="actionForm.newPasswordConfirm"
            label="Confirm password"
            autocomplete="new-password"
            required
          />
        </div>

        <div v-if="currentAction === 'changeRole'" class="space-y-4">
          <label class="block text-sm font-medium text-slate-700">Role</label>
          <select
            v-model="actionForm.role"
            class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-slate-400"
          >
            <option value="" disabled>Select role</option>
            <option v-for="role in roleOptions" :key="role" :value="role">{{ role }}</option>
          </select>
        </div>

        <div class="space-y-2">
          <TextInput
            v-model="confirmEmailInput"
            label="Confirm user email"
            autocomplete="email"
            placeholder="Type the user's email to confirm"
            required
          />
          <p class="text-sm text-slate-500">
            This action requires typing the exact email address of
            <strong>{{ currentUser.email }}</strong
            >.
          </p>
        </div>

        <div
          v-if="actionError"
          class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {{ actionError }}
        </div>
        <div
          v-if="actionSuccess"
          class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {{ actionSuccess }}
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="btn bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
            @click="closeModal"
            :disabled="actionSubmitting"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-primary text-white hover:bg-primary-dark"
            :disabled="actionSubmitting"
            @click="submitAction"
          >
            {{ actionSubmitting ? 'Saving…' : actionLabel }}
          </button>
        </div>
      </div>
    </Modal>
  </section>
</template>

<style scoped></style>
