<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useEstoqueStore } from '../stores/estoque'

const store = useEstoqueStore()
const auth = useAuthStore()
const router = useRouter()

const podeGerenciar = computed(() => ['GESTOR', 'ADMIN'].includes(auth.user?.papel))

const busca = ref('')
const soAbaixo = ref(false)

const novoAberto = ref(false)
const salvandoNovo = ref(false)
const erroNovo = ref('')
const novo = ref({ descricao: '', unidade: '', saldo_inicial: '', custo_inicial: '', estoque_minimo: '' })

const catalogoAberto = ref(false)
const pendentes = ref([])
const selecionados = ref([])
const importando = ref(false)

const lista = computed(() => {
  const termo = busca.value.trim().toLowerCase()
  return store.materiais.filter((m) => {
    if (soAbaixo.value && !m.abaixo_minimo) return false
    if (termo && !m.descricao.toLowerCase().includes(termo)) return false
    return true
  })
})

function moeda(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
function qtd(v) {
  return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}
function corSaldo(m) {
  if (Number(m.saldo) < 0) return 'var(--danger)'
  if (m.abaixo_minimo) return 'var(--warning)'
  return 'inherit'
}

async function salvarNovo() {
  if (!novo.value.descricao.trim()) {
    erroNovo.value = 'Informe a descrição.'
    return
  }
  salvandoNovo.value = true
  erroNovo.value = ''
  try {
    const payload = { descricao: novo.value.descricao.trim(), unidade: novo.value.unidade.trim() }
    if (novo.value.estoque_minimo) payload.estoque_minimo = novo.value.estoque_minimo
    if (novo.value.saldo_inicial) payload.saldo_inicial = novo.value.saldo_inicial
    if (novo.value.custo_inicial) payload.custo_inicial = novo.value.custo_inicial
    await store.criar(payload)
    await store.carregarResumo()
    novo.value = { descricao: '', unidade: '', saldo_inicial: '', custo_inicial: '', estoque_minimo: '' }
    novoAberto.value = false
  } catch (e) {
    erroNovo.value = e.response?.data?.descricao?.[0] || e.response?.data?.detail || 'Não foi possível salvar.'
  } finally {
    salvandoNovo.value = false
  }
}

async function abrirCatalogo() {
  catalogoAberto.value = true
  selecionados.value = []
  try {
    pendentes.value = await store.catalogoPendente()
  } catch {
    pendentes.value = []
  }
}

async function importarSelecionados() {
  if (!selecionados.value.length) return
  importando.value = true
  try {
    await store.importarDoCatalogo(selecionados.value)
    await store.carregarResumo()
    catalogoAberto.value = false
  } finally {
    importando.value = false
  }
}

onMounted(() => {
  store.carregar()
  store.carregarResumo()
})
</script>

<template>
  <div class="top-bar">
    <strong>Estoque</strong>
    <button
      v-if="podeGerenciar"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      @click="novoAberto = !novoAberto"
    >
      + Novo
    </button>
  </div>

  <div class="content">
    <div class="painel-kpis" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 14px">
      <div class="kpi" style="padding: 12px 14px">
        <div class="kpi-valor" style="font-size: 20px">{{ store.resumo.total_itens }}</div>
        <div class="kpi-rotulo">Itens ativos</div>
      </div>
      <div class="kpi" style="padding: 12px 14px">
        <div class="kpi-valor" style="font-size: 20px">{{ moeda(store.resumo.valor_em_estoque) }}</div>
        <div class="kpi-rotulo">Valor em estoque</div>
      </div>
      <div class="kpi" :class="{ 'kpi-alerta': store.resumo.abaixo_minimo > 0 }" style="padding: 12px 14px">
        <div class="kpi-valor" style="font-size: 20px">{{ store.resumo.abaixo_minimo }}</div>
        <div class="kpi-rotulo">Abaixo do mínimo</div>
      </div>
    </div>

    <form
      v-if="novoAberto"
      class="card"
      style="margin-bottom: 14px; display: flex; flex-direction: column; gap: 8px"
      @submit.prevent="salvarNovo"
    >
      <strong>Novo material</strong>
      <input v-model="novo.descricao" placeholder="Descrição (ex.: Perfilado)" class="entrada" />
      <div style="display: flex; gap: 8px">
        <input v-model="novo.unidade" placeholder="Unidade (un, m, kg)" class="entrada" style="flex: 1" />
        <input v-model="novo.estoque_minimo" type="number" step="any" min="0" placeholder="Estoque mínimo" class="entrada" style="flex: 1" />
      </div>
      <div style="display: flex; gap: 8px">
        <input v-model="novo.saldo_inicial" type="number" step="any" min="0" placeholder="Saldo inicial" class="entrada" style="flex: 1" />
        <input v-model="novo.custo_inicial" type="number" step="any" min="0" placeholder="Custo unit. (R$)" class="entrada" style="flex: 1" />
      </div>
      <p v-if="erroNovo" style="color: var(--danger); font-size: 13px; margin: 0">{{ erroNovo }}</p>
      <div style="display: flex; gap: 8px">
        <button type="submit" class="btn" style="flex: 1" :disabled="salvandoNovo">Salvar</button>
        <button type="button" class="btn-secondary" style="flex: 1" @click="novoAberto = false">Cancelar</button>
      </div>
    </form>

    <div style="display: flex; gap: 8px; margin-bottom: 10px">
      <input v-model="busca" placeholder="Buscar material..." class="entrada" style="flex: 1" />
      <RouterLink
        to="/estoque/movimentacoes"
        class="btn-secondary"
        style="text-decoration: none; display: flex; align-items: center; padding: 0 12px; border-radius: 10px; font-size: 13px; white-space: nowrap"
      >
        Movimentações
      </RouterLink>
    </div>

    <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 14px">
      <input v-model="soAbaixo" type="checkbox" />
      Só os que estão abaixo do mínimo
    </label>

    <button
      v-if="podeGerenciar"
      type="button"
      class="btn-secondary"
      style="width: 100%; margin-bottom: 12px; font-size: 13px"
      @click="abrirCatalogo"
    >
      Importar materiais do catálogo de OS
    </button>

    <div v-if="catalogoAberto" class="card" style="margin-bottom: 12px">
      <strong>Materiais já usados em OS que ainda não estão no estoque</strong>
      <p v-if="!pendentes.length" style="color: var(--text-muted); font-size: 13px; margin: 8px 0 0">
        Nada pendente — todos os materiais do catálogo já estão no estoque.
      </p>
      <div v-else style="max-height: 260px; overflow-y: auto; margin: 8px 0; display: flex; flex-direction: column; gap: 4px">
        <label v-for="p in pendentes" :key="p.descricao" style="display: flex; align-items: center; gap: 8px; font-size: 14px">
          <input v-model="selecionados" type="checkbox" :value="p.descricao" />
          {{ p.descricao }}
          <span style="color: var(--text-muted); font-size: 12px">{{ p.unidade }} · {{ p.usos }}× em OS</span>
        </label>
      </div>
      <div style="display: flex; gap: 8px">
        <button type="button" class="btn" style="flex: 1" :disabled="importando || !selecionados.length" @click="importarSelecionados">
          Adicionar {{ selecionados.length || '' }} ao estoque
        </button>
        <button type="button" class="btn-secondary" style="flex: 1" @click="catalogoAberto = false">Fechar</button>
      </div>
    </div>

    <p v-if="store.carregando && !store.materiais.length">Carregando...</p>
    <p v-else-if="!lista.length" style="color: var(--text-muted)">
      {{ busca || soAbaixo ? 'Nenhum material com esse filtro.' : 'Nenhum material cadastrado no estoque.' }}
    </p>

    <ul class="grid-cards">
      <li
        v-for="m in lista"
        :key="m.id"
        class="card"
        style="cursor: pointer"
        @click="router.push(`/estoque/${m.id}`)"
      >
        <div style="display: flex; justify-content: space-between; gap: 8px; align-items: baseline">
          <strong>{{ m.descricao }}</strong>
          <span :style="{ color: corSaldo(m), fontWeight: 700, whiteSpace: 'nowrap' }">
            {{ qtd(m.saldo) }} {{ m.unidade }}
          </span>
        </div>
        <div style="color: var(--text-muted); font-size: 13px; margin-top: 4px">
          <span v-if="Number(m.estoque_minimo) > 0">mín. {{ qtd(m.estoque_minimo) }} · </span>
          <span v-if="Number(m.custo_unitario) > 0">{{ moeda(m.custo_unitario) }}/{{ m.unidade || 'un' }} · {{ moeda(m.valor_em_estoque) }} em estoque</span>
          <span v-else>sem custo cadastrado</span>
        </div>
        <div v-if="m.abaixo_minimo || Number(m.saldo) < 0" style="margin-top: 6px">
          <span class="badge" :class="Number(m.saldo) < 0 ? 'badge-cancelada' : 'badge-aberta'">
            {{ Number(m.saldo) < 0 ? 'saldo negativo' : 'abaixo do mínimo' }}
          </span>
        </div>
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
