<script setup>
import { onBeforeUnmount, onMounted, computed, watch, ref } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'close'])

const isVisible = computed(() => props.modelValue)
const showContainer = ref(props.modelValue)

watch(isVisible, (value) => {
  if (value) {
    showContainer.value = true
  }
})

function close() {
  emit('update:modelValue', false)
  emit('close')
}

function handleKeydown(event) {
  if (event.key === 'Escape' && isVisible.value) {
    close()
  }
}

function onAfterLeave() {
  showContainer.value = false
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div
    v-show="showContainer"
    class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
  >
    <transition
      enter-active-class="duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <button
        v-if="isVisible"
        class="absolute inset-0 bg-black/40 backdrop-blur-sm"
        type="button"
        aria-label="Close modal"
        @click="close"
      ></button>
    </transition>

    <transition
      enter-active-class="duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-8"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-8"
      @after-leave="onAfterLeave"
    >
      <div
        v-if="isVisible"
        class="relative w-full max-w-2xl overflow-hidden rounded-3xl bg-white p-6 shadow-2xl shadow-black/10 ring-1 ring-slate-200 sm:p-8"
        @click.stop
      >
        <button
          type="button"
          class="absolute right-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300"
          @click="close"
          aria-label="Close modal"
        >
          <X class="h-4 w-4" />
        </button>

        <div v-if="title" class="mb-5 border-b border-slate-200 pb-4">
          <h2 class="text-xl font-semibold text-slate-900">{{ title }}</h2>
        </div>

        <div class="space-y-4">
          <slot />
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
button[aria-label='Close modal'] {
  line-height: 0;
}
</style>
