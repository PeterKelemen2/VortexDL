<script setup>
import { ref, useAttrs } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'

const attrs = useAttrs()
const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  modelValue: {
    type: String,
    default: '',
  },
  autocomplete: {
    type: String,
    default: 'current-password',
  },
  name: {
    type: String,
    default: '',
  },
  id: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '',
  },
  required: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])
const showPassword = ref(false)
const generatedId = `password-input-${Math.random().toString(36).slice(2, 9)}`
const inputId = props.id || props.name || generatedId

function updateValue(event) {
  emit('update:modelValue', event.target.value)
}

function togglePassword() {
  showPassword.value = !showPassword.value
}
</script>

<template>
  <div>
    <label :for="inputId" class="block text-gray-700 dark:text-slate-300 mb-1 font-medium">{{ label }}</label>
    <div class="relative">
      <input
        :id="inputId"
        :name="name"
        :type="showPassword ? 'text' : 'password'"
        :autocomplete="autocomplete"
        :placeholder="placeholder"
        :required="required"
        :value="modelValue"
        @input="updateValue"
        v-bind="attrs"
      />
      <button
        type="button"
        @click="togglePassword"
        class="absolute right-2 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 p-1"
        :aria-label="showPassword ? 'Hide password' : 'Show password'"
      >
        <component :is="showPassword ? EyeOff : Eye" class="w-5 h-5" />
      </button>
    </div>
  </div>
</template>

<style scoped></style>
