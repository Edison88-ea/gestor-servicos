import { defineStore } from 'pinia'
import client from '../api/client'

export const useNotificacoesStore = defineStore('notificacoes', {
  state: () => ({
    itens: [],
    naoLidas: 0,
  }),
  actions: {
    async carregar() {
      const { data } = await client.get('/notificacoes/')
      this.itens = data.results ?? data
    },

    async atualizarContagem() {
      const { data } = await client.get('/notificacoes/nao_lidas/')
      this.naoLidas = data.total
    },

    async marcarLida(id) {
      await client.post(`/notificacoes/${id}/marcar-lida/`)
      const item = this.itens.find((n) => n.id === id)
      if (item) item.lida = true
      await this.atualizarContagem()
    },

    async marcarTodasLidas() {
      await client.post('/notificacoes/marcar-todas-lidas/')
      this.itens.forEach((n) => (n.lida = true))
      this.naoLidas = 0
    },
  },
})
