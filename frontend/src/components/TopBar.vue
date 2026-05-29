<script setup>
import { BRAND_NAME, BRAND_ICON } from '@/constants/branding'
import { Menu } from 'lucide-vue-next'

defineProps({
  hidden: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['openSidebar'])
</script>

<template>
  <Transition name="topbar">
    <header
      v-if="!hidden"
      class="fixed inset-x-0 top-0 z-30 flex h-14 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90"
    >
      <button
        type="button"
        @click="emit('openSidebar')"
        class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
        aria-label="Open navigation"
      >
        <Menu class="h-5 w-5" />
      </button>

      <div class="flex items-center gap-2 font-bold text-blue-600 dark:text-blue-400">
        <component :is="BRAND_ICON" class="h-5 w-5" />
        <span class="text-base tracking-tight">{{ BRAND_NAME }}</span>
      </div>
    </header>
  </Transition>
</template>

<style scoped>
.topbar-enter-active,
.topbar-leave-active {
  transition:
    transform 0.25s ease,
    opacity 0.25s ease;
}
.topbar-enter-from,
.topbar-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
