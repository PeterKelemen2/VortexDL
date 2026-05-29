<script setup>
import { computed, ref, reactive, watch, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import { resolveBackendUrl } from '@/utils/url'
import Modal from '@/components/Modal.vue'
import PasswordInput from '@/components/PasswordInput.vue'
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter.vue'
import TextInput from '@/components/TextInput.vue'
import ProfileImageCropper from '@/components/ProfileImageCropper.vue'
import { usePasswordStrength } from '@/composables/usePasswordStrength'
import { useUserInitials } from '@/composables/useUserInitials'
import { Pencil } from 'lucide-vue-next'

const auth = useAuthStore()

const profileForm = reactive({
  username: auth.user?.username ?? '',
  currentPassword: '',
})
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  newPasswordConfirm: '',
})

const passwordFocused = ref(false)
const confirmFocused = ref(false)
const confirmTouched = ref(false)
const showUnsavedModal = ref(false)
const pendingRouteLeave = ref(null)
const originalUsername = ref(auth.user?.username ?? '')
const { isPasswordValid } = usePasswordStrength(computed(() => passwordForm.newPassword))
const hasProfileChanges = computed(
  () => profileForm.username.trim() !== (originalUsername.value ?? ''),
)
const hasPasswordChanges = computed(
  () =>
    Boolean(passwordForm.currentPassword) ||
    Boolean(passwordForm.newPassword) ||
    Boolean(passwordForm.newPasswordConfirm),
)
const hasUnsavedChanges = computed(() => hasProfileChanges.value || hasPasswordChanges.value)
const showConfirmMismatch = computed(
  () =>
    isPasswordValid.value &&
    (confirmFocused.value || confirmTouched.value) &&
    passwordForm.newPasswordConfirm &&
    passwordForm.newPassword !== passwordForm.newPasswordConfirm,
)

const activeProfileImage = computed(() => auth.user?.profile_image ?? null)

const activeProfileImageUrl = computed(() => {
  const image = activeProfileImage.value
  if (!image) return null
  return resolveBackendUrl(image.avatar_url || image.url || image.file_path, image.updated_at)
})

const profileImageStyle = computed(() => {
  const imageUrl = activeProfileImageUrl.value
  if (!imageUrl) return null
  return {
    backgroundImage: `url('${imageUrl}')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
    width: '100%',
    height: '100%',
  }
})

const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const profileSubmitting = ref(false)
const passwordSubmitting = ref(false)
const uploadError = ref('')
const uploadInProgress = ref(false)
const showCropModal = ref(false)
const currentCropSession = ref(null)
const recentProfileImages = ref([])
const showActivateModal = ref(false)
const selectedImageToActivate = ref(null)
const activationError = ref('')
const activationInProgress = ref(false)

function buildVariantPreviewStyle(imageUrl, version = null) {
  if (!imageUrl) return null
  return {
    backgroundImage: `url('${resolveBackendUrl(imageUrl, version)}')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
    width: '100%',
    height: '100%',
  }
}

const selectedImagePreviewStyle = computed(() => {
  const image = selectedImageToActivate.value
  if (!image) return null
  return buildVariantPreviewStyle(
    image.preview_url || image.url || image.file_path,
    image.updated_at,
  )
})

async function loadRecentProfileImages() {
  if (!auth.user) {
    recentProfileImages.value = []
    return
  }

  try {
    recentProfileImages.value = await api.listProfileImages(auth.accessToken, auth.setAccessToken)
  } catch {
    recentProfileImages.value = []
  }
}

function revokeCurrentUploadPreview() {
  if (currentCropSession.value?.previewUrl) {
    URL.revokeObjectURL(currentCropSession.value.previewUrl)
  }
}

function resetProfileFeedback() {
  profileError.value = ''
  profileSuccess.value = ''
}

function resetPasswordFeedback() {
  passwordError.value = ''
  passwordSuccess.value = ''
}

function resetUploadFeedback() {
  uploadError.value = ''
}

async function onProfileImageSelected(event) {
  resetUploadFeedback()
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  if (!file.type.startsWith('image/')) {
    uploadError.value = 'Please select a valid image file.'
    event.target.value = ''
    return
  }

  const previewUrl = URL.createObjectURL(file)
  currentCropSession.value = {
    mode: 'upload',
    file,
    previewUrl,
  }
  showCropModal.value = true
  event.target.value = ''
}

async function handleCropSave(cropData) {
  if (!currentCropSession.value) {
    uploadError.value = 'Unable to crop image: missing upload session.'
    return
  }

  if (currentCropSession.value.mode === 'upload') {
    if (!currentCropSession.value.file) {
      uploadError.value = 'Unable to crop image: missing upload file.'
      return
    }

    uploadInProgress.value = true
    try {
      const formData = new FormData()
      formData.append('image', currentCropSession.value.file)
      const uploaded = await api.uploadProfileImage(formData, auth.accessToken, auth.setAccessToken)
      const updatedImage = await api.setProfileImageCrop(
        uploaded.id,
        cropData,
        auth.accessToken,
        auth.setAccessToken,
      )
      if (auth.user) {
        auth.user.profile_image = updatedImage
      }
      await loadRecentProfileImages()
      showCropModal.value = false
      revokeCurrentUploadPreview()
      currentCropSession.value = null
    } catch (error) {
      uploadError.value = error.message
    } finally {
      uploadInProgress.value = false
    }
    return
  }

  if (currentCropSession.value.mode === 'edit') {
    uploadInProgress.value = true
    try {
      const updatedImage = await api.setProfileImageCrop(
        currentCropSession.value.imageId,
        cropData,
        auth.accessToken,
        auth.setAccessToken,
      )
      if (auth.user) {
        auth.user.profile_image = updatedImage
      }
      await loadRecentProfileImages()
      showCropModal.value = false
      currentCropSession.value = null
    } catch (error) {
      uploadError.value = error.message
    } finally {
      uploadInProgress.value = false
    }
    return
  }

  uploadError.value = 'Unsupported crop session.'
}

function handleCropCancel() {
  showCropModal.value = false
  revokeCurrentUploadPreview()
  currentCropSession.value = null
}

function editCurrentCrop() {
  const image = activeProfileImage.value
  if (!image) return

  currentCropSession.value = {
    mode: 'edit',
    imageId: image.id,
    imageUrl: resolveBackendUrl(image.url || image.file_path),
    cropData: {
      crop_x: image.crop_x,
      crop_y: image.crop_y,
      crop_size: image.crop_size,
      original_width: image.original_width,
      original_height: image.original_height,
    },
  }
  showCropModal.value = true
}

function selectImageToActivate(image) {
  selectedImageToActivate.value = image
  activationError.value = ''
  showActivateModal.value = true
}

function cancelActivate() {
  showActivateModal.value = false
  selectedImageToActivate.value = null
  activationError.value = ''
}

async function confirmActivateImage() {
  if (!selectedImageToActivate.value) return

  activationInProgress.value = true
  activationError.value = ''

  try {
    const updatedImage = await api.activateProfileImage(
      selectedImageToActivate.value.id,
      auth.accessToken,
      auth.setAccessToken,
    )
    if (auth.user) {
      auth.user.profile_image = updatedImage
    }
    await loadRecentProfileImages()
    cancelActivate()
  } catch (error) {
    activationError.value = error.message
  } finally {
    activationInProgress.value = false
  }
}

function setShowActivateModal(value) {
  showActivateModal.value = value
  if (!value) {
    cancelActivate()
  }
}

function setShowCropModal(value) {
  showCropModal.value = value
  if (!value) handleCropCancel()
}

function setShowUnsavedModal(value) {
  showUnsavedModal.value = value
  if (!value) cancelNavigation()
}

watch(
  () => auth.user?.username,
  (username) => {
    if (username) {
      originalUsername.value = username
      profileForm.username = username
    }
  },
)

watch(
  () => auth.user?.id,
  () => {
    loadRecentProfileImages()
  },
  { immediate: true },
)

function confirmNavigation() {
  if (pendingRouteLeave.value) {
    pendingRouteLeave.value(true)
  }
  pendingRouteLeave.value = null
  showUnsavedModal.value = false
}

function cancelNavigation() {
  if (pendingRouteLeave.value) {
    pendingRouteLeave.value(false)
  }
  pendingRouteLeave.value = null
  showUnsavedModal.value = false
}

function handleBeforeUnload(event) {
  if (hasUnsavedChanges.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

onBeforeRouteLeave((to, from) => {
  if (!hasUnsavedChanges.value) {
    return true
  }

  showUnsavedModal.value = true
  return new Promise((resolve) => {
    pendingRouteLeave.value = resolve
  })
})

async function updateProfile() {
  resetProfileFeedback()
  if (!auth.user) {
    profileError.value = 'Unable to update profile: not authenticated.'
    return
  }

  const trimmedUsername = profileForm.username.trim()
  if (trimmedUsername === auth.user.username) {
    profileError.value = 'No changes were made.'
    return
  }

  profileSubmitting.value = true
  try {
    const updatedUser = await api.updateCurrentUser(
      {
        username: trimmedUsername,
        current_password: profileForm.currentPassword,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    auth.user = updatedUser
    originalUsername.value = updatedUser.username
    profileSuccess.value = 'Username updated successfully.'
    profileForm.currentPassword = ''
  } catch (e) {
    profileError.value = e.message
  } finally {
    profileSubmitting.value = false
  }
}

async function updatePassword() {
  resetPasswordFeedback()
  if (!passwordForm.newPassword) {
    passwordError.value = 'Enter a new password.'
    return
  }

  passwordSubmitting.value = true
  try {
    await api.updateCurrentUser(
      {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
        new_password_confirm: passwordForm.newPasswordConfirm,
      },
      auth.accessToken,
      auth.setAccessToken,
    )
    passwordSuccess.value = 'Password updated successfully.'
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.newPasswordConfirm = ''
  } catch (e) {
    passwordError.value = e.message
  } finally {
    passwordSubmitting.value = false
  }
}
</script>

<template>
  <section class="space-y-6">
    <section
      class="rounded-3xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 lg:p-6 shadow-sm"
    >
      <h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3">Profile photo</h2>
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-5">
        Upload a profile image and crop it to choose what appears in the avatar button.
      </p>
      <div class="grid gap-5 sm:grid-cols-[auto_1fr] sm:items-center">
        <div class="flex items-center justify-center">
          <div
            class="relative group h-24 w-24 overflow-hidden rounded-full border border-slate-200 bg-slate-100"
          >
            <div
              v-if="activeProfileImage && profileImageStyle"
              :style="profileImageStyle"
              aria-label="Current profile image"
            />
            <img
              v-else-if="activeProfileImage"
              :src="resolveBackendUrl(activeProfileImage.url || activeProfileImage.file_path)"
              alt="Current profile image"
              class="h-full w-full object-cover"
            />
            <div
              v-else
              class="flex h-full w-full items-center justify-center bg-blue-400 text-white text-3xl font-semibold"
            >
              {{ useUserInitials(auth.user.username) }}
            </div>

            <button
              v-if="activeProfileImage"
              type="button"
              @click="editCurrentCrop"
              class="absolute inset-0 flex items-center justify-center bg-slate-950/0 opacity-0 transition duration-200 hover:bg-slate-950/30 group-hover:opacity-100 group/edit"
              aria-label="Edit crop"
            >
              <Pencil
                class="h-6 w-6 m-3 text-white transition-transform group-hover/edit:scale-110"
              />
            </button>
          </div>
        </div>

        <div class="space-y-4">
          <div class="flex flex-wrap gap-3">
            <label
              class="inline-flex cursor-pointer items-center rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark"
            >
              Choose photo
              <input type="file" accept="image/*" class="hidden" @change="onProfileImageSelected" />
            </label>
            <span
              v-if="uploadInProgress"
              class="inline-flex items-center rounded-2xl bg-slate-100 dark:bg-slate-800 px-4 py-3 text-sm text-slate-700 dark:text-slate-300"
            >
              Uploading…
            </span>
          </div>
          <p class="text-sm text-slate-600 dark:text-slate-400">
            We store the image on the backend and then crop the selected square area for your
            avatar.
          </p>
          <p
            v-if="uploadError"
            class="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-700 dark:text-red-300"
          >
            {{ uploadError }}
          </p>
        </div>
      </div>

      <div v-if="recentProfileImages.length > 1" class="mt-6">
        <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
          Recent profile photos
        </h3>
        <div class="flex gap-3 pb-1">
          <button
            v-for="image in recentProfileImages.slice(0, 5)"
            :key="image.id"
            type="button"
            class="shrink-0 rounded-full border p-1 transition hover:border-slate-400 dark:hover:border-slate-500"
            :class="
              image.is_active
                ? 'border-primary ring-2 ring-primary/20'
                : 'border-slate-200 dark:border-slate-600'
            "
            @click="selectImageToActivate(image)"
          >
            <div class="relative h-16 w-16 overflow-hidden rounded-full bg-slate-100">
              <div
                v-if="image.thumbnail_url"
                :style="buildVariantPreviewStyle(image.thumbnail_url, image.updated_at)"
                class="h-full w-full"
              />
              <img
                v-else
                :src="resolveBackendUrl(image.url || image.file_path)"
                alt="Recent profile image"
                class="h-full w-full object-cover"
              />
            </div>
          </button>
        </div>
        <p class="text-xs text-slate-500 mt-2">
          Click a previous image to preview and restore it as your current profile photo.
        </p>
      </div>
    </section>

    <section
      class="rounded-3xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 lg:p-6 shadow-sm"
    >
      <h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3">Change username</h2>
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-5">
        Update your account name and confirm changes with your current password.
      </p>
      <div class="space-y-4">
        <TextInput
          v-model="profileForm.username"
          label="Username"
          autocomplete="username"
          required
        />
        <PasswordInput
          v-model="profileForm.currentPassword"
          label="Password"
          autocomplete="current-password"
          required
        />

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600 dark:text-slate-400">
            Your current username is <strong>{{ auth.user?.username }}</strong
            >.
          </p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="profileSubmitting"
            @click="updateProfile"
          >
            {{ profileSubmitting ? 'Saving…' : 'Save changes' }}
          </button>
        </div>
        <div
          v-if="profileError"
          class="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {{ profileError }}
        </div>
        <div
          v-if="profileSuccess"
          class="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300"
        >
          {{ profileSuccess }}
        </div>
      </div>
    </section>

    <section
      class="rounded-3xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 lg:p-6 shadow-sm"
    >
      <h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3">Change password</h2>
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-5">
        Use a strong, unique password for your account. Password changes require your current
        password.
      </p>
      <div class="space-y-4">
        <PasswordInput
          v-model="passwordForm.currentPassword"
          label="Current password"
          autocomplete="password-current-password"
          required
        />
        <PasswordInput
          v-model="passwordForm.newPassword"
          label="New password"
          autocomplete="password-new-password"
          required
          @focus="passwordFocused = true"
          @blur="passwordFocused = false"
        />
        <div
          class="overflow-hidden transition-all duration-300 ease-out bg-slate-100 dark:bg-slate-800 rounded-lg mt-2"
          :class="passwordFocused ? 'max-h-120' : 'max-h-0'"
        >
          <PasswordStrengthMeter
            :password="passwordForm.newPassword"
            help-text="Choose a strong new password that meets the policy."
            class="px-3 py-3"
          />
        </div>
        <PasswordInput
          v-model="passwordForm.newPasswordConfirm"
          label="Confirm new password"
          autocomplete="password-confirm-new"
          required
          @focus="confirmFocused = true"
          @blur="confirmTouched = true"
        />
        <div v-if="showConfirmMismatch" class="text-sm font-semibold text-red-600 mt-2">
          Passwords do not match.
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600 dark:text-slate-400">
            Password strength must meet the backend policy.
          </p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="passwordSubmitting"
            @click="updatePassword"
          >
            {{ passwordSubmitting ? 'Updating…' : 'Update password' }}
          </button>
        </div>
        <div
          v-if="passwordError"
          class="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {{ passwordError }}
        </div>
        <div
          v-if="passwordSuccess"
          class="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300"
        >
          {{ passwordSuccess }}
        </div>
      </div>
    </section>

    <Modal
      :model-value="showCropModal"
      title="Crop profile photo"
      @update:modelValue="setShowCropModal"
      @close="handleCropCancel"
    >
      <template #default>
        <ProfileImageCropper
          v-if="currentCropSession"
          :image-url="
            currentCropSession.mode === 'upload'
              ? currentCropSession.previewUrl
              : currentCropSession.imageUrl
          "
          :initial-crop="currentCropSession.mode === 'edit' ? currentCropSession.cropData : null"
          @save="handleCropSave"
          @cancel="handleCropCancel"
        />
      </template>
    </Modal>

    <Modal
      :model-value="showActivateModal"
      title="Restore previous photo"
      @update:modelValue="setShowActivateModal"
      @close="cancelActivate"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          Review the selected previous image before restoring it as your current profile photo.
        </p>
        <div
          class="mx-auto h-72 w-72 overflow-hidden rounded-full border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800"
        >
          <div
            v-if="selectedImagePreviewStyle"
            :style="selectedImagePreviewStyle"
            class="h-full w-full"
          />
          <img
            v-else-if="selectedImageToActivate"
            :src="
              resolveBackendUrl(selectedImageToActivate.url || selectedImageToActivate.file_path)
            "
            alt="Selected profile image"
            class="h-full w-full object-cover"
          />
          <div
            v-else
            class="flex h-full w-full items-center justify-center text-slate-500 dark:text-slate-400"
          >
            No image selected.
          </div>
        </div>
        <p
          v-if="activationError"
          class="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {{ activationError }}
        </p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="inline-flex justify-center rounded-2xl bg-slate-100 dark:bg-slate-800 px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-200 transition hover:bg-slate-200 dark:hover:bg-slate-700"
            @click="cancelActivate"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex justify-center rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="activationInProgress"
            @click="confirmActivateImage"
          >
            {{ activationInProgress ? 'Restoring…' : 'Use this photo' }}
          </button>
        </div>
      </div>
    </Modal>

    <Modal
      :model-value="showUnsavedModal"
      title="Unsaved changes"
      @update:modelValue="setShowUnsavedModal"
      @close="cancelNavigation"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-700 dark:text-slate-300">
          You have unsaved changes. Are you sure you want to leave and discard them?
        </p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="btn bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="cancelNavigation"
          >
            Stay
          </button>
          <button
            type="button"
            class="btn bg-primary text-white hover:bg-primary-dark"
            @click="confirmNavigation"
          >
            Leave anyway
          </button>
        </div>
      </div>
    </Modal>
  </section>
</template>
