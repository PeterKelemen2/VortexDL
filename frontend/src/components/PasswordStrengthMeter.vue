<script setup>
import { computed } from 'vue'
import { usePasswordStrength } from '@/composables/usePasswordStrength'
import { Check, X } from 'lucide-vue-next'

const props = defineProps({
  password: {
    type: String,
    default: '',
  },
  minLength: {
    type: Number,
    default: 12,
  },
  minScore: {
    type: Number,
    default: 2,
  },
  label: {
    type: String,
    default: 'Password strength',
  },
  helpText: {
    type: String,
    default: '',
  },
  showCriteria: {
    type: Boolean,
    default: true,
  },
})

const { strengthCriteria, passwordStrengthScore, passwordStrengthLabel, isPasswordValid } =
  usePasswordStrength(
    computed(() => props.password),
    {
      minLength: props.minLength,
      minScore: props.minScore,
    },
  )

const barWidth = computed(() => `${(passwordStrengthScore.value / 3) * 100}%`)
const barColor = computed(() => {
  if (!isPasswordValid.value) return passwordStrengthScore.value === 2 ? '#eab308' : '#ef4444'
  return '#16a34a'
})
</script>

<template>
  <div class="space-y-2">
    <div>
      <p class="text-sm font-medium text-slate-900 dark:text-slate-100">{{ label }}</p>
      <span
        class="inline-flex rounded-full text-xs font-semibold"
        :class="isPasswordValid ? ' text-emerald-700 ' : ' text-amber-600 '"
      >
        {{ passwordStrengthLabel }}
      </span>
    </div>

    <div class="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
      <div
        class="h-full rounded-full transition-all"
        :style="{ width: barWidth, backgroundColor: barColor }"
      />
    </div>

    <p v-if="helpText" class="text-xs text-slate-500 dark:text-slate-400">{{ helpText }}</p>

    <ul v-if="showCriteria" class="grid gap-2 text-xs text-slate-600 dark:text-slate-400">
      <li v-for="(rule, index) in strengthCriteria" :key="index" class="flex items-center gap-2">
        <div>
          <Check v-if="rule.valid" class="w-4 h-4 text-emerald-700"></Check>
          <X v-else class="w-4 h-4 text-slate-600"></X>
        </div>

        <span :class="[rule.valid ? 'text-emerald-700' : '']">{{ rule.label }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped></style>
