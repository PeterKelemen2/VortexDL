import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, hasSessionCookies } from '@/utils/api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(null)
  const user = ref(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  let initPromise = null
  let _transientFailCount = 0

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
        _transientFailCount = 0
        return
      } catch {
        // access token might be expired or invalid
      }
    }

    try {
      if (!hasSessionCookies()) {
        initialized.value = true
        _transientFailCount = 0
        return
      }
      const tokens = await api.refresh()
      setAccessToken(tokens.access_token)
      user.value = await api.getCurrentUser(tokens.access_token, setAccessToken)
      initialized.value = true
      _transientFailCount = 0
    } catch (err) {
      // Explicit auth rejection: session is gone, definitively logged out.
      if (err?.status === 401 || err?.status === 403) {
        _clearAuth()
        initialized.value = true
        _transientFailCount = 0
        return
      }
      // Transient failure (network error, AbortError from a rapid F5 reload, 5xx).
      // Do NOT mark initialized — App.vue will keep showing the spinner instead of
      // flashing the login page. Reset initPromise so the next navigation guard
      // triggers a fresh retry automatically (the /login route's beforeEach will
      // call auth.init() again).
      // After 3 consecutive transient failures we give up to avoid an infinite loop
      // (e.g. backend is genuinely down), and fall through to showing the login page.
      _transientFailCount++
      initPromise = null
      if (_transientFailCount >= 3) {
        _transientFailCount = 0
        initialized.value = true
      }
    }
  }

  async function login(username, password, deviceName = null, userAgent = null, totpCode = null) {
    const payload = { username, password }
    if (deviceName) payload.device_name = deviceName
    if (userAgent) payload.user_agent = userAgent
    if (totpCode) payload.totp_code = totpCode

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
  }

  function _clearAuth() {
    accessToken.value = null
    user.value = null
    initPromise = null
    initialized.value = false
    _transientFailCount = 0
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
