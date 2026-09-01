<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOrdensServicoStore } from '../stores/ordensServico'
import { useNovaOsRascunhoStore } from '../stores/novaOsRascunho'
import { useAuthStore } from '../stores/auth'
import ModalNovaTarefa from '../components/ModalNovaTarefa.vue'

const store = useOrdensServicoStore()
const rascunho = useNovaOsRascunhoStore()
const auth = useAuthStore()

// Técnico só vê OS dele — mostrar o nome seria repetição. Encarregado/gestor
// veem OS da equipe, então o responsável importa.
const mostraTecnico = () => auth.user?.papel !== 'TECNICO'
const router = useRouter()

const modalAberto = ref(false)

onMounted(() => {
  store.carregar()
})

function abrirModal() {
  rascunho.limpar()
  modalAberto.value = true
}

function naoEstouNoLocal() {
  modalAberto.value = false
  router.push('/ordens-servico/nova')
}

function estouNoLocal() {
  modalAberto.value = false
  if (!navigator.geolocation) {
    router.push('/ordens-servico/nova')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (posicao) => {
      rascunho.definirLocal({
        latitude: posicao.coords.latitude,
        longitude: posicao.coords.longitude,
      })
      router.push('/ordens-servico/nova')
    },
    () => {
      // sem permissão/erro de GPS: segue sem localização em vez de travar o fluxo
      router.push('/ordens-servico/nova')
    },
    { enableHighAccuracy: true, timeout: 8000 }
  )
}
</script>

<template>
  <div class="top-bar">
    <strong>Ordens de Serviço</strong>
    <button type="button" style="border: none; background: none; color: var(--accent); font-weight: 600" @click="abrirModal">
      + Nova OS
    </button>
  </div>

  <div class="content">
    <p v-if="store.carregando && !store.listaCompleta.length">Carregando...</p>
    <p v-else-if="store.listaCompleta.length === 0">Nenhuma ordem de serviço atribuída.</p>

    <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 10px">
      <li v-for="os in store.listaCompleta" :key="os.id">
        <RouterLink :to="`/ordens-servico/${os.id}`" style="text-decoration: none; color: inherit">
          <div class="card">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px">
              <strong>{{ os.numero || 'OS (não enviada)' }}</strong>
              <span class="badge" :class="`badge-${os.status.toLowerCase()}`">{{ os.status }}</span>
            </div>
            <div>{{ os.cliente_nome }}</div>
            <div style="color: var(--text-muted); font-size: 14px">{{ os.tipo_servico }}</div>
            <div
              v-if="mostraTecnico() && os.tecnico_nome"
              style="color: var(--accent); font-size: 13px; margin-top: 2px"
            >
              👷 {{ os.tecnico_nome }}
            </div>
            <div v-if="os.offline" style="color: var(--warning); font-size: 13px; margin-top: 4px">
              ⚠ Criada offline — será enviada quando houver sinal<template v-if="os.erroSync"> · {{ os.erroSync }}</template>
            </div>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>

  <ModalNovaTarefa
    v-if="modalAberto"
    @fechar="modalAberto = false"
    @estou-no-local="estouNoLocal"
    @nao-estou-no-local="naoEstouNoLocal"
  />
</template>
