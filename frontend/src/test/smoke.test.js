import { describe, expect, it } from 'vitest'

describe('infraestrutura de teste', () => {
  it('roda e enxerga o IndexedDB fake', () => {
    expect(typeof indexedDB).toBe('object')
    expect(typeof indexedDB.open).toBe('function')
  })
})
