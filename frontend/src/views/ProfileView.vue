<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AccountSettings from '@/components/AccountSettings.vue'
import SecuritySettings from '@/components/SecuritySettings.vue'

const router = useRouter()
const route = useRoute()

const menuItems = [
  { id: 'account', label: 'Account', route: 'profile', query: { tab: 'account' } },
  { id: 'security', label: 'Security', route: 'profile', query: { tab: 'security' } },
]

const selectedItem = computed(() => {
  const currentTab = String(route.query.tab ?? '')
  return menuItems.find((item) => item.id === currentTab) ?? menuItems[0]
})

const selectedTab = computed(() => selectedItem.value.id)

function selectMenuItem(item) {
  router.push({ name: item.route, query: item.query })
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4">
    <div class="grid gap-6 lg:grid-cols-[200px_1fr] items-start">
      <aside class="border-r-2 border-gray-200 bg-white px-3 py-6 h-[calc(100vh-8rem)]">
        <nav class="space-y-2">
          <button
            v-for="item in menuItems"
            :key="item.id"
            @click="selectMenuItem(item)"
            class="w-full rounded-lg px-3 py-2 text-left font-medium transition hover:bg-blue-50 hover:text-blue-700"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="space-y-6 h-[calc(100vh-8rem)] overflow-auto">
        <div class="flex mt-6">
          <h1>{{ selectedItem.label }} settings</h1>
        </div>

        <AccountSettings v-if="selectedTab === 'account'" />

        <SecuritySettings v-else />
      </main>
    </div>
  </div>
</template>

<style scoped></style>
