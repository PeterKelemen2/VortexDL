import { createRouter, createWebHistory } from 'vue-router'
import RegisterView from '@/views/RegisterView.vue'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import ProfileView from '@/views/ProfileView.vue'
import AdminView from '@/views/AdminView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { useAuthStore } from '@/stores/auth'
import { setLucideFavicon } from '@/utils/favicon'
import { BRAND_NAME, BRAND_ICON } from '@/constants/branding'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '', requiresAuth: true } },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { title: 'Profile', requiresAuth: true } },
  { path: '/admin', name: 'admin', component: AdminView, meta: { title: 'Admin', requiresAuth: true, requiresAdmin: true } },
  { path: '/not-found', name: 'not-found', component: NotFoundView, meta: { title: 'Not Found' } },
  { path: '/forbidden', name: 'forbidden', component: ForbiddenView, meta: { title: 'Forbidden' } },
  { path: '/register', name: 'register', component: RegisterView, meta: { title: 'Register', guestOnly: true } },
  { path: '/login', name: 'login', component: LoginView, meta: { title: 'Login', guestOnly: true } },
  { path: '/:pathMatch(.*)*', redirect: '/not-found' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
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
