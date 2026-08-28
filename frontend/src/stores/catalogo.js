import { defineStore } from 'pinia'
import client from '../api/client'

// Catálogo de serviços e materiais já usados, para sugerir no formulário de
// relato. Carrega uma vez por sessão.
export const useCatalogoStore = defineStore('catalogo', {
  state: () => ({
    servicos: [], // [{ descricao }]
    materiais: [], // [{ descricao, unidade_padrao }]
    carregado: false,
  }),
  actions: {
    async carregar() {
      if (this.carregado) return
      try {
        const [s, m] = await Promise.all([
          client.get('/catalogo/servicos/'),
          client.get('/catalogo/materiais/'),
        ])
        this.servicos = s.data
        this.materiais = m.data
        this.carregado = true
      } catch {
        // catálogo é só conveniência; se falhar, o formulário funciona igual
      }
    },
    unidadeDe(descricao) {
      const alvo = (descricao || '').trim().toLowerCase()
      const item = this.materiais.find((m) => m.descricao.toLowerCase() === alvo)
      return item ? item.unidade_padrao : ''
    },
  },
})
