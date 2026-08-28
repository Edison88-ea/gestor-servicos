import { defineStore } from 'pinia'
import client from '../api/client'

export const useSolicitacoesPontoStore = defineStore('solicitacoesPonto', {
  state: () => ({
    itens: [],
    carregando: false,
  }),
  actions: {
    async carregar(statusFiltro) {
      this.carregando = true
      try {
        const { data } = await client.get('/solicitacoes-ponto/', {
          params: statusFiltro ? { status: statusFiltro } : {},
        })
        this.itens = data.results ?? data
      } finally {
        this.carregando = false
      }
    },

    async criar(payload) {
      const { data } = await client.post('/solicitacoes-ponto/', payload)
      this.itens.unshift(data)
      return data
    },

    async aprovar(id, resposta) {
      const { data } = await client.post(`/solicitacoes-ponto/${id}/aprovar/`, { resposta })
      this._atualizar(data)
      return data
    },

    async rejeitar(id, resposta) {
      const { data } = await client.post(`/solicitacoes-ponto/${id}/rejeitar/`, { resposta })
      this._atualizar(data)
      return data
    },

    _atualizar(item) {
      const i = this.itens.findIndex((s) => s.id === item.id)
      if (i !== -1) this.itens[i] = item
    },
  },
})
