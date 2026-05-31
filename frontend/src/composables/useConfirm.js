import { ref } from 'vue'

// Module-level singleton state shared between useConfirm() callers and the
// globally-mounted <ConfirmDialog /> component.
const state = ref({
  open: false,
  title: '',
  message: '',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  tone: 'default', // 'default' | 'danger'
})

let resolver = null

function close(result) {
  state.value.open = false
  if (resolver) {
    resolver(result)
    resolver = null
  }
}

export function useConfirm() {
  /**
   * Open the confirm dialog and resolve to true (confirmed) or false (cancelled).
   * @param {string|object} options - message string, or { title, message, confirmLabel, cancelLabel, tone }
   */
  function confirm(options = {}) {
    const config = typeof options === 'string' ? { message: options } : options
    state.value = {
      open: true,
      title: config.title || 'Are you sure?',
      message: config.message || '',
      confirmLabel: config.confirmLabel || 'Confirm',
      cancelLabel: config.cancelLabel || 'Cancel',
      tone: config.tone || 'default',
    }
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  return {
    state,
    confirm,
    handleConfirm: () => close(true),
    handleCancel: () => close(false),
  }
}
