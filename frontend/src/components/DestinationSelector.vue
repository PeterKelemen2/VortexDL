<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRemoteMachinesStore } from '@/stores/remoteMachines'
import { useToast } from '@/composables/useToast'
import { FolderSearch, Monitor, Download, Layers } from 'lucide-vue-next'
import RemoteFolderBrowser from '@/components/RemoteFolderBrowser.vue'

const destination = defineModel({
  type: Object,
  required: true,
})

const store = useRemoteMachinesStore()
const toast = useToast()

const showBrowser = ref(false)

const options = [
  { value: 'local', label: 'Local', icon: Download, desc: 'Download in your browser' },
  { value: 'remote', label: 'Remote', icon: Monitor, desc: 'Send to a remote machine' },
  { value: 'both', label: 'Both', icon: Layers, desc: 'Browser + remote machine' },
]

const needsRemote = computed(
  () =>
    destination.value.destination_type === 'remote' ||
    destination.value.destination_type === 'both',
)

const hasMachines = computed(() => (store.myMachines ?? []).length > 0)

const selectClass =
  'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

function selectType(value) {
  destination.value.destination_type = value
}

function openBrowser() {
  if (!destination.value.remote_machine_id) {
    toast.error('Select a remote machine first')
    return
  }
  showBrowser.value = true
}

function onFolderPicked(path) {
  // Strip the leading slash for a relative subfolder.
  destination.value.remote_subfolder = path.replace(/^\/+/, '')
  showBrowser.value = false
}

onMounted(async () => {
  try {
    await store.fetchMyMachines()
  } catch {
    // ignore — user may have no machines assigned
  }
})
</script>

<template>
  <div class="space-y-3">
    <p class="block text-sm font-medium text-slate-700 dark:text-slate-300">Destination</p>
    <div class="grid grid-cols-3 gap-2">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        @click="selectType(opt.value)"
        :class="[
          'flex flex-col items-center gap-1 rounded-lg border px-2 py-3 text-xs font-medium transition',
          destination.destination_type === opt.value
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400'
            : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800',
        ]"
      >
        <component :is="opt.icon" class="w-5 h-5" />
        {{ opt.label }}
      </button>
    </div>

    <div v-if="needsRemote" class="space-y-3 pt-1">
      <div v-if="!hasMachines" class="text-sm text-amber-600 dark:text-amber-400">
        You have no remote machines assigned. Ask an administrator for access.
      </div>
      <template v-else>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Remote machine
          </label>
          <select v-model="destination.remote_machine_id" :class="selectClass">
            <option :value="null" disabled>Select a machine…</option>
            <option v-for="m in store.myMachines" :key="m.id" :value="m.id">
              {{ m.name }} ({{ m.host }})
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Subfolder (optional)
          </label>
          <div class="flex gap-2">
            <input
              v-model="destination.remote_subfolder"
              type="text"
              placeholder="e.g. music/albums"
              :class="selectClass"
            />
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 shrink-0"
              @click="openBrowser"
            >
              <FolderSearch class="w-4 h-4" />
              Browse
            </button>
          </div>
        </div>
      </template>
    </div>

    <RemoteFolderBrowser
      v-if="destination.remote_machine_id"
      v-model="showBrowser"
      :machine-id="destination.remote_machine_id"
      @select="onFolderPicked"
    />
  </div>
</template>
