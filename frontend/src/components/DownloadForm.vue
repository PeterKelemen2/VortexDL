<script setup>
import { reactive, ref, watch } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import DownloadParams from '@/components/DownloadParams.vue'
import DestinationSelector from '@/components/DestinationSelector.vue'
import { Download, Loader2 } from 'lucide-vue-next'

const store = useJobsStore()
const toast = useToast()

const url = ref('')
const submitting = ref(false)

const PARAMS_KEY = 'dl_params'
const DESTINATION_KEY = 'dl_destination'

const defaultParams = () => ({
  quality: 'best',
  audio_format: 'mp3',
  container: 'auto',
  embed_subtitles: false,
  embed_metadata: false,
  embed_music_metadata: false,
  allow_playlist: false,
  write_thumbnail: false,
})

const defaultDestination = () => ({
  destination_type: 'local',
  remote_machine_id: null,
  remote_subfolder: '',
})

function loadParams() {
  try {
    const saved = localStorage.getItem(PARAMS_KEY)
    if (saved) return { ...defaultParams(), ...JSON.parse(saved) }
  } catch {
    // ignore corrupt storage
  }
  return defaultParams()
}

function loadDestination() {
  try {
    const saved = localStorage.getItem(DESTINATION_KEY)
    if (saved) return { ...defaultDestination(), ...JSON.parse(saved) }
  } catch {
    // ignore corrupt storage
  }
  return defaultDestination()
}

const params = reactive(loadParams())
const destination = reactive(loadDestination())

watch(
  params,
  (val) => {
    try {
      localStorage.setItem(PARAMS_KEY, JSON.stringify({ ...val }))
    } catch {
      // storage full or unavailable
    }
  },
  { deep: true },
)

watch(
  destination,
  (val) => {
    try {
      localStorage.setItem(DESTINATION_KEY, JSON.stringify({ ...val }))
    } catch {
      // storage full or unavailable
    }
  },
  { deep: true },
)

function resetForm() {
  // Only clear the URL; params and destination are intentionally kept.
  url.value = ''
}

async function submit() {
  const trimmed = url.value.trim()
  if (!trimmed) {
    toast.error('Enter a URL to download')
    return
  }
  if (
    (destination.destination_type === 'remote' || destination.destination_type === 'both') &&
    !destination.remote_machine_id
  ) {
    toast.error('Select a remote machine')
    return
  }

  submitting.value = true
  try {
    const payload = {
      url: trimmed,
      ...params,
      destination_type: destination.destination_type,
      remote_machine_id: destination.remote_machine_id,
      remote_subfolder: destination.remote_subfolder || null,
    }
    await store.startDownload(payload)
    toast.success('Download queued')
    resetForm()
  } catch (e) {
    toast.error(e.message || 'Failed to queue download')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div>
      <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
        >Video URL</label
      >
      <input
        v-model="url"
        type="url"
        placeholder="https://…"
        class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>

    <DownloadParams v-model="params" />

    <DestinationSelector v-model="destination" />

    <button
      type="submit"
      :disabled="submitting"
      class="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2.5 text-sm font-semibold transition"
    >
      <component
        :is="submitting ? Loader2 : Download"
        class="w-4 h-4"
        :class="submitting ? 'animate-spin' : ''"
      />
      {{ submitting ? 'Queuing…' : 'Start download' }}
    </button>

    <label class="flex items-center gap-2.5 text-sm text-slate-600 dark:text-slate-400 cursor-pointer select-none">
      <input
        type="checkbox"
        :checked="store.autoDownload"
        @change="store.setAutoDownload($event.target.checked)"
        class="h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
      />
      Auto-download to browser when finished
    </label>
  </form>
</template>
