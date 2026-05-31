import { computed, reactive, ref, watch } from 'vue'

/**
 * Lightweight form state + validation composable.
 *
 * Usage:
 *   const form = useForm({
 *     fields: { email: '', password: '' },
 *     rules: {
 *       email: [rules.required(), rules.email()],
 *       password: [rules.required(), rules.minLength(12)],
 *     },
 *   })
 *
 *   form.values.email           // reactive field value
 *   form.errors.email           // first error message for the field (or '')
 *   form.touched.email          // whether the field has been blurred/validated
 *   form.isValid                // all rules currently pass
 *   form.isDirty                // any value differs from its initial value
 *   form.handleBlur('email')    // mark touched + validate that field
 *   form.validate()             // validate all fields, returns boolean
 *   form.reset()                // restore initial values and clear state
 */
export function useForm({ fields = {}, rules = {}, validateOnChange = true } = {}) {
  const initial = { ...fields }
  const values = reactive({ ...fields })
  const errors = reactive(
    Object.keys(fields).reduce((acc, key) => ((acc[key] = ''), acc), {}),
  )
  const touched = reactive(
    Object.keys(fields).reduce((acc, key) => ((acc[key] = false), acc), {}),
  )
  const submitting = ref(false)

  function runRules(name) {
    const fieldRules = rules[name] || []
    for (const rule of fieldRules) {
      const result = rule(values[name], values)
      if (result !== true && result != null && result !== '') {
        return typeof result === 'string' ? result : 'Invalid value'
      }
    }
    return ''
  }

  function validateField(name) {
    const message = runRules(name)
    errors[name] = message
    return message === ''
  }

  function validate() {
    let valid = true
    for (const name of Object.keys(values)) {
      touched[name] = true
      if (!validateField(name)) valid = false
    }
    return valid
  }

  function handleBlur(name) {
    touched[name] = true
    validateField(name)
  }

  function reset() {
    for (const key of Object.keys(initial)) {
      values[key] = initial[key]
      errors[key] = ''
      touched[key] = false
    }
    submitting.value = false
  }

  function setErrors(serverErrors = {}) {
    for (const [key, message] of Object.entries(serverErrors)) {
      if (key in errors) {
        errors[key] = message
        touched[key] = true
      }
    }
  }

  if (validateOnChange) {
    watch(
      () => ({ ...values }),
      (next, prev) => {
        for (const name of Object.keys(values)) {
          if (touched[name] && next[name] !== prev?.[name]) {
            validateField(name)
          }
        }
      },
    )
  }

  const isValid = computed(() => Object.keys(values).every((name) => runRules(name) === ''))
  const isDirty = computed(() => Object.keys(initial).some((key) => values[key] !== initial[key]))

  return {
    values,
    errors,
    touched,
    submitting,
    isValid,
    isDirty,
    validate,
    validateField,
    handleBlur,
    reset,
    setErrors,
  }
}

/** Common reusable validation rules. Each returns true on success or a message string. */
export const rules = {
  required:
    (message = 'This field is required') =>
    (value) =>
      (value !== null && value !== undefined && String(value).trim() !== '') || message,
  email:
    (message = 'Enter a valid email address') =>
    (value) =>
      !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || message,
  minLength:
    (length, message) =>
    (value) =>
      !value || String(value).length >= length || message || `Must be at least ${length} characters`,
  maxLength:
    (length, message) =>
    (value) =>
      !value || String(value).length <= length || message || `Must be at most ${length} characters`,
  pattern:
    (regex, message = 'Invalid format') =>
    (value) =>
      !value || regex.test(value) || message,
  matches:
    (otherField, message = 'Values do not match') =>
    (value, allValues) =>
      value === allValues[otherField] || message,
}
