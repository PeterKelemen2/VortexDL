<script setup>
import SkeletonBlock from './SkeletonBlock.vue'
import SkeletonAvatar from './SkeletonAvatar.vue'

defineProps({
  /** Number of placeholder rows to render. */
  rows: { type: Number, default: 5 },
  /** Number of text columns per row. */
  columns: { type: Number, default: 3 },
  /** Whether to render a leading circular avatar placeholder. */
  withAvatar: { type: Boolean, default: false },
})
</script>

<template>
  <div class="space-y-3" role="status" aria-busy="true" aria-live="polite">
    <span class="sr-only">Loading…</span>
    <div
      v-for="row in rows"
      :key="row"
      class="flex items-center gap-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3"
    >
      <SkeletonAvatar v-if="withAvatar" size="h-10 w-10" />
      <div
        class="grid flex-1 gap-2"
        :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
      >
        <SkeletonBlock
          v-for="col in columns"
          :key="col"
          :width="col === 1 ? 'w-3/4' : 'w-1/2'"
          height="h-4"
        />
      </div>
    </div>
  </div>
</template>
