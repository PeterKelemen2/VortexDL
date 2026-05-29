<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { useUserInitials } from '@/composables/useUserInitials'
import { resolveBackendUrl } from '@/utils/url'
import { BRAND_NAME, BRAND_ICON } from '@/constants/branding'
import { Home, Settings, ShieldCheck, LogOut, Sun, Moon, X } from 'lucide-vue-next'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['close'])

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isDark, toggle: toggleTheme } = useTheme()

const navItems = computed(() => {
  const items = [
    { label: 'Home', icon: Home, route: 'home' },
    { label: 'Settings', icon: Settings, route: 'settings', query: { tab: 'account' } },
  ]
  if (auth.isAdmin) {
    items.push({ label: 'Admin', icon: ShieldCheck, route: 'admin' })
  }
  return items
})

function isActive(item) {
  return route.name === item.route
}

function navigate(item) {
  router.push({ name: item.route, query: item.query })
  emit('close')
}

async function onLogout() {
  await auth.logout()
  emit('close')
  router.push('/login')
}

const avatarStyle = computed(() => {
  const image = auth.user?.profile_image
  if (!image) return null
  const url = resolveBackendUrl(image.avatar_url || image.url || image.file_path, image.updated_at)
  if (!url) return null
  return {
    backgroundImage: `url('${url}')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }
})
</script>

<template>
  <!-- Backdrop -->
  <Transition name="fade">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
      @click="emit('close')"
    />
  </Transition>

  <!-- Sidebar panel -->
  <Transition name="slide">
    <aside
      v-if="isOpen"
      class="fixed left-0 top-0 z-50 flex h-full w-72 flex-col bg-white dark:bg-linear-to-b dark:from-slate-900 dark:to-slate-950 shadow-2xl border-r border-slate-200 dark:border-transparent"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-white/10">
        <div class="flex items-center gap-2.5">
          <div
            class="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 text-blue-500 dark:text-blue-400"
          >
            <component :is="BRAND_ICON" class="h-4 w-4" />
          </div>
          <span class="text-base font-bold tracking-tight text-slate-900 dark:text-white">{{ BRAND_NAME }}</span>
        </div>
        <button
          type="button"
          @click="emit('close')"
          class="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-100 dark:hover:bg-white/10 hover:text-slate-900 dark:hover:text-white"
          aria-label="Close sidebar"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <button
          v-for="item in navItems"
          :key="item.route"
          type="button"
          @click="navigate(item)"
          :class="[
            'group w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
            isActive(item)
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/8 hover:text-slate-900 dark:hover:text-white',
          ]"
        >
          <component
            :is="item.icon"
            :class="[
              'h-4 w-4 shrink-0 transition-colors',
              isActive(item) ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300',
            ]"
          />
          {{ item.label }}
          <span v-if="isActive(item)" class="ml-auto h-1.5 w-1.5 rounded-full bg-blue-500 dark:bg-blue-400" />
        </button>
      </nav>

      <!-- Footer -->
      <div class="border-t border-slate-200 dark:border-white/10 px-3 py-3 space-y-1">
        <!-- Dark mode toggle -->
        <button
          type="button"
          @click="toggleTheme"
          class="group w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-400 transition-all hover:bg-slate-100 dark:hover:bg-white/8 hover:text-slate-900 dark:hover:text-white"
        >
          <component
            :is="isDark ? Sun : Moon"
            class="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors"
          />
          {{ isDark ? 'Light mode' : 'Dark mode' }}
          <!-- Toggle pill -->
          <span
            class="ml-auto flex h-5 w-9 shrink-0 items-center rounded-full px-0.5 transition-colors"
            :class="isDark ? 'bg-blue-600' : 'bg-slate-300'"
          >
            <span
              class="h-4 w-4 rounded-full bg-white shadow transition-transform duration-300"
              :class="isDark ? 'translate-x-4' : 'translate-x-0'"
            />
          </span>
        </button>

        <!-- Logout -->
        <button
          type="button"
          @click="onLogout"
          class="group w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-400 transition-all hover:bg-red-50 dark:hover:bg-red-500/15 hover:text-red-600 dark:hover:text-red-400"
        >
          <LogOut
            class="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500 group-hover:text-red-500 dark:group-hover:text-red-400 transition-colors"
          />
          Log out
        </button>

        <!-- User info -->
        <div
          class="mt-2 flex items-center gap-3 rounded-lg px-3 py-2.5 border border-slate-200 dark:border-white/8 bg-slate-50 dark:bg-white/5"
        >
          <div
            class="relative h-8 w-8 shrink-0 overflow-hidden rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold text-white"
          >
            <div v-if="avatarStyle" class="absolute inset-0" :style="avatarStyle" />
            <span v-else>{{ useUserInitials(auth.user?.username ?? '') }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-slate-800 dark:text-slate-200">{{ auth.user?.username }}</p>
            <p class="truncate text-xs text-slate-500">{{ auth.user?.role }}</p>
          </div>
          <ShieldCheck v-if="auth.isAdmin" class="h-4 w-4 shrink-0 text-blue-500 dark:text-blue-400" />
        </div>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
