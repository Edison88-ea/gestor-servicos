// Falhas do IndexedDB (bloqueado por outra aba, quota estourada, transação
// abortada) não podem virar perda de fila nem exceção subindo pelo app. Aqui o
// `idb` é mockado para falhar sob comando — o resto (filaStorage e as stores) é
// o código de verdade.
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('../utils/idb', () => ({
  filaStore: { obter: vi.fn(), definir: vi.fn(), remover: vi.fn() },
  blobStore: { salvar: vi.fn(), ler: vi.fn(), remover: vi.fn() },
  novaChaveBlob: (prefixo = 'blob') => `${prefixo}_teste`,
  paraBlobPersistente: async (arquivo) => arquivo,
}))

import client from '../api/client'
import { filaStore } from '../utils/idb'
import { useOsOfflineStore } from './osOffline'
import { useClientesStore } from './clientes'
import { usePontoStore } from './ponto'

function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  definirOnline(true)
  // silencia os console.warn esperados destes cenários
  vi.spyOn(console, 'warn').mockImplementation(() => {})
  filaStore.obter.mockResolvedValue(undefined)
  filaStore.definir.mockResolvedValue(undefined)
  filaStore.remover.mockResolvedValue(undefined)
})

describe('iniciar() com carga parcial (uma chave falha)', () => {
  it('osOffline: não marca iniciado nem zera a fila que não carregou', async () => {
    // os_locais carrega; os_acoes_pendentes falha (IndexedDB bloqueado).
    filaStore.obter.mockImplementation((chave) =>
      chave === 'os_locais'
        ? Promise.resolve([{ id: 'tmp_1', cliente: 9 }])
        : Promise.reject(new Error('IndexedDB bloqueado')),
    )

    const store = useOsOfflineStore()
    await store.iniciar()

    // nada foi atribuído ao state: a store fica retryável, não meio-carregada
    expect(store.iniciado).toBe(false)
    expect(store.locais).toEqual([])
    expect(store.acoesPendentes).toEqual([])
    // e nada foi gravado — era isso que apagava a fila do disco
    expect(filaStore.definir).not.toHaveBeenCalled()
  })

  it('osOffline: o gatilho seguinte recarrega quando o IndexedDB volta', async () => {
    filaStore.obter.mockImplementation((chave) =>
      chave === 'os_locais'
        ? Promise.resolve([{ id: 'tmp_1', cliente: 9 }])
        : Promise.reject(new Error('IndexedDB bloqueado')),
    )
    const store = useOsOfflineStore()
    await store.iniciar()
    expect(store.iniciado).toBe(false)

    // outra aba fechou: agora as duas chaves leem normalmente
    filaStore.obter.mockImplementation((chave) =>
      Promise.resolve(chave === 'os_locais' ? [{ id: 'tmp_1', cliente: 9 }] : []),
    )
    await store.iniciar()

    expect(store.iniciado).toBe(true)
    expect(store.locais).toHaveLength(1)
  })

  it('ponto: fila e rejeitados entram em bloco ou nenhum dos dois', async () => {
    filaStore.obter.mockImplementation((chave) =>
      chave === 'ponto_fila_offline'
        ? Promise.resolve([{ tipo: 'ENTRADA', registrado_em: '2026-09-12T10:00:00.000Z' }])
        : Promise.reject(new Error('IndexedDB bloqueado')),
    )

    const store = usePontoStore()
    await store.iniciar()

    expect(store.iniciado).toBe(false)
    expect(store.filaOffline).toEqual([])
    expect(store.rejeitados).toEqual([])
  })

  it('clientes: falha na leitura deixa a store não-iniciada', async () => {
    filaStore.obter.mockRejectedValue(new Error('IndexedDB bloqueado'))

    const store = useClientesStore()
    await store.iniciar()

    expect(store.iniciado).toBe(false)
    expect(store.pendentes).toEqual([])
  })
})

describe('gravação que falha não lança pelo app', () => {
  it('criarLocal e sincronizar seguem funcionando com o IndexedDB recusando escrita', async () => {
    filaStore.definir.mockRejectedValue(new Error('QuotaExceededError'))
    client.post.mockRejectedValue(new Error('Network Error'))

    const store = useOsOfflineStore()
    await store.iniciar()

    // criação local: persiste em memória mesmo sem conseguir gravar
    await expect(store.criarLocal({ cliente: 1, tipo_servico: 'A', descricao: 'a' })).resolves.toBeTruthy()
    expect(store.locais).toHaveLength(1)

    // _enviarOsLocal tem de continuar tratando a própria falha (erroSync) e
    // não lançar — nem por causa da rede, nem por causa do persist.
    await expect(store.sincronizar()).resolves.toBeUndefined()
    expect(store.locais[0].erroSync).toMatch(/Falha de conexão/)
    expect(store.sincronizando).toBe(false)
  })

  it('_enviarAcao não lança quando o persist falha', async () => {
    filaStore.definir.mockRejectedValue(new Error('QuotaExceededError'))
    client.post.mockRejectedValue(new Error('Network Error'))

    const store = useOsOfflineStore()
    await store.iniciar()
    await store.enfileirarAcao(7, 'iniciar')

    await expect(store.sincronizar()).resolves.toBeUndefined()
    expect(store.acoesPendentes).toHaveLength(1)
    expect(store.acoesPendentes[0].erroSync).toMatch(/Falha de conexão/)
  })

  it('clientes: a trava sincronizando é liberada mesmo com o persist falhando', async () => {
    filaStore.definir.mockRejectedValue(new Error('QuotaExceededError'))
    const store = useClientesStore()
    await store.iniciar()
    store.pendentes = [{ id: 'tmp_cli_1', _local: true, nome: 'Um' }]
    client.post.mockResolvedValue({ data: { id: 77, nome: 'Um' } })

    await expect(store.sincronizar()).resolves.toBeUndefined()
    expect(store.sincronizando).toBe(false)
    // POST aceito: o cliente não volta para a fila (senão viraria duplicata)
    expect(store.pendentes).toEqual([])
  })

  it('ponto: a trava sincronizando é liberada mesmo com o persist falhando', async () => {
    filaStore.definir.mockRejectedValue(new Error('QuotaExceededError'))
    const store = usePontoStore()
    await store.iniciar()
    store.filaOffline = [{ tipo: 'ENTRADA', registrado_em: new Date().toISOString() }]
    client.post.mockRejectedValue(new Error('Network Error'))
    client.get.mockRejectedValue(new Error('Network Error'))

    await expect(store.sincronizarFila()).resolves.toBeUndefined()
    expect(store.sincronizando).toBe(false)
    expect(store.filaOffline).toHaveLength(1) // batida nunca é descartada
  })
})
