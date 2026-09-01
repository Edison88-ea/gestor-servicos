import { defineStore } from 'pinia'
import client from '../api/client'
import { useOsOfflineStore } from './osOffline'

const KEY = 'clientes_cache'
const PENDENTES_KEY = 'clientes_pendentes'

function ler(chave) {
  try {
    return JSON.parse(localStorage.getItem(chave) || '[]')
  } catch {
    return []
  }
}

function salvar(chave, valor) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor))
  } catch {
    // cota estourada
  }
}

function novoTmpId() {
  return `tmp_cli_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function filtrar(lista, termo) {
  const t = (termo || '').trim().toLowerCase()
  if (!t) return lista
  return lista.filter((c) =>
    [c.nome, c.documento, c.cidade, c.estado].some((v) => (v || '').toLowerCase().includes(t)),
  )
}

// Junta a lista do servidor com os clientes criados offline que ainda não
// subiram, sem duplicar.
function comPendentes(doServidor, pendentes) {
  const idsPendentes = new Set(pendentes.map((c) => c.id))
  return [...pendentes, ...doServidor.filter((c) => !idsPendentes.has(c.id))]
}

export const useClientesStore = defineStore('clientes', {
  state: () => ({
    resultados: [],
    todos: ler(KEY), // lista completa em cache, para busca offline
    // clientes cadastrados sem sinal, aguardando envio
    pendentes: ler(PENDENTES_KEY),
    carregando: false,
    sincronizando: false,
  }),
  actions: {
    _persistir() {
      salvar(KEY, this.todos)
      salvar(PENDENTES_KEY, this.pendentes)
    },

    _inserirLocal(c) {
      this.todos = [c, ...this.todos.filter((x) => x.id !== c.id)]
      this.resultados = [c, ...this.resultados.filter((x) => x.id !== c.id)]
      this._persistir()
    },

    // Substitui um cliente (por id) na memória e no cache — usado ao trocar o
    // id temporário pelo real depois da sincronização.
    _substituir(idAntigo, novo) {
      const troca = (lista) => lista.map((c) => (c.id === idAntigo ? novo : c))
      this.todos = troca(this.todos)
      this.resultados = troca(this.resultados)
      this._persistir()
    },

    async buscar(termo) {
      this.carregando = true
      try {
        const { data } = await client.get('/clientes/', {
          params: termo ? { search: termo } : {},
        })
        const doServidor = data.results ?? data
        this.resultados = comPendentes(doServidor, filtrar(this.pendentes, termo))
        if (!termo) {
          this.todos = comPendentes(doServidor, this.pendentes)
          salvar(KEY, this.todos)
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

    async criar(payload) {
      if (navigator.onLine) {
        try {
          const { data } = await client.post('/clientes/', payload)
          this._inserirLocal(data)
          return data
        } catch (e) {
          if (e.response) throw e // 4xx: erro de validação de verdade
          // sem rede: continua para o caminho offline
        }
      }
      const local = { id: novoTmpId(), _local: true, ...payload }
      this.pendentes.push(local)
      this._inserirLocal(local)
      return local
    },

    async atualizar(id, payload) {
      // Cliente ainda não sincronizado: edita só localmente.
      if (String(id).startsWith('tmp_')) {
        const p = this.pendentes.find((c) => c.id === id)
        if (p) Object.assign(p, payload)
        const atualizado = { ...(p || { id, _local: true }), ...payload }
        this._substituir(id, atualizado)
        return atualizado
      }
      if (!navigator.onLine) {
        const e = new Error('offline')
        e.offline = true
        throw e
      }
      const { data } = await client.patch(`/clientes/${id}/`, payload)
      this._substituir(id, data)
      return data
    },

    async sincronizar() {
      if (this.sincronizando || !navigator.onLine || !this.pendentes.length) return
      this.sincronizando = true
      const osOffline = useOsOfflineStore()
      const restantes = []
      for (const local of this.pendentes) {
        try {
          const { id, _local, erroSync, ...payload } = local
          const { data } = await client.post('/clientes/', payload)
          this._substituir(local.id, data)
          // qualquer OS criada offline que aponta para este cliente tmp
          osOffline.trocarClienteTmp(local.id, data.id)
        } catch (e) {
          if (e.response) {
            local.erroSync = e.response.data?.detail || `Erro ${e.response.status}`
            restantes.push(local)
          } else {
            restantes.push(local)
            break // sem rede: para e tenta de novo depois
          }
        }
      }
      this.pendentes = restantes
      this._persistir()
      this.sincronizando = false
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
        this.todos = comPendentes(todos, this.pendentes)
        salvar(KEY, this.todos)
      } catch {
        // sem rede: mantém o cache atual
      }
    },
  },
})
