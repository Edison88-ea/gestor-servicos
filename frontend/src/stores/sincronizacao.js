import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { useOsOfflineStore } from './osOffline'
import { useClientesStore } from './clientes'
import { usePontoStore } from './ponto'

/**
 * Orquestrador de sincronização e status agregado das três filas offline.
 *
 * Não é um motor de fila: cada store (`osOffline`, `clientes`, `ponto`)
 * continua dona do conteúdo e da lógica de envio da sua própria fila. Aqui
 * mora só o que precisa ser *um* para o app inteiro:
 *
 * - o gatilho (`sincronizarTudo`) — com a ordem fixa clientes → OS → ponto e
 *   uma trava única contra sobreposição, compartilhada entre o disparo
 *   automático do `App.vue` (online/visibilitychange/intervalo) e o botão
 *   "Tentar agora" da tela Pendências. Antes o botão reimplementava o
 *   disparo: sem await, sem ordem e sem trava — tocá-lo com um cliente e uma
 *   OS pendentes podia não resolver nada (a OS é adiada enquanto o cliente
 *   ainda tem id `tmp_`) e sem nenhuma explicação na tela;
 * - os números de status (`pendentes`, `temErro`, ...) — antes existiam três
 *   fórmulas diferentes (banner, contador do menu, tela Pendências), que não
 *   concordavam entre si: um técnico com só um cliente criado offline não via
 *   banner nenhum, e um cliente ou uma batida travados não acendiam o banner
 *   vermelho.
 */
export const useSincronizacaoStore = defineStore('sincronizacao', {
  state: () => ({
    // Trava do orquestrador, além dos `sincronizando` de cada store: dois
    // gatilhos que disparem juntos não devem rodar o ciclo duas vezes.
    sincronizando: false,
  }),

  getters: {
    // Itens aguardando envio, somando os três domínios.
    pendentes() {
      const osOffline = useOsOfflineStore()
      const clientes = useClientesStore()
      const ponto = usePontoStore()
      return osOffline.pendentes + clientes.pendentes.length + ponto.filaOffline.length
    },

    // Batidas que o servidor recusou (4xx). Não estão "aguardando envio" —
    // não entram em `pendentes` — mas exigem ação do funcionário, então
    // contam como atenção (`temErro`) e aparecem na tela Pendências.
    rejeitados() {
      return usePontoStore().rejeitados.length
    },

    // Tudo que a tela Pendências lista — é o que o contador do menu mostra.
    totalItens() {
      return this.pendentes + this.rejeitados
    },

    // Algo precisa de atenção: qualquer item com mensagem de erro em qualquer
    // uma das três filas, ou uma batida recusada.
    temErro() {
      const osOffline = useOsOfflineStore()
      const clientes = useClientesStore()
      const ponto = usePontoStore()
      return (
        osOffline.temErro ||
        clientes.pendentes.some((c) => c.erroSync) ||
        ponto.filaOffline.some((r) => r.erroSync) ||
        ponto.rejeitados.length > 0
      )
    },

    // Ciclo em andamento (o orquestrador ou qualquer uma das stores).
    sincronizandoAlgo() {
      const osOffline = useOsOfflineStore()
      const clientes = useClientesStore()
      const ponto = usePontoStore()
      return (
        this.sincronizando ||
        osOffline.sincronizando ||
        clientes.sincronizando ||
        ponto.sincronizando
      )
    },
  },

  actions: {
    // Carrega as filas do IndexedDB. Idempotente: `iniciar()` de cada store
    // sai na hora se já estiver iniciada, e nunca lança — se a leitura do
    // IndexedDB falhar, a store fica não-iniciada e esta chamada (feita de
    // novo a cada ciclo de sincronização) é a nova tentativa.
    async iniciarStores() {
      const osOffline = useOsOfflineStore()
      const clientes = useClientesStore()
      const ponto = usePontoStore()
      await Promise.all([osOffline.iniciar(), clientes.iniciar(), ponto.iniciar()])
    },

    async sincronizarTudo() {
      const auth = useAuthStore()
      if (this.sincronizando || !navigator.onLine || !auth.isAuthenticated) return
      this.sincronizando = true
      try {
        await this.iniciarStores()
        const osOffline = useOsOfflineStore()
        const clientes = useClientesStore()
        const ponto = usePontoStore()
        ponto.sincronizarFila()
        // clientes primeiro: uma OS criada offline pode apontar para um cliente
        // criado offline, que precisa ganhar id real antes de a OS subir.
        await clientes.sincronizar()
        await osOffline.sincronizar()
      } catch (e) {
        // Todos os gatilhos são fire-and-forget (intervalo, listener de evento,
        // clique): uma rejeição aqui viraria unhandled rejection e, pior,
        // deixaria a trava presa se não houvesse o finally.
        console.warn('[sincronizacao] ciclo de sincronização falhou', e)
      } finally {
        this.sincronizando = false
      }
    },
  },
})
