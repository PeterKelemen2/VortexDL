// Centralized API client for backend calls
import { BACKEND_URL } from './env'

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
  const res = await fetch(`${BACKEND_URL}${path}`, opts)
  let data
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) throw new Error(data?.detail || 'API error')
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
