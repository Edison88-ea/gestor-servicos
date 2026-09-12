import { beforeEach, describe, expect, it } from 'vitest'
import { carregarFila, salvarFila } from './filaStorage'

describe('carregarFila / salvarFila', () => {
  it('retorna o valor padrão quando não há nada salvo', async () => {
    const valor = await carregarFila('chave-vazia-' + Math.random(), [])
    expect(valor).toEqual([])
  })

  it('salva e recupera o mesmo valor', async () => {
    const chave = 'chave-teste-' + Math.random()
    await salvarFila(chave, [{ id: 1 }, { id: 2 }])
    const valor = await carregarFila(chave)
    expect(valor).toEqual([{ id: 1 }, { id: 2 }])
  })

  it('migra automaticamente um valor antigo do localStorage, uma vez só', async () => {
    const chave = 'chave-migracao-' + Math.random()
    localStorage.setItem(chave, JSON.stringify([{ id: 'antigo' }]))

    const valor = await carregarFila(chave)
    expect(valor).toEqual([{ id: 'antigo' }])
    // migrado: não fica mais no localStorage
    expect(localStorage.getItem(chave)).toBeNull()

    // uma segunda leitura não depende mais do localStorage
    const segunda = await carregarFila(chave)
    expect(segunda).toEqual([{ id: 'antigo' }])
  })

  it('localStorage com JSON inválido não quebra — usa o valor padrão', async () => {
    const chave = 'chave-invalida-' + Math.random()
    localStorage.setItem(chave, '{ isso não é json')
    const valor = await carregarFila(chave, [])
    expect(valor).toEqual([])
  })
})
