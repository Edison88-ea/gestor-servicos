import { defineStore } from 'pinia'
import { arredondarCoord } from '../utils/geo'

// Guarda dados temporários entre a escolha "Estou no local" / "Não estou no
// local" (na listagem de OS) e o formulário de criação, já que são telas
// diferentes. Limpo assim que a OS é criada ou o formulário é aberto sem vir
// desse fluxo.
export const useNovaOsRascunhoStore = defineStore('novaOsRascunho', {
  state: () => ({
    latitude: null,
    longitude: null,
  }),
  actions: {
    definirLocal(coords) {
      this.latitude = arredondarCoord(coords.latitude)
      this.longitude = arredondarCoord(coords.longitude)
    },
    limpar() {
      this.latitude = null
      this.longitude = null
    },
  },
})
