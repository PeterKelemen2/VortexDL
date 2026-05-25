<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AccountSettings from '@/components/AccountSettings.vue'
import SecuritySettings from '@/components/SecuritySettings.vue'

const router = useRouter()
const route = useRoute()

const menuItems = [
  {
    id: 'account',
    label: 'Account',
    route: 'profile',
    query: { tab: 'account' },
    component: AccountSettings,
  },
  {
    id: 'security',
    label: 'Security',
    route: 'profile',
    query: { tab: 'security' },
    component: SecuritySettings,
  },
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
  <div class="max-w-7xl mx-auto min-h-[calc(100vh-57px)] overflow-hidden">
    <div class="grid gap-6 lg:grid-cols-[240px_1fr] min-h-full">
      <aside
        class="overflow-hidden border-b border-gray-200 bg-white pt-4 lg:border-b-0 lg:border-x lg:sticky lg:top-0 lg:self-start lg:min-h-[calc(100vh-57px)]"
      >
        <div class="mb-6 border-b border-gray-200 pb-2">
          <h3>Settings</h3>
        </div>

        <nav class="space-y-2 px-2">
          <button
            v-for="item in menuItems"
            :key="item.id"
            type="button"
            @click="selectMenuItem(item)"
            :class="[
              'w-full rounded-md px-3 py-2 text-left text-sm font-medium transition',
              'border border-transparent hover:border-blue-200 hover:bg-blue-100 hover:text-blue-700',
              { 'bg-blue-50 text-blue-700 border-blue-200': selectedTab === item.id },
              { 'text-slate-700': selectedTab !== item.id },
            ]"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="flex min-h-full flex-col overflow-hidden rounded-3xl">
        <!-- <div class="border-b border-gray-200 bg-white px-6 py-5">
          <h2>{{ selectedItem.label }} settings</h2>
        </div> -->

        <section class="flex-1 min-h-0 overflow-auto py-6 px-4">
          <component :is="selectedItem.component" />
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped></style>
