import { beforeEach, describe, expect, it } from 'vitest'
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

describe('blobStore (não regride com a mudança)', () => {
  it('continua guardando e lendo blobs', async () => {
    const blob = new Blob(['conteudo'], { type: 'text/plain' })
    await blobStore.salvar('blob-teste', blob)
    const lido = await blobStore.ler('blob-teste')
    expect(lido.size).toBe(blob.size)
  })
})
