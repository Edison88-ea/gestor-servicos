import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import client from '../api/client'
import { filaStore } from '../utils/idb'
import { useOsOfflineStore } from './osOffline'

// navigator.onLine é getter-only em jsdom — Object.defineProperty é a forma
// confiável de sobrescrever em teste (atribuição direta pode ser ignorada
// em silêncio dependendo da versão do jsdom).
function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(async () => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  definirOnline(true)
  // O IndexedDB fake (setup.js) não é recriado por teste como o Pinia é —
  // sem isso, o item com erroSync deixado por um teste vaza para o próximo.
  await filaStore.remover('os_locais')
  await filaStore.remover('os_acoes_pendentes')
})

describe('osOffline — durabilidade', () => {
  it('iniciar() carrega o estado vazio quando não há nada salvo', async () => {
    const store = useOsOfflineStore()
    await store.iniciar()
    expect(store.locais).toEqual([])
    expect(store.acoesPendentes).toEqual([])
  })

  it('criarLocal + sincronizar com sucesso remove a OS da fila local', async () => {
    client.post.mockResolvedValueOnce({ data: { id: 42 } }) // criação

    const store = useOsOfflineStore()
    await store.iniciar()
    const os = await store.criarLocal({ cliente: 5, tipo_servico: 'Teste', descricao: 'x' })
    expect(store.locais).toHaveLength(1)

    await store.sincronizar()
    expect(store.locais).toHaveLength(0)
    expect(client.post).toHaveBeenCalledWith('/ordens-servico/', expect.objectContaining({ cliente: 5 }))
  })

  it('falha sem resposta HTTP mantém a OS na fila, com mensagem, e não trava as outras', async () => {
    const semResposta = new Error('Network Error') // sem e.response, como um timeout/conexão derrubada
    client.post
      .mockRejectedValueOnce(semResposta) // 1ª OS falha ao criar
      .mockResolvedValueOnce({ data: { id: 99 } }) // 2ª OS cria com sucesso

    const store = useOsOfflineStore()
    await store.iniciar()
    await store.criarLocal({ cliente: 1, tipo_servico: 'A', descricao: 'a' })
    await store.criarLocal({ cliente: 2, tipo_servico: 'B', descricao: 'b' })

    await store.sincronizar()

    expect(store.locais).toHaveLength(1) // só a que falhou continua
    expect(store.locais[0].erroSync).toMatch(/Falha de conexão/)
    expect(store.temErro).toBe(true)
  })

  it('persiste no IndexedDB entre instâncias da store (sobrevive a um "reload")', async () => {
    const store1 = useOsOfflineStore()
    await store1.iniciar()
    await store1.criarLocal({ cliente: 1, tipo_servico: 'A', descricao: 'a' })

    // simula reabrir o app: nova instância de Pinia, nova store
    setActivePinia(createPinia())
    const store2 = useOsOfflineStore()
    await store2.iniciar()
    expect(store2.locais).toHaveLength(1)
  })
})
