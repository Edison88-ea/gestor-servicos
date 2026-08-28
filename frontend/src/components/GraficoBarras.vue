<script setup>
import { computed, ref } from 'vue'
import { formatarMinutos } from '../utils/tempo'

const props = defineProps({
  dados: { type: Array, required: true }, // [{ rotulo, valorMinutos }]
  status: { type: String, default: 'good' }, // 'good' | 'critical'
})

const corBarra = props.status === 'critical' ? '#d03b3b' : '#0ca30c'
const hoverIndex = ref(null)

const ALTURA = 180
const LARGURA_BARRA = 22
const GAP = 18
const MARGEM_ESQUERDA = 44

const maximo = computed(() => Math.max(...props.dados.map((d) => d.valorMinutos), 1))

// Passo "limpo" pro eixo (múltiplos de 10, 30 ou 60 minutos conforme a escala)
const passo = computed(() => {
  const candidatos = [10, 30, 60, 120, 180, 300, 600, 1200]
  const alvo = maximo.value / 4
  return candidatos.find((c) => c >= alvo) || Math.ceil(alvo / 600) * 600
})

const topoEscala = computed(() => Math.ceil(maximo.value / passo.value) * passo.value || passo.value)

const ticks = computed(() => {
  const lista = []
  for (let v = 0; v <= topoEscala.value; v += passo.value) lista.push(v)
  return lista
})

const largura = computed(() => MARGEM_ESQUERDA + props.dados.length * (LARGURA_BARRA + GAP) + GAP)

function escalaY(valorMinutos) {
  return (valorMinutos / topoEscala.value) * ALTURA
}
</script>

<template>
  <div style="overflow-x: auto">
    <svg :width="largura" :height="ALTURA + 36" :viewBox="`0 0 ${largura} ${ALTURA + 36}`" role="img" :aria-label="`Gráfico de barras`">
      <g v-for="t in ticks" :key="t">
        <line
          :x1="MARGEM_ESQUERDA"
          :x2="largura"
          :y1="ALTURA - escalaY(t) + 8"
          :y2="ALTURA - escalaY(t) + 8"
          stroke="var(--border)"
          stroke-width="1"
        />
        <text :x="MARGEM_ESQUERDA - 8" :y="ALTURA - escalaY(t) + 11" text-anchor="end" font-size="11" fill="var(--text-muted)">
          {{ formatarMinutos(t) }}
        </text>
      </g>

      <g v-for="(d, i) in dados" :key="d.rotulo">
        <rect
          :x="MARGEM_ESQUERDA + GAP + i * (LARGURA_BARRA + GAP)"
          :y="ALTURA - escalaY(d.valorMinutos) + 8"
          :width="LARGURA_BARRA"
          :height="Math.max(escalaY(d.valorMinutos), 0)"
          :rx="4"
          :fill="corBarra"
          :opacity="hoverIndex === i ? 1 : 0.9"
          style="cursor: pointer"
          @mouseenter="hoverIndex = i"
          @mouseleave="hoverIndex = null"
          @touchstart="hoverIndex = i"
        >
          <title>{{ d.rotulo }}: {{ formatarMinutos(d.valorMinutos) }}</title>
        </rect>
        <text
          :x="MARGEM_ESQUERDA + GAP + i * (LARGURA_BARRA + GAP) + LARGURA_BARRA / 2"
          :y="ALTURA + 22"
          text-anchor="middle"
          font-size="11"
          fill="var(--text-muted)"
        >
          {{ d.rotulo }}
        </text>
      </g>
    </svg>
    <p v-if="hoverIndex != null" style="margin: 4px 0 0; font-size: 13px; color: var(--text)">
      <strong>{{ dados[hoverIndex].rotulo }}:</strong> {{ formatarMinutos(dados[hoverIndex].valorMinutos) }}
    </p>
  </div>
</template>
