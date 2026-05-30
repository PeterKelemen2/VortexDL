<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, ShieldCheck, Settings } from 'lucide-vue-next'
import Dropdown from '@/components/Dropdown.vue'
import { useUserInitials } from '@/composables/useUserInitials'
import { resolveBackendUrl } from '@/utils/url'
import { BRAND_NAME, BRAND_ROUTE, BRAND_ICON } from '@/constants/branding'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const showMenu = ref(false)

const activeProfileImageUrl = computed(() => {
  const image = auth.user?.profile_image
  if (!image) return null
  return resolveBackendUrl(image.avatar_url || image.url || image.file_path, image.updated_at)
})

const avatarStyle = computed(() => {
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

watch(
  () => route.fullPath,
  () => {
    showMenu.value = false
  },
)

async function onLogout() {
  await auth.logout()
  router.push('/login')
}

const profileMenuItems = [
  { label: 'Settings', route: 'settings', query: { tab: 'account' }, icon: Settings },
  // { label: 'Security', route: 'profile', query: { tab: 'security' }, icon: Shield },
  { separator: true },
  {
    label: 'Log out',
    action: onLogout,
    icon: LogOut,
    textClass: 'text-red-600 font-medium',
    hoverClass: 'hover:bg-red-50',
  },
]
</script>

<template>
  <nav class="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
      <!-- Brand -->
      <router-link
        :to="BRAND_ROUTE"
        class="flex items-center gap-2 font-bold text-lg text-blue-600 hover:text-blue-800 transition-colors"
      >
        <component :is="BRAND_ICON" class="w-5 h-5" />
        <span>{{ BRAND_NAME }}</span>
      </router-link>

      <!-- Right side -->
      <div class="flex items-center gap-3">
        <!-- <router-link
          v-if="auth.isAdmin"
          to="/admin"
          class="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors px-2 py-1 rounded-md hover:bg-blue-50"
        >
          <ShieldCheck class="w-4 h-4" />
          Admin
        </router-link> -->

        <div v-if="auth.user?.username" class="relative">
          <Dropdown :items="profileMenuItems">
            <template #trigger="{ toggle }">
              <div class="relative inline-flex">
                <button
                  type="button"
                  @click="toggle"
                  class="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-blue-400 text-sm font-semibold leading-none text-white transition-colors hover:bg-blue-500 active:bg-blue-700"
                >
                  <template v-if="auth.user?.profile_image && avatarStyle">
                    <div :style="avatarStyle" aria-label="Profile" />
                  </template>
                  <template v-else-if="auth.user?.profile_image">
                    <img
                      :src="
                        resolveBackendUrl(
                          auth.user.profile_image.url || auth.user.profile_image.file_path,
                        )
                      "
                      alt="Profile"
                      class="absolute inset-0 h-full w-full object-cover"
                    />
                  </template>
                  <template v-else>
                    {{ useUserInitials(auth.user.username) }}
                  </template>
                </button>
                <ShieldCheck
                  v-if="auth.isAdmin"
                  class="absolute -bottom-px -right-1.5 h-5 w-5 rounded-full bg-white text-blue-600 border border-white shadow-sm"
                />
              </div>
            </template>
          </Dropdown>
        </div>
      </div>
    </div>
  </nav>
</template>
