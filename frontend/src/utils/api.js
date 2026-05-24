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

async function request(path, { method = 'GET', body, headers = {}, token } = {}) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }
  if (body) opts.body = JSON.stringify(body)
  if (token) opts.headers['Authorization'] = `Bearer ${token}`

  const sanitizedBody = body ? sanitizeBody(body) : null
  console.debug('[api] request', { path, method, body: sanitizedBody, token: !!token })

  const res = await fetch(`${BACKEND_URL}${path}`, opts)
  let data
  try {
    data = await res.json()
  } catch {
    data = null
  }

  console.debug('[api] response', { path, status: res.status, ok: res.ok, data })

  if (!res.ok) {
    console.error('[api] error', { path, status: res.status, data })
    throw new Error(data?.detail || 'API error')
  }
  return data
}

export const api = {
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  refresh: (refresh_token) => request('/auth/refresh', { method: 'POST', body: { refresh_token } }),
  logout: (refresh_token) => request('/auth/logout', { method: 'POST', body: { refresh_token } }),
  getCurrentUser: (token) => request('/auth/me', { token }),
  getSessions: (token) => request('/auth/sessions', { token }),
  revokeSession: (sessionId, token) => request(`/auth/sessions/${sessionId}`, { method: 'DELETE', token }),
}
