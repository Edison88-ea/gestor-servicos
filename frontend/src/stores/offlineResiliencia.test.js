// Falhas do IndexedDB (bloqueado por outra aba, quota estourada, transação
// abortada) não podem virar perda de fila nem exceção subindo pelo app. Aqui o
// `idb` é mockado para falhar sob comando — o resto (filaStorage e as stores) é
// o código de verdade.
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

afterEach(() => {
  // Restaura o relógio real mesmo se o teste falhar no meio — senão o
  // `vi.useFakeTimers()`/`vi.setSystemTime()` do teste do "ponto" vazaria
  // (tempo congelado) para os testes seguintes no mesmo arquivo.
  vi.useRealTimers()
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

// Cenário do incidente, na forma que o próprio conserto anterior abriu: como
// `iniciar()` passou a ser retryável e o app nunca bloqueia o técnico enquanto
// ela não passa, o que ele criou na janela tem de sobreviver ao `iniciar()` que
// enfim dá certo — o disco, nessa hora, é a cópia ATRASADA.
describe('iniciar() que dá certo depois de falhar não apaga o que está em memória', () => {
  it('osOffline: OS e ação criadas na janela sobrevivem ao retry', async () => {
    // 1) leitura falha (outra aba segurando a versão antiga do banco)
    filaStore.obter.mockRejectedValue(new Error('IndexedDB bloqueado'))
    // a gravação também não passa — é a mesma condição que derrubou a leitura
    filaStore.definir.mockRejectedValue(new Error('IndexedDB bloqueado'))

    const store = useOsOfflineStore()
    await store.iniciar()
    expect(store.iniciado).toBe(false)

    // 2) o técnico, sem saber de nada, cria uma OS offline e uma ação
    const criada = await store.criarLocal({ cliente: 5, tipo_servico: 'A', descricao: 'na janela' })
    await store.enfileirarAcao(42, 'iniciar')
    expect(store.locais).toHaveLength(1)

    // 3) a outra aba recarregou: a leitura passa, mas devolve o que estava
    //    durável ANTES — sem a OS nem a ação do passo 2
    filaStore.definir.mockResolvedValue(undefined)
    filaStore.obter.mockImplementation((chave) =>
      Promise.resolve(
        chave === 'os_locais'
          ? [{ id: 'tmp_do_disco', cliente: 9 }]
          : [{ osId: 7, tipo: 'concluir', criadoEm: '2026-09-11T08:00:00.000Z' }],
      ),
    )
    await store.iniciar()

    // 4) união: o disco entra e o que foi criado na janela continua ali
    expect(store.iniciado).toBe(true)
    expect(store.locais.map((o) => o.id)).toEqual([criada.id, 'tmp_do_disco'])
    expect(store.acoesPendentes).toHaveLength(2)
    expect(store.acoesPendentes.map((a) => a.osId)).toEqual([7, 42])
    // e a união virou durável agora que o IndexedDB voltou
    const gravacoes = filaStore.definir.mock.calls.filter(([chave]) => chave === 'os_locais')
    expect(gravacoes.at(-1)[1].map((o) => o.id)).toEqual([criada.id, 'tmp_do_disco'])
  })

  it('osOffline: um iniciar() normal (memória vazia) continua carregando só o disco', async () => {
    filaStore.obter.mockImplementation((chave) =>
      Promise.resolve(chave === 'os_locais' ? [{ id: 'tmp_a' }] : []),
    )
    const store = useOsOfflineStore()
    await store.iniciar()

    expect(store.iniciado).toBe(true)
    expect(store.locais).toEqual([{ id: 'tmp_a' }])
    // nada a mesclar: não grava de volta sem necessidade
    expect(filaStore.definir).not.toHaveBeenCalled()
  })

  it('osOffline: item presente nos dois lados não duplica e mantém a versão em memória', async () => {
    filaStore.obter.mockRejectedValue(new Error('IndexedDB bloqueado'))
    const store = useOsOfflineStore()
    await store.iniciar()
    const criada = await store.criarLocal({ cliente: 5, tipo_servico: 'A', descricao: 'x' })
    criada.erroSync = 'Falha de conexão ao enviar — tentando de novo automaticamente'

    // desta vez a gravação do passo anterior CHEGOU ao disco, mas numa versão
    // anterior à mutação in-place (sem o erroSync)
    filaStore.obter.mockImplementation((chave) =>
      Promise.resolve(chave === 'os_locais' ? [{ id: criada.id, cliente: 5, erroSync: '' }] : []),
    )
    await store.iniciar()

    expect(store.locais).toHaveLength(1)
    expect(store.locais[0].erroSync).toMatch(/Falha de conexão/)
  })

  it('ponto: batida feita na janela não desaparece da fila nem de registrosHoje', async () => {
    // relógio fixo: `registrosHoje` compara a data LOCAL com o ISO (UTC) da
    // batida, então um horário de borda deixaria o teste dependente do fuso.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-12T12:00:00Z'))
    filaStore.obter.mockRejectedValue(new Error('IndexedDB bloqueado'))
    filaStore.definir.mockRejectedValue(new Error('IndexedDB bloqueado'))
    client.post.mockRejectedValue(new Error('Network Error'))

    const store = usePontoStore()
    await store.iniciar()
    expect(store.iniciado).toBe(false)

    // técnico bate o ponto: vai para a fila offline (só em memória)
    expect(await store.registrarPonto('ENTRADA')).toBe('na_fila')
    const daJanela = store.filaOffline[0].registrado_em
    expect(store.registrosHoje).toHaveLength(1)

    // leitura volta, devolvendo o disco de antes da batida
    filaStore.definir.mockResolvedValue(undefined)
    filaStore.obter.mockImplementation((chave) =>
      Promise.resolve(
        chave === 'ponto_fila_offline'
          ? [{ tipo: 'SAIDA', registrado_em: '2026-09-11T22:00:00.000Z' }]
          : [],
      ),
    )
    await store.iniciar()

    expect(store.iniciado).toBe(true)
    // ordem determinística: disco primeiro (sem colisão de id), a batida da
    // janela entra depois por não estar no disco (mesmo `mesclarFila` das
    // outras stores, com `novosPrimeiro` padrão)
    expect(store.filaOffline.map((r) => r.registrado_em)).toEqual([
      '2026-09-11T22:00:00.000Z',
      daJanela,
    ])
    // a batida de hoje continua visível na tela do técnico — e é a ÚNICA de
    // hoje (a do disco é de ontem, não deve aparecer em "Registros de hoje")
    expect(store.registrosHoje.map((r) => r.registrado_em)).toEqual([daJanela])
  })

  it('clientes: cliente cadastrado na janela continua em pendentes (e sobe depois)', async () => {
    filaStore.obter.mockRejectedValue(new Error('IndexedDB bloqueado'))
    filaStore.definir.mockRejectedValue(new Error('IndexedDB bloqueado'))
    client.post.mockRejectedValue(new Error('Network Error')) // sem rede: cai no offline

    const store = useClientesStore()
    await store.iniciar()
    expect(store.iniciado).toBe(false)

    const local = await store.criar({ nome: 'Criado na janela' })
    expect(store.pendentes.map((c) => c.id)).toEqual([local.id])

    filaStore.definir.mockResolvedValue(undefined)
    filaStore.obter.mockResolvedValue([{ id: 'tmp_cli_do_disco', _local: true, nome: 'Do disco' }])
    await store.iniciar()

    expect(store.iniciado).toBe(true)
    expect(store.pendentes.map((c) => c.id)).toEqual(['tmp_cli_do_disco', local.id])
    // e o cliente da janela de fato sobe no ciclo seguinte
    client.post.mockResolvedValue({ data: { id: 123, nome: 'Criado na janela' } })
    await store.sincronizar()
    expect(client.post).toHaveBeenCalledWith('/clientes/', expect.objectContaining({ nome: 'Criado na janela' }))
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
