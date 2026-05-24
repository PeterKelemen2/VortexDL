import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/utils/api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('accessToken') || null)
  const user = ref(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  let initPromise = null

  async function init() {
    if (initialized.value) return
    if (!initPromise) initPromise = _doInit()
    return initPromise
  }

  async function _doInit() {
    if (accessToken.value) {
      try {
        user.value = await api.getCurrentUser(accessToken.value, setAccessToken)
        initialized.value = true
        return
      } catch {
        // access token might be expired or invalid
      }
    }

    try {
      const tokens = await api.refresh()
      setAccessToken(tokens.access_token)
      user.value = await api.getCurrentUser(tokens.access_token, setAccessToken)
    } catch {
      _clearAuth()
    } finally {
      initialized.value = true
    }
  }

  async function login(username, password, deviceName = null, userAgent = null) {
    const payload = { username, password }
    if (deviceName) payload.device_name = deviceName
    if (userAgent) payload.user_agent = userAgent

    console.debug('[auth] login payload', { username, deviceName, userAgent })
    const tokens = await api.login(payload)
    setAccessToken(tokens.access_token)
    user.value = await api.getCurrentUser(tokens.access_token, setAccessToken)
    initialized.value = true
    initPromise = null
  }

  async function logout() {
    try {
      await api.logout()
    } catch {
      // best effort
    }
    _clearAuth()
  }

  function setAccessToken(token) {
    accessToken.value = token
    if (token) {
      localStorage.setItem('accessToken', token)
    } else {
      localStorage.removeItem('accessToken')
    }
  }

  function _clearAuth() {
    accessToken.value = null
    user.value = null
    initPromise = null
    initialized.value = false
    localStorage.removeItem('accessToken')
  }

  return {
    accessToken,
    user,
    initialized,
    isAuthenticated,
    isAdmin,
    init,
    login,
    logout,
    setAccessToken,
  }
})
