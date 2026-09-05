<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePontoStore } from '../stores/ponto'
import GraficoBarras from '../components/GraficoBarras.vue'
import SeletorFuncionario from '../components/SeletorFuncionario.vue'
import { dataLocalISO, formatarMinutos } from '../utils/tempo'

// 'pessoal' = os próprios indicadores, sem seletor (quem bate ponto).
// 'equipe'  = indicadores de qualquer funcionário, com seletor (gestão).
const props = defineProps({ escopo: { type: String, default: 'pessoal' } })
const ehEquipe = computed(() => props.escopo === 'equipe')

const router = useRouter()
const ponto = usePontoStore()

const hoje = new Date()
const dataInicio = ref(dataLocalISO(new Date(hoje.getFullYear(), hoje.getMonth(), 1)))
const dataFim = ref(dataLocalISO(hoje))
const agruparPor = ref('semana')
const funcionarioSel = ref('')

const carregando = ref(false)
const erro = ref('')
const indicadores = ref(null)

const opcoesAgrupamento = [
  { valor: 'dia', rotulo: 'Dia' },
  { valor: 'semana', rotulo: 'Semana' },
  { valor: 'mes', rotulo: 'Mês' },
]

// Na visão da equipe não há "meus indicadores" pra cair em cima — quem é
// gestão pode nem bater ponto. Sem funcionário escolhido, não busca nada.
const aguardandoFuncionario = computed(() => ehEquipe.value && !funcionarioSel.value)

async function carregar() {
  if (aguardandoFuncionario.value) {
    indicadores.value = null
    return
  }
  carregando.value = true
  erro.value = ''
  try {
    indicadores.value = await ponto.buscarIndicadores({
      dataInicio: dataInicio.value,
      dataFim: dataFim.value,
      agruparPor: agruparPor.value,
      funcionario: ehEquipe.value ? funcionarioSel.value : undefined,
    })
  } catch {
    erro.value = 'Não foi possível carregar os indicadores.'
  } finally {
    carregando.value = false
  }
}

watch([dataInicio, dataFim, agruparPor, funcionarioSel], carregar, { immediate: true })
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>{{ ehEquipe ? 'Indicadores da Equipe' : 'Meus Indicadores' }}</strong>
  </div>

  <div class="content">
    <SeletorFuncionario v-if="ehEquipe" v-model="funcionarioSel" rotulo-vazio="Selecione um funcionário" />

    <p v-if="aguardandoFuncionario" class="card" style="color: var(--text-muted)">
      Escolha um funcionário para ver os indicadores.
    </p>

    <template v-else>
    <div class="card" style="margin-bottom: 16px">
      <h2 style="margin: 0 0 10px">Filtrar</h2>
      <div style="display: flex; gap: 10px">
        <label style="flex: 1">
          De
          <input v-model="dataInicio" type="date" style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px" />
        </label>
        <label style="flex: 1">
          Até
          <input v-model="dataFim" type="date" style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px" />
        </label>
      </div>
    </div>

    <p v-if="carregando">Carregando...</p>
    <p v-else-if="erro" style="color: var(--danger)">{{ erro }}</p>

    <template v-else-if="indicadores">
      <div class="card" style="margin-bottom: 16px">
        <h2 style="margin: 0 0 10px">Horas Extras</h2>
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <button
            v-for="o in opcoesAgrupamento"
            :key="o.valor"
            type="button"
            :class="agruparPor === o.valor ? 'btn' : 'btn-secondary'"
            style="flex: 1; padding: 8px"
            @click="agruparPor = o.valor"
          >
            {{ o.rotulo }}
          </button>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px">
          <span style="color: #0ca30c">⏱</span>
          <span style="font-size: 24px; font-weight: 700">{{ formatarMinutos(indicadores.total_horas_extras_minutos) }}</span>
          <span style="color: var(--text-muted)">Horas Extras no Período</span>
        </div>
        <GraficoBarras
          :dados="indicadores.grupos.map((g) => ({ rotulo: g.rotulo, valorMinutos: g.horas_extras_minutos }))"
          status="good"
        />
      </div>

      <div class="card">
        <h2 style="margin: 0 0 10px">Horas Faltantes</h2>
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <button
            v-for="o in opcoesAgrupamento"
            :key="o.valor"
            type="button"
            :class="agruparPor === o.valor ? 'btn' : 'btn-secondary'"
            style="flex: 1; padding: 8px"
            @click="agruparPor = o.valor"
          >
            {{ o.rotulo }}
          </button>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px">
          <span style="color: #d03b3b">⏱</span>
          <span style="font-size: 24px; font-weight: 700">{{ formatarMinutos(indicadores.total_horas_faltantes_minutos) }}</span>
          <span style="color: var(--text-muted)">Horas Faltantes no Período</span>
        </div>
        <GraficoBarras
          :dados="indicadores.grupos.map((g) => ({ rotulo: g.rotulo, valorMinutos: g.horas_faltantes_minutos }))"
          status="critical"
        />
      </div>
    </template>
    </template>
  </div>
</template>
