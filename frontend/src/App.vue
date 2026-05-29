<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import TopBar from '@/components/TopBar.vue'
import SideBar from '@/components/SideBar.vue'

const auth = useAuthStore()
const route = useRoute()
const { init: initTheme } = useTheme()

initTheme()

const sidebarOpen = ref(false)

const showShell = computed(() => auth.isAuthenticated && !route.meta.guestOnly)
</script>

<template>
  <!-- Block all rendering until auth has been determined (prevents flicker to login on F5) -->
  <template v-if="!auth.initialized">
    <div class="min-h-screen flex items-center justify-center dark:bg-slate-950 bg-slate-100">
      <div class="w-8 h-8 rounded-full border-4 border-slate-300 border-t-blue-500 animate-spin" />
    </div>
  </template>
  <template v-else-if="showShell">
    <TopBar :hidden="sidebarOpen" @open-sidebar="sidebarOpen = true" />
    <SideBar :is-open="sidebarOpen" @close="sidebarOpen = false" />
    <!-- Page content — padded to clear the mobile top bar -->
    <main class="min-h-screen pt-14 dark:bg-slate-950">
      <router-view />
    </main>
  </template>
  <template v-else>
    <router-view />
  </template>
</template>

<style scoped></style>
