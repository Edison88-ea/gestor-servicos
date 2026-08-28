import { defineStore } from 'pinia'
import client from '../api/client'
import { blobStore, novaChaveBlob, paraBlobPersistente } from '../utils/idb'

const KEY_LOCAIS = 'os_locais'
const KEY_ACOES = 'os_acoes_pendentes'

function carregar(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '[]')
  } catch {
    return []
  }
}
function salvar(key, valor) {
  localStorage.setItem(key, JSON.stringify(valor))
}

function novoTmpId() {
  return `tmp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

// Uma OS criada offline: guarda tudo que for preciso pra recriar o ciclo
// inteiro quando o sinal voltar.
function osLocalVazia(dados) {
  return {
    id: novoTmpId(),
    offline: true,
    status: 'ATRIBUIDA',
    cliente: dados.cliente,
    cliente_nome: dados.cliente_nome || '',
    tecnico_nome: dados.tecnico_nome || '',
    tipo_servico: dados.tipo_servico || '',
    descricao: dados.descricao || '',
    prioridade: dados.prioridade || 'MEDIA',
    latitude_abertura: dados.latitude_abertura ?? null,
    longitude_abertura: dados.longitude_abertura ?? null,
    relato: {},
    observacoes_tecnico: '',
    fotos: [], // [{ id: chaveBlob, legenda }]
    assinaturaChave: null,
    pausas: [],
    data_inicio: null,
    data_conclusao: null,
    criado_em: new Date().toISOString(),
    erroSync: '',
  }
}

export const useOsOfflineStore = defineStore('osOffline', {
  state: () => ({
    locais: carregar(KEY_LOCAIS),
    acoesPendentes: carregar(KEY_ACOES),
    sincronizando: false,
  }),

  getters: {
    pendentes: (s) => s.locais.length + s.acoesPendentes.length,
    temErro: (s) =>
      s.locais.some((o) => o.erroSync) || s.acoesPendentes.some((a) => a.erroSync),
  },

  actions: {
    _persistir() {
      salvar(KEY_LOCAIS, this.locais)
      salvar(KEY_ACOES, this.acoesPendentes)
    },

    local(id) {
      return this.locais.find((o) => o.id === id) || null
    },

    // --- criação/edição local (usadas quando offline ou a OS é tmp_) ---

    criarLocal(dados) {
      const os = osLocalVazia(dados)
      this.locais.unshift(os)
      this._persistir()
      return os
    },

    aplicarLocal(id, mudancas) {
      const os = this.local(id)
      if (!os) return null
      Object.assign(os, mudancas)
      this._persistir()
      return os
    },

    async adicionarFotoLocal(id, arquivo) {
      const chave = novaChaveBlob('foto')
      const blob = await paraBlobPersistente(arquivo)
      await blobStore.salvar(chave, blob)
      const os = this.local(id)
      const foto = { id: chave, legenda: '', imagem: URL.createObjectURL(blob), _local: true }
      os.fotos.push(foto)
      this._persistir()
      return foto
    },

    async concluirLocal(id, { relato, observacoes_tecnico, assinaturaBlob }) {
      const os = this.local(id)
      if (relato) os.relato = relato
      if (observacoes_tecnico != null) os.observacoes_tecnico = observacoes_tecnico
      if (assinaturaBlob) {
        os.assinaturaChave = novaChaveBlob('assinatura')
        await blobStore.salvar(os.assinaturaChave, await paraBlobPersistente(assinaturaBlob))
      }
      os.status = 'CONCLUIDA'
      os.data_conclusao = new Date().toISOString()
      this._persistir()
      return os
    },

    // --- ações pendentes em OS que já existem no servidor ---

    enfileirarAcao(osId, tipo, payload = {}, blobChave = null) {
      this.acoesPendentes.push({
        osId,
        tipo, // 'iniciar' | 'pausar' | 'retomar' | 'foto' | 'concluir'
        payload,
        blobChave,
        criadoEm: new Date().toISOString(),
        erroSync: '',
      })
      this._persistir()
    },

    // --- sincronização ---

    async sincronizar() {
      if (this.sincronizando || !navigator.onLine) return
      if (!this.locais.length && !this.acoesPendentes.length) return
      this.sincronizando = true
      try {
        for (const os of [...this.locais]) {
          await this._enviarOsLocal(os)
        }
        for (const acao of [...this.acoesPendentes]) {
          await this._enviarAcao(acao)
        }
      } catch (e) {
        // erro de rede: para e tenta de novo na próxima
      } finally {
        this.sincronizando = false
      }
    },

    async _enviarOsLocal(os) {
      // Progresso persistido: se um passo falhar, no retry a gente retoma de
      // onde parou em vez de recriar a OS no servidor.
      os.sync = os.sync || { realId: null, iniciado: false, fotosOk: [], concluido: false }
      try {
        if (!os.sync.realId) {
          const { data: criada } = await client.post('/ordens-servico/', {
            cliente: os.cliente,
            tipo_servico: os.tipo_servico,
            descricao: os.descricao,
            prioridade: os.prioridade,
            latitude_abertura: os.latitude_abertura ?? undefined,
            longitude_abertura: os.longitude_abertura ?? undefined,
          })
          os.sync.realId = criada.id
          this._persistir()
        }
        const realId = os.sync.realId

        if (!os.sync.iniciado && ['EM_ANDAMENTO', 'PAUSADA', 'CONCLUIDA'].includes(os.status)) {
          await client.post(`/ordens-servico/${realId}/iniciar/`)
          os.sync.iniciado = true
          this._persistir()
        }

        for (const foto of os.fotos) {
          if (os.sync.fotosOk.includes(foto.id)) continue
          const blob = await blobStore.ler(foto.id)
          if (blob && blob.size > 0) {
            const fd = new FormData()
            fd.append('imagem', blob, 'foto.jpg')
            if (foto.legenda) fd.append('legenda', foto.legenda)
            await client.post(`/ordens-servico/${realId}/fotos/`, fd)
          }
          os.sync.fotosOk.push(foto.id)
          this._persistir()
        }

        if (!os.sync.concluido && os.status === 'CONCLUIDA') {
          const fd = new FormData()
          fd.append('relato', JSON.stringify(os.relato || {}))
          if (os.assinaturaChave) {
            const ass = await blobStore.ler(os.assinaturaChave)
            if (ass && ass.size > 0) fd.append('assinatura_cliente', ass, 'assinatura.png')
          }
          await client.post(`/ordens-servico/${realId}/concluir/`, fd)
          os.sync.concluido = true
        }

        // sucesso: limpa blobs e remove a OS local
        for (const foto of os.fotos) await blobStore.remover(foto.id)
        if (os.assinaturaChave) await blobStore.remover(os.assinaturaChave)
        this.locais = this.locais.filter((o) => o.id !== os.id)
        this._persistir()
      } catch (e) {
        if (e.response) {
          os.erroSync = e.response.data?.detail || `Erro ${e.response.status} ao enviar`
          this._persistir()
        } else {
          throw e // rede: interrompe a sincronização
        }
      }
    },

    async _enviarAcao(acao) {
      try {
        const base = `/ordens-servico/${acao.osId}`
        if (acao.tipo === 'iniciar') await client.post(`${base}/iniciar/`)
        else if (acao.tipo === 'pausar') await client.post(`${base}/pausar/`, acao.payload)
        else if (acao.tipo === 'retomar') await client.post(`${base}/retomar/`)
        else if (acao.tipo === 'foto') {
          const blob = await blobStore.ler(acao.blobChave)
          if (blob && blob.size > 0) {
            const fd = new FormData()
            fd.append('imagem', blob, 'foto.jpg')
            await client.post(`${base}/fotos/`, fd)
          }
        } else if (acao.tipo === 'concluir') {
          const fd = new FormData()
          fd.append('relato', JSON.stringify(acao.payload.relato || {}))
          if (acao.blobChave) {
            const ass = await blobStore.ler(acao.blobChave)
            if (ass && ass.size > 0) fd.append('assinatura_cliente', ass, 'assinatura.png')
          }
          await client.post(`${base}/concluir/`, fd)
        }
        if (acao.blobChave) await blobStore.remover(acao.blobChave)
        this.acoesPendentes = this.acoesPendentes.filter((a) => a !== acao)
        this._persistir()
      } catch (e) {
        if (e.response) {
          acao.erroSync = e.response.data?.detail || `Erro ${e.response.status}`
          this._persistir()
        } else {
          throw e
        }
      }
    },

    descartarComErro() {
      this.locais = this.locais.filter((o) => !o.erroSync)
      this.acoesPendentes = this.acoesPendentes.filter((a) => !a.erroSync)
      this._persistir()
    },
  },
})
