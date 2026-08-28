<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSolicitacoesPontoStore } from '../stores/solicitacoesPonto'

const router = useRouter()
const auth = useAuthStore()
const store = useSolicitacoesPontoStore()

const ehGestor = computed(() => auth.user?.papel !== 'TECNICO')
const filtro = ref('PENDENTE')
const respostas = ref({})
const processando = ref({})

const TIPO_ROTULO = {
  AJUSTE: 'Ajuste de ponto',
  AJUSTE_DIA: 'Ajuste dos pontos do dia',
  JUSTIFICATIVA_AUSENCIA: 'Justificativa de ausência',
}

const PONTO_ROTULO = {
  ENTRADA: 'Entrada',
  SAIDA_INTERVALO: 'Saída p/ intervalo',
  VOLTA_INTERVALO: 'Volta do intervalo',
  SAIDA: 'Saída',
}

function resumoPontos(lista) {
  if (!lista || !lista.length) return '—'
  return lista
    .map((p) => `${PONTO_ROTULO[p.tipo] || p.tipo} ${p.horario}`)
    .join(' · ')
}

const STATUS_STYLE = {
  PENDENTE: { bg: '#fef3c7', cor: '#92400e', rotulo: 'Pendente' },
  APROVADA: { bg: '#dcfce7', cor: '#166534', rotulo: 'Aprovada' },
  REJEITADA: { bg: '#fee2e2', cor: '#991b1b', rotulo: 'Rejeitada' },
}

function formatarData(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR')
}

async function carregar() {
  await store.carregar(ehGestor.value ? filtro.value : undefined)
}

async function aprovar(id) {
  processando.value[id] = true
  try {
    await store.aprovar(id, respostas.value[id] || '')
    if (filtro.value === 'PENDENTE') await carregar()
  } finally {
    processando.value[id] = false
  }
}

async function rejeitar(id) {
  processando.value[id] = true
  try {
    await store.rejeitar(id, respostas.value[id] || '')
    if (filtro.value === 'PENDENTE') await carregar()
  } finally {
    processando.value[id] = false
  }
}

onMounted(carregar)
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Solicitações</strong>
    <RouterLink v-if="!ehGestor" to="/ponto/solicitacoes/nova" style="color: var(--accent); text-decoration: none; font-weight: 600">
      + Nova
    </RouterLink>
  </div>

  <div class="content">
    <div v-if="ehGestor" style="display: flex; gap: 8px; margin-bottom: 16px">
      <button
        type="button"
        :class="filtro === 'PENDENTE' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="filtro = 'PENDENTE'; carregar()"
      >
        Pendentes
      </button>
      <button
        type="button"
        :class="filtro === '' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="filtro = ''; carregar()"
      >
        Todas
      </button>
    </div>

    <p v-if="store.carregando">Carregando...</p>
    <p v-else-if="store.itens.length === 0" class="card">Nenhuma solicitação encontrada.</p>

    <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 10px">
      <li v-for="s in store.itens" :key="s.id" class="card">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px">
          <strong>{{ TIPO_ROTULO[s.tipo] }}</strong>
          <span
            class="badge"
            :style="{ background: STATUS_STYLE[s.status].bg, color: STATUS_STYLE[s.status].cor }"
          >
            {{ STATUS_STYLE[s.status].rotulo }}
          </span>
        </div>
        <div v-if="ehGestor" style="font-size: 14px; margin-bottom: 4px">{{ s.funcionario_nome }}</div>
        <div style="color: var(--text-muted); font-size: 14px">
          Referente a {{ formatarData(s.data_referencia) }}
          <span v-if="s.tipo === 'AJUSTE'"> — {{ s.tipo_ponto_solicitado }} às {{ s.horario_solicitado?.slice(0, 5) }}</span>
        </div>

        <div v-if="s.tipo === 'AJUSTE_DIA'" style="margin-top: 8px; font-size: 13px; display: flex; flex-direction: column; gap: 4px">
          <div>
            <span style="color: var(--text-muted)">Antes:</span> {{ resumoPontos(s.pontos_anteriores) }}
          </div>
          <div>
            <span style="color: var(--text-muted)">Proposto:</span> <strong>{{ resumoPontos(s.pontos_propostos) }}</strong>
          </div>
        </div>

        <p style="margin: 8px 0 0">{{ s.descricao }}</p>

        <p v-if="s.status !== 'PENDENTE' && s.resposta_gestor" style="margin-top: 8px; font-size: 14px">
          <strong>Resposta:</strong> {{ s.resposta_gestor }}
        </p>

        <div v-if="ehGestor && s.status === 'PENDENTE'" style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px">
          <textarea
            v-model="respostas[s.id]"
            placeholder="Resposta (opcional)"
            rows="2"
            style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid var(--border)"
          />
          <div style="display: flex; gap: 8px">
            <button type="button" class="btn-secondary" style="flex: 1" :disabled="processando[s.id]" @click="rejeitar(s.id)">
              Rejeitar
            </button>
            <button type="button" class="btn" style="flex: 1" :disabled="processando[s.id]" @click="aprovar(s.id)">
              Aprovar
            </button>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
