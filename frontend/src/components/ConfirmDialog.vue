<script setup>
import { computed } from 'vue'
import Modal from '@/components/Modal.vue'
import { useConfirm } from '@/composables/useConfirm'

const { state, handleConfirm, handleCancel } = useConfirm()

const isOpen = computed({
  get: () => state.value.open,
  set: (value) => {
    if (!value) handleCancel()
  },
})

const confirmButtonClass = computed(() =>
  state.value.tone === 'danger'
    ? 'bg-red-600 hover:bg-red-700 focus:ring-red-400 text-white'
    : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-400 text-white',
)
</script>

<template>
  <Modal v-model="isOpen" :title="state.title" @close="handleCancel">
    <p class="text-sm text-slate-600 dark:text-slate-300">{{ state.message }}</p>
    <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
      <button
        type="button"
        class="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-50 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-300"
        @click="handleCancel"
      >
        {{ state.cancelLabel }}
      </button>
      <button
        type="button"
        class="rounded-2xl px-4 py-2 text-sm font-semibold transition focus:outline-none focus:ring-2"
        :class="confirmButtonClass"
        @click="handleConfirm"
      >
        {{ state.confirmLabel }}
      </button>
    </div>
  </Modal>
</template>
