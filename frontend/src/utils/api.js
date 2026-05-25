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
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    credentials: 'include',
  }

  if (body instanceof FormData) {
    delete opts.headers['Content-Type']
    opts.body = body
  } else if (body) {
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
}

export { hasSessionCookies, api }
