import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

async function startApp() {
  if (typeof window !== 'undefined' && window.__TAURI__) {
    console.log('Running in Tauri environment')
    try {
      const { startBackend } = await import('./utils/backend')
      await startBackend()
      console.log('Backend started successfully')
    } catch (error) {
      console.error('Failed to start backend:', error)
    }
  }

  const app = createApp(App)
  app.use(router)
  app.mount('#app')
}

startApp()
