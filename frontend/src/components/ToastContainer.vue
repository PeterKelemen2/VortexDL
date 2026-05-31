<script setup>
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'

const { toasts, dismiss } = useToast()

const icons = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const accentClasses = {
  success:
    'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/60 text-green-800 dark:text-green-200',
  error:
    'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/60 text-red-800 dark:text-red-200',
  info: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200',
  warning:
    'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-200',
}

const iconClasses = {
  success: 'text-green-500',
  error: 'text-red-500',
  info: 'text-blue-500',
  warning: 'text-amber-500',
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 top-4 z-100 flex flex-col items-center gap-3 px-4 sm:inset-x-auto sm:right-4 sm:items-end"
    aria-live="polite"
    aria-atomic="true"
  >
    <transition-group
      enter-active-class="duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-[-8px] sm:translate-x-4 sm:translate-y-0"
      enter-to-class="opacity-100 translate-x-0 translate-y-0"
      leave-active-class="duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0 translate-x-4"
      move-class="duration-200"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border px-4 py-3 shadow-lg shadow-black/5 ring-1 ring-black/5"
        :class="accentClasses[toast.type]"
        role="status"
      >
        <component
          :is="icons[toast.type]"
          class="mt-0.5 h-5 w-5 shrink-0"
          :class="iconClasses[toast.type]"
        />
        <div class="min-w-0 flex-1">
          <p v-if="toast.title" class="text-sm font-semibold">{{ toast.title }}</p>
          <p class="text-sm wrap-break-word">{{ toast.message }}</p>
        </div>
        <button
          type="button"
          class="shrink-0 rounded-full p-1 opacity-70 transition hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-current"
          aria-label="Dismiss notification"
          @click="dismiss(toast.id)"
        >
          <X class="h-4 w-4" />
        </button>
      </div>
    </transition-group>
  </div>
</template>
