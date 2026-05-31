<script setup>
import { watch, computed } from 'vue'
import { useRemoteMachinesStore } from '@/stores/remoteMachines'
import Modal from '@/components/Modal.vue'
import { Folder, File as FileIcon, ChevronUp, Check } from 'lucide-vue-next'

const open = defineModel({ type: Boolean, required: true })

const props = defineProps({
  machineId: { type: Number, required: true },
})

const emit = defineEmits(['select'])

const store = useRemoteMachinesStore()

const breadcrumbs = computed(() => {
  const parts = store.currentPath.split('/').filter(Boolean)
  return ['/', ...parts]
})

function formatSize(bytes) {
  if (bytes == null) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value.toFixed(value < 10 && i > 0 ? 1 : 0)} ${units[i]}`
}

function selectCurrent() {
  emit('select', store.currentPath)
}

watch(
  open,
  (value) => {
    if (value) {
      store.browse(props.machineId, '/').catch(() => {})
    }
  },
  { immediate: false },
)
</script>

<template>
  <Modal v-model="open" title="Browse remote folder">
    <div class="space-y-4">
      <div class="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
        <span v-for="(crumb, idx) in breadcrumbs" :key="idx" class="font-mono">
          {{ crumb === '/' ? '/' : crumb
          }}<span v-if="idx < breadcrumbs.length - 1 && crumb !== '/'">/</span>
        </span>
      </div>

      <div
        class="rounded-lg border border-slate-200 dark:border-slate-800 divide-y divide-slate-100 dark:divide-slate-800 max-h-72 overflow-y-auto"
      >
        <button
          v-if="store.currentPath !== '/'"
          type="button"
          class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
          @click="store.navigateUp()"
        >
          <ChevronUp class="w-4 h-4 text-slate-400" />
          ..
        </button>

        <div v-if="store.browsing" class="px-3 py-6 text-center text-sm text-slate-500">
          Loading…
        </div>
        <div
          v-else-if="store.browseError"
          class="px-3 py-6 text-center text-sm text-red-600 dark:text-red-400"
        >
          {{ store.browseError }}
        </div>
        <div
          v-else-if="store.entries.length === 0"
          class="px-3 py-6 text-center text-sm text-slate-500"
        >
          Empty folder
        </div>

        <template v-else>
          <button
            v-for="entry in store.entries"
            :key="entry.name"
            type="button"
            :disabled="entry.type !== 'dir'"
            class="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-left"
            :class="
              entry.type === 'dir'
                ? 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer'
                : 'text-slate-400 dark:text-slate-500 cursor-default'
            "
            @click="entry.type === 'dir' && store.navigateInto(entry.name)"
          >
            <span class="flex items-center gap-2 min-w-0">
              <component
                :is="entry.type === 'dir' ? Folder : FileIcon"
                class="w-4 h-4 shrink-0"
                :class="entry.type === 'dir' ? 'text-blue-500' : 'text-slate-400'"
              />
              <span class="truncate">{{ entry.name }}</span>
            </span>
            <span v-if="entry.type === 'file'" class="text-xs shrink-0">{{
              formatSize(entry.size)
            }}</span>
          </button>
        </template>
      </div>

      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-slate-500 dark:text-slate-400 truncate">
          Selected: <span class="font-mono">{{ store.currentPath }}</span>
        </p>
        <button
          type="button"
          class="btn bg-blue-600 hover:bg-blue-700 text-white inline-flex items-center gap-1.5"
          @click="selectCurrent"
        >
          <Check class="w-4 h-4" />
          Use this folder
        </button>
      </div>
    </div>
  </Modal>
</template>
