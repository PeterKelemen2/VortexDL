<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, ShieldCheck, Home, ChevronDown } from 'lucide-vue-next'

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

function goTo(tab) {
  router.push({ name: 'profile', query: { tab } })
}
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
          <button
            type="button"
            @click="showMenu = !showMenu"
            class="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-700 transition-colors px-2 py-1 rounded-md hover:bg-blue-50"
          >
            {{ auth.user.username }}
            <ChevronDown class="w-4 h-4" />
          </button>
          <div
            v-if="showMenu"
            class="absolute right-0 mt-2 w-40 rounded-xl border border-gray-200 bg-white shadow-lg ring-1 ring-black ring-opacity-5"
          >
            <button
              type="button"
              @click="goTo('profile')"
              class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              Profile
            </button>
            <button
              type="button"
              @click="goTo('security')"
              class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              Security
            </button>
          </div>
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
