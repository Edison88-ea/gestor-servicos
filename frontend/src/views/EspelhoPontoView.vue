<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePontoStore } from '../stores/ponto'
import { useAuthStore } from '../stores/auth'
import { dataLocalISO, formatarMinutos } from '../utils/tempo'

const store = usePontoStore()
const auth = useAuthStore()
const router = useRouter()

function exportar() {
  window.print()
}

const hoje = new Date()
const mesReferencia = ref(new Date(hoje.getFullYear(), hoje.getMonth(), 1))
const espelho = ref(null)
const carregando = ref(false)
const erro = ref('')
const modo = ref('completo') // 'resumido' | 'completo'

const rotuloMes = computed(() =>
  mesReferencia.value.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
)

function formatarHora(iso) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatarData(isoData) {
  return new Date(`${isoData}T00:00:00`).toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
  })
}

function statusDia(dia) {
  if (dia.futuro) return 'futuro'
  if (dia.folga) return 'ok'
  if (dia.registros.length === 0) return 'alerta'
  return dia.saldo_minutos >= 0 ? 'ok' : 'alerta'
}

function paresDeHorarios(registros) {
  const pares = []
  for (let i = 0; i < registros.length; i += 2) {
    const a = registros[i]
    const b = registros[i + 1]
    pares.push(`${formatarHora(a.registrado_em)} - ${b ? formatarHora(b.registrado_em) : 'X'}`)
  }
  return pares.join(' • ')
}

async function carregarMes() {
  carregando.value = true
  erro.value = ''
  const inicio = mesReferencia.value
  const fim = new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0)
  try {
    espelho.value = await store.buscarEspelho({
      dataInicio: dataLocalISO(inicio),
      dataFim: dataLocalISO(fim),
    })
  } catch {
    erro.value = 'Não foi possível carregar o cartão de ponto.'
  } finally {
    carregando.value = false
  }
}

function mudarMes(delta) {
  mesReferencia.value = new Date(
    mesReferencia.value.getFullYear(),
    mesReferencia.value.getMonth() + delta,
    1
  )
}

watch(mesReferencia, carregarMes, { immediate: true })
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Cartão Ponto</strong>
    <button type="button" style="border: none; background: none; color: var(--accent); font-weight: 600" @click="exportar">
      Exportar
    </button>
  </div>

  <div class="content">
    <div class="somente-impressao" style="display: none; margin-bottom: 12px">
      <strong style="font-size: 18px">
        {{ auth.user?.first_name ? `${auth.user.first_name} ${auth.user.last_name}` : auth.user?.username }}
      </strong>
      <div>Cartão Ponto — <span style="text-transform: capitalize">{{ rotuloMes }}</span></div>
    </div>

    <div class="ocultar-impressao card" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
      <button class="btn-secondary" style="padding: 6px 12px" @click="mudarMes(-1)">‹</button>
      <strong style="text-transform: capitalize">{{ rotuloMes }}</strong>
      <button class="btn-secondary" style="padding: 6px 12px" @click="mudarMes(1)">›</button>
    </div>

    <div class="ocultar-impressao" style="display: flex; gap: 8px; margin-bottom: 16px">
      <button
        type="button"
        :class="modo === 'resumido' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="modo = 'resumido'"
      >
        Resumido
      </button>
      <button
        type="button"
        :class="modo === 'completo' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="modo = 'completo'"
      >
        Completo
      </button>
    </div>

    <p v-if="carregando">Carregando...</p>
    <p v-else-if="erro" style="color: var(--danger)">{{ erro }}</p>

    <template v-else-if="espelho">
      <div class="card" style="margin-bottom: 16px; text-align: center">
        <div style="color: var(--text-muted); font-size: 14px">Total no mês</div>
        <div style="font-size: 28px; font-weight: 700">{{ formatarMinutos(espelho.total_minutos) }}</div>
      </div>

      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li v-for="dia in espelho.dias" :key="dia.data" class="card">
          <div style="display: flex; align-items: center; gap: 8px">
            <span v-if="statusDia(dia) === 'ok'" style="color: #0ca30c; font-size: 18px">✓</span>
            <span v-else-if="statusDia(dia) === 'alerta'" style="color: #d03b3b; font-size: 18px">!</span>
            <span v-else style="color: var(--text-muted); font-size: 18px">·</span>
            <strong style="text-transform: capitalize; flex: 1">{{ formatarData(dia.data) }}</strong>
            <span v-if="!dia.futuro" :style="{ color: dia.saldo_minutos >= 0 ? '#0ca30c' : '#d03b3b', fontWeight: 600 }">
              {{ dia.saldo_minutos > 0 ? '+' : '' }}{{ formatarMinutos(dia.saldo_minutos) }}
            </span>
          </div>
          <div v-if="modo === 'completo'" style="margin-top: 6px; font-size: 13px; color: var(--text-muted)">
            <span v-if="dia.futuro"></span>
            <span v-else-if="dia.folga && dia.registros.length === 0">Folga</span>
            <span v-else-if="dia.registros.length === 0">Nenhum ponto registrado</span>
            <span v-else>
              {{ paresDeHorarios(dia.registros) }}
              <span v-if="dia.em_aberto" style="color: var(--warning)"> (em aberto)</span>
            </span>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>
