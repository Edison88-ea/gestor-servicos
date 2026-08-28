import { defineStore } from 'pinia'
import client from '../api/client'
import { dataLocalISO } from '../utils/tempo'
import { arredondarCoord, arredondarMetros } from '../utils/geo'

const QUEUE_KEY = 'ponto_fila_offline'

function carregarFila() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
  } catch {
    return []
  }
}

function salvarFila(fila) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(fila))
}

export const usePontoStore = defineStore('ponto', {
  state: () => ({
    registrosHoje: [],
    filaOffline: carregarFila(),
    sincronizando: false,
  }),
  actions: {
    async carregarRegistrosHoje() {
      const hoje = dataLocalISO()
      const { data } = await client.get('/registros-ponto/', {
        params: { data_inicio: hoje, data_fim: hoje },
      })
      this.registrosHoje = data.results ?? data
    },

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
      } catch (error) {
        if (!error.response) {
          // sem rede: guarda na fila local e sincroniza depois
          this.filaOffline.push({ ...registro, origem_offline: true })
          salvarFila(this.filaOffline)
        } else {
          throw error
        }
      }
    },

    async sincronizarFila() {
      if (this.sincronizando || this.filaOffline.length === 0) return
      this.sincronizando = true
      const restantes = []
      for (const registro of this.filaOffline) {
        try {
          await client.post('/registros-ponto/', registro)
        } catch (error) {
          if (!error.response) {
            restantes.push(registro)
          }
          // erros de validação (4xx) são descartados para não travar a fila
        }
      }
      this.filaOffline = restantes
      salvarFila(restantes)
      this.sincronizando = false
      if (restantes.length === 0) {
        await this.carregarRegistrosHoje()
      }
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
