<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useObrasStore } from '../stores/obras'

const store = useObrasStore()
const auth = useAuthStore()
const router = useRouter()

const filtro = ref('')

const podeGerenciar = computed(() => ['ENCARREGADO', 'GESTOR', 'ADMIN'].includes(auth.user?.papel))

const STATUS_ROTULO = {
  PLANEJADO: 'Planejado',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDO: 'Concluído',
  CANCELADO: 'Cancelado',
}

const lista = computed(() =>
  filtro.value ? store.obras.filter((o) => o.status === filtro.value) : store.obras,
)

function corBarra(pct) {
  if (pct >= 100) return 'var(--success)'
  if (pct > 0) return 'var(--accent)'
  return 'var(--border)'
}

function prazo(iso) {
  return iso ? new Date(iso + 'T00:00:00').toLocaleDateString('pt-BR') : null
}

onMounted(() => {
  store.carregar()
  store.carregarOpcoes()
})
</script>

<template>
  <div class="top-bar">
    <strong>Obras</strong>
    <button
      v-if="podeGerenciar"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      @click="router.push('/obras/nova')"
    >
      + Nova
    </button>
  </div>

  <div class="content">
    <div style="display: flex; gap: 8px; margin-bottom: 12px">
      <div class="card" style="flex: 1; text-align: center; padding: 10px">
        <div style="font-size: 20px; font-weight: 700">{{ store.contadores.total }}</div>
        <div style="font-size: 12px; color: var(--text-muted)">Total</div>
      </div>
      <div class="card" style="flex: 1; text-align: center; padding: 10px">
        <div style="font-size: 20px; font-weight: 700; color: var(--accent)">
          {{ store.contadores.andamento }}
        </div>
        <div style="font-size: 12px; color: var(--text-muted)">Em andamento</div>
      </div>
      <div class="card" style="flex: 1; text-align: center; padding: 10px">
        <div style="font-size: 20px; font-weight: 700; color: var(--success)">
          {{ store.contadores.concluidas }}
        </div>
        <div style="font-size: 12px; color: var(--text-muted)">Concluídas</div>
      </div>
    </div>

    <select
      v-model="filtro"
      style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 12px"
    >
      <option value="">Todos os status</option>
      <option v-for="(rotulo, valor) in STATUS_ROTULO" :key="valor" :value="valor">{{ rotulo }}</option>
    </select>

    <p v-if="store.carregando && !store.obras.length">Carregando...</p>
    <p v-else-if="!lista.length" style="color: var(--text-muted)">
      Nenhuma obra {{ filtro ? 'nesse status' : 'cadastrada' }}.
    </p>

    <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 10px">
      <li
        v-for="obra in lista"
        :key="obra.id"
        class="card"
        style="cursor: pointer"
        @click="router.push(`/obras/${obra.id}`)"
      >
        <div style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 4px">
          <strong>{{ obra.nome }}</strong>
          <span style="color: var(--text-muted); font-size: 13px">{{ obra.numero }}</span>
        </div>
        <div style="color: var(--text-muted); font-size: 13px; margin-bottom: 8px">
          {{ STATUS_ROTULO[obra.status] || obra.status }}
          <template v-if="obra.responsavel"> · {{ obra.responsavel }}</template>
          <template v-if="prazo(obra.data_termino_previsto)"> · prazo {{ prazo(obra.data_termino_previsto) }}</template>
        </div>

        <div style="height: 8px; background: var(--border); border-radius: 999px; overflow: hidden">
          <div
            :style="{
              width: obra.progresso + '%',
              height: '100%',
              background: corBarra(obra.progresso),
            }"
          />
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px">
          {{ obra.progresso }}% · {{ obra.total_realizado }}/{{ obra.total_meta }} pontos
        </div>
      </li>
    </ul>
  </div>
</template>
