// Service worker "autodestrutivo". O SW de desenvolvimento foi desligado, mas
// aparelhos que já o registraram continuam servindo chunks antigos em cache e
// travam a navegação. Quando o navegador busca esta URL na verificação de
// atualização, este SW assume, remove a si mesmo, limpa todos os caches e
// recarrega as abas — deixando o app carregar direto do servidor.
self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      try {
        const chaves = await caches.keys()
        await Promise.all(chaves.map((c) => caches.delete(c)))
      } catch (e) {
        // ignora
      }
      await self.registration.unregister()
      const clientes = await self.clients.matchAll({ type: 'window' })
      clientes.forEach((c) => c.navigate(c.url))
    })(),
  )
})
