<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import client from '../api/client'
import { useSolicitacoesPontoStore } from '../stores/solicitacoesPonto'
import { dataLocalISO } from '../utils/tempo'

const router = useRouter()
const solicitacoesStore = useSolicitacoesPontoStore()

const carregando = ref(true)
const tecnicos = ref([])
const registrosHoje = ref([])
const ordensAbertas = ref([])

// Seção de comprovantes (exportação de OS concluídas), com filtro no servidor.
const hojeData = new Date()
const filtroMes = ref(
  `${hojeData.getFullYear()}-${String(hojeData.getMonth() + 1).padStart(2, '0')}`,
)
const filtroTecnico = ref('')
const ordensConcluidas = ref([])
const carregandoConcluidas = ref(false)

async function carregarConcluidas() {
  if (!filtroMes.value) return
  carregandoConcluidas.value = true
  try {
    const { data } = await client.get('/ordens-servico/', {
      params: {
        status: 'CONCLUIDA',
        concluida_mes: filtroMes.value,
        tecnico: filtroTecnico.value || undefined,
        page_size: 500,
      },
    })
    ordensConcluidas.value = (data.results ?? data).sort(
      (a, b) => new Date(b.data_conclusao) - new Date(a.data_conclusao),
    )
  } finally {
    carregandoConcluidas.value = false
  }
}

watch([filtroMes, filtroTecnico], carregarConcluidas)

const ULTIMO_ROTULO = {
  ENTRADA: 'Em andamento',
  VOLTA_INTERVALO: 'Em andamento',
  SAIDA_INTERVALO: 'Em intervalo',
  SAIDA: 'Jornada concluída',
}

const statusPorTecnico = computed(() => {
  const mapa = {}
  for (const tecnico of tecnicos.value) {
    const registrosDoTecnico = registrosHoje.value
      .filter((r) => r.funcionario === tecnico.id)
      .sort((a, b) => new Date(b.registrado_em) - new Date(a.registrado_em))
    const ultimo = registrosDoTecnico[0]
    mapa[tecnico.id] = ultimo
      ? { rotulo: ULTIMO_ROTULO[ultimo.tipo] || ultimo.tipo, hora: ultimo.registrado_em }
      : { rotulo: 'Não bateu ponto', hora: null }
  }
  return mapa
})

function formatarHora(iso) {
  return iso ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : ''
}

async function carregar() {
  carregando.value = true
  try {
    const hoje = dataLocalISO()
    const [respTecnicos, respRegistros, respOrdens] = await Promise.all([
      client.get('/usuarios/', { params: { papel: 'TECNICO,ENCARREGADO' } }),
      client.get('/registros-ponto/', { params: { data_inicio: hoje, data_fim: hoje, equipe: 1 } }),
      client.get('/ordens-servico/'),
    ])
    tecnicos.value = respTecnicos.data.results ?? respTecnicos.data
    registrosHoje.value = respRegistros.data.results ?? respRegistros.data
    const ordens = respOrdens.data.results ?? respOrdens.data
    ordensAbertas.value = ordens.filter((o) => ['ATRIBUIDA', 'EM_ANDAMENTO'].includes(o.status))
    await solicitacoesStore.carregar('PENDENTE')
  } finally {
    carregando.value = false
  }
}

onMounted(() => {
  carregar()
  carregarConcluidas()
})
</script>

<template>
  <div class="top-bar">
    <strong>Painel</strong>
  </div>

  <div class="content">
    <p v-if="carregando">Carregando...</p>

    <template v-else>
      <div
        v-if="solicitacoesStore.itens.length > 0"
        class="card"
        style="margin-bottom: 16px; cursor: pointer; border-color: var(--warning)"
        @click="router.push('/ponto/solicitacoes')"
      >
        <strong>{{ solicitacoesStore.itens.length }} solicitação(ões) pendente(s)</strong>
        <div style="color: var(--text-muted); font-size: 14px">Toque para revisar</div>
      </div>

      <h2>Equipe hoje</h2>
      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px">
        <li v-for="t in tecnicos" :key="t.id" class="card" style="display: flex; justify-content: space-between; align-items: center">
          <div>
            <strong>{{ t.first_name ? `${t.first_name} ${t.last_name}` : t.username }}</strong>
            <div style="color: var(--text-muted); font-size: 13px">{{ t.cargo }}</div>
          </div>
          <div style="text-align: right">
            <div>{{ statusPorTecnico[t.id]?.rotulo }}</div>
            <div v-if="statusPorTecnico[t.id]?.hora" style="color: var(--text-muted); font-size: 13px">
              {{ formatarHora(statusPorTecnico[t.id].hora) }}
            </div>
          </div>
        </li>
        <li v-if="tecnicos.length === 0" class="card">Ninguém cadastrado.</li>
      </ul>

      <h2>Ordens de serviço em aberto ({{ ordensAbertas.length }})</h2>
      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li v-for="os in ordensAbertas" :key="os.id" class="card" style="cursor: pointer" @click="router.push(`/ordens-servico/${os.id}`)">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
            <strong>{{ os.numero }}</strong>
            <span class="badge" :class="`badge-${os.status.toLowerCase()}`">{{ os.status }}</span>
          </div>
          <div>{{ os.cliente_nome }} — {{ os.tecnico_nome || 'sem técnico' }}</div>
        </li>
        <li v-if="ordensAbertas.length === 0" class="card">Nenhuma OS em aberto.</li>
      </ul>

      <h2 style="margin-top: 20px">Comprovantes de OS</h2>
      <div class="card" style="display: flex; gap: 8px; margin-bottom: 8px">
        <input
          v-model="filtroMes"
          type="month"
          style="flex: 1; padding: 8px; border-radius: 8px; border: 1px solid var(--border)"
        />
        <select
          v-model="filtroTecnico"
          style="flex: 1; padding: 8px; border-radius: 8px; border: 1px solid var(--border)"
        >
          <option value="">Todos os técnicos</option>
          <option v-for="t in tecnicos" :key="t.id" :value="String(t.id)">
            {{ t.first_name ? `${t.first_name} ${t.last_name}` : t.username }}
          </option>
        </select>
      </div>
      <p v-if="carregandoConcluidas" style="color: var(--text-muted)">Carregando...</p>
      <ul v-else style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li
          v-for="os in ordensConcluidas"
          :key="os.id"
          class="card"
          style="cursor: pointer"
          @click="router.push(`/ordens-servico/${os.id}/comprovante`)"
        >
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
            <strong>{{ os.numero }}</strong>
            <span style="color: var(--accent); font-weight: 600; font-size: 14px">Comprovante →</span>
          </div>
          <div>{{ os.cliente_nome }} — {{ os.tecnico_nome || 'sem técnico' }}</div>
          <div style="color: var(--text-muted); font-size: 13px">
            Concluída em {{ new Date(os.data_conclusao).toLocaleDateString('pt-BR') }}
          </div>
        </li>
        <li v-if="ordensConcluidas.length === 0" class="card">
          Nenhuma OS concluída neste filtro.
        </li>
      </ul>
    </template>
  </div>
</template>
