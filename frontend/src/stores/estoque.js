import { defineStore } from 'pinia'
import client from '../api/client'

const KEY_LISTA = 'estoque_lista_cache'

function lerCache(chave, vazio) {
  try {
    return JSON.parse(localStorage.getItem(chave) || JSON.stringify(vazio))
  } catch {
    return vazio
  }
}

function semRede(erro) {
  return !erro.response
}

export const useEstoqueStore = defineStore('estoque', {
  state: () => ({
    materiais: lerCache(KEY_LISTA, []),
    resumo: { total_itens: 0, valor_em_estoque: '0', abaixo_minimo: 0 },
    carregando: false,
  }),

  getters: {
    abaixoDoMinimo(state) {
      return state.materiais.filter((m) => m.abaixo_minimo)
    },
  },

  actions: {
    async carregar(params = {}) {
      this.carregando = true
      try {
        const { data } = await client.get('/materiais-estoque/', {
          params: { page_size: 500, ...params },
        })
        this.materiais = data.results ?? data
        if (!Object.keys(params).length) {
          localStorage.setItem(KEY_LISTA, JSON.stringify(this.materiais))
        }
      } catch (erro) {
        if (!semRede(erro)) throw erro
      } finally {
        this.carregando = false
      }
    },

    async carregarResumo() {
      try {
        const { data } = await client.get('/materiais-estoque/resumo/')
        this.resumo = data
      } catch (erro) {
        if (!semRede(erro)) throw erro
      }
    },

    async buscar(id) {
      const { data } = await client.get(`/materiais-estoque/${id}/`)
      this._troca(data)
      return data
    },

    async movimentos(id, params = {}) {
      const { data } = await client.get(`/materiais-estoque/${id}/movimentos/`, { params })
      return data.results ?? data
    },

    async movimentacoes(params = {}) {
      const { data } = await client.get('/movimentos-estoque/', { params })
      return data.results ?? data
    },

    async criar(payload) {
      const { data } = await client.post('/materiais-estoque/', payload)
      this.materiais.push(data)
      this.materiais.sort((a, b) => a.descricao.localeCompare(b.descricao, 'pt-BR'))
      return data
    },

    async atualizar(id, payload) {
      const { data } = await client.patch(`/materiais-estoque/${id}/`, payload)
      this._troca(data)
      return data
    },

    async registrarEntrada(id, payload) {
      const { data } = await client.post(`/materiais-estoque/${id}/entrada/`, payload)
      await this.buscar(id)
      return data
    },

    async registrarAjuste(id, payload) {
      const { data } = await client.post(`/materiais-estoque/${id}/ajuste/`, payload)
      await this.buscar(id)
      return data
    },

    async catalogoPendente() {
      const { data } = await client.get('/materiais-estoque/do-catalogo/')
      return data
    },

    async importarDoCatalogo(descricoes) {
      const { data } = await client.post('/materiais-estoque/do-catalogo/', { descricoes })
      const criados = data.criados ?? []
      for (const m of criados) this.materiais.push(m)
      this.materiais.sort((a, b) => a.descricao.localeCompare(b.descricao, 'pt-BR'))
      return criados
    },

    _troca(m) {
      const i = this.materiais.findIndex((x) => x.id === m.id)
      if (i !== -1) this.materiais[i] = { ...this.materiais[i], ...m }
    },
  },
})
