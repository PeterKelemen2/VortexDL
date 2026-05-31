<script setup>
defineProps({
  size: { type: String, default: 'h-12 w-12' },
})
</script>

<template>
  <div
    class="animate-pulse rounded-full bg-slate-200 dark:bg-slate-700"
    :class="size"
    aria-hidden="true"
  />
</template>
