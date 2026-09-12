import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { useSincronizacaoStore } from './sincronizacao'
import { useOsOfflineStore } from './osOffline'
import { useClientesStore } from './clientes'
import { usePontoStore } from './ponto'
import { useAuthStore } from './auth'
import { filaStore } from '../utils/idb'

function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(async () => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  definirOnline(true)
  for (const chave of [
    'os_locais',
    'os_acoes_pendentes',
    'clientes_pendentes',
    'ponto_fila_offline',
    'ponto_rejeitados',
  ]) {
    await filaStore.remover(chave)
  }
})

describe('status agregado das três filas', () => {
  it('conta pendentes dos três domínios (antes o banner ignorava clientes)', async () => {
    const sinc = useSincronizacaoStore()
    expect(sinc.pendentes).toBe(0)

    useClientesStore().pendentes = [{ id: 'tmp_cli_1', nome: 'Um' }]
    expect(sinc.pendentes).toBe(1)
    expect(sinc.totalItens).toBe(1)

    useOsOfflineStore().locais = [{ id: 'tmp_1' }]
    usePontoStore().filaOffline = [{ tipo: 'ENTRADA', registrado_em: 'x' }]
    expect(sinc.pendentes).toBe(3)
  })

  it('temErro acende para erro em cliente e em batida de ponto, não só em OS', () => {
    const sinc = useSincronizacaoStore()
    expect(sinc.temErro).toBe(false)

    useClientesStore().pendentes = [{ id: 'tmp_cli_1', nome: 'Um', erroSync: 'Erro 400' }]
    expect(sinc.temErro).toBe(true)

    useClientesStore().pendentes = []
    usePontoStore().filaOffline = [{ tipo: 'ENTRADA', registrado_em: 'x', erroSync: 'falhou' }]
    expect(sinc.temErro).toBe(true)
  })

  it('batida recusada não conta como "aguardando envio", mas pede atenção e aparece no total', () => {
    const sinc = useSincronizacaoStore()
    usePontoStore().rejeitados = [{ tipo: 'SAIDA', registrado_em: 'x', motivo: 'sequência inválida' }]

    expect(sinc.pendentes).toBe(0)
    expect(sinc.rejeitados).toBe(1)
    expect(sinc.totalItens).toBe(1)
    expect(sinc.temErro).toBe(true)
  })
})

describe('sincronizarTudo', () => {
  it('não roda sem autenticação nem sem rede', async () => {
    const sinc = useSincronizacaoStore()
    const osOffline = useOsOfflineStore()
    const espiao = vi.spyOn(osOffline, 'sincronizar')

    await sinc.sincronizarTudo() // sem token
    expect(espiao).not.toHaveBeenCalled()

    useAuthStore().accessToken = 'token'
    definirOnline(false)
    await sinc.sincronizarTudo()
    expect(espiao).not.toHaveBeenCalled()
  })

  it('mantém a ordem clientes → OS e inicia as stores antes de sincronizar', async () => {
    useAuthStore().accessToken = 'token'
    const sinc = useSincronizacaoStore()
    const clientes = useClientesStore()
    const osOffline = useOsOfflineStore()
    const ponto = usePontoStore()

    const ordem = []
    vi.spyOn(clientes, 'sincronizar').mockImplementation(async () => {
      ordem.push('clientes')
    })
    vi.spyOn(osOffline, 'sincronizar').mockImplementation(async () => {
      ordem.push('os')
    })
    vi.spyOn(ponto, 'sincronizarFila').mockImplementation(async () => {
      ordem.push('ponto')
    })

    await sinc.sincronizarTudo()

    expect(ordem).toEqual(['ponto', 'clientes', 'os'])
    expect(clientes.iniciado).toBe(true)
    expect(osOffline.iniciado).toBe(true)
    expect(ponto.iniciado).toBe(true)
    expect(sinc.sincronizando).toBe(false)
  })

  it('dois gatilhos ao mesmo tempo rodam o ciclo uma vez só', async () => {
    useAuthStore().accessToken = 'token'
    const sinc = useSincronizacaoStore()
    const clientes = useClientesStore()
    const espiao = vi.spyOn(clientes, 'sincronizar').mockResolvedValue(undefined)
    vi.spyOn(useOsOfflineStore(), 'sincronizar').mockResolvedValue(undefined)
    vi.spyOn(usePontoStore(), 'sincronizarFila').mockResolvedValue(undefined)

    await Promise.all([sinc.sincronizarTudo(), sinc.sincronizarTudo()])

    expect(espiao).toHaveBeenCalledTimes(1)
    expect(sinc.sincronizando).toBe(false)
  })

  it('libera a trava mesmo se uma store lançar (gatilhos são fire-and-forget)', async () => {
    useAuthStore().accessToken = 'token'
    const sinc = useSincronizacaoStore()
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(useClientesStore(), 'sincronizar').mockRejectedValue(new Error('inesperado'))

    await expect(sinc.sincronizarTudo()).resolves.toBeUndefined()
    expect(sinc.sincronizando).toBe(false)
  })
})
