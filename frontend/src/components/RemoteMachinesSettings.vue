<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Modal from '@/components/Modal.vue'
import TextInput from '@/components/TextInput.vue'
import { Server, Plug, Users, Pencil, Trash2, Loader2, CheckCircle2 } from 'lucide-vue-next'

const auth = useAuthStore()
const toast = useToast()
const { confirm } = useConfirm()

const machines = ref([])
const loading = ref(true)
const testingId = ref(null)

const showForm = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formError = ref('')

const form = reactive({
  name: '',
  host: '',
  port: 22,
  username: '',
  auth_type: 'password',
  password: '',
  ssh_key_path: '',
  download_folder: '',
  is_active: true,
})

// --- assignment management ---
const showUsers = ref(false)
const usersMachine = ref(null)
const assignedUsers = ref([])
const allUsers = ref([])
const assignUserId = ref(null)
const usersLoading = ref(false)

const selectClass =
  'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

function tokenArgs() {
  return [auth.accessToken, auth.setAccessToken]
}

async function load() {
  loading.value = true
  try {
    const res = await api.adminListRemoteMachines({ page: 1, pageSize: 100 }, ...tokenArgs())
    machines.value = res.items
  } catch (e) {
    toast.error(e.message || 'Failed to load remote machines')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    host: '',
    port: 22,
    username: '',
    auth_type: 'password',
    password: '',
    ssh_key_path: '',
    download_folder: '',
    is_active: true,
  })
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  resetForm()
  showForm.value = true
}

function openEdit(machine) {
  editingId.value = machine.id
  formError.value = ''
  Object.assign(form, {
    name: machine.name,
    host: machine.host,
    port: machine.port,
    username: machine.username,
    auth_type: machine.auth_type,
    password: '',
    ssh_key_path: machine.ssh_key_path || '',
    download_folder: machine.download_folder,
    is_active: machine.is_active,
  })
  showForm.value = true
}

async function save() {
  saving.value = true
  formError.value = ''
  try {
    const payload = {
      name: form.name.trim(),
      host: form.host.trim(),
      port: Number(form.port) || 22,
      username: form.username.trim(),
      auth_type: form.auth_type,
      download_folder: form.download_folder.trim(),
      is_active: form.is_active,
    }
    if (form.auth_type === 'password') {
      if (form.password) payload.password = form.password
    } else {
      payload.ssh_key_path = form.ssh_key_path.trim()
    }

    if (editingId.value) {
      await api.adminUpdateRemoteMachine(editingId.value, payload, ...tokenArgs())
      toast.success('Remote machine updated')
    } else {
      await api.adminCreateRemoteMachine(payload, ...tokenArgs())
      toast.success('Remote machine created')
    }
    showForm.value = false
    await load()
  } catch (e) {
    formError.value = e.message || 'Failed to save remote machine'
  } finally {
    saving.value = false
  }
}

async function testConnection(machine) {
  testingId.value = machine.id
  try {
    const res = await api.adminTestRemoteMachine(machine.id, ...tokenArgs())
    if (res.success) {
      toast.success(res.message || 'Connection successful')
      await load()
    } else {
      toast.error(res.message || 'Connection failed')
    }
  } catch (e) {
    toast.error(e.message || 'Connection test failed')
  } finally {
    testingId.value = null
  }
}

async function remove(machine) {
  const ok = await confirm({
    title: 'Delete remote machine',
    message: `Delete "${machine.name}"? Assigned users will lose access.`,
    confirmLabel: 'Delete',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await api.adminDeleteRemoteMachine(machine.id, ...tokenArgs())
    toast.success('Remote machine deleted')
    await load()
  } catch (e) {
    toast.error(e.message || 'Failed to delete remote machine')
  }
}

async function openUsers(machine) {
  usersMachine.value = machine
  showUsers.value = true
  assignUserId.value = null
  usersLoading.value = true
  try {
    const [assigned, usersRes] = await Promise.all([
      api.adminListMachineUsers(machine.id, ...tokenArgs()),
      api.listUsers(1, 100, ...tokenArgs()),
    ])
    assignedUsers.value = assigned
    allUsers.value = usersRes.items
  } catch (e) {
    toast.error(e.message || 'Failed to load assignments')
  } finally {
    usersLoading.value = false
  }
}

const availableUsers = computed(() => {
  const assignedIds = new Set(assignedUsers.value.map((u) => u.id))
  return allUsers.value.filter((u) => !assignedIds.has(u.id))
})

async function assign() {
  if (!assignUserId.value) return
  try {
    await api.adminAssignUser(usersMachine.value.id, assignUserId.value, ...tokenArgs())
    assignUserId.value = null
    assignedUsers.value = await api.adminListMachineUsers(usersMachine.value.id, ...tokenArgs())
    toast.success('User assigned')
  } catch (e) {
    toast.error(e.message || 'Failed to assign user')
  }
}

async function unassign(user) {
  try {
    await api.adminUnassignUser(usersMachine.value.id, user.id, ...tokenArgs())
    assignedUsers.value = assignedUsers.value.filter((u) => u.id !== user.id)
    toast.success('User unassigned')
  } catch (e) {
    toast.error(e.message || 'Failed to unassign user')
  }
}

onMounted(load)
</script>

<template>
  <div
    class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden mb-6"
  >
    <div
      class="px-5 py-5 sm:px-8 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-4"
    >
      <div>
        <p
          class="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500"
        >
          Remote machines
        </p>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
          Configure SSH/SFTP targets and assign which users may download to them.
        </p>
      </div>
      <button
        type="button"
        class="btn bg-blue-600 hover:bg-blue-700 text-white shrink-0"
        @click="openCreate"
      >
        New machine
      </button>
    </div>

    <div class="px-5 py-5 sm:px-8">
      <div v-if="loading" class="text-slate-600 dark:text-slate-400">Loading…</div>
      <div v-else-if="machines.length === 0" class="text-slate-500 dark:text-slate-400 text-sm">
        No remote machines configured yet.
      </div>
      <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="m in machines" :key="m.id" class="py-4 first:pt-1 last:pb-0">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-center gap-3 min-w-0">
              <Server class="w-5 h-5 text-slate-400 shrink-0" />
              <div class="min-w-0">
                <p class="font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {{ m.name }}
                  <span
                    v-if="!m.is_active"
                    class="ml-2 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-500"
                    >Inactive</span
                  >
                  <span
                    v-if="m.host_key_fingerprint"
                    class="ml-2 inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/40 px-2 py-0.5 text-xs font-semibold text-green-700 dark:text-green-400"
                  >
                    <CheckCircle2 class="w-3 h-3" /> verified
                  </span>
                </p>
                <p class="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  {{ m.username }}@{{ m.host }}:{{ m.port }} · {{ m.auth_type }}
                </p>
                <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5 font-mono truncate">
                  {{ m.download_folder }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700"
                :disabled="testingId === m.id"
                @click="testConnection(m)"
              >
                <component
                  :is="testingId === m.id ? Loader2 : Plug"
                  class="w-4 h-4"
                  :class="testingId === m.id ? 'animate-spin' : ''"
                />
                Test
              </button>
              <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700"
                @click="openUsers(m)"
              >
                <Users class="w-4 h-4" />
                Users
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                @click="openEdit(m)"
              >
                <Pencil class="w-4 h-4" />
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40"
                @click="remove(m)"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </li>
      </ul>
    </div>

    <!-- Create / edit -->
    <Modal v-model="showForm" :title="editingId ? 'Edit remote machine' : 'New remote machine'">
      <div class="space-y-4">
        <TextInput v-model="form.name" label="Name" placeholder="e.g. media-server" />
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-2">
            <TextInput v-model="form.host" label="Host" placeholder="192.168.1.10" />
          </div>
          <TextInput v-model="form.port" label="Port" inputmode="numeric" />
        </div>
        <TextInput v-model="form.username" label="Username" placeholder="downloader" />

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
            >Authentication</label
          >
          <select v-model="form.auth_type" :class="selectClass">
            <option value="password">Password</option>
            <option value="key">SSH key (server-side path)</option>
          </select>
        </div>

        <TextInput
          v-if="form.auth_type === 'password'"
          v-model="form.password"
          type="password"
          label="Password"
          :placeholder="editingId ? 'Leave blank to keep current' : ''"
          autocomplete="new-password"
        />
        <TextInput
          v-else
          v-model="form.ssh_key_path"
          label="SSH key path (on the app server)"
          placeholder="/keys/id_ed25519"
        />

        <TextInput
          v-model="form.download_folder"
          label="Download folder"
          placeholder="/srv/downloads"
        />

        <label
          class="flex items-center gap-2.5 text-sm text-slate-700 dark:text-slate-300 cursor-pointer"
        >
          <input
            v-model="form.is_active"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
          />
          Active
        </label>

        <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
        <p v-if="editingId" class="text-xs text-amber-600 dark:text-amber-400">
          Editing connection details clears the verified host key — run Test again afterwards.
        </p>

        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="showForm = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-blue-600 hover:bg-blue-700 text-white"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </div>
    </Modal>

    <!-- Assignments -->
    <Modal v-model="showUsers" :title="`Users · ${usersMachine?.name ?? ''}`">
      <div class="space-y-4">
        <div v-if="usersLoading" class="text-sm text-slate-500">Loading…</div>
        <template v-else>
          <div class="flex gap-2">
            <select v-model="assignUserId" :class="selectClass">
              <option :value="null" disabled>Select a user…</option>
              <option v-for="u in availableUsers" :key="u.id" :value="u.id">
                {{ u.username }}
              </option>
            </select>
            <button
              type="button"
              class="btn bg-blue-600 hover:bg-blue-700 text-white shrink-0"
              :disabled="!assignUserId"
              @click="assign"
            >
              Assign
            </button>
          </div>

          <div v-if="assignedUsers.length === 0" class="text-sm text-slate-500">
            No users assigned yet.
          </div>
          <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800">
            <li
              v-for="u in assignedUsers"
              :key="u.id"
              class="flex items-center justify-between py-2.5"
            >
              <span class="text-sm text-slate-800 dark:text-slate-200">{{ u.username }}</span>
              <button
                type="button"
                class="text-sm font-medium text-red-600 dark:text-red-400 hover:underline"
                @click="unassign(u)"
              >
                Remove
              </button>
            </li>
          </ul>
        </template>
      </div>
    </Modal>
  </div>
</template>
