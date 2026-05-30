<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AccountSettings from '@/components/AccountSettings.vue'
import SecuritySettings from '@/components/SecuritySettings.vue'
import UsersSettings from '@/components/UsersSettings.vue'
import AuditLogSettings from '@/components/AuditLogSettings.vue'
import { ContactRound, Users, Shield, ScrollText } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const menuItems = computed(() => {
  const items = [
    {
      id: 'account',
      label: 'Account',
      icon: ContactRound,
      route: 'settings',
      query: { tab: 'account' },
      component: AccountSettings,
      description: 'Manage your profile, username, and password.',
    },
    {
      id: 'security',
      label: 'Security',
      icon: Shield,
      route: 'settings',
      query: { tab: 'security' },
      component: SecuritySettings,
      description: 'Review and revoke your active login sessions.',
    },
  ]

  if (auth.isAdmin) {
    items.push({
      id: 'users',
      label: 'Users',
      icon: Users,
      route: 'settings',
      query: { tab: 'users' },
      component: UsersSettings,
      description: 'Administer user accounts and roles.',
    })
    items.push({
      id: 'audit',
      label: 'Audit log',
      icon: ScrollText,
      route: 'settings',
      query: { tab: 'audit' },
      component: AuditLogSettings,
      description: 'Review security-relevant events.',
      wide: true,
    })
  }

  return items
})

const selectedItem = computed(() => {
  const currentTab = String(route.query.tab ?? '')
  return menuItems.value.find((item) => item.id === currentTab) ?? menuItems.value[0]
})

const selectedTab = computed(() => selectedItem.value.id)

function selectMenuItem(item) {
  router.push({ name: item.route, query: item.query })
}
</script>

<template>
  <div class="flex min-h-[calc(100vh-3.5rem)]">
    <!-- Left sidebar — desktop only -->
    <aside
      class="hidden lg:flex flex-col w-52 shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950"
    >
      <div class="px-4 pt-6 pb-1">
        <p
          class="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600 px-2"
        >
          Settings
        </p>
      </div>
      <nav class="px-3 py-2 space-y-0.5">
        <button
          v-for="item in menuItems"
          :key="item.id"
          type="button"
          @click="selectMenuItem(item)"
          :class="[
            'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
            selectedTab === item.id
              ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100',
          ]"
        >
          <component
            :is="item.icon"
            :class="[
              'w-4 h-4 shrink-0',
              selectedTab === item.id
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-slate-400 dark:text-slate-500',
            ]"
          />
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <!-- Main content column -->
    <div class="flex-1 min-w-0 flex flex-col">
      <!-- Mobile horizontal tab bar -->
      <div
        class="lg:hidden sticky top-14 z-10 flex border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950"
      >
        <nav class="flex gap-1 px-4 py-2 overflow-x-auto">
          <button
            v-for="item in menuItems"
            :key="item.id"
            type="button"
            @click="selectMenuItem(item)"
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all shrink-0',
              selectedTab === item.id
                ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800',
            ]"
          >
            <component :is="item.icon" class="w-4 h-4 shrink-0" />
            {{ item.label }}
          </button>
        </nav>
      </div>

      <!-- Page content -->
      <div class="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-950">
        <div :class="['mx-auto px-4 py-8 lg:py-10', selectedItem.wide ? 'max-w-7xl' : 'max-w-3xl']">
          <div class="mb-7">
            <p class="text-xl font-bold text-slate-900 dark:text-slate-100">
              {{ selectedItem.label }}
            </p>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {{ selectedItem.description }}
            </p>
          </div>
          <component :is="selectedItem.component" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
