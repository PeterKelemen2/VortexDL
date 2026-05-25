<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  items: {
    type: Array,
    required: true,
    validator(value) {
      if (!Array.isArray(value)) return false
      return value.every((item) => {
        if (item?.separator) {
          return true
        }

        const hasLabel = typeof item.label === 'string'
        const hasRoute = item.route === undefined || typeof item.route === 'string'
        const hasQuery = item.query === undefined || typeof item.query === 'object'
        const hasIcon =
          item.icon === undefined ||
          typeof item.icon === 'object' ||
          typeof item.icon === 'function'
        const hasTextClass = item.textClass === undefined || typeof item.textClass === 'string'
        const hasBgClass = item.bgClass === undefined || typeof item.bgClass === 'string'
        const hasHoverClass = item.hoverClass === undefined || typeof item.hoverClass === 'string'
        const hasAction =
          item.action === undefined ||
          typeof item.action === 'string' ||
          typeof item.action === 'function'

        return (
          hasLabel &&
          hasRoute &&
          hasQuery &&
          hasIcon &&
          hasTextClass &&
          hasBgClass &&
          hasHoverClass &&
          hasAction
        )
      })
    },
  },
  textClass: {
    type: String,
    default: 'text-gray-700',
  },
  bgClass: {
    type: String,
    default: '',
  },
  hoverClass: {
    type: String,
    default: 'hover:bg-gray-100',
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

  if (typeof item.action === 'function') {
    item.action(item)
    return
  }

  if (item.route && item.route !== 'logout') {
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
        <hr v-if="item.separator" class="border-gray-200" />
        <button
          v-else
          type="button"
          @click="navigate(item)"
          :class="[
            'flex w-full items-center gap-2 px-4 py-2 text-left text-sm',
            item.textClass ?? props.textClass,
            item.bgClass ?? props.bgClass,
            item.hoverClass ?? props.hoverClass,
          ]"
        >
          <component
            :is="item.icon"
            v-if="item.icon"
            :size="16"
            class="shrink-0 text-gray-400"
            :class="[item.textClass ?? props.textClass]"
          />
          {{ item.label }}
        </button>
      </template>
    </div>
  </div>
</template>
