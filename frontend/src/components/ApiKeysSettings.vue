<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Modal from '@/components/Modal.vue'
import TextInput from '@/components/TextInput.vue'
import { KeyRound, Copy, Check, Trash2 } from 'lucide-vue-next'

const auth = useAuthStore()
const toast = useToast()
const { confirm } = useConfirm()

const keys = ref([])
const loading = ref(true)

const showCreate = ref(false)
const newName = ref('')
const newExpiry = ref('')
const creating = ref(false)
const createError = ref('')

const createdKey = ref(null) // plaintext shown once
const copied = ref(false)

function tokenArgs() {
  return [auth.accessToken, auth.setAccessToken]
}

async function loadKeys() {
  loading.value = true
  try {
    keys.value = (await api.listApiKeys(...tokenArgs())) ?? []
  } catch (e) {
    toast.error(e.message || 'Failed to load API keys')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newName.value = ''
  newExpiry.value = ''
  createError.value = ''
  createdKey.value = null
  showCreate.value = true
}

async function submitCreate() {
  if (!newName.value.trim()) {
    createError.value = 'Give the key a name.'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const payload = { name: newName.value.trim() }
    const days = parseInt(newExpiry.value, 10)
    if (!Number.isNaN(days) && days > 0) payload.expires_in_days = days
    const res = await api.createApiKey(payload, ...tokenArgs())
    createdKey.value = res.key
    await loadKeys()
    toast.success('API key created')
  } catch (e) {
    createError.value = e.message || 'Failed to create API key'
  } finally {
    creating.value = false
  }
}

async function copyKey() {
  if (!createdKey.value) return
  try {
    await navigator.clipboard.writeText(createdKey.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    toast.error('Could not copy to clipboard')
  }
}

async function revoke(key) {
  const ok = await confirm({
    title: 'Revoke API key',
    message: `Revoke "${key.name}"? Applications using it will stop working immediately.`,
    confirmLabel: 'Revoke',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await api.revokeApiKey(key.id, ...tokenArgs())
    toast.success('API key revoked')
    await loadKeys()
  } catch (e) {
    toast.error(e.message || 'Failed to revoke API key')
  }
}

onMounted(loadKeys)
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
          API keys
        </p>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
          Create personal API keys to access the API programmatically with the
          <span class="font-mono">X-API-Key</span> header.
        </p>
      </div>
      <button
        type="button"
        class="btn bg-blue-600 hover:bg-blue-700 text-white shrink-0"
        @click="openCreate"
      >
        New key
      </button>
    </div>

    <div class="px-5 py-5 sm:px-8">
      <div v-if="loading" class="text-slate-600 dark:text-slate-400">Loading…</div>
      <div v-else-if="keys.length === 0" class="text-slate-500 dark:text-slate-400 text-sm">
        You don't have any API keys yet.
      </div>
      <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800">
        <li v-for="key in keys" :key="key.id" class="py-4 first:pt-1 last:pb-0">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-center gap-3 min-w-0">
              <KeyRound class="w-5 h-5 text-slate-400 shrink-0" />
              <div class="min-w-0">
                <p class="font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {{ key.name }}
                  <span
                    v-if="key.revoked"
                    class="ml-2 rounded-full bg-red-100 dark:bg-red-900/40 px-2 py-0.5 text-xs font-semibold text-red-700 dark:text-red-400"
                    >Revoked</span
                  >
                </p>
                <p class="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  {{ key.prefix }}…
                </p>
                <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                  Created {{ new Date(key.created_at).toLocaleDateString() }}
                  <template v-if="key.expires_at">
                    · expires {{ new Date(key.expires_at).toLocaleDateString() }}
                  </template>
                  <template v-if="key.last_used_at">
                    · last used {{ new Date(key.last_used_at).toLocaleString() }}
                  </template>
                </p>
              </div>
            </div>
            <button
              v-if="!key.revoked"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 transition hover:bg-red-50 dark:hover:bg-red-950/40 shrink-0"
              @click="revoke(key)"
            >
              <Trash2 class="w-4 h-4" />
              Revoke
            </button>
          </div>
        </li>
      </ul>
    </div>

    <Modal v-model="showCreate" title="Create API key" @close="showCreate = false">
      <div v-if="!createdKey" class="space-y-4">
        <TextInput v-model="newName" label="Name" placeholder="e.g. CLI on my laptop" />
        <TextInput
          v-model="newExpiry"
          label="Expires in (days, optional)"
          inputmode="numeric"
          placeholder="Leave blank for no expiry"
        />
        <p v-if="createError" class="text-sm text-red-600 dark:text-red-400">{{ createError }}</p>
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="showCreate = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn bg-blue-600 hover:bg-blue-700 text-white"
            :disabled="creating"
            @click="submitCreate"
          >
            {{ creating ? 'Creating…' : 'Create' }}
          </button>
        </div>
      </div>

      <div v-else class="space-y-4">
        <p class="text-sm text-slate-700 dark:text-slate-300">
          Copy your new API key now. For security, it won't be shown again.
        </p>
        <div
          class="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 font-mono text-sm break-all text-slate-800 dark:text-slate-200"
        >
          {{ createdKey }}
        </div>
        <div class="flex items-center justify-between">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            @click="copyKey"
          >
            <component :is="copied ? Check : Copy" class="w-4 h-4" />
            {{ copied ? 'Copied' : 'Copy key' }}
          </button>
          <button
            type="button"
            class="btn bg-blue-600 hover:bg-blue-700 text-white"
            @click="showCreate = false"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  </div>
</template>
