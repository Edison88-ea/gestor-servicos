import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      // 'prompt': em vez de trocar o service worker silenciosamente, o app
      // mostra um aviso ("nova versão disponível") e só atualiza quando o
      // usuário confirma — evita recarregar a tela de um técnico no meio de
      // um registro de ponto ou de uma OS.
      registerType: 'prompt',
      // O registro do SW é feito por useRegisterSW() em PwaAtualizacao.vue,
      // então desligamos a injeção automática do script para não registrar 2x.
      injectRegister: null,
      includeAssets: ['favicon.svg', 'apple-touch-icon-180x180.png'],
      // Service worker só no build de produção. Em `npm run dev` ele atrapalha:
      // serve chunks antigos em cache e quebra os imports dinâmicos das rotas
      // ("Importing a module script failed") toda vez que o código muda.
      // Para testar instalação/offline: `npm run build && npm run preview`.
      devOptions: {
        enabled: false,
      },
      workbox: {
        navigateFallback: 'index.html',
        // Sem isto o service worker responde QUALQUER navegação (inclusive
        // /admin/, /api/, /media/) com o index.html do SPA em cache — e a tela
        // do Django admin nunca carrega no navegador que já registrou o SW.
        navigateFallbackDenylist: [
          /^\/admin/,
          /^\/api/,
          /^\/media/,
          /^\/static/,
          /^\/healthz/,
        ],
        // Leitura offline. As gravações (criar/iniciar/concluir OS, ponto)
        // passam pela fila do próprio app, não pelo service worker.
        runtimeCaching: [
          {
            // GET da API: rede primeiro, cai para o cache quando sem sinal.
            urlPattern: ({ url, request }) =>
              url.pathname.startsWith('/api/') && request.method === 'GET',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 7 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Fotos e assinaturas já baixadas: cache primeiro.
            urlPattern: ({ url }) => url.pathname.startsWith('/media/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'media-cache',
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Tiles do mapa (OpenStreetMap): cache primeiro, para reabrir
            // áreas já vistas offline.
            urlPattern: ({ url }) => /tile\.openstreetmap\.org/.test(url.href),
            handler: 'CacheFirst',
            options: {
              cacheName: 'mapa-tiles',
              expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      manifest: {
        id: '/',
        name: 'Gestor de Serviços',
        short_name: 'Gestor',
        description: 'Ordens de serviço e ponto eletrônico em um único app',
        lang: 'pt-BR',
        theme_color: '#1e293b',
        background_color: '#1e293b',
        display: 'standalone',
        orientation: 'portrait',
        categories: ['business', 'productivity'],
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    allowedHosts: true,
    proxy: {
      // changeOrigin:false (padrão) preserva o Host original do pedido do
      // celular/túnel, para que o Django gere URLs de mídia (fotos,
      // assinatura) apontando de volta para esse mesmo host, e não para
      // 127.0.0.1 (que não existiria no celular).
      '/api': {
        target: 'http://127.0.0.1:8000',
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
      },
    },
  },
  preview: {
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
      },
    },
  },
})
