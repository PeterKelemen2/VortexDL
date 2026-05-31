<script setup>
import { ref, computed } from 'vue'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'

const params = defineModel({
  type: Object,
  required: true,
})

const EXPANDED_KEY = 'dl_params_expanded'

function loadExpanded() {
  try {
    return localStorage.getItem(EXPANDED_KEY) === 'true'
  } catch {
    return false
  }
}

const expanded = ref(loadExpanded())

function toggleExpanded() {
  expanded.value = !expanded.value
  try {
    localStorage.setItem(EXPANDED_KEY, String(expanded.value))
  } catch {
    // storage unavailable
  }
}

const qualityOptions = [
  { value: 'best', label: 'Best available' },
  { value: '1080p', label: '1080p' },
  { value: '720p', label: '720p' },
  { value: '480p', label: '480p' },
  { value: '360p', label: '360p' },
  { value: 'audio_only', label: 'Audio only' },
]

const audioFormatOptions = [
  { value: 'mp3', label: 'MP3' },
  { value: 'aac', label: 'AAC' },
  { value: 'flac', label: 'FLAC' },
  { value: 'opus', label: 'Opus' },
  { value: 'wav', label: 'WAV' },
]

const containerOptions = [
  { value: 'auto', label: 'Auto' },
  { value: 'mp4', label: 'MP4' },
  { value: 'mkv', label: 'MKV' },
  { value: 'webm', label: 'WebM' },
]

const isAudioOnly = computed(() => params.value.quality === 'audio_only')

const selectClass =
  'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

const checkboxes = [
  { key: 'embed_subtitles', label: 'Embed subtitles' },
  { key: 'embed_metadata', label: 'Embed metadata & chapters' },
  { key: 'embed_music_metadata', label: 'Embed music tags (artist / title / album)' },
  { key: 'write_thumbnail', label: 'Embed thumbnail' },
]
</script>

<template>
  <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
    <button
      type="button"
      class="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-200"
      @click="toggleExpanded()"
    >
      <span>Advanced options</span>
      <component :is="expanded ? ChevronDown : ChevronRight" class="w-4 h-4 text-slate-400" />
    </button>

    <div
      v-if="expanded"
      class="px-4 pb-4 space-y-4 border-t border-slate-100 dark:border-slate-800 pt-4"
    >
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
            >Quality</label
          >
          <select v-model="params.quality" :class="selectClass">
            <option v-for="opt in qualityOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div v-if="isAudioOnly">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
            >Audio format</label
          >
          <select v-model="params.audio_format" :class="selectClass">
            <option v-for="opt in audioFormatOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div v-else>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
            >Container</label
          >
          <select v-model="params.container" :class="selectClass">
            <option v-for="opt in containerOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>

      <div class="space-y-2.5">
        <label
          v-for="cb in checkboxes"
          :key="cb.key"
          class="flex items-center gap-2.5 text-sm text-slate-700 dark:text-slate-300 cursor-pointer"
        >
          <input
            v-model="params[cb.key]"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
          />
          {{ cb.label }}
        </label>
      </div>

      <div class="pt-2 border-t border-slate-100 dark:border-slate-800">
        <label
          class="flex items-center justify-between text-sm text-slate-700 dark:text-slate-300 cursor-pointer"
        >
          <span>Download entire playlist</span>
          <input
            v-model="params.allow_playlist"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
          />
        </label>
      </div>
    </div>
  </div>
</template>
