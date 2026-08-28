import { defineStore } from 'pinia'
import client from '../api/client'

const KEY = 'clientes_cache'

function lerCache() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

function filtrar(lista, termo) {
  const t = (termo || '').trim().toLowerCase()
  if (!t) return lista
  return lista.filter((c) =>
    [c.nome, c.cnpj, c.cidade, c.estado].some((v) => (v || '').toLowerCase().includes(t)),
  )
}

export const useClientesStore = defineStore('clientes', {
  state: () => ({
    resultados: [],
    todos: lerCache(), // lista completa em cache, para busca offline
    carregando: false,
  }),
  actions: {
    async buscar(termo) {
      this.carregando = true
      try {
        const { data } = await client.get('/clientes/', {
          params: termo ? { search: termo } : {},
        })
        this.resultados = data.results ?? data
        // guarda a lista sem filtro para uso offline
        if (!termo) {
          this.todos = this.resultados
          localStorage.setItem(KEY, JSON.stringify(this.resultados))
        }
      } catch (erro) {
        if (!erro.response) {
          this.resultados = filtrar(this.todos, termo)
        } else {
          throw erro
        }
      } finally {
        this.carregando = false
      }
    },

    async carregarTodosParaCache() {
      try {
        const todos = []
        let params = {}
        for (let pagina = 1; pagina <= 50; pagina += 1) {
          const { data } = await client.get('/clientes/', { params })
          todos.push(...(data.results ?? data))
          if (!data.next) break
          params = { page: pagina + 1 }
        }
        this.todos = todos
        localStorage.setItem(KEY, JSON.stringify(todos))
      } catch {
        // sem rede: mantém o cache atual
      }
    },
  },
})
