import { defineStore } from 'pinia'
import client from '../api/client'

const KEY_LISTA = 'obras_lista_cache'
const KEY_OPCOES = 'obras_opcoes_cache'

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

export const useObrasStore = defineStore('obras', {
  state: () => ({
    obras: lerCache(KEY_LISTA, []),
    opcoes: lerCache(KEY_OPCOES, null),
    carregando: false,
  }),

  getters: {
    contadores(state) {
      const total = state.obras.length
      const concluidas = state.obras.filter((o) => o.status === 'CONCLUIDO').length
      const andamento = state.obras.filter((o) => o.status === 'EM_ANDAMENTO').length
      return { total, concluidas, andamento, planejadas: total - concluidas - andamento }
    },
  },

  actions: {
    async carregar(status) {
      this.carregando = true
      try {
        const { data } = await client.get('/projetos/', {
          params: status ? { status } : {},
        })
        this.obras = data.results ?? data
        if (!status) localStorage.setItem(KEY_LISTA, JSON.stringify(this.obras))
      } catch (erro) {
        if (!semRede(erro)) throw erro
      } finally {
        this.carregando = false
      }
    },

    async buscar(id) {
      const { data } = await client.get(`/projetos/${id}/`)
      return data
    },

    async carregarOpcoes() {
      if (this.opcoes) return this.opcoes
      try {
        const { data } = await client.get('/projetos/opcoes/')
        this.opcoes = data
        localStorage.setItem(KEY_OPCOES, JSON.stringify(data))
      } catch (erro) {
        if (!semRede(erro)) throw erro
      }
      return this.opcoes
    },

    async criar(payload) {
      const { data } = await client.post('/projetos/', payload)
      this.obras.unshift(data)
      return data
    },

    async atualizar(id, payload) {
      const { data } = await client.patch(`/projetos/${id}/`, payload)
      this._trocarNaLista(data)
      return data
    },

    async remover(id) {
      await client.delete(`/projetos/${id}/`)
      this.obras = this.obras.filter((o) => o.id !== id)
    },

    // --- Etapas ---
    async criarEtapa(payload) {
      const { data } = await client.post('/etapas/', payload)
      return data
    },

    async atualizarEtapa(id, payload) {
      const { data } = await client.patch(`/etapas/${id}/`, payload)
      return data
    },

    async removerEtapa(id) {
      await client.delete(`/etapas/${id}/`)
    },

    async atualizarProgresso(etapaId, { realizado, observacao }) {
      const { data } = await client.post(`/etapas/${etapaId}/progresso/`, {
        realizado,
        observacao,
      })
      return data
    },

    async adicionarFoto(etapaId, arquivo, legenda) {
      const fd = new FormData()
      fd.append('imagem', arquivo)
      if (legenda) fd.append('legenda', legenda)
      const { data } = await client.post(`/etapas/${etapaId}/fotos/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },

    // --- Plantas ---
    async adicionarPlanta(projetoId, arquivo, { pagina, descricao } = {}) {
      const fd = new FormData()
      fd.append('arquivo', arquivo)
      if (pagina) fd.append('pagina', pagina)
      if (descricao) fd.append('descricao', descricao)
      const { data } = await client.post(`/projetos/${projetoId}/plantas/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },

    _trocarNaLista(obra) {
      const i = this.obras.findIndex((o) => o.id === obra.id)
      if (i !== -1) this.obras[i] = { ...this.obras[i], ...obra }
    },
  },
})
