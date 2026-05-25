<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  imageUrl: {
    type: String,
    required: true,
  },
  imageAlt: {
    type: String,
    default: 'Profile image preview',
  },
})

const emit = defineEmits(['save', 'cancel'])

const containerSize = 360
const cropViewportSize = 280
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const baseScale = ref(1)
const zoom = ref(1)
const position = ref({ x: 0, y: 0 })
const dragging = ref(false)
const imageRef = ref(null)
const dragStart = ref({ x: 0, y: 0 })
const pointerStart = ref({ x: 0, y: 0 })
const imageLoaded = ref(false)

const currentScale = computed(() => baseScale.value * zoom.value)
const displaySize = computed(() => ({
  width: imageNaturalWidth.value * currentScale.value,
  height: imageNaturalHeight.value * currentScale.value,
}))

const imageStyle = computed(() => ({
  width: `${imageNaturalWidth.value}px`,
  height: 'auto',
  left: '50%',
  top: '50%',
  transform: `translate(-50%, -50%) scale(${currentScale.value}) translate(${position.value.x}px, ${position.value.y}px)`,
  transformOrigin: 'center center',
  touchAction: 'none',
}))

const instructions =
  'Drag the image until the area within the circle shows the portion you want to use. Use zoom to adjust the crop size if needed.'

function updateBounds(newPosition) {
  const halfVisible = cropViewportSize / 2
  const halfImageWidth = displaySize.value.width / 2
  const halfImageHeight = displaySize.value.height / 2
  const scale = currentScale.value || 1
  const limitX = Math.max(0, (halfImageWidth - halfVisible) / scale)
  const limitY = Math.max(0, (halfImageHeight - halfVisible) / scale)

  return {
    x: Math.min(limitX, Math.max(-limitX, newPosition.x)),
    y: Math.min(limitY, Math.max(-limitY, newPosition.y)),
  }
}

function centerImage() {
  position.value = {
    x: 0,
    y: 0,
  }
}

function setImageDimensions(image) {
  if (!image || !image.naturalWidth || !image.naturalHeight) {
    return
  }

  imageNaturalWidth.value = image.naturalWidth
  imageNaturalHeight.value = image.naturalHeight
  const baseScaleValue = Math.max(
    cropViewportSize / imageNaturalWidth.value,
    cropViewportSize / imageNaturalHeight.value,
  )
  baseScale.value = baseScaleValue
  zoom.value = 1
  centerImage()
  imageLoaded.value = true
}

function onImageLoad(event) {
  setImageDimensions(event.target)
}

function startDrag(event) {
  event.preventDefault()
  dragging.value = true
  dragStart.value = { ...position.value }
  pointerStart.value = { x: event.clientX, y: event.clientY }
  event.target.setPointerCapture(event.pointerId)
}

function onPointerMove(event) {
  if (!dragging.value) return
  const deltaX = event.clientX - pointerStart.value.x
  const deltaY = event.clientY - pointerStart.value.y
  const scale = currentScale.value || 1
  position.value = updateBounds({
    x: dragStart.value.x + deltaX / scale,
    y: dragStart.value.y + deltaY / scale,
  })
}

function stopDrag(event) {
  dragging.value = false
  if (event.pointerId && event.target.releasePointerCapture) {
    event.target.releasePointerCapture(event.pointerId)
  }
}

function onScaleChange(event) {
  const newZoom = Number(event.target.value)
  zoom.value = Math.max(1, newZoom)
  position.value = updateBounds(position.value)
}

function save() {
  if (!imageLoaded.value) return
  const effectiveScale = currentScale.value
  const cropSize = Math.round(cropViewportSize / effectiveScale)
  const cropX = Math.round(
    (displaySize.value.width / 2 - cropViewportSize / 2 - position.value.x * effectiveScale) /
      effectiveScale,
  )
  const cropY = Math.round(
    (displaySize.value.height / 2 - cropViewportSize / 2 - position.value.y * effectiveScale) /
      effectiveScale,
  )
  emit('save', {
    crop_x: Math.max(0, cropX),
    crop_y: Math.max(0, cropY),
    crop_size: Math.max(0, cropSize),
    original_width: imageNaturalWidth.value,
    original_height: imageNaturalHeight.value,
  })
}

function cancel() {
  emit('cancel')
}

watch([displaySize, () => imageNaturalWidth.value, () => imageNaturalHeight.value], () => {
  if (imageLoaded.value) {
    position.value = updateBounds(position.value)
  }
})

watch(
  () => props.imageUrl,
  () => {
    if (imageRef.value && imageRef.value.complete) {
      setImageDimensions(imageRef.value)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
      {{ instructions }}
    </div>

    <div class="mx-auto w-90 rounded-3xl border border-slate-200 bg-slate-900/5 p-4">
      <div
        class="relative mx-auto h-90 w-90 overflow-hidden rounded-3xl bg-slate-900"
        @pointermove="onPointerMove"
        @pointerup="stopDrag"
        @pointercancel="stopDrag"
      >
        <img
          ref="imageRef"
          v-if="imageUrl"
          :src="imageUrl"
          :alt="imageAlt"
          class="absolute top-1/2 left-1/2 cursor-grab"
          :style="imageStyle"
          @pointerdown="startDrag"
          @load="onImageLoad"
        />

        <div
          class="pointer-events-none absolute inset-0"
          style="
            background: radial-gradient(
              circle at center,
              transparent 140px,
              rgba(0, 0, 0, 0.55) 141px
            );
          "
        >
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="h-70 w-70 rounded-full border-4 border-white/90 bg-transparent"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex items-center justify-between gap-4">
        <p class="text-sm font-medium text-slate-900">Zoom</p>
        <span class="text-sm text-slate-500">{{ zoom.toFixed(1) }}×</span>
      </div>
      <input
        type="range"
        min="1"
        max="10"
        step="0.05"
        :value="zoom"
        @input="onScaleChange"
        class="w-full"
      />
    </div>

    <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
      <button
        type="button"
        class="inline-flex justify-center rounded-2xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
        @click="cancel"
      >
        Cancel
      </button>
      <button
        type="button"
        class="inline-flex justify-center rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark"
        @click="save"
      >
        Save crop
      </button>
    </div>
  </div>
</template>

<style scoped>
img {
  user-select: none;
}
</style>
