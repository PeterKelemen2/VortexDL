// Centralized API client for backend calls
import { BACKEND_URL } from './env'

function sanitizeBody(body) {
  if (!body || typeof body !== 'object') return body
  if (Array.isArray(body)) return body.map((item) => sanitizeBody(item))
  return Object.entries(body).reduce((result, [key, value]) => {
    if (key.toLowerCase().includes('password')) {
      result[key] = '[REDACTED]'
    } else if (typeof value === 'object' && value !== null) {
      result[key] = sanitizeBody(value)
    } else {
      result[key] = value
    }
    return result
  }, {})
}

function getCookie(name) {
  return document.cookie.split(';').reduce((current, cookie) => {
    const [cookieName, ...cookieValue] = cookie.trim().split('=')
    return cookieName === name ? decodeURIComponent(cookieValue.join('=')) : current
  }, null)
}

function getCsrfHeader() {
  const csrfToken = getCookie('csrf_token')
  return csrfToken ? { 'X-CSRF-Token': csrfToken } : {}
}

function hasSessionCookies() {
  // refresh_token is stored in HttpOnly cookie and is not accessible from JS.
  // Use csrf_token as a visible session indicator instead.
  return !!getCookie('csrf_token')
}

async function request(path, { method = 'GET', body, headers = {}, token } = {}) {
  const opts = {
    method,
    headers: { ...headers },
    credentials: 'include',
  }

  if (body instanceof FormData) {
    opts.body = body
  } else if (body) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }

  if (token) opts.headers['Authorization'] = `Bearer ${token}`

  const sanitizedBody = body ? sanitizeBody(body) : null
  console.debug('[api] request', { path, method, body: sanitizedBody, token: !!token })

  const res = await fetch(`${BACKEND_URL}${path}`, opts)
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  console.debug('[api] response', { path, status: res.status, ok: res.ok, data })

  if (!res.ok) {
    console.error('[api] error', { path, status: res.status, data })
    const error = new Error(data?.detail || 'API error')
    error.status = res.status
    throw error
  }

  return data
}

async function requestBlobWithAuth(path, { token, onTokenRefresh } = {}) {
  const doFetch = async (authToken) =>
    fetch(`${BACKEND_URL}${path}`, {
      method: 'GET',
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      credentials: 'include',
    })

  let res = await doFetch(token)
  if (res.status === 401) {
    const refreshResponse = await refresh()
    if (refreshResponse?.access_token) {
      if (typeof onTokenRefresh === 'function') onTokenRefresh(refreshResponse.access_token)
      res = await doFetch(refreshResponse.access_token)
    }
  }
  if (!res.ok) {
    const error = new Error('Download failed')
    error.status = res.status
    throw error
  }
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  const filename = match ? decodeURIComponent(match[1]) : 'download'
  const blob = await res.blob()
  return { blob, filename }
}

async function requestWithAuth(path, { method = 'GET', body, headers = {}, token, onTokenRefresh } = {}) {
  const combinedHeaders = { ...headers, ...getCsrfHeader() }
  try {
    return await request(path, { method, body, headers: combinedHeaders, token })
  } catch (error) {
    if (error?.status === 401 && !['/auth/refresh', '/auth/login'].includes(path)) {
      const refreshResponse = await refresh()
      if (refreshResponse?.access_token) {
        if (typeof onTokenRefresh === 'function') {
          onTokenRefresh(refreshResponse.access_token)
        }
        return await request(path, {
          method,
          body,
          headers: { ...combinedHeaders, ...getCsrfHeader() },
          token: refreshResponse.access_token,
        })
      }
    }
    throw error
  }
}

const api = {
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  refresh: () => request('/auth/refresh', { method: 'POST', headers: getCsrfHeader() }),
  logout: () => request('/auth/logout', { method: 'POST', headers: getCsrfHeader() }),

  requestEmailVerification: (email) =>
    request('/auth/verify-email/request', { method: 'POST', body: { email } }),
  verifyEmail: (token) => request('/auth/verify-email', { method: 'POST', body: { token } }),
  requestPasswordReset: (email) =>
    request('/auth/password-reset/request', { method: 'POST', body: { email } }),
  resetPassword: (payload) => request('/auth/password-reset', { method: 'POST', body: payload }),

  // --- Two-factor authentication ---
  getTwoFactorStatus: (token, onTokenRefresh) =>
    requestWithAuth('/auth/2fa/status', { token, onTokenRefresh }),
  setupTwoFactor: (token, onTokenRefresh) =>
    requestWithAuth('/auth/2fa/setup', { method: 'POST', token, onTokenRefresh }),
  verifyTwoFactor: (code, token, onTokenRefresh) =>
    requestWithAuth('/auth/2fa/verify', { method: 'POST', body: { code }, token, onTokenRefresh }),
  disableTwoFactor: (password, token, onTokenRefresh) =>
    requestWithAuth('/auth/2fa/disable', { method: 'POST', body: { password }, token, onTokenRefresh }),
  regenerateBackupCodes: (code, token, onTokenRefresh) =>
    requestWithAuth('/auth/2fa/backup-codes', { method: 'POST', body: { code }, token, onTokenRefresh }),

  // --- API keys ---
  listApiKeys: (token, onTokenRefresh) =>
    requestWithAuth('/api-keys', { token, onTokenRefresh }),
  createApiKey: (payload, token, onTokenRefresh) =>
    requestWithAuth('/api-keys', { method: 'POST', body: payload, token, onTokenRefresh }),
  revokeApiKey: (keyId, token, onTokenRefresh) =>
    requestWithAuth(`/api-keys/${keyId}`, { method: 'DELETE', token, onTokenRefresh }),

  getCurrentUser: (token, onTokenRefresh) => requestWithAuth('/auth/me', { token, onTokenRefresh }),
  getSessions: (token, onTokenRefresh) => requestWithAuth('/auth/sessions', { token, onTokenRefresh }),
  revokeSession: (sessionId, token, onTokenRefresh) => requestWithAuth(`/auth/sessions/${sessionId}`, {
    method: 'DELETE',
    token,
    onTokenRefresh,
  }),
  logoutAll: (token, onTokenRefresh) => requestWithAuth('/auth/sessions', {
    method: 'DELETE',
    token,
    onTokenRefresh,
  }),
  revokeCurrentSession: (token, onTokenRefresh) => requestWithAuth('/auth/sessions/current', {
    method: 'DELETE',
    token,
    onTokenRefresh,
  }),
  updateCurrentUser: (payload, token, onTokenRefresh) => requestWithAuth('/auth/me', {
    method: 'PATCH',
    body: payload,
    token,
    onTokenRefresh,
  }),
  listUsers: (page, pageSize, token, onTokenRefresh) => requestWithAuth(
    `/admin/users?page=${page}&page_size=${pageSize}`,
    { token, onTokenRefresh },
  ),
  getAdminRoles: (token, onTokenRefresh) => requestWithAuth('/admin/roles', { token, onTokenRefresh }),
  listAuditLogs: ({ page = 1, pageSize = 50, action = '', userId = null } = {}, token, onTokenRefresh) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (action) params.set('action', action)
    if (userId != null && userId !== '') params.set('user_id', String(userId))
    return requestWithAuth(`/admin/audit-logs?${params.toString()}`, { token, onTokenRefresh })
  },
  updateUserByAdmin: (userId, payload, token, onTokenRefresh) => requestWithAuth(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: payload,
    token,
    onTokenRefresh,
  }),
  deleteUserByAdmin: (userId, payload, token, onTokenRefresh) => requestWithAuth(`/admin/users/${userId}`, {
    method: 'DELETE',
    body: payload,
    token,
    onTokenRefresh,
  }),
  uploadProfileImage: (formData, token, onTokenRefresh) => requestWithAuth('/auth/me/avatar', {
    method: 'POST',
    body: formData,
    token,
    onTokenRefresh,
  }),
  setProfileImageCrop: (imageId, payload, token, onTokenRefresh) => requestWithAuth(`/auth/me/avatar/${imageId}`, {
    method: 'PATCH',
    body: payload,
    token,
    onTokenRefresh,
  }),
  activateProfileImage: (imageId, token, onTokenRefresh) => requestWithAuth(`/auth/me/avatar/${imageId}/activate`, {
    method: 'PATCH',
    token,
    onTokenRefresh,
  }),
  listProfileImages: (token, onTokenRefresh) => requestWithAuth('/auth/me/avatars', {
    token,
    onTokenRefresh,
  }),

  // --- Downloads / jobs ---
  createDownloadJob: (payload, token, onTokenRefresh) =>
    requestWithAuth('/jobs/downloads', { method: 'POST', body: payload, token, onTokenRefresh }),
  listJobs: ({ page = 1, pageSize = 20, status = null } = {}, token, onTokenRefresh) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (status) params.set('status', status)
    return requestWithAuth(`/jobs?${params.toString()}`, { token, onTokenRefresh })
  },
  getJob: (jobId, token, onTokenRefresh) =>
    requestWithAuth(`/jobs/${jobId}`, { token, onTokenRefresh }),
  cancelJob: (jobId, token, onTokenRefresh) =>
    requestWithAuth(`/jobs/${jobId}/cancel`, { method: 'POST', token, onTokenRefresh }),
  retryJob: (jobId, token, onTokenRefresh) =>
    requestWithAuth(`/jobs/${jobId}/retry`, { method: 'POST', token, onTokenRefresh }),
  downloadJobFile: (jobId, token, onTokenRefresh) =>
    requestBlobWithAuth(`/jobs/${jobId}/download`, { token, onTokenRefresh }),
  jobStreamUrl: (token) => `${BACKEND_URL}/jobs/stream?token=${encodeURIComponent(token)}`,

  // --- Remote machines (user) ---
  listMyRemoteMachines: (token, onTokenRefresh) =>
    requestWithAuth('/remote-machines', { token, onTokenRefresh }),
  browseRemoteFolder: (machineId, path, token, onTokenRefresh) => {
    const params = new URLSearchParams()
    if (path) params.set('path', path)
    const qs = params.toString()
    return requestWithAuth(
      `/remote-machines/${machineId}/browse${qs ? `?${qs}` : ''}`,
      { token, onTokenRefresh },
    )
  },

  // --- Remote machines (admin) ---
  adminListRemoteMachines: ({ page = 1, pageSize = 20 } = {}, token, onTokenRefresh) =>
    requestWithAuth(
      `/admin/remote-machines?page=${page}&page_size=${pageSize}`,
      { token, onTokenRefresh },
    ),
  adminCreateRemoteMachine: (payload, token, onTokenRefresh) =>
    requestWithAuth('/admin/remote-machines', { method: 'POST', body: payload, token, onTokenRefresh }),
  adminUpdateRemoteMachine: (machineId, payload, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}`, {
      method: 'PATCH',
      body: payload,
      token,
      onTokenRefresh,
    }),
  adminDeleteRemoteMachine: (machineId, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}`, {
      method: 'DELETE',
      token,
      onTokenRefresh,
    }),
  adminTestRemoteMachine: (machineId, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}/test`, {
      method: 'POST',
      token,
      onTokenRefresh,
    }),
  adminListMachineUsers: (machineId, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}/users`, { token, onTokenRefresh }),
  adminAssignUser: (machineId, userId, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}/users`, {
      method: 'POST',
      body: { user_id: userId },
      token,
      onTokenRefresh,
    }),
  adminUnassignUser: (machineId, userId, token, onTokenRefresh) =>
    requestWithAuth(`/admin/remote-machines/${machineId}/users/${userId}`, {
      method: 'DELETE',
      token,
      onTokenRefresh,
    }),
}

export { hasSessionCookies, api }
