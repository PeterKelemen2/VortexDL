<script setup>
import { computed, ref, reactive, watch, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Modal from '@/components/Modal.vue'
import PasswordInput from '@/components/PasswordInput.vue'
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter.vue'
import TextInput from '@/components/TextInput.vue'
import ProfileImageCropper from '@/components/ProfileImageCropper.vue'
import { usePasswordStrength } from '@/composables/usePasswordStrength'

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

const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const profileSubmitting = ref(false)
const passwordSubmitting = ref(false)
const uploadError = ref('')
const uploadInProgress = ref(false)
const showCropModal = ref(false)
const currentUpload = ref(null)

function revokeCurrentUploadPreview() {
  if (currentUpload.value?.previewUrl) {
    URL.revokeObjectURL(currentUpload.value.previewUrl)
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
  currentUpload.value = {
    file,
    previewUrl,
  }
  showCropModal.value = true
  event.target.value = ''
}

async function handleCropSave(cropData) {
  if (!currentUpload.value?.file) {
    uploadError.value = 'Unable to crop image: missing upload file.'
    return
  }

  uploadInProgress.value = true
  try {
    const formData = new FormData()
    formData.append('image', currentUpload.value.file)
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
    showCropModal.value = false
    revokeCurrentUploadPreview()
    currentUpload.value = null
  } catch (error) {
    uploadError.value = error.message
  } finally {
    uploadInProgress.value = false
  }
}

function handleCropCancel() {
  showCropModal.value = false
  revokeCurrentUploadPreview()
  currentUpload.value = null
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
    <section class="rounded-3xl border border-gray-200 bg-white p-4 lg:p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Profile photo</h2>
      <p class="text-sm text-slate-600 mb-5">
        Upload a profile image and crop it to choose what appears in the avatar button.
      </p>
      <div class="grid gap-5 sm:grid-cols-[auto_1fr] sm:items-center">
        <div class="flex items-center justify-center">
          <div class="h-24 w-24 overflow-hidden rounded-full border border-slate-200 bg-slate-100">
            <img
              v-if="activeProfileImage?.url"
              :src="activeProfileImage.url"
              alt="Current profile image"
              class="h-full w-full object-cover"
            />
            <div
              v-else
              class="flex h-full w-full items-center justify-center bg-blue-400 text-white text-lg font-semibold"
            >
              {{ auth.user ? auth.user.username.charAt(0).toUpperCase() : '' }}
            </div>
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
              class="inline-flex items-center rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700"
            >
              Uploading…
            </span>
          </div>
          <p class="text-sm text-slate-600">
            We store the image on the backend and then crop the selected square area for your
            avatar.
          </p>
          <p
            v-if="uploadError"
            class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {{ uploadError }}
          </p>
        </div>
      </div>
    </section>

    <section class="rounded-3xl border border-gray-200 bg-white p-4 lg:p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Change username</h2>
      <p class="text-sm text-slate-600 mb-5">
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
          <p class="text-sm text-slate-600">
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
          class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {{ profileError }}
        </div>
        <div
          v-if="profileSuccess"
          class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {{ profileSuccess }}
        </div>
      </div>
    </section>

    <section class="rounded-3xl border border-gray-200 bg-white p-4 lg:p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Change password</h2>
      <p class="text-sm text-slate-600 mb-5">
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
          class="overflow-hidden transition-all duration-300 ease-out bg-slate-100 rounded-lg mt-2"
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
          <p class="text-sm text-slate-600">Password strength must meet the backend policy.</p>
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
          class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {{ passwordError }}
        </div>
        <div
          v-if="passwordSuccess"
          class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
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
          v-if="currentUpload"
          :image-url="currentUpload.previewUrl"
          @save="handleCropSave"
          @cancel="handleCropCancel"
        />
      </template>
    </Modal>

    <Modal
      :model-value="showUnsavedModal"
      title="Unsaved changes"
      @update:modelValue="setShowUnsavedModal"
      @close="cancelNavigation"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-700">
          You have unsaved changes. Are you sure you want to leave and discard them?
        </p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="btn bg-white text-slate-700 border border-slate-300 hover:bg-slate-100"
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
