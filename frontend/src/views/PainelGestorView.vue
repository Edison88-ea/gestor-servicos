<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import client from '../api/client'
import { useSolicitacoesPontoStore } from '../stores/solicitacoesPonto'
import { formatarMinutos } from '../utils/tempo'

const router = useRouter()
const solicitacoesStore = useSolicitacoesPontoStore()

const carregando = ref(true)
const painel = ref(null)
const processandoSolic = ref(null)

const kpis = computed(() => painel.value?.kpis)
const equipe = computed(() => painel.value?.equipe ?? [])
const pendencias = computed(
  () => painel.value?.pendencias ?? { solicitacoes: [], os_sem_tecnico: [], os_paradas: [] },
)
const produtividade = computed(() => painel.value?.produtividade ?? [])
const obras = computed(() => painel.value?.obras ?? [])
const eGestao = computed(() => !!painel.value?.e_gestao)

const tilesKpi = computed(() => {
  const k = kpis.value
  if (!k) return []
  return [
    { valor: k.os_abertas, rotulo: 'OS em aberto' },
    { valor: k.os_concluidas_semana, rotulo: 'OS concluídas na semana' },
    { valor: k.os_concluidas_mes, rotulo: 'OS concluídas no mês' },
    { valor: k.solicitacoes_pendentes, rotulo: 'Solicitações pendentes', alerta: k.solicitacoes_pendentes > 0 },
    { valor: formatarMinutos(k.horas_extras_mes_min), rotulo: 'Horas extras no mês' },
    { valor: formatarMinutos(k.horas_faltantes_mes_min), rotulo: 'Horas faltantes no mês', alerta: k.horas_faltantes_mes_min > 0 },
    { valor: k.obras_ativas, rotulo: 'Obras ativas' },
  ]
})

async function carregar() {
  carregando.value = true
  try {
    const { data } = await client.get('/painel/')
    painel.value = data
  } finally {
    carregando.value = false
  }
}

async function decidirSolic(id, aprovar) {
  processandoSolic.value = id
  try {
    if (aprovar) await solicitacoesStore.aprovar(id)
    else await solicitacoesStore.rejeitar(id)
    await carregar()
  } catch {
    // deixa o gestor tentar de novo
  } finally {
    processandoSolic.value = null
  }
}

// --- Comprovantes (OS concluídas), com filtro no servidor ---
const hojeData = new Date()
const filtroMes = ref(`${hojeData.getFullYear()}-${String(hojeData.getMonth() + 1).padStart(2, '0')}`)
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

const exportando = ref(false)
async function exportarCsv() {
  exportando.value = true
  try {
    const { data } = await client.get('/ordens-servico/exportar/', {
      params: { concluida_mes: filtroMes.value, tecnico: filtroTecnico.value || undefined },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `os-${filtroMes.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exportando.value = false
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

  <div class="content painel-wide">
    <p v-if="carregando">Carregando...</p>

    <template v-else-if="painel">
      <div v-if="tilesKpi.length" class="painel-kpis">
        <div v-for="t in tilesKpi" :key="t.rotulo" class="kpi" :class="{ 'kpi-alerta': t.alerta }">
          <div class="kpi-valor">{{ t.valor }}</div>
          <div class="kpi-rotulo">{{ t.rotulo }}</div>
        </div>
      </div>

      <div class="painel-colunas">
        <!-- Operação de hoje -->
        <section>
          <h2>Operação de hoje</h2>
          <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
            <li v-for="m in equipe" :key="m.id" class="card">
              <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 8px">
                <strong>{{ m.nome }}</strong>
                <span style="font-size: 13px" :style="{ color: m.ponto.hora ? 'var(--text)' : 'var(--text-muted)' }">
                  {{ m.ponto.rotulo }}<template v-if="m.ponto.hora"> · {{ m.ponto.hora }}</template>
                </span>
              </div>
              <div v-if="m.cargo" style="color: var(--text-muted); font-size: 13px">{{ m.cargo }}</div>
              <div
                v-if="m.os_atual"
                style="margin-top: 4px; font-size: 13px; color: var(--accent); cursor: pointer"
                @click="router.push(`/ordens-servico/${m.os_atual.id}`)"
              >
                🔧 {{ m.os_atual.numero }} · {{ m.os_atual.cliente }}<template v-if="m.os_atual.desde"> (desde {{ m.os_atual.desde }})</template>
              </div>
            </li>
            <li v-if="equipe.length === 0" class="card">Ninguém na equipe.</li>
          </ul>
        </section>

        <!-- Pendências -->
        <section>
          <h2>Pendências</h2>

          <template v-if="eGestao && pendencias.solicitacoes.length">
            <div style="color: var(--text-muted); font-size: 13px; margin-bottom: 6px">Solicitações de ponto</div>
            <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px">
              <li v-for="s in pendencias.solicitacoes" :key="s.id" class="card" style="border-left: 3px solid var(--warning)">
                <strong>{{ s.funcionario_nome }}</strong> — {{ s.tipo_display }}
                <div style="color: var(--text-muted); font-size: 13px">{{ s.data_referencia }} · {{ s.descricao }}</div>
                <div style="display: flex; gap: 8px; margin-top: 8px">
                  <button class="btn" style="flex: 1; padding: 6px; font-size: 13px" :disabled="processandoSolic === s.id" @click="decidirSolic(s.id, true)">Aprovar</button>
                  <button class="btn-secondary" style="flex: 1; padding: 6px; font-size: 13px" :disabled="processandoSolic === s.id" @click="decidirSolic(s.id, false)">Rejeitar</button>
                </div>
              </li>
            </ul>
          </template>

          <template v-if="pendencias.os_sem_tecnico.length">
            <div style="color: var(--text-muted); font-size: 13px; margin-bottom: 6px">OS sem técnico</div>
            <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px">
              <li v-for="o in pendencias.os_sem_tecnico" :key="o.id" class="card" style="cursor: pointer" @click="router.push(`/ordens-servico/${o.id}`)">
                <strong>{{ o.numero }}</strong> — {{ o.cliente_nome }}
                <div style="color: var(--danger); font-size: 13px">aberta há {{ o.dias }} dia(s), sem técnico</div>
              </li>
            </ul>
          </template>

          <template v-if="pendencias.os_paradas.length">
            <div style="color: var(--text-muted); font-size: 13px; margin-bottom: 6px">OS paradas</div>
            <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
              <li v-for="o in pendencias.os_paradas" :key="o.id" class="card" style="cursor: pointer" @click="router.push(`/ordens-servico/${o.id}`)">
                <strong>{{ o.numero }}</strong> — {{ o.cliente_nome }} · {{ o.tecnico_nome }}
                <div style="color: var(--danger); font-size: 13px">{{ o.motivo }} há {{ o.dias }} dia(s)</div>
              </li>
            </ul>
          </template>

          <p
            v-if="!pendencias.os_sem_tecnico.length && !pendencias.os_paradas.length && !(eGestao && pendencias.solicitacoes.length)"
            class="card"
            style="color: var(--text-muted)"
          >
            Nada pendente. 🎉
          </p>
        </section>
      </div>

      <h2 style="margin-top: 20px">Ordens de serviço em aberto ({{ painel.os_abertas.length }})</h2>
      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li v-for="os in painel.os_abertas" :key="os.id" class="card" style="cursor: pointer" @click="router.push(`/ordens-servico/${os.id}`)">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
            <strong>{{ os.numero }}</strong>
            <span class="badge" :class="`badge-${os.status.toLowerCase()}`">{{ os.status }}</span>
          </div>
          <div>{{ os.cliente_nome }} — {{ os.tecnico_nome || 'sem técnico' }}</div>
        </li>
        <li v-if="painel.os_abertas.length === 0" class="card">Nenhuma OS em aberto.</li>
      </ul>

      <div class="painel-colunas" style="margin-top: 20px">
        <section>
          <h2>Produtividade no mês</h2>
          <div class="card" style="overflow-x: auto">
            <table class="tabela-simples">
              <thead>
                <tr>
                  <th>Técnico</th>
                  <th class="num">Em aberto</th>
                  <th class="num">Concluídas</th>
                  <th class="num">Paradas</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in produtividade" :key="p.id">
                  <td>{{ p.nome }}</td>
                  <td class="num">{{ p.os_em_aberto }}</td>
                  <td class="num">{{ p.os_concluidas_mes }}</td>
                  <td class="num" :style="{ color: p.os_paradas ? 'var(--danger)' : 'inherit' }">{{ p.os_paradas }}</td>
                </tr>
                <tr v-if="produtividade.length === 0"><td colspan="4" style="color: var(--text-muted)">Sem dados.</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>Obras ativas</h2>
          <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
            <li v-for="o in obras" :key="o.id" class="card" style="cursor: pointer" @click="router.push(`/obras/${o.id}`)">
              <div style="display: flex; justify-content: space-between; gap: 8px">
                <strong>{{ o.nome }}</strong>
                <span style="color: var(--text-muted); font-size: 13px">{{ o.progresso }}%</span>
              </div>
              <div class="barra-progresso" :class="{ atrasada: o.atrasada }">
                <span :style="{ width: o.progresso + '%' }" />
              </div>
              <div style="color: var(--text-muted); font-size: 12px; margin-top: 4px">
                {{ o.realizado }}/{{ o.meta }} pontos · {{ o.etapas }} etapa(s)
                <span v-if="o.termino_previsto">· prev. {{ new Date(o.termino_previsto).toLocaleDateString('pt-BR') }}</span>
                <span v-if="o.atrasada" style="color: var(--danger)"> · atrasada</span>
              </div>
            </li>
            <li v-if="obras.length === 0" class="card">Nenhuma obra ativa.</li>
          </ul>
        </section>
      </div>

      <h2 style="margin-top: 20px">Comprovantes de OS</h2>
      <div class="card" style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap">
        <input v-model="filtroMes" type="month" style="flex: 1; min-width: 130px; padding: 8px; border-radius: 8px; border: 1px solid var(--border)" />
        <select v-model="filtroTecnico" style="flex: 1; min-width: 130px; padding: 8px; border-radius: 8px; border: 1px solid var(--border)">
          <option value="">Todos os técnicos</option>
          <option v-for="m in equipe" :key="m.id" :value="String(m.id)">{{ m.nome }}</option>
        </select>
        <button class="btn-secondary" style="white-space: nowrap; padding: 8px 12px" :disabled="exportando" @click="exportarCsv">
          {{ exportando ? '...' : '⬇ CSV' }}
        </button>
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
        <li v-if="ordensConcluidas.length === 0" class="card">Nenhuma OS concluída neste filtro.</li>
      </ul>
    </template>
  </div>
</template>
