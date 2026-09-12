import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))
// `osOffline` NÃO é mockado aqui de propósito: a troca do id temporário pelo
// id real (trocarClienteTmp) é a única integração de verdade entre as duas
// stores neste fluxo, e é justamente o que o design exige que tenha teste.

import client from '../api/client'
import { useClientesStore } from './clientes'
import { useOsOfflineStore } from './osOffline'
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
  await filaStore.remover('os_locais')
  await filaStore.remover('os_acoes_pendentes')
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

describe('cliente offline + OS offline (integração real com osOffline)', () => {
  it('ao sincronizar o cliente, a OS que apontava pro id tmp passa a apontar pro id real', async () => {
    const clientes = useClientesStore()
    const osOffline = useOsOfflineStore()
    await clientes.iniciar()
    await osOffline.iniciar()

    // 1) cliente criado sem sinal: ganha um id temporário e vai pra fila
    definirOnline(false)
    const cliente = await clientes.criar({ nome: 'Obra do Zé' })
    expect(cliente.id).toMatch(/^tmp_cli_/)
    expect(clientes.pendentes).toHaveLength(1)

    // 2) OS criada sem sinal apontando para esse cliente temporário
    const os = await osOffline.criarLocal({
      cliente: cliente.id,
      cliente_nome: 'Obra do Zé',
      tipo_servico: 'Instalação',
      descricao: 'x',
    })
    expect(osOffline.local(os.id).cliente).toBe(cliente.id)

    // 3) sinal volta e o cliente sobe: o servidor devolve o id real
    definirOnline(true)
    client.post.mockResolvedValueOnce({ data: { id: 321, nome: 'Obra do Zé' } })
    await clientes.sincronizar()

    expect(clientes.pendentes).toEqual([])
    // trocarClienteTmp de verdade (sem mock) atualizou a OS local
    expect(osOffline.local(os.id).cliente).toBe(321)
    // e a troca ficou durável, não só em memória
    const salvas = await filaStore.obter('os_locais')
    expect(salvas[0].cliente).toBe(321)
  })

  it('a OS só é enviada depois que o cliente tmp ganha id real', async () => {
    const clientes = useClientesStore()
    const osOffline = useOsOfflineStore()
    await clientes.iniciar()
    await osOffline.iniciar()

    definirOnline(false)
    const cliente = await clientes.criar({ nome: 'Depois' })
    await osOffline.criarLocal({ cliente: cliente.id, tipo_servico: 'A', descricao: 'a' })
    definirOnline(true)

    // Primeiro ciclo: só o cliente sobe; a OS é adiada (cliente ainda tmp_ no
    // momento em que a OS seria enviada em um app que não respeitasse a ordem).
    client.post.mockResolvedValueOnce({ data: { id: 900, nome: 'Depois' } }) // cliente
    client.post.mockResolvedValueOnce({ data: { id: 1001 } }) // OS
    await clientes.sincronizar()
    await osOffline.sincronizar()

    expect(osOffline.locais).toHaveLength(0)
    expect(client.post).toHaveBeenNthCalledWith(2, '/ordens-servico/', expect.objectContaining({ cliente: 900 }))
  })
})
