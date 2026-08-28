import { defineStore } from 'pinia'
import client from '../api/client'
import { useOsOfflineStore } from './osOffline'
import { blobStore, novaChaveBlob, paraBlobPersistente } from '../utils/idb'

const KEY_CACHE = 'os_cache'

function ehTmp(id) {
  return String(id).startsWith('tmp_')
}
function semRede(erro) {
  return !erro.response
}

function lerCache() {
  try {
    return JSON.parse(localStorage.getItem(KEY_CACHE) || '{}')
  } catch {
    return {}
  }
}

export const useOrdensServicoStore = defineStore('ordensServico', {
  state: () => ({
    ordens: [],
    carregando: false,
  }),

  getters: {
    // Lista do servidor + OS criadas offline que ainda não subiram.
    listaCompleta(state) {
      const offline = useOsOfflineStore()
      return [...offline.locais, ...state.ordens]
    },
  },

  actions: {
    async carregar(statusFiltro) {
      this.carregando = true
      try {
        const { data } = await client.get('/ordens-servico/', {
          params: statusFiltro ? { status: statusFiltro } : {},
        })
        this.ordens = data.results ?? data
        this._guardarNoCache()
      } catch (erro) {
        if (semRede(erro)) {
          this.ordens = Object.values(lerCache())
        } else {
          throw erro
        }
      } finally {
        this.carregando = false
      }
    },

    async buscar(id) {
      const offline = useOsOfflineStore()
      if (ehTmp(id)) return offline.local(id)
      try {
        const { data } = await client.get(`/ordens-servico/${id}/`)
        this._guardarUmaNoCache(data)
        return data
      } catch (erro) {
        if (semRede(erro)) {
          const cache = lerCache()
          if (cache[id]) return cache[id]
        }
        throw erro
      }
    },

    async criar(payload) {
      const offline = useOsOfflineStore()
      if (!navigator.onLine) {
        return offline.criarLocal(payload)
      }
      try {
        const { data } = await client.post('/ordens-servico/', payload)
        this.ordens.unshift(data)
        return data
      } catch (erro) {
        if (semRede(erro)) return offline.criarLocal(payload)
        throw erro
      }
    },

    async iniciar(id) {
      const offline = useOsOfflineStore()
      if (ehTmp(id)) {
        return offline.aplicarLocal(id, {
          status: 'EM_ANDAMENTO',
          data_inicio: new Date().toISOString(),
        })
      }
      try {
        const { data } = await client.post(`/ordens-servico/${id}/iniciar/`)
        this._atualizarNaLista(data)
        return data
      } catch (erro) {
        if (semRede(erro)) {
          offline.enfileirarAcao(id, 'iniciar')
          return this._otimista(id, { status: 'EM_ANDAMENTO' })
        }
        throw erro
      }
    },

    async pausar(id, { motivo, observacao }) {
      const offline = useOsOfflineStore()
      if (ehTmp(id)) {
        const os = offline.local(id)
        os.pausas.unshift({ motivo, motivo_display: motivo, observacao, iniciada_em: new Date().toISOString(), retomada_em: null })
        return offline.aplicarLocal(id, { status: 'PAUSADA' })
      }
      try {
        const { data } = await client.post(`/ordens-servico/${id}/pausar/`, { motivo, observacao })
        this._atualizarNaLista(data)
        return data
      } catch (erro) {
        if (semRede(erro)) {
          offline.enfileirarAcao(id, 'pausar', { motivo, observacao })
          return this._otimista(id, { status: 'PAUSADA' })
        }
        throw erro
      }
    },

    async retomar(id) {
      const offline = useOsOfflineStore()
      if (ehTmp(id)) return offline.aplicarLocal(id, { status: 'EM_ANDAMENTO' })
      try {
        const { data } = await client.post(`/ordens-servico/${id}/retomar/`)
        this._atualizarNaLista(data)
        return data
      } catch (erro) {
        if (semRede(erro)) {
          offline.enfileirarAcao(id, 'retomar')
          return this._otimista(id, { status: 'EM_ANDAMENTO' })
        }
        throw erro
      }
    },

    async concluir(id, payload) {
      const offline = useOsOfflineStore()
      const assinatura = payload.assinatura_cliente instanceof Blob ? payload.assinatura_cliente : null

      if (ehTmp(id)) {
        return offline.concluirLocal(id, {
          relato: payload.relato,
          observacoes_tecnico: payload.observacoes_tecnico,
          assinaturaBlob: assinatura,
        })
      }

      const enviar = () => {
        const fd = new FormData()
        if (payload.relato) fd.append('relato', JSON.stringify(payload.relato))
        if (payload.observacoes_tecnico) fd.append('observacoes_tecnico', payload.observacoes_tecnico)
        if (payload.checklist) fd.append('checklist', JSON.stringify(payload.checklist))
        if (assinatura) fd.append('assinatura_cliente', assinatura, 'assinatura.png')
        return client.post(`/ordens-servico/${id}/concluir/`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }

      try {
        const { data } = await enviar()
        this._atualizarNaLista(data)
        return data
      } catch (erro) {
        if (semRede(erro)) {
          let blobChave = null
          if (assinatura) {
            blobChave = novaChaveBlob('assinatura')
            await blobStore.salvar(blobChave, await paraBlobPersistente(assinatura))
          }
          offline.enfileirarAcao(id, 'concluir', { relato: payload.relato }, blobChave)
          return this._otimista(id, { status: 'CONCLUIDA', data_conclusao: new Date().toISOString() })
        }
        throw erro
      }
    },

    async adicionarFoto(id, arquivo, legenda) {
      const offline = useOsOfflineStore()
      if (ehTmp(id)) return offline.adicionarFotoLocal(id, arquivo)
      try {
        const fd = new FormData()
        fd.append('imagem', arquivo)
        if (legenda) fd.append('legenda', legenda)
        const { data } = await client.post(`/ordens-servico/${id}/fotos/`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        return data
      } catch (erro) {
        if (semRede(erro)) {
          const chave = novaChaveBlob('foto')
          const blob = await paraBlobPersistente(arquivo)
          await blobStore.salvar(chave, blob)
          offline.enfileirarAcao(id, 'foto', {}, chave)
          return { id: chave, legenda: legenda || '', imagem: URL.createObjectURL(blob), _local: true }
        }
        throw erro
      }
    },

    async relatosAnteriores() {
      const { data } = await client.get('/ordens-servico/relatos-anteriores/')
      return data
    },

    async padronizarRelato(id, texto) {
      const { data } = await client.post(`/ordens-servico/${id}/padronizar-relato/`, { texto })
      return data.texto_padronizado
    },

    _otimista(id, mudancas) {
      const os = this.ordens.find((o) => o.id === id)
      if (os) Object.assign(os, mudancas)
      return os || { id, ...mudancas }
    },

    _atualizarNaLista(ordemAtualizada) {
      const index = this.ordens.findIndex((o) => o.id === ordemAtualizada.id)
      if (index !== -1) this.ordens[index] = ordemAtualizada
      this._guardarUmaNoCache(ordemAtualizada)
    },

    _guardarNoCache() {
      const mapa = {}
      for (const o of this.ordens) mapa[o.id] = o
      localStorage.setItem(KEY_CACHE, JSON.stringify(mapa))
    },

    _guardarUmaNoCache(os) {
      const mapa = lerCache()
      mapa[os.id] = os
      localStorage.setItem(KEY_CACHE, JSON.stringify(mapa))
    },
  },
})
