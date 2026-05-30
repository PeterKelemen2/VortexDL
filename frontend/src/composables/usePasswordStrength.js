import { computed, isRef } from 'vue'

export function usePasswordStrength(password, options = {}) {
  const passwordRef = isRef(password) ? password : computed(() => password ?? '')
  const minLength = options.minLength ?? 12
  const minScore = options.minScore ?? 2

  const strengthCriteria = computed(() => {
    const value = passwordRef.value || ''
    const hasNumber = /\d/.test(value)
    const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(value)

    return [
      { label: `At least ${minLength} characters`, valid: value.length >= minLength, mandatory: true },
      { label: 'No spaces', valid: /^\S+$/.test(value), mandatory: true },
      { label: 'An uppercase letter', valid: /[A-Z]/.test(value), mandatory: true },
      { label: 'A lowercase letter', valid: /[a-z]/.test(value), mandatory: false },
      { label: 'A number', valid: hasNumber, mandatory: false },
      { label: 'A special character', valid: hasSpecial, mandatory: false },
    ]
  })

  const passwordStrengthScore = computed(() => {
    const password = passwordRef.value || ''
    const lengthValid = password.length >= minLength
    const noSpacesValid = /^\S+$/.test(password)
    const hasUppercase = /[A-Z]/.test(password)
    const hasNumber = /\d/.test(password)
    const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)

    if (!lengthValid || !noSpacesValid || !hasUppercase) return 0
    if (hasNumber && hasSpecial) return 3
    if (hasNumber || hasSpecial) return 2
    return 1
  })

  const passwordStrengthLabel = computed(() => {
    const password = passwordRef.value || ''
    if (!password) return 'Enter password'

    const lengthValid = strengthCriteria.value[0].valid
    const noSpacesValid = strengthCriteria.value[1].valid
    const hasUppercase = strengthCriteria.value[2].valid
    const hasNumber = strengthCriteria.value[4].valid
    const hasSpecial = strengthCriteria.value[5].valid
    const score = passwordStrengthScore.value

    if (!lengthValid) return `Use at least ${minLength} characters`
    if (!noSpacesValid) return 'No spaces allowed'
    if (!hasUppercase) return 'Add an uppercase letter'
    if (!hasNumber && !hasSpecial) return 'Add a number or special character'
    if (score === 1) return 'Weak'
    if (score === 2) return 'Acceptable'
    return 'Strong'
  })

  const isPasswordValid = computed(() => {
    const mandatory = strengthCriteria.value.filter((item) => item.mandatory)
    return mandatory.every((item) => item.valid) && passwordStrengthScore.value >= minScore
  })

  return {
    strengthCriteria,
    passwordStrengthScore,
    passwordStrengthLabel,
    isPasswordValid,
  }
}
