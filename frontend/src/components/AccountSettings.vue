<script setup>
const props = defineProps({
  profileForm: {
    type: Object,
    required: true,
  },
  passwordForm: {
    type: Object,
    required: true,
  },
  authUser: {
    type: Object,
    required: false,
  },
  profileError: {
    type: String,
    default: '',
  },
  profileSuccess: {
    type: String,
    default: '',
  },
  passwordError: {
    type: String,
    default: '',
  },
  passwordSuccess: {
    type: String,
    default: '',
  },
  profileSubmitting: {
    type: Boolean,
    default: false,
  },
  passwordSubmitting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update-profile', 'update-password'])
</script>

<template>
  <section class="space-y-6">
    <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Account</h2>
      <p class="text-sm text-slate-600 mb-5">
        Update your account name and confirm changes with your current password.
      </p>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-800 mb-2" for="username">
            Username
          </label>
          <input
            id="username"
            v-model="profileForm.username"
            type="text"
            class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium text-slate-800 mb-2"
            for="username-current-password"
          >
            Current password
          </label>
          <input
            id="username-current-password"
            v-model="profileForm.currentPassword"
            type="password"
            class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600">
            Your current username is <strong>{{ authUser?.username }}</strong
            >.
          </p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="profileSubmitting"
            @click="$emit('update-profile')"
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

    <section class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 class="text-xl font-semibold text-slate-900 mb-3">Change password</h2>
      <p class="text-sm text-slate-600 mb-5">
        Use a strong, unique password for your account. Password changes require your current
        password.
      </p>
      <div class="space-y-4">
        <div>
          <label
            class="block text-sm font-medium text-slate-800 mb-2"
            for="password-current-password"
          >
            Current password
          </label>
          <input
            id="password-current-password"
            v-model="passwordForm.currentPassword"
            type="password"
            class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-800 mb-2" for="new-password">
            New password
          </label>
          <input
            id="new-password"
            v-model="passwordForm.newPassword"
            type="password"
            class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-800 mb-2" for="confirm-new-password">
            Confirm new password
          </label>
          <input
            id="confirm-new-password"
            v-model="passwordForm.newPasswordConfirm"
            type="password"
            class="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-600">Password strength must meet the backend policy.</p>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="passwordSubmitting"
            @click="$emit('update-password')"
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
  </section>
</template>
