<script setup>
import { computed } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import JobCard from '@/components/JobCard.vue'
import { ChevronLeft, ChevronRight, Inbox } from 'lucide-vue-next'

const store = useJobsStore()

const filters = [
  { value: '', label: 'All' },
  { value: 'running', label: 'Active' },
  { value: 'finished', label: 'Finished' },
  { value: 'failed', label: 'Failed' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))

function prev() {
  if (store.page > 1) store.setPage(store.page - 1)
}
function next() {
  if (store.page < totalPages.value) store.setPage(store.page + 1)
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3">
      <h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">Downloads</h2>
      <span
        class="inline-flex items-center gap-1.5 text-xs text-slate-400"
        :title="store.sseConnected ? 'Live updates active' : 'Reconnecting…'"
      >
        <span
          class="w-2 h-2 rounded-full"
          :class="store.sseConnected ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'"
        />
        {{ store.sseConnected ? 'Live' : 'Offline' }}
      </span>
    </div>

    <div class="flex gap-1.5">
      <button
        v-for="f in filters"
        :key="f.value"
        type="button"
        @click="store.setStatusFilter(f.value)"
        :class="[
          'px-3 py-1.5 rounded-lg text-sm font-medium transition',
          store.statusFilter === f.value
            ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800',
        ]"
      >
        {{ f.label }}
      </button>
    </div>

    <div
      v-if="store.loading && store.jobs.length === 0"
      class="text-sm text-slate-500 py-8 text-center"
    >
      Loading…
    </div>
    <div
      v-else-if="store.jobs.length === 0"
      class="flex flex-col items-center gap-2 py-12 text-slate-400 dark:text-slate-500"
    >
      <Inbox class="w-10 h-10" />
      <p class="text-sm">No downloads yet</p>
    </div>

    <div v-else class="space-y-3">
      <JobCard v-for="job in store.jobs" :key="job.id" :job="job" />
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-between pt-2">
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm disabled:opacity-40"
        :disabled="store.page <= 1"
        @click="prev"
      >
        <ChevronLeft class="w-4 h-4" /> Prev
      </button>
      <span class="text-xs text-slate-500">Page {{ store.page }} of {{ totalPages }}</span>
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm disabled:opacity-40"
        :disabled="store.page >= totalPages"
        @click="next"
      >
        Next <ChevronRight class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>
