<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, ShieldCheck, Home } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

async function onLogout() {
  await auth.logout()
  router.push('/login')
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

        <span class="text-sm text-gray-500 hidden sm:block">
          {{ auth.user?.username }}
        </span>

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
