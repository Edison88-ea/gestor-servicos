import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))
vi.mock('./osOffline', () => ({
  useOsOfflineStore: () => ({ trocarClienteTmp: vi.fn() }),
}))

import client from '../api/client'
import { useClientesStore } from './clientes'
import { filaStore } from '../utils/idb'

// navigator.onLine é getter-only em jsdom — Object.defineProperty é a forma
// confiável de sobrescrever em teste (atribuição direta pode ser ignorada
// em silêncio dependendo da versão do jsdom).
function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(async () => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  definirOnline(true)
  // fake-indexeddb persiste entre testes do mesmo arquivo — sem isto, um
  // pendente deixado por um teste anterior vaza para o próximo via iniciar().
  await filaStore.remover('clientes_pendentes')
})

describe('clientes — durabilidade e fila', () => {
  it('iniciar() carrega pendentes vazio quando não há nada salvo', async () => {
    const store = useClientesStore()
    await store.iniciar()
    expect(store.pendentes).toEqual([])
  })

  it('criar offline enfileira e persiste entre instâncias da store', async () => {
    definirOnline(false)

    const store1 = useClientesStore()
    await store1.iniciar()
    await store1.criar({ nome: 'Cliente Teste' })
    expect(store1.pendentes).toHaveLength(1)

    setActivePinia(createPinia())
    const store2 = useClientesStore()
    await store2.iniciar()
    expect(store2.pendentes).toHaveLength(1)
    expect(store2.pendentes[0].nome).toBe('Cliente Teste')
  })

  it('um cliente pendente que falha sem resposta HTTP não trava os outros da fila', async () => {
    definirOnline(true)
    const store = useClientesStore()
    await store.iniciar()

    // dois pendentes já enfileirados (simulando estado offline anterior)
    store.pendentes = [
      { id: 'tmp_cli_1', _local: true, nome: 'Um' },
      { id: 'tmp_cli_2', _local: true, nome: 'Dois' },
    ]

    client.post
      .mockRejectedValueOnce(new Error('Network Error')) // 'Um' falha sem resposta
      .mockResolvedValueOnce({ data: { id: 501, nome: 'Dois' } }) // 'Dois' sincroniza

    await store.sincronizar()

    expect(store.pendentes).toHaveLength(1)
    expect(store.pendentes[0].nome).toBe('Um')
    expect(store.pendentes[0].erroSync).toMatch(/Falha de conexão/)
  })
})
