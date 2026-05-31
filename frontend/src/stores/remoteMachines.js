import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

export const useRemoteMachinesStore = defineStore('remoteMachines', () => {
  const auth = useAuthStore()

  // User-facing: machines the current user may download to.
  const myMachines = ref([])
  const myMachinesLoaded = ref(false)

  // Browser state.
  const currentMachineId = ref(null)
  const currentPath = ref('/')
  const entries = ref([])
  const browsing = ref(false)
  const browseError = ref('')

  function _onRefresh(token) {
    auth.setAccessToken(token)
  }

  async function fetchMyMachines(force = false) {
    if (myMachinesLoaded.value && !force) return myMachines.value
    myMachines.value = (await api.listMyRemoteMachines(auth.accessToken, _onRefresh)) ?? []
    myMachinesLoaded.value = true
    return myMachines.value
  }

  async function browse(machineId, path = '/') {
    browsing.value = true
    browseError.value = ''
    try {
      const res = await api.browseRemoteFolder(machineId, path, auth.accessToken, _onRefresh)
      currentMachineId.value = machineId
      currentPath.value = res.path
      entries.value = res.entries
      return res
    } catch (err) {
      browseError.value = err?.message || 'Failed to browse folder'
      throw err
    } finally {
      browsing.value = false
    }
  }

  function navigateInto(name) {
    const base = currentPath.value === '/' ? '' : currentPath.value
    return browse(currentMachineId.value, `${base}/${name}`)
  }

  function navigateUp() {
    if (currentPath.value === '/') return Promise.resolve()
    const parts = currentPath.value.split('/').filter(Boolean)
    parts.pop()
    return browse(currentMachineId.value, '/' + parts.join('/'))
  }

  function reset() {
    currentMachineId.value = null
    currentPath.value = '/'
    entries.value = []
    browseError.value = ''
  }

  return {
    myMachines,
    myMachinesLoaded,
    currentMachineId,
    currentPath,
    entries,
    browsing,
    browseError,
    fetchMyMachines,
    browse,
    navigateInto,
    navigateUp,
    reset,
  }
})
