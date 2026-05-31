<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import DownloadForm from '@/components/DownloadForm.vue'
import JobQueue from '@/components/JobQueue.vue'

const store = useJobsStore()

onMounted(async () => {
  await store.fetchJobs()
  store.connectSSE()
})

onBeforeUnmount(() => {
  store.disconnectSSE()
})
</script>

<template>
  <div class="bg-slate-50 dark:bg-slate-950 min-h-[calc(100vh-3.5rem)]">
    <div class="mx-auto max-w-6xl px-4 py-8 lg:py-10">
      <div class="mb-7">
        <h1 class="text-xl font-bold text-slate-900 dark:text-slate-100">Download</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Paste a URL, choose your options, and download locally or to a remote machine.
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <DownloadForm />
        </div>
        <div>
          <JobQueue />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
