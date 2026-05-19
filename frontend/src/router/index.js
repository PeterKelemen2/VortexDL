import { createRouter, createWebHistory } from 'vue-router'
import RegisterView from '@/views/RegisterView.vue'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/register', name: 'register', component: RegisterView },
  { path: '/login', name: 'login', component: LoginView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
