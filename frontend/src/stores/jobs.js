import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

export const useJobsStore = defineStore('jobs', () => {
  const auth = useAuthStore()

  const jobs = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref('')
  const loading = ref(false)
  const sseConnected = ref(false)

  const AUTO_DOWNLOAD_KEY = 'dl_auto_download'
  const autoDownload = ref(localStorage.getItem(AUTO_DOWNLOAD_KEY) === 'true')

  function setAutoDownload(val) {
    autoDownload.value = val
    try {
      localStorage.setItem(AUTO_DOWNLOAD_KEY, String(val))
    } catch {
      // storage unavailable
    }
  }

  let eventSource = null
  let reconnectTimer = null

  function _onRefresh(token) {
    auth.setAccessToken(token)
  }

  async function fetchJobs() {
    loading.value = true
    try {
      const res = await api.listJobs(
        { page: page.value, pageSize: pageSize.value, status: statusFilter.value || null },
        auth.accessToken,
        _onRefresh,
      )
      jobs.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function startDownload(payload) {
    const job = await api.createDownloadJob(payload, auth.accessToken, _onRefresh)
    // Prepend if we're on the first page so the user sees it immediately.
    if (page.value === 1) {
      jobs.value = [job, ...jobs.value].slice(0, pageSize.value)
      total.value += 1
    }
    return job
  }

  async function cancelJob(jobId) {
    const updated = await api.cancelJob(jobId, auth.accessToken, _onRefresh)
    _mergeJob(updated)
    return updated
  }

  async function downloadFile(jobId) {
    const { blob, filename } = await api.downloadJobFile(jobId, auth.accessToken, _onRefresh)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function _mergeJob(job) {
    const idx = jobs.value.findIndex((j) => j.id === job.id)
    const previous = idx !== -1 ? jobs.value[idx] : null
    if (idx !== -1) {
      jobs.value[idx] = { ...jobs.value[idx], ...job }
    } else if (page.value === 1 && (!statusFilter.value || statusFilter.value === job.status)) {
      jobs.value = [job, ...jobs.value].slice(0, pageSize.value)
    }
    // Auto-download: trigger when a job transitions into finished with a local file.
    if (
      autoDownload.value &&
      job.status === 'finished' &&
      job.result?.local_available &&
      previous?.status !== 'finished'
    ) {
      downloadFile(job.id).catch(() => {})
    }
  }

  function connectSSE() {
    if (eventSource || !auth.accessToken) return
    const url = api.jobStreamUrl(auth.accessToken)
    eventSource = new EventSource(url)
    eventSource.addEventListener('open', () => {
      sseConnected.value = true
    })
    eventSource.addEventListener('job_update', (evt) => {
      try {
        const parsed = JSON.parse(evt.data)
        if (parsed?.data) _mergeJob(parsed.data)
      } catch {
        // ignore malformed event
      }
    })
    eventSource.addEventListener('error', () => {
      sseConnected.value = false
      // EventSource auto-reconnects, but if the token expired the server will
      // reject it (401). Rebuild the connection with a fresh token after a delay.
      if (eventSource && eventSource.readyState === EventSource.CLOSED) {
        disconnectSSE()
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null
            connectSSE()
          }, 5000)
        }
      }
    })
  }

  function disconnectSSE() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    sseConnected.value = false
  }

  function setPage(value) {
    page.value = value
    return fetchJobs()
  }

  function setStatusFilter(value) {
    statusFilter.value = value
    page.value = 1
    return fetchJobs()
  }

  return {
    jobs,
    total,
    page,
    pageSize,
    statusFilter,
    loading,
    sseConnected,
    autoDownload,
    setAutoDownload,
    fetchJobs,
    startDownload,
    cancelJob,
    downloadFile,
    connectSSE,
    disconnectSSE,
    setPage,
    setStatusFilter,
  }
})
