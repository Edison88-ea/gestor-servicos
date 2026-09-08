<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useEstoqueStore } from '../stores/estoque'

const store = useEstoqueStore()

const filtros = ref({ tipo: '', material: '', desde: '' })
const movimentos = ref([])
const carregando = ref(false)

const TIPO_BADGE = {
  ENTRADA: 'badge-concluida',
  SAIDA: 'badge-cancelada',
  AJUSTE: 'badge-atribuida',
}

function qtd(v) {
  return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}
function dataHora(iso) {
  return new Date(iso).toLocaleString('pt-BR')
}

const materiais = computed(() => store.materiais)

async function carregar() {
  carregando.value = true
  try {
    const params = { page_size: 200 }
    if (filtros.value.tipo) params.tipo = filtros.value.tipo
    if (filtros.value.material) params.material = filtros.value.material
    if (filtros.value.desde) params.desde = filtros.value.desde
    movimentos.value = await store.movimentacoes(params)
  } finally {
    carregando.value = false
  }
}

watch(filtros, carregar, { deep: true })

onMounted(() => {
  if (!store.materiais.length) store.carregar()
  carregar()
})
</script>

<template>
  <div class="top-bar">
    <strong>Movimentações de estoque</strong>
    <RouterLink to="/estoque" style="color: var(--accent); font-weight: 600; text-decoration: none">Voltar</RouterLink>
  </div>

  <div class="content">
    <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px">
      <select v-model="filtros.tipo" class="entrada">
        <option value="">Todos os tipos</option>
        <option value="ENTRADA">Entrada</option>
        <option value="SAIDA">Saída</option>
        <option value="AJUSTE">Ajuste</option>
      </select>
      <select v-model="filtros.material" class="entrada">
        <option value="">Todos os materiais</option>
        <option v-for="m in materiais" :key="m.id" :value="m.id">{{ m.descricao }}</option>
      </select>
      <label style="font-size: 13px; color: var(--text-muted)">
        A partir de
        <input v-model="filtros.desde" type="date" class="entrada" style="width: 100%; margin-top: 4px" />
      </label>
    </div>

    <p v-if="carregando && !movimentos.length">Carregando...</p>
    <p v-else-if="!movimentos.length" style="color: var(--text-muted)">Nenhuma movimentação com esse filtro.</p>

    <ul class="grid-cards">
      <li v-for="mv in movimentos" :key="mv.id" class="card" style="padding: 12px">
        <div style="display: flex; justify-content: space-between; gap: 8px; align-items: baseline">
          <strong>{{ mv.material_descricao }}</strong>
          <span style="font-weight: 700; white-space: nowrap">
            {{ mv.tipo === 'AJUSTE' ? '=' : mv.tipo === 'SAIDA' ? '−' : '+' }}{{ qtd(mv.quantidade) }}
          </span>
        </div>
        <div style="margin-top: 4px">
          <span class="badge" :class="TIPO_BADGE[mv.tipo]">{{ mv.tipo_display }}</span>
          <span style="color: var(--text-muted); font-size: 13px"> · saldo após {{ qtd(mv.saldo_apos) }}</span>
        </div>
        <div style="color: var(--text-muted); font-size: 12px; margin-top: 4px">
          {{ dataHora(mv.criado_em) }}<template v-if="mv.usuario_nome"> · {{ mv.usuario_nome }}</template>
          <template v-if="mv.os_numero"> · <RouterLink :to="`/ordens-servico/${mv.ordem_servico}`" style="color: var(--accent)">OS {{ mv.os_numero }}</RouterLink></template>
          <template v-else-if="mv.documento"> · {{ mv.documento }}</template>
        </div>
        <div v-if="mv.observacao" style="font-size: 13px; margin-top: 4px">{{ mv.observacao }}</div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.entrada {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
}
</style>
