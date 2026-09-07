<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useEstoqueStore } from '../stores/estoque'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useEstoqueStore()
const auth = useAuthStore()
const router = useRouter()

const podeGerenciar = computed(() => ['GESTOR', 'ADMIN'].includes(auth.user?.papel))

const material = ref(null)
const movimentos = ref([])
const erro = ref('')

const painel = ref('') // '', 'entrada', 'ajuste', 'editar'
const processando = ref(false)
const erroForm = ref('')

const formEntrada = ref({ quantidade: '', custo_unitario: '', documento: '', observacao: '' })
const formAjuste = ref({ saldo_contado: '', observacao: '' })
const formEditar = ref({ unidade: '', estoque_minimo: '', ativo: true })

const TIPO_BADGE = {
  ENTRADA: 'badge-concluida',
  SAIDA: 'badge-cancelada',
  AJUSTE: 'badge-atribuida',
}

function moeda(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
function qtd(v) {
  return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}
function dataHora(iso) {
  return new Date(iso).toLocaleString('pt-BR')
}

const corSaldo = computed(() => {
  if (!material.value) return 'inherit'
  if (Number(material.value.saldo) < 0) return 'var(--danger)'
  if (material.value.abaixo_minimo) return 'var(--warning)'
  return 'var(--text)'
})

async function carregar() {
  try {
    material.value = await store.buscar(props.id)
    formEditar.value = {
      unidade: material.value.unidade,
      estoque_minimo: material.value.estoque_minimo,
      ativo: material.value.ativo,
    }
    movimentos.value = await store.movimentos(props.id, { page_size: 100 })
  } catch (e) {
    erro.value = e.response?.status === 404 ? 'Material não encontrado.' : 'Não foi possível carregar.'
  }
}

function abrir(qual) {
  painel.value = painel.value === qual ? '' : qual
  erroForm.value = ''
}

async function salvarEntrada() {
  if (!formEntrada.value.quantidade) {
    erroForm.value = 'Informe a quantidade.'
    return
  }
  processando.value = true
  erroForm.value = ''
  try {
    await store.registrarEntrada(props.id, { ...formEntrada.value })
    formEntrada.value = { quantidade: '', custo_unitario: '', documento: '', observacao: '' }
    painel.value = ''
    await carregar()
  } catch (e) {
    erroForm.value = primeiroErro(e) || 'Não foi possível registrar a entrada.'
  } finally {
    processando.value = false
  }
}

async function salvarAjuste() {
  if (formAjuste.value.saldo_contado === '') {
    erroForm.value = 'Informe o saldo contado.'
    return
  }
  processando.value = true
  erroForm.value = ''
  try {
    await store.registrarAjuste(props.id, { ...formAjuste.value })
    formAjuste.value = { saldo_contado: '', observacao: '' }
    painel.value = ''
    await carregar()
  } catch (e) {
    erroForm.value = primeiroErro(e) || 'Não foi possível registrar o ajuste.'
  } finally {
    processando.value = false
  }
}

async function salvarEdicao() {
  processando.value = true
  erroForm.value = ''
  try {
    await store.atualizar(props.id, {
      unidade: formEditar.value.unidade,
      estoque_minimo: formEditar.value.estoque_minimo || 0,
      ativo: formEditar.value.ativo,
    })
    painel.value = ''
    await carregar()
  } catch (e) {
    erroForm.value = primeiroErro(e) || 'Não foi possível salvar.'
  } finally {
    processando.value = false
  }
}

function primeiroErro(e) {
  const d = e.response?.data
  if (!d) return ''
  if (typeof d === 'string') return d
  const primeira = Object.values(d)[0]
  return Array.isArray(primeira) ? primeira[0] : String(primeira)
}

onMounted(carregar)
</script>

<template>
  <div class="top-bar">
    <strong>Material</strong>
    <RouterLink to="/estoque" style="color: var(--accent); font-weight: 600; text-decoration: none">Voltar</RouterLink>
  </div>

  <div class="content">
    <p v-if="erro" class="card" style="color: var(--danger)">{{ erro }}</p>

    <template v-if="material">
      <div class="card" style="margin-bottom: 14px">
        <div style="display: flex; justify-content: space-between; gap: 8px; align-items: baseline">
          <strong style="font-size: 18px">{{ material.descricao }}</strong>
          <span v-if="!material.ativo" class="badge badge-pausada">inativo</span>
        </div>
        <div style="font-size: 34px; font-weight: 800; margin: 8px 0 2px" :style="{ color: corSaldo }">
          {{ qtd(material.saldo) }} <span style="font-size: 16px; font-weight: 600">{{ material.unidade }}</span>
        </div>
        <div style="color: var(--text-muted); font-size: 13px">
          <span v-if="Number(material.estoque_minimo) > 0">mínimo {{ qtd(material.estoque_minimo) }} · </span>
          custo {{ moeda(material.custo_unitario) }} · {{ moeda(material.valor_em_estoque) }} em estoque
        </div>
        <div v-if="material.abaixo_minimo || Number(material.saldo) < 0" style="margin-top: 8px">
          <span class="badge" :class="Number(material.saldo) < 0 ? 'badge-cancelada' : 'badge-aberta'">
            {{ Number(material.saldo) < 0 ? 'saldo negativo' : 'abaixo do mínimo' }}
          </span>
        </div>
      </div>

      <div v-if="podeGerenciar" style="display: flex; gap: 8px; margin-bottom: 12px">
        <button type="button" class="btn" style="flex: 1; padding: 10px; font-size: 14px" @click="abrir('entrada')">Entrada</button>
        <button type="button" class="btn-secondary" style="flex: 1; padding: 10px; font-size: 14px" @click="abrir('ajuste')">Ajuste</button>
        <button type="button" class="btn-secondary" style="flex: 1; padding: 10px; font-size: 14px" @click="abrir('editar')">Editar</button>
      </div>

      <form v-if="painel === 'entrada'" class="card" style="margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px" @submit.prevent="salvarEntrada">
        <strong>Registrar entrada (compra / recebimento)</strong>
        <input v-model="formEntrada.quantidade" type="number" step="any" min="0" placeholder="Quantidade" class="entrada" />
        <input v-model="formEntrada.custo_unitario" type="number" step="any" min="0" placeholder="Custo unitário (R$) — opcional" class="entrada" />
        <input v-model="formEntrada.documento" placeholder="Nota fiscal / fornecedor — opcional" class="entrada" />
        <input v-model="formEntrada.observacao" placeholder="Observação — opcional" class="entrada" />
        <p v-if="erroForm" style="color: var(--danger); font-size: 13px; margin: 0">{{ erroForm }}</p>
        <button type="submit" class="btn" :disabled="processando">Confirmar entrada</button>
      </form>

      <form v-if="painel === 'ajuste'" class="card" style="margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px" @submit.prevent="salvarAjuste">
        <strong>Ajuste de inventário</strong>
        <p style="color: var(--text-muted); font-size: 13px; margin: 0">Informe o saldo real que você contou. O sistema registra a diferença.</p>
        <input v-model="formAjuste.saldo_contado" type="number" step="any" min="0" placeholder="Saldo contado" class="entrada" />
        <input v-model="formAjuste.observacao" placeholder="Motivo / observação" class="entrada" />
        <p v-if="erroForm" style="color: var(--danger); font-size: 13px; margin: 0">{{ erroForm }}</p>
        <button type="submit" class="btn" :disabled="processando">Confirmar ajuste</button>
      </form>

      <form v-if="painel === 'editar'" class="card" style="margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px" @submit.prevent="salvarEdicao">
        <strong>Editar material</strong>
        <input v-model="formEditar.unidade" placeholder="Unidade" class="entrada" />
        <input v-model="formEditar.estoque_minimo" type="number" step="any" min="0" placeholder="Estoque mínimo" class="entrada" />
        <label style="display: flex; align-items: center; gap: 8px; font-size: 14px">
          <input v-model="formEditar.ativo" type="checkbox" /> Material ativo
        </label>
        <p v-if="erroForm" style="color: var(--danger); font-size: 13px; margin: 0">{{ erroForm }}</p>
        <button type="submit" class="btn" :disabled="processando">Salvar</button>
      </form>

      <h3 style="margin: 4px 0 8px">Movimentações</h3>
      <p v-if="!movimentos.length" style="color: var(--text-muted)">Nenhuma movimentação ainda.</p>
      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li v-for="mv in movimentos" :key="mv.id" class="card" style="padding: 12px">
          <div style="display: flex; justify-content: space-between; gap: 8px; align-items: baseline">
            <span class="badge" :class="TIPO_BADGE[mv.tipo]">{{ mv.tipo_display }}</span>
            <span style="font-weight: 700">
              {{ mv.tipo === 'AJUSTE' ? '=' : mv.tipo === 'SAIDA' ? '−' : '+' }}{{ qtd(mv.quantidade) }}
            </span>
          </div>
          <div style="color: var(--text-muted); font-size: 13px; margin-top: 4px">
            saldo após: {{ qtd(mv.saldo_apos) }}
            <template v-if="mv.os_numero"> · <RouterLink :to="`/ordens-servico/${mv.ordem_servico}`" style="color: var(--accent)">OS {{ mv.os_numero }}</RouterLink></template>
            <template v-else-if="mv.documento"> · {{ mv.documento }}</template>
          </div>
          <div style="color: var(--text-muted); font-size: 12px; margin-top: 2px">
            {{ dataHora(mv.criado_em) }}<template v-if="mv.usuario_nome"> · {{ mv.usuario_nome }}</template>
          </div>
          <div v-if="mv.observacao" style="font-size: 13px; margin-top: 4px">{{ mv.observacao }}</div>
        </li>
      </ul>
    </template>
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
