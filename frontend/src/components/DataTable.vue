<script setup>
import { computed } from 'vue'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  /** Column definitions: { key, label, sortable?, align?, width?, headerClass?, cellClass? } */
  columns: { type: Array, required: true },
  /** Array of row objects. */
  rows: { type: Array, default: () => [] },
  /** Property name or function returning a unique key per row. */
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: 'No records found.' },
  loadingText: { type: String, default: 'Loading…' },
  // Pagination (controlled by parent for server-side data).
  page: { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 },
  pageSizeOptions: { type: Array, default: () => [5, 10, 20, 50] },
  showPagination: { type: Boolean, default: true },
  // Sorting state (use with v-model:sort-key / v-model:sort-dir).
  sortKey: { type: String, default: '' },
  sortDir: { type: String, default: 'asc' }, // 'asc' | 'desc'
})

const emit = defineEmits([
  'update:page',
  'update:pageSize',
  'update:sortKey',
  'update:sortDir',
  'sort',
  'row-click',
])

function keyFor(row, index) {
  if (typeof props.rowKey === 'function') return props.rowKey(row)
  return row?.[props.rowKey] ?? index
}

function valueFor(row, column) {
  return column.key.split('.').reduce((acc, part) => (acc == null ? acc : acc[part]), row)
}

function alignClass(align) {
  if (align === 'right') return 'text-right'
  if (align === 'center') return 'text-center'
  return 'text-left'
}

function onSort(column) {
  if (!column.sortable) return
  let nextDir = 'asc'
  if (props.sortKey === column.key) {
    nextDir = props.sortDir === 'asc' ? 'desc' : 'asc'
  }
  emit('update:sortKey', column.key)
  emit('update:sortDir', nextDir)
  emit('sort', { key: column.key, dir: nextDir })
}

const isEmpty = computed(() => !props.loading && props.rows.length === 0)

function goToPage(target) {
  if (target < 1 || target > props.totalPages || target === props.page) return
  emit('update:page', target)
}

function onPageSizeChange(event) {
  emit('update:pageSize', Number(event.target.value))
}
</script>

<template>
  <div class="space-y-4">
    <div
      class="overflow-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
    >
      <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
        <thead class="bg-slate-50 dark:bg-slate-800">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              class="px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-300 select-none"
              :class="[
                alignClass(column.align),
                column.headerClass,
                column.sortable ? 'cursor-pointer' : '',
              ]"
              :style="column.width ? { width: column.width } : undefined"
              @click="onSort(column)"
            >
              <span
                class="inline-flex items-center gap-1"
                :class="column.align === 'right' ? 'flex-row-reverse' : ''"
              >
                {{ column.label }}
                <template v-if="column.sortable">
                  <ChevronUp
                    v-if="sortKey === column.key && sortDir === 'asc'"
                    class="h-3.5 w-3.5"
                  />
                  <ChevronDown
                    v-else-if="sortKey === column.key && sortDir === 'desc'"
                    class="h-3.5 w-3.5"
                  />
                  <ChevronsUpDown v-else class="h-3.5 w-3.5 opacity-40" />
                </template>
              </span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
          <tr v-if="loading && rows.length === 0">
            <td
              :colspan="columns.length"
              class="px-4 py-8 text-center text-slate-500 dark:text-slate-400"
            >
              {{ loadingText }}
            </td>
          </tr>
          <tr v-else-if="isEmpty">
            <td
              :colspan="columns.length"
              class="px-4 py-8 text-center text-slate-500 dark:text-slate-400"
            >
              <slot name="empty">{{ emptyText }}</slot>
            </td>
          </tr>
          <tr
            v-for="(row, index) in rows"
            v-else
            :key="keyFor(row, index)"
            class="transition hover:bg-slate-50 dark:hover:bg-slate-800/60"
            @click="emit('row-click', row)"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-4 py-3 text-sm text-slate-700 dark:text-slate-200"
              :class="[alignClass(column.align), column.cellClass]"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="valueFor(row, column)">
                {{ valueFor(row, column) }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="showPagination && totalPages > 0"
      class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <span>Rows per page</span>
        <select
          :value="pageSize"
          class="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
          @change="onPageSizeChange"
        >
          <option v-for="option in pageSizeOptions" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
      </div>

      <div class="flex items-center gap-3 text-sm">
        <span class="text-slate-500 dark:text-slate-400">Page {{ page }} of {{ totalPages }}</span>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 transition hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="page <= 1"
            aria-label="Previous page"
            @click="goToPage(page - 1)"
          >
            <ChevronLeft class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 transition hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="page >= totalPages"
            aria-label="Next page"
            @click="goToPage(page + 1)"
          >
            <ChevronRight class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
