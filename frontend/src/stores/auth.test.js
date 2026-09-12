import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { filaStore } from '../utils/idb'

vi.mock('axios', async (importOriginal) => {
  const real = await importOriginal()
  return { ...real, default: { ...real.default, post: vi.fn().mockRejectedValue(new Error('sem rede')) } }
})

import { useAuthStore } from './auth'

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('logout não apaga fila offline pendente', () => {
  it('logout() só remove as chaves de sessão, nunca a fila do IndexedDB', async () => {
    await filaStore.definir('os_locais', [{ id: 'tmp_1' }])
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('refresh_token', 'r')
    localStorage.setItem('user', '{}')

    const auth = useAuthStore()
    auth.logout()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()

    const fila = await filaStore.obter('os_locais')
    expect(fila).toEqual([{ id: 'tmp_1' }])
  })
})
