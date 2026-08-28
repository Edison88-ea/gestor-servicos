import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

// Em desenvolvimento não deve haver service worker. Se um ficou registrado de
// uma sessão antiga (ex.: quando o SW de dev estava ligado), ele serve chunks
// velhos em cache e quebra a navegação — então removemos qualquer SW e limpamos
// os caches ao carregar. Em produção isto é no-op (import.meta.env.DEV = false).
if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((reg) => reg.unregister())
  })
  if (window.caches) {
    caches.keys().then((chaves) => chaves.forEach((c) => caches.delete(c)))
  }
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')
