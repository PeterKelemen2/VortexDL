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
router.isReady().then(() => app.mount('#app'))
