import { defineStore } from 'pinia'
import client from '../api/client'

// Cadastro de funcionários é tela de escritório (RH/gestão), sempre com sinal —
// não tem camada offline como ponto/OS. Só um cache simples da última lista.
export const useFuncionariosStore = defineStore('funcionarios', {
  state: () => ({
    lista: [],
    carregando: false,
  }),
  actions: {
    async buscar(termo = '', incluirInativos = false) {
      this.carregando = true
      try {
        const { data } = await client.get('/funcionarios/', {
          params: {
            search: termo || undefined,
            incluir_inativos: incluirInativos ? 1 : undefined,
            page_size: 500,
          },
        })
        this.lista = data.results ?? data
        return this.lista
      } finally {
        this.carregando = false
      }
    },

    async criar(payload) {
      const { data } = await client.post('/funcionarios/', payload)
      return data
    },

    async atualizar(id, payload) {
      const { data } = await client.patch(`/funcionarios/${id}/`, payload)
      return data
    },

    // Desligar = inativar no servidor (histórico de ponto/OS preservado).
    async inativar(id) {
      await client.delete(`/funcionarios/${id}/`)
    },

    async meusDados() {
      const { data } = await client.get('/funcionarios/meu/')
      return data
    },
  },
})
