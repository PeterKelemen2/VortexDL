import { BACKEND_URL } from './env'

export function resolveBackendUrl(path) {
  if (!path) {
    return ''
  }
  if (/^https?:\/\//.test(path)) {
    return path
  }

  const backend = BACKEND_URL.replace(/\/$/, '')
  if (path.startsWith('/')) {
    return `${backend}${path}`
  }
  return `${backend}/${path}`
}
