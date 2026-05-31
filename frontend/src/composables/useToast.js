import { ref } from 'vue'

// Module-level singleton so every component shares the same toast queue.
const toasts = ref([])
let nextId = 0

const DEFAULT_DURATION = 4500

function dismiss(id) {
  const index = toasts.value.findIndex((toast) => toast.id === id)
  if (index !== -1) {
    toasts.value.splice(index, 1)
  }
}

function show(message, { type = 'info', duration = DEFAULT_DURATION, title = '' } = {}) {
  const id = ++nextId
  toasts.value.push({ id, message, type, title })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
  return id
}

export function useToast() {
  return {
    toasts,
    dismiss,
    show,
    success: (message, options = {}) => show(message, { ...options, type: 'success' }),
    error: (message, options = {}) => show(message, { ...options, type: 'error', duration: options.duration ?? 6000 }),
    info: (message, options = {}) => show(message, { ...options, type: 'info' }),
    warning: (message, options = {}) => show(message, { ...options, type: 'warning' }),
  }
}
