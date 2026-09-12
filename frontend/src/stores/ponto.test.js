import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn() },
}))

import client from '../api/client'
import { usePontoStore } from './ponto'
import { filaStore } from '../utils/idb'

beforeEach(async () => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  // fake-indexeddb persiste entre testes do mesmo arquivo — sem isto, uma
  // batida deixada por um teste anterior vaza para o próximo via iniciar().
  await filaStore.remover('ponto_fila_offline')
  await filaStore.remover('ponto_rejeitados')
})

describe('ponto — durabilidade da fila', () => {
  it('iniciar() carrega fila e rejeitados vazios quando não há nada salvo', async () => {
    const store = usePontoStore()
    await store.iniciar()
    expect(store.filaOffline).toEqual([])
    expect(store.rejeitados).toEqual([])
  })

  it('uma batida enfileirada por falta de rede persiste entre instâncias da store', async () => {
    client.post.mockRejectedValueOnce(new Error('Network Error'))

    const store1 = usePontoStore()
    await store1.iniciar()
    const resultado = await store1.registrarPonto('ENTRADA')
    expect(resultado).toBe('na_fila')
    expect(store1.filaOffline).toHaveLength(1)

    setActivePinia(createPinia())
    const store2 = usePontoStore()
    await store2.iniciar()
    expect(store2.filaOffline).toHaveLength(1)
  })

  it('falha de rede na sincronização mostra mensagem no item, sem descartar', async () => {
    client.post.mockRejectedValueOnce(new Error('Network Error'))
    const store = usePontoStore()
    await store.iniciar()
    await store1_enfileirarDireto(store)

    await store.sincronizarFila()

    expect(store.filaOffline).toHaveLength(1)
    expect(store.filaOffline[0].erroSync).toMatch(/tentando de novo/i)
  })
})

// helper local: enfileira uma batida sem passar pelo registrarPonto (que já
// faria uma chamada de rede própria)
async function store1_enfileirarDireto(store) {
  store.filaOffline.push({
    tipo: 'ENTRADA',
    registrado_em: new Date().toISOString(),
    origem_offline: true,
  })
  await store._persistirFila()
}
