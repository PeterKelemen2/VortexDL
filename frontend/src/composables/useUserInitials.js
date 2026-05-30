export function useUserInitials(name) {
  if (!name) return ''
  const parts = name.trim().split(/\s+/)
  let initials = parts[0].charAt(0).toUpperCase()
  if (parts.length > 1) {
    initials += parts[parts.length - 1].charAt(0).toUpperCase()
  }
  return initials
}