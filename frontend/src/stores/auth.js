import { defineStore } from 'pinia'
import axios from 'axios'
import client from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },
  actions: {
    async login(username, password) {
      const { data } = await axios.post('/api/auth/token/', { username, password })
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      this.accessToken = data.access

      await this.atualizarPerfil()
    },
    async atualizarPerfil() {
      // Revalida o usuário logado (papel, jornada, equipe...) contra o servidor.
      // Chamado no login e na abertura do app — sem isto, uma mudança de papel
      // feita no admin só valeria no próximo login.
      try {
        const { data: me } = await client.get('/usuarios/me/')
        this.user = me
        localStorage.setItem('user', JSON.stringify(me))
      } catch {
        // sem rede: mantém o perfil que já está em cache
      }
    },
    logout() {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      this.accessToken = null
      this.user = null
    },
  },
})
