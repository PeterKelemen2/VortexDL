<script setup>
import { useRouter } from 'vue-router'
import { Compass, ArrowLeft, Home } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center px-4 bg-slate-100 dark:bg-slate-950"
  >
    <div class="text-center max-w-md">
      <div
        class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 dark:bg-blue-500/10"
      >
        <Compass class="h-8 w-8 text-blue-600 dark:text-blue-400" />
      </div>
      <p class="text-5xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">
        404
      </p>
      <h1 class="mt-3 text-xl font-bold text-slate-900 dark:text-slate-100">Page not found</h1>
      <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
        The page you're looking for doesn't exist or may have been moved.
      </p>
      <div class="mt-8 flex items-center justify-center gap-3">
        <button
          type="button"
          @click="router.back()"
          class="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft class="h-4 w-4" />
          Go back
        </button>
        <router-link
          to="/"
          class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Home class="h-4 w-4" />
          Home
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
