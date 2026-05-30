<script setup>
import { useAttrs, ref } from 'vue'

const attrs = useAttrs()
const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  modelValue: {
    type: [String, Number],
    default: '',
  },
  type: {
    type: String,
    default: 'text',
  },
  autocomplete: {
    type: String,
    default: 'off',
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
const generatedId = `text-input-${Math.random().toString(36).slice(2, 9)}`
const inputId = props.id || props.name || generatedId

function updateValue(event) {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <div>
    <label :for="inputId" class="block text-gray-700 dark:text-slate-300 mb-1 font-medium">{{ label }}</label>
    <input
      :id="inputId"
      :name="name"
      :type="type"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :required="required"
      :value="modelValue"
      @input="updateValue"
      v-bind="attrs"
    />
  </div>
</template>

<style scoped></style>
