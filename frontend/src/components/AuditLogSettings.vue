<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import DataTable from '@/components/DataTable.vue'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const toast = useToast()

const rows = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const actionFilter = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const columns = [
  { key: 'created_at', label: 'Time', width: '200px' },
  { key: 'action', label: 'Action' },
  { key: 'username', label: 'User' },
  { key: 'ip_address', label: 'IP address' },
  { key: 'detail', label: 'Detail' },
]

function formatTime(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

async function load() {
  loading.value = true
  try {
    const data = await api.listAuditLogs(
      { page: page.value, pageSize: pageSize.value, action: actionFilter.value.trim() },
      auth.accessToken,
      auth.setAccessToken,
    )
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    toast.error(e?.message || 'Failed to load audit log')
  } finally {
    loading.value = false
  }
}

watch([page, pageSize], load)

let filterTimer = null
watch(actionFilter, () => {
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 350)
})

onMounted(load)
</script>

<template>
  <div
    class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden"
  >
    <div
      class="px-5 py-5 sm:px-6 border-b border-slate-200 dark:border-slate-800 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p
          class="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500"
        >
          Audit log
        </p>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
          Append-only record of security-relevant events.
        </p>
      </div>
      <input
        v-model="actionFilter"
        type="text"
        placeholder="Filter by action…"
        class="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 outline-none transition focus:border-slate-400 dark:focus:border-slate-500 sm:w-56"
      />
    </div>

    <div class="px-5 py-5 sm:px-6">
      <DataTable
        :columns="columns"
        :rows="rows"
        :loading="loading"
        :page="page"
        :total-pages="totalPages"
        :page-size="pageSize"
        :page-size-options="[20, 50, 100]"
        empty-text="No audit events recorded."
        @update:page="(p) => (page = p)"
        @update:page-size="
          (s) => {
            pageSize = s
            page = 1
          }
        "
      >
        <template #cell-created_at="{ value }">
          <span class="whitespace-nowrap">{{ formatTime(value) }}</span>
        </template>
        <template #cell-action="{ value }">
          <code class="text-xs">{{ value }}</code>
        </template>
        <template #cell-username="{ value }">{{ value || '—' }}</template>
        <template #cell-ip_address="{ value }">{{ value || '—' }}</template>
        <template #cell-detail="{ value }">{{ value || '—' }}</template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped></style>
