<script setup>
defineProps({
  /** Tailwind width class or arbitrary value, e.g. 'w-full', 'w-24'. */
  width: { type: String, default: 'w-full' },
  /** Tailwind height class, e.g. 'h-4'. */
  height: { type: String, default: 'h-4' },
  /** Border radius class. */
  rounded: { type: String, default: 'rounded-md' },
})
</script>

<template>
  <div
    class="animate-pulse bg-slate-200 dark:bg-slate-700"
    :class="[width, height, rounded]"
    aria-hidden="true"
  />
</template>
