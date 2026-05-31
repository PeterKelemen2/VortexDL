import { createRouter, createWebHistory } from 'vue-router'
import RegisterView from '@/views/RegisterView.vue'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import SettingsView from '@/views/SettingsView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import ForgotPasswordView from '@/views/ForgotPasswordView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import VerifyEmailView from '@/views/VerifyEmailView.vue'
import { useAuthStore } from '@/stores/auth'
import { setLucideFavicon } from '@/utils/favicon'
import { BRAND_NAME, BRAND_ICON } from '@/constants/branding'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '', requiresAuth: true } },
  { path: '/settings', name: 'settings', component: SettingsView, meta: { title: 'Settings', requiresAuth: true } },
  { path: '/not-found', name: 'not-found', component: NotFoundView, meta: { title: 'Not Found' } },
  { path: '/forbidden', name: 'forbidden', component: ForbiddenView, meta: { title: 'Forbidden' } },
  { path: '/register', name: 'register', component: RegisterView, meta: { title: 'Register', guestOnly: true } },
  { path: '/login', name: 'login', component: LoginView, meta: { title: 'Login', guestOnly: true } },
  { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { title: 'Forgot Password', guestOnly: true } },
  { path: '/reset-password', name: 'reset-password', component: ResetPasswordView, meta: { title: 'Reset Password', guestOnly: true } },
  { path: '/verify-email', name: 'verify-email', component: VerifyEmailView, meta: { title: 'Verify Email' } },
  { path: '/:pathMatch(.*)*', redirect: '/not-found' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Only allow redirects to internal paths (no protocol-relative or external URLs).
function resolveRedirect(redirectParam) {
  if (typeof redirectParam === 'string' && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
    return { path: redirectParam }
  }
  return { name: 'home' }
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.meta.guestOnly && auth.isAuthenticated) {
    // Honour the ?redirect= param so that a user who was bounced to login
    // (e.g. mid-refresh on F5) ends up back at the page they came from
    // instead of always landing on home.
    return to.query.redirect ? resolveRedirect(to.query.redirect) : { name: 'home' }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined }
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'forbidden' }
  }

  return true
})

setLucideFavicon(BRAND_ICON)

router.afterEach((to) => {
  const title = to.meta.title && typeof to.name === 'string' ?
    `${to.meta.title} | ${BRAND_NAME}` :
    BRAND_NAME
  document.title = title
})

export default router
