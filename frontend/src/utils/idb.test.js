// Este arquivo roda em Node puro, não em jsdom (diferente do padrão do
// projeto). Motivo: o Blob do jsdom não é reconhecido pelo fake-indexeddb —
// grava algo, mas a leitura de volta vem como `{}` em vez do Blob de
// verdade. O Blob nativo do Node funciona corretamente com o
// fake-indexeddb. `filaStore`/`blobStore` não usam nenhuma API exclusiva de
// DOM, então rodar em Node aqui não perde cobertura nenhuma.
// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'
import { blobStore, filaStore } from './idb'

function novoNomeDb() {
  // Cada teste usa um banco isolado (nome único) — evita que a conexão
  // cacheada de um teste anterior interfira no próximo.
  return `teste-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

describe('filaStore', () => {
  it('guarda e lê um valor por chave', async () => {
    await filaStore.definir('minha-chave', [{ a: 1 }])
    const valor = await filaStore.obter('minha-chave')
    expect(valor).toEqual([{ a: 1 }])
  })

  it('retorna undefined para chave inexistente', async () => {
    const valor = await filaStore.obter('nao-existe-' + Math.random())
    expect(valor).toBeUndefined()
  })

  it('remove um valor', async () => {
    await filaStore.definir('pra-remover', [1, 2, 3])
    await filaStore.remover('pra-remover')
    const valor = await filaStore.obter('pra-remover')
    expect(valor).toBeUndefined()
  })
})

describe('abertura do banco que falha', () => {
  it('não desliga o IndexedDB pelo resto da sessão — a chamada seguinte tenta de novo', async () => {
    // `dbPromise` é módulo-escopo e os testes acima já o preencheram com uma
    // conexão boa; recarregar o módulo devolve o estado "nada aberto ainda".
    vi.resetModules()
    const { filaStore: fila } = await import('./idb')

    // Primeira abertura cai no onblocked — o caso real: outra aba segurando a
    // versão antiga do banco (ex.: logo depois de atualizar o PWA).
    const spy = vi.spyOn(indexedDB, 'open').mockImplementationOnce(() => {
      const req = { onupgradeneeded: null, onsuccess: null, onerror: null, onblocked: null }
      setTimeout(() => req.onblocked?.(), 0)
      return req
    })

    await expect(fila.obter('qualquer')).rejects.toThrow(/bloqueado/i)

    // a outra aba fechou: a abertura volta a funcionar sem reload da página
    spy.mockRestore()
    await fila.definir('depois-do-blocked', [{ ok: true }])
    expect(await fila.obter('depois-do-blocked')).toEqual([{ ok: true }])
  })
})

describe('blobStore (não regride com a mudança)', () => {
  it('continua guardando e lendo blobs', async () => {
    const blob = new Blob(['conteudo'], { type: 'text/plain' })
    await blobStore.salvar('blob-teste', blob)
    const lido = await blobStore.ler('blob-teste')
    expect(lido.size).toBe(blob.size)
  })
})
