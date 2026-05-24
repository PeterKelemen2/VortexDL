import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/utils/api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('accessToken') || null)
  const refreshToken = ref(localStorage.getItem('refreshToken') || null)
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
        user.value = await api.getCurrentUser(accessToken.value)
      } catch {
        if (refreshToken.value) {
          try {
            const tokens = await api.refresh(refreshToken.value)
            _setTokens(tokens.access_token, tokens.refresh_token)
            user.value = await api.getCurrentUser(accessToken.value)
          } catch {
            _clearAuth()
          }
        } else {
          _clearAuth()
        }
      }
    }
    initialized.value = true
  }

  async function login(username, password, deviceName = null, userAgent = null) {
    const payload = { username, password }
    if (deviceName) payload.device_name = deviceName
    if (userAgent) payload.user_agent = userAgent
    console.debug('[auth] login payload', { username, deviceName, userAgent })
    const tokens = await api.login(payload)
    _setTokens(tokens.access_token, tokens.refresh_token)
    user.value = await api.getCurrentUser(accessToken.value)
    initialized.value = true
    initPromise = null
  }

  async function logout() {
    if (refreshToken.value) {
      try { await api.logout(refreshToken.value) } catch { /* best-effort */ }
    }
    _clearAuth()
  }

  function _setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
  }

  function _clearAuth() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    initPromise = null
    initialized.value = false
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  return {
    accessToken,
    refreshToken,
    user,
    initialized,
    isAuthenticated,
    isAdmin,
    init,
    login,
    logout,
  }
})
