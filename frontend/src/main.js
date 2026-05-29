import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Wait for the initial navigation (and its beforeEach guards, which include
// auth.init()) to complete before mounting. Without this, Vue renders the app
// before the guard has resolved, causing a brief flash of the login page.
router.isReady().then(() => {
  app.mount('#app')
  // Delay overlay removal until after requestAnimationFrame fires. rAF is a
  // macrotask, so it only runs after all pending microtasks have settled —
  // that includes any in-flight navigation redirect chains and Vue re-renders.
  // This means the overlay stays visible until the *final* route is painted.
  requestAnimationFrame(() => {
    const overlay = document.getElementById('loading-overlay')
    if (!overlay) return
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true })
    overlay.classList.add('fade-out')
  })
})
