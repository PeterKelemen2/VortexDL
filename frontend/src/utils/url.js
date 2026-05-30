import { BACKEND_URL } from './env'

export function resolveBackendUrl(path, version = null) {
  if (!path) {
    return ''
  }
  if (/^https?:\/\//.test(path)) {
    return version ? `${path}${path.includes('?') ? '&' : '?'}v=${encodeURIComponent(version)}` : path
  }

  const backend = BACKEND_URL.replace(/\/$/, '')
  const resolved = path.startsWith('/') ? `${backend}${path}` : `${backend}/${path}`
  return version ? `${resolved}${resolved.includes('?') ? '&' : '?'}v=${encodeURIComponent(version)}` : resolved
}
