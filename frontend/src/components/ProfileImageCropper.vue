<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  imageUrl: {
    type: String,
    required: true,
  },
  initialCrop: {
    type: Object,
    default: null,
  },
  imageAlt: {
    type: String,
    default: 'Profile image preview',
  },
})

const emit = defineEmits(['save', 'cancel'])

const cropViewportSize = 360
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const baseScale = ref(1)
const zoom = ref(1)
const position = ref({ x: 0, y: 0 })
const dragging = ref(false)
const imageRef = ref(null)
const containerRef = ref(null)
const dragStart = ref({ x: 0, y: 0 })
const pointerStart = ref({ x: 0, y: 0 })
const imageLoaded = ref(false)

const currentScale = computed(() => baseScale.value * zoom.value)
const displaySize = computed(() => ({
  width: imageNaturalWidth.value * currentScale.value,
  height: imageNaturalHeight.value * currentScale.value,
}))

const imageStyle = computed(() => ({
  width: `${displaySize.value.width}px`,
  height: `${displaySize.value.height}px`,
  maxWidth: 'none',
  left: '50%',
  top: '50%',
  transform: `translate(calc(-50% + ${position.value.x}px), calc(-50% + ${position.value.y}px))`,
  touchAction: 'none',
}))

const instructions =
  'Drag the image until the area within the circle shows the portion you want to use. Use zoom to adjust the crop size if needed.'

function updateBounds(newPosition) {
  // Position is in screen pixels; clamp so the crop circle never exposes outside the image
  const limitX = Math.max(0, displaySize.value.width / 2 - cropViewportSize / 2)
  const limitY = Math.max(0, displaySize.value.height / 2 - cropViewportSize / 2)
  return {
    x: Math.min(limitX, Math.max(-limitX, newPosition.x)),
    y: Math.min(limitY, Math.max(-limitY, newPosition.y)),
  }
}

function centerImage() {
  position.value = { x: 0, y: 0 }
}

function applyInitialCrop(cropData) {
  if (
    !cropData ||
    cropData.crop_x == null ||
    cropData.crop_y == null ||
    cropData.crop_size == null ||
    cropData.original_width == null ||
    cropData.original_height == null
  ) {
    return
  }

  const desiredScale = cropViewportSize / cropData.crop_size
  zoom.value = Math.max(1, desiredScale / baseScale.value)

  const cropCenterX = cropData.crop_x + cropData.crop_size / 2
  const cropCenterY = cropData.crop_y + cropData.crop_size / 2
  const effectiveScale = currentScale.value

  position.value = updateBounds({
    x: -(cropCenterX - imageNaturalWidth.value / 2) * effectiveScale,
    y: -(cropCenterY - imageNaturalHeight.value / 2) * effectiveScale,
  })
}

function setImageDimensions(image) {
  if (!image || !image.naturalWidth || !image.naturalHeight) {
    return
  }

  imageNaturalWidth.value = image.naturalWidth
  imageNaturalHeight.value = image.naturalHeight

  // Fit the image so it fully covers the crop viewport:
  // - If landscape (width > height), fit by height so height === cropViewportSize
  // - If portrait (height > width), fit by width so width === cropViewportSize
  // Math.max ensures the shorter dimension fills the viewport (cover behaviour)
  const baseScaleValue = Math.max(
    cropViewportSize / imageNaturalWidth.value,
    cropViewportSize / imageNaturalHeight.value,
  )
  baseScale.value = baseScaleValue
  zoom.value = 1
  centerImage()
  if (props.initialCrop) {
    applyInitialCrop(props.initialCrop)
  }
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
  position.value = updateBounds({
    x: dragStart.value.x + deltaX,
    y: dragStart.value.y + deltaY,
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
  if (!imageLoaded.value || !imageRef.value || !containerRef.value) return

  const imageRect = imageRef.value.getBoundingClientRect()
  const cropRect = containerRef.value.getBoundingClientRect()
  const scaleFactor = imageNaturalWidth.value / imageRect.width

  const rawCropX = Math.round((cropRect.left - imageRect.left) * scaleFactor)
  const rawCropY = Math.round((cropRect.top - imageRect.top) * scaleFactor)
  const rawCropSize = Math.round(cropViewportSize * scaleFactor)

  const cropSize = Math.max(
    1,
    Math.min(rawCropSize, imageNaturalWidth.value, imageNaturalHeight.value),
  )
  const cropX = Math.max(0, Math.min(rawCropX, imageNaturalWidth.value - cropSize))
  const cropY = Math.max(0, Math.min(rawCropY, imageNaturalHeight.value - cropSize))

  emit('save', {
    crop_x: cropX,
    crop_y: cropY,
    crop_size: cropSize,
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
  [() => props.imageUrl, () => props.initialCrop],
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
        ref="containerRef"
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
              transparent 180px,
              rgba(0, 0, 0, 0.55) 181px
            );
          "
        >
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="h-90 w-90 rounded-full border-4 border-white/90 bg-transparent"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-3 rounded-3xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div class="flex items-center justify-between gap-4">
        <p class="text-sm font-medium text-slate-900 dark:text-slate-100">Zoom</p>
        <span class="text-sm text-slate-500 dark:text-slate-400">{{ zoom.toFixed(1) }}×</span>
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
        class="inline-flex justify-center rounded-2xl bg-slate-100 dark:bg-slate-700 px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-200 transition hover:bg-slate-200 dark:hover:bg-slate-600"
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
