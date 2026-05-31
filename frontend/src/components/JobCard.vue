<script setup>
import { computed } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import { useToast } from '@/composables/useToast'
import {
  Download,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Ban,
  Clock,
  Monitor,
} from 'lucide-vue-next'

const props = defineProps({
  job: { type: Object, required: true },
})

const store = useJobsStore()
const toast = useToast()

const statusMeta = computed(() => {
  switch (props.job.status) {
    case 'queued':
      return {
        label: 'Queued',
        icon: Clock,
        color: 'text-slate-500',
        badge: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300',
      }
    case 'running':
      return {
        label: 'Running',
        icon: Loader2,
        color: 'text-blue-500',
        badge: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400',
        spin: true,
      }
    case 'finished':
      return {
        label: 'Finished',
        icon: CheckCircle2,
        color: 'text-green-500',
        badge: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400',
      }
    case 'failed':
      return {
        label: 'Failed',
        icon: AlertCircle,
        color: 'text-red-500',
        badge: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400',
      }
    case 'canceled':
      return {
        label: 'Canceled',
        icon: Ban,
        color: 'text-slate-400',
        badge: 'bg-slate-100 dark:bg-slate-800 text-slate-500',
      }
    default:
      return {
        label: props.job.status,
        icon: Clock,
        color: 'text-slate-500',
        badge: 'bg-slate-100 text-slate-600',
      }
  }
})

const title = computed(
  () => props.job.result?.title || props.job.payload?.url || `Job #${props.job.id}`,
)

const isActive = computed(() => props.job.status === 'queued' || props.job.status === 'running')
const canDownload = computed(
  () => props.job.status === 'finished' && (props.job.result?.local_available ?? true),
)
const hasRemote = computed(
  () => props.job.destination_type === 'remote' || props.job.destination_type === 'both',
)

async function cancel() {
  try {
    await store.cancelJob(props.job.id)
    toast.success('Job canceled')
  } catch (e) {
    toast.error(e.message || 'Failed to cancel job')
  }
}

async function download() {
  try {
    await store.downloadFile(props.job.id)
  } catch (e) {
    toast.error(e.message || 'Download failed')
  }
}
</script>

<template>
  <div
    class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4"
  >
    <div class="flex items-start gap-3">
      <!-- Thumbnail -->
      <div class="shrink-0 w-16 h-12 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
        <img
          v-if="job.result?.thumbnail"
          :src="job.result.thumbnail"
          :alt="title"
          class="w-full h-full object-cover"
          loading="lazy"
        />
        <component v-else :is="statusMeta.icon" class="w-5 h-5 text-slate-400" :class="statusMeta.spin ? 'animate-spin' : ''" />
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <p class="font-medium text-slate-900 dark:text-slate-100 truncate" :title="title">
            {{ title }}
          </p>
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="canDownload"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm font-medium"
              @click="download"
            >
              <Download class="w-4 h-4" />
              Download
            </button>
            <button
              v-if="isActive"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40"
              @click="cancel"
            >
              <X class="w-4 h-4" />
              Cancel
            </button>
          </div>
        </div>

        <div class="flex items-center gap-2 mt-1">
          <span
            :class="[
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold',
              statusMeta.badge,
            ]"
          >
            <component
              :is="statusMeta.icon"
              class="w-3 h-3"
              :class="statusMeta.spin ? 'animate-spin' : ''"
            />
            {{ statusMeta.label }}
          </span>
          <span v-if="hasRemote" class="inline-flex items-center gap-1 text-xs text-slate-400">
            <Monitor class="w-3 h-3" /> remote
          </span>
        </div>

        <div v-if="isActive" class="mt-2">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-slate-400">{{ job.progress || 0 }}%</span>
          </div>
          <div class="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              class="h-full rounded-full bg-blue-500 transition-all duration-300"
              :style="{ width: `${job.progress || 0}%` }"
            />
          </div>
        </div>

        <p
          v-if="job.status === 'failed' && job.error"
          class="mt-2 text-xs text-red-600 dark:text-red-400 wrap-break-word"
        >
          {{ job.error }}
        </p>
      </div>
    </div>
  </div>
</template>
