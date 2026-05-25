<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, ShieldCheck, User, Shield, Home, ChevronDown } from 'lucide-vue-next'
import Dropdown from '@/components/Dropdown.vue'
import { useUserInitials } from '@/composables/useUserInitials'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const showMenu = ref(false)

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
  { label: 'Profile', route: 'profile', query: { tab: 'profile' }, icon: User },
  { label: 'Security', route: 'profile', query: { tab: 'security' }, icon: Shield },
  { separator: true },
  {
    label: 'Log out',
    route: 'logout',
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
        to="/"
        class="flex items-center gap-2 font-bold text-lg text-blue-600 hover:text-blue-800 transition-colors"
      >
        <Home class="w-5 h-5" />
        <span>yt-dlp Client</span>
      </router-link>

      <!-- Right side -->
      <div class="flex items-center gap-3">
        <router-link
          v-if="auth.isAdmin"
          to="/admin"
          class="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors px-2 py-1 rounded-md hover:bg-blue-50"
        >
          <ShieldCheck class="w-4 h-4" />
          Admin
        </router-link>

        <div v-if="auth.user?.username" class="relative">
          <Dropdown :items="profileMenuItems">
            <template #trigger="{ toggle }">
              <button
                type="button"
                @click="toggle"
                class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-400 text-sm font-semibold leading-none text-white transition-colors hover:bg-blue-500 active:bg-blue-700"
              >
                {{ useUserInitials(auth.user.username) }}
              </button>
            </template>
          </Dropdown>
        </div>

        <button
          @click="onLogout"
          class="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-red-600 transition-colors px-2 py-1 rounded-md hover:bg-red-50"
          title="Logout"
        >
          <LogOut class="w-4 h-4" />
          <span class="hidden sm:block">Logout</span>
        </button>
      </div>
    </div>
  </nav>
</template>
