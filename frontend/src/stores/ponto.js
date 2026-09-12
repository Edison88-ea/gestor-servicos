import { defineStore } from 'pinia'
import client from '../api/client'
import { dataLocalISO } from '../utils/tempo'
import { arredondarCoord, arredondarMetros } from '../utils/geo'
import { carregarFila, salvarFila } from '../utils/filaStorage'

function ontemISO() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return dataLocalISO(d)
}

const QUEUE_KEY = 'ponto_fila_offline'
const REJEITADOS_KEY = 'ponto_rejeitados'
const RECENTES_KEY = 'ponto_recentes'

function carregar(chave) {
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
    // cota de localStorage estourada: mantém só em memória nesta sessão
  }
}

// Erro de rede puro (sem resposta) ou servidor fora do ar (5xx): a batida NÃO
// pode ser descartada — é registro de ponto. Só um 4xx é recusa de verdade.
function deveManterNaFila(error) {
  const status = error?.response?.status
  return !status || status >= 500
}

export const usePontoStore = defineStore('ponto', {
  state: () => ({
    // Últimos ~2 dias de batidas, em cache (persiste): precisa de ontem+hoje
    // para saber se há jornada que virou a noite, e o técnico precisa ver o
    // que já bateu mesmo sem sinal.
    registrosRecentes: carregar(RECENTES_KEY),
    filaOffline: [],
    // Batidas que o servidor recusou (4xx — sequência inválida, etc.). Ficam
    // visíveis para o funcionário em vez de sumir caladas; ele pode abrir uma
    // solicitação de ajuste a partir daí.
    rejeitados: [],
    sincronizando: false,
    iniciado: false,
  }),
  getters: {
    // Batidas de hoje para a lista "Registros de hoje" — inclui as que ainda
    // estão na fila offline (marcadas _pendente), senão o técnico bate o ponto
    // sem sinal e não vê nada aparecer.
    registrosHoje(state) {
      const hoje = dataLocalISO()
      const doHoje = (r) => (r.registrado_em || '').slice(0, 10) === hoje
      const servidor = state.registrosRecentes.filter(doHoje)
      const fila = state.filaOffline.filter(doHoje).map((r) => ({ ...r, _pendente: true }))
      return [...servidor, ...fila].sort(
        (a, b) => new Date(a.registrado_em) - new Date(b.registrado_em),
      )
    },
  },
  actions: {
    async iniciar() {
      if (this.iniciado) return
      this.iniciado = true
      this.filaOffline = await carregarFila(QUEUE_KEY)
      this.rejeitados = await carregarFila(REJEITADOS_KEY)
    },

    async _persistirFila() {
      await salvarFila(QUEUE_KEY, this.filaOffline)
    },

    async _persistirRejeitados() {
      await salvarFila(REJEITADOS_KEY, this.rejeitados)
    },

    async carregarRegistrosHoje() {
      try {
        const { data } = await client.get('/registros-ponto/', {
          params: { data_inicio: ontemISO(), data_fim: dataLocalISO() },
        })
        this.registrosRecentes = data.results ?? data
        salvar(RECENTES_KEY, this.registrosRecentes)
      } catch (error) {
        if (error.response) throw error
        // sem sinal: mantém o cache que já está no state
      }
    },

    async _enfileirar(registro) {
      const jaTem = this.filaOffline.some(
        (r) => r.tipo === registro.tipo && r.registrado_em === registro.registrado_em,
      )
      if (!jaTem) {
        this.filaOffline.push(registro)
        await this._persistirFila()
      }
    },

    /**
     * Registra uma batida. Retorna 'enviado' se foi aceita pelo servidor na
     * hora, ou 'na_fila' se ficou guardada para sincronizar depois.
     * Lança erro apenas quando o servidor recusa a batida (4xx).
     */
    async registrarPonto(tipo, localizacao = {}) {
      const registro = {
        tipo,
        registrado_em: new Date().toISOString(),
        latitude: arredondarCoord(localizacao.latitude),
        longitude: arredondarCoord(localizacao.longitude),
        precisao_metros: arredondarMetros(localizacao.precisao),
        endereco: localizacao.endereco ?? '',
        justificativa: localizacao.justificativa ?? '',
      }

      try {
        await client.post('/registros-ponto/', { ...registro, origem_offline: false })
        await this.carregarRegistrosHoje()
        return 'enviado'
      } catch (error) {
        if (deveManterNaFila(error)) {
          await this._enfileirar({ ...registro, origem_offline: true })
          return 'na_fila'
        }
        throw error
      }
    },

    async sincronizarFila() {
      if (this.sincronizando || this.filaOffline.length === 0) return
      this.sincronizando = true

      // Envia em ordem cronológica (a fila pode ter batidas fora de ordem se
      // alguma foi reenfileirada depois de uma falha).
      const pendentes = [...this.filaOffline].sort(
        (a, b) => new Date(a.registrado_em) - new Date(b.registrado_em),
      )

      const restantes = []
      let servidorIndisponivel = false

      for (const registro of pendentes) {
        if (servidorIndisponivel) {
          restantes.push(registro)
          continue
        }
        try {
          await client.post('/registros-ponto/', registro)
        } catch (error) {
          if (deveManterNaFila(error)) {
            // Rede caiu de novo ou backend indisponível: mantém esta e todas as
            // seguintes, tenta tudo de novo na próxima. NUNCA descarta aqui.
            restantes.push({
              ...registro,
              erroSync: error.response
                ? `Erro ${error.response.status} — tentando de novo automaticamente`
                : 'Falha de conexão ao enviar — tentando de novo automaticamente',
            })
            servidorIndisponivel = true
          } else if (error.response?.data?.duplicado) {
            // Já chegou ao servidor por outro caminho (Background Sync do
            // service worker, uma sincronização anterior que caiu antes de
            // atualizar a fila local). Não é recusa — só descarta.
          } else {
            // 4xx: recusa real. Não some calado — vai para "rejeitados".
            // `tipo` vem como string (validar_sequencia_ponto) ou lista (erro
            // de campo do serializer) dependendo de quem recusou.
            const erroTipo = error.response?.data?.tipo
            const motivo =
              (Array.isArray(erroTipo) ? erroTipo[0] : erroTipo) ||
              error.response?.data?.detail ||
              'Batida recusada pelo servidor.'
            this.rejeitados.push({
              ...registro,
              motivo,
              rejeitado_em: new Date().toISOString(),
            })
            await this._persistirRejeitados()
          }
        }
      }

      this.filaOffline = restantes
      await this._persistirFila()
      this.sincronizando = false

      if (restantes.length === 0) {
        try {
          await this.carregarRegistrosHoje()
        } catch {
          // ficou offline de novo; recarrega numa próxima
        }
      }
    },

    async descartarRejeitado(indice) {
      this.rejeitados.splice(indice, 1)
      await this._persistirRejeitados()
    },

    // Devolve uma batida recusada para a fila (a recusa pode ter sido corrigida
    // — ex.: agora a lógica aceita turno que virou a noite).
    async reenviarRejeitado(indice) {
      const [item] = this.rejeitados.splice(indice, 1)
      if (!item) return
      await this._persistirRejeitados()
      const { motivo, rejeitado_em, ...registro } = item
      await this._enfileirar(registro)
      await this.sincronizarFila()
    },

    async buscarEspelho({ dataInicio, dataFim, funcionario } = {}) {
      const { data } = await client.get('/registros-ponto/espelho/', {
        params: {
          data_inicio: dataInicio,
          data_fim: dataFim,
          funcionario,
        },
      })
      return data
    },

    async buscarIndicadores({ dataInicio, dataFim, agruparPor, funcionario } = {}) {
      const { data } = await client.get('/registros-ponto/indicadores/', {
        params: {
          data_inicio: dataInicio,
          data_fim: dataFim,
          agrupar_por: agruparPor,
          funcionario,
        },
      })
      return data
    },
  },
})
