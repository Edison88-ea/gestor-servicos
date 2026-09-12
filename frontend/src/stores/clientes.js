import { defineStore } from 'pinia'
import client from '../api/client'
import { useOsOfflineStore } from './osOffline'
import { carregarFila, mesclarFila, salvarFila } from '../utils/filaStorage'

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
    pendentes: [], // clientes cadastrados sem sinal, aguardando envio
    carregando: false,
    sincronizando: false,
    iniciado: false,
  }),
  actions: {
    // Só marca `iniciado` depois de a fila estar de fato em memória: se a
    // leitura do IndexedDB falhar, a store continua não-iniciada (o próximo
    // gatilho de sincronização tenta de novo) em vez de achar que a fila está
    // vazia e sobrescrever no disco, com `[]`, clientes que nunca subiram.
    // Nunca lança — quem chama faz fire-and-forget.
    //
    // O que entra em `pendentes` é a UNIÃO do disco com o que já está em
    // memória: esta ação é retryável e, enquanto ela não passa, o técnico
    // continua podendo cadastrar cliente sem sinal (o app não bloqueia). Um
    // cliente criado nessa janela pode não ter chegado ao disco — atribuir o
    // disco direto o tirava de `pendentes` e ele nunca mais era enviado (ficava
    // só no cache de busca `todos`, parecendo cadastrado). Ver `mesclarFila`.
    async iniciar() {
      if (this.iniciado) return
      try {
        // (uma chave só aqui — os outros dados da store são cache de leitura,
        // não fila; por isso não há Promise.all como nas outras duas stores)
        const pendentes = await carregarFila(PENDENTES_KEY)
        const haviaEmMemoria = this.pendentes.length > 0
        this.pendentes = mesclarFila(pendentes, this.pendentes, (c) => c.id)
        // um cliente pendente carregado agora também precisa aparecer na busca
        this.todos = comPendentes(this.todos, this.pendentes)
        this.iniciado = true
        // leitura voltou a funcionar: torna a união durável
        if (haviaEmMemoria) await this._persistir()
      } catch (e) {
        console.warn('[clientes] falha ao carregar a fila de pendentes; tentando de novo no próximo ciclo', e)
      }
    },

    async _persistir() {
      salvar(KEY, this.todos) // cache de leitura: continua síncrono em localStorage
      await salvarFila(PENDENTES_KEY, this.pendentes)
    },

    async _inserirLocal(c) {
      this.todos = [c, ...this.todos.filter((x) => x.id !== c.id)]
      this.resultados = [c, ...this.resultados.filter((x) => x.id !== c.id)]
      await this._persistir()
    },

    // Substitui um cliente (por id) na memória e no cache — usado ao trocar o
    // id temporário pelo real depois da sincronização.
    async _substituir(idAntigo, novo) {
      const troca = (lista) => lista.map((c) => (c.id === idAntigo ? novo : c))
      this.todos = troca(this.todos)
      this.resultados = troca(this.resultados)
      await this._persistir()
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
          await this._inserirLocal(data)
          return data
        } catch (e) {
          if (e.response) throw e // 4xx: erro de validação de verdade
          // sem rede: continua para o caminho offline
        }
      }
      const local = { id: novoTmpId(), _local: true, ...payload }
      this.pendentes.push(local)
      await this._inserirLocal(local)
      return local
    },

    async atualizar(id, payload) {
      // Cliente ainda não sincronizado: edita só localmente.
      if (String(id).startsWith('tmp_')) {
        const p = this.pendentes.find((c) => c.id === id)
        if (p) Object.assign(p, payload)
        const atualizado = { ...(p || { id, _local: true }), ...payload }
        await this._substituir(id, atualizado)
        return atualizado
      }
      if (!navigator.onLine) {
        const e = new Error('offline')
        e.offline = true
        throw e
      }
      const { data } = await client.patch(`/clientes/${id}/`, payload)
      await this._substituir(id, data)
      return data
    },

    async sincronizar() {
      if (this.sincronizando || !navigator.onLine || !this.pendentes.length) return
      this.sincronizando = true
      try {
        const osOffline = useOsOfflineStore()
        const restantes = []
        // Percorre todos os pendentes mesmo se algum falhar: um cliente travado
        // não pode fazer os outros (e as OS que dependem deles) ficarem presos
        // sem nunca serem tentados de novo.
        for (const local of this.pendentes) {
          let criado = null
          // O try/catch envolve SÓ a chamada de rede. Antes ele cobria também
          // a escrita local que vem depois: se o POST passava e a gravação
          // local falhava, a falha era diagnosticada como "falha de conexão" e
          // o cliente voltava para a fila — ou seja, era criado de novo no
          // servidor no ciclo seguinte (duplicata), e o `trocarClienteTmp`
          // nunca rodava (a OS ficava presa no id temporário para sempre).
          try {
            const { id, _local, erroSync, ...payload } = local
            const { data } = await client.post('/clientes/', payload)
            criado = data
          } catch (e) {
            local.erroSync = e.response
              ? e.response.data?.detail || `Erro ${e.response.status}`
              : 'Falha de conexão ao enviar — tentando de novo automaticamente'
            restantes.push(local)
            continue
          }
          // POST aceito: o cliente existe no servidor. Daqui pra frente ele
          // nunca volta para a fila. As escritas locais abaixo são contidas
          // (filaStorage não lança), mas se alguma falhasse mesmo assim, o
          // certo é perder a atualização local — não reenviar o cadastro.
          // A troca do id na OS vem primeiro de propósito: se ela não
          // acontecer, a OS fica adiada para sempre (o envio é bloqueado
          // enquanto o cliente for `tmp_`); já falhar no _substituir custa só
          // um item desatualizado no cache de busca.
          try {
            // qualquer OS criada offline que aponta para este cliente tmp
            await osOffline.trocarClienteTmp(local.id, criado.id)
            await this._substituir(local.id, criado)
          } catch (e) {
            console.warn('[clientes] cliente enviado, mas a atualização local falhou', e)
          }
        }
        this.pendentes = restantes
        await this._persistir()
      } finally {
        // Em `finally`: uma exceção no meio do laço deixaria a trava presa em
        // true e a sincronização de clientes morta pelo resto da sessão.
        this.sincronizando = false
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
        this.todos = comPendentes(todos, this.pendentes)
        salvar(KEY, this.todos)
      } catch {
        // sem rede: mantém o cache atual
      }
    },
  },
})
