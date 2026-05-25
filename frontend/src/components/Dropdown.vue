<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  items: {
    type: Array,
    required: true,
    // Each item: { label, route, query, icon } or { separator: true }
  },
})

const emit = defineEmits(['select'])

const router = useRouter()
const open = ref(false)
const containerRef = ref(null)

function toggle() {
  open.value = !open.value
}

function navigate(item) {
  open.value = false
  emit('select', item)
  if (item.route) {
    router.push({ name: item.route, query: item.query ?? {} })
  }
}

function onClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div class="relative" ref="containerRef">
    <slot name="trigger" :toggle="toggle" />

    <div
      v-if="open"
      class="absolute right-0 mt-2 w-40 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg z-50"
    >
      <template v-for="(item, index) in items" :key="index">
        <hr v-if="item.separator" class="my-1 border-gray-200" />
        <button
          v-else
          type="button"
          @click="navigate(item)"
          class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
        >
          <component :is="item.icon" v-if="item.icon" :size="16" class="shrink-0 text-gray-400" />
          {{ item.label }}
        </button>
      </template>
    </div>
  </div>
</template>
