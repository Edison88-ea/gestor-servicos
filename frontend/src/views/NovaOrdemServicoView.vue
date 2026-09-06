<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useClientesStore } from '../stores/clientes'
import { useOrdensServicoStore } from '../stores/ordensServico'
import { useNovaOsRascunhoStore } from '../stores/novaOsRascunho'
import NovoClienteForm from '../components/NovoClienteForm.vue'

const router = useRouter()
const clientesStore = useClientesStore()
const ordensStore = useOrdensServicoStore()
const rascunho = useNovaOsRascunhoStore()

const termoBusca = ref('')
const clienteSelecionado = ref(null)
const cadastrandoCliente = ref(false)
const tipoServico = ref('')
const descricao = ref('')
const prioridade = ref('MEDIA')
const criando = ref(false)
const erro = ref('')

// Rascunho local do formulário: salvo neste aparelho conforme se preenche,
// pra não perder cliente + tipo + descrição ao sair da tela antes de criar.
const CHAVE_RASCUNHO = 'nova_os_rascunho'
const rascunhoRestaurado = ref(false)
let rascunhoPronto = false
let rascunhoTimer = null

function salvarRascunho() {
  const temConteudo =
    clienteSelecionado.value || tipoServico.value.trim() || descricao.value.trim()
  try {
    if (temConteudo) {
      localStorage.setItem(
        CHAVE_RASCUNHO,
        JSON.stringify({
          cliente: clienteSelecionado.value,
          tipoServico: tipoServico.value,
          descricao: descricao.value,
          prioridade: prioridade.value,
        }),
      )
    } else {
      localStorage.removeItem(CHAVE_RASCUNHO)
    }
  } catch {
    /* cota cheia / aba privada: ignora */
  }
}
function limparRascunho() {
  try {
    localStorage.removeItem(CHAVE_RASCUNHO)
  } catch {
    /* ignora */
  }
  rascunhoRestaurado.value = false
}
function descartarRascunho() {
  limparRascunho()
  clienteSelecionado.value = null
  tipoServico.value = ''
  descricao.value = ''
  prioridade.value = 'MEDIA'
}

onMounted(() => {
  try {
    const r = JSON.parse(localStorage.getItem(CHAVE_RASCUNHO) || 'null')
    if (r && (r.cliente || r.tipoServico || r.descricao)) {
      clienteSelecionado.value = r.cliente || null
      tipoServico.value = r.tipoServico || ''
      descricao.value = r.descricao || ''
      prioridade.value = r.prioridade || 'MEDIA'
      rascunhoRestaurado.value = true
    }
  } catch {
    /* ignora */
  }
  rascunhoPronto = true
})

watch([clienteSelecionado, tipoServico, descricao, prioridade], () => {
  if (!rascunhoPronto) return
  clearTimeout(rascunhoTimer)
  rascunhoTimer = setTimeout(salvarRascunho, 600)
})

let debounceId = null
watch(termoBusca, (valor) => {
  clearTimeout(debounceId)
  debounceId = setTimeout(() => clientesStore.buscar(valor), 300)
})
clientesStore.buscar('')

function selecionarCliente(cliente) {
  clienteSelecionado.value = cliente
}

function trocarCliente() {
  clienteSelecionado.value = null
}

function clienteCadastrado(cliente) {
  cadastrandoCliente.value = false
  clienteSelecionado.value = cliente
}

async function criarOs() {
  erro.value = ''
  if (!tipoServico.value.trim()) {
    erro.value = 'Informe o tipo de serviço.'
    return
  }
  criando.value = true
  try {
    const payload = {
      cliente: clienteSelecionado.value.id,
      cliente_nome: clienteSelecionado.value.nome,
      tipo_servico: tipoServico.value,
      descricao: descricao.value,
      prioridade: prioridade.value,
    }
    if (rascunho.latitude != null) {
      payload.latitude_abertura = rascunho.latitude
      payload.longitude_abertura = rascunho.longitude
    }
    const nova = await ordensStore.criar(payload)
    rascunho.limpar()
    limparRascunho()
    router.replace(`/ordens-servico/${nova.id}`)
  } catch {
    erro.value = 'Não foi possível criar a OS. Tente novamente.'
  } finally {
    criando.value = false
  }
}
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Nova Ordem de Serviço</strong>
  </div>

  <div class="content">
    <div
      v-if="rascunhoRestaurado && !cadastrandoCliente"
      style="background: var(--surface-2, rgba(255, 255, 255, 0.04)); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; font-size: 13px; color: var(--text-muted); display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 12px"
    >
      <span>Rascunho restaurado deste aparelho.</span>
      <button type="button" class="btn-secondary" style="padding: 4px 10px; border-radius: 6px; font-size: 12px" @click="descartarRascunho">
        descartar
      </button>
    </div>

    <p v-if="rascunho.latitude != null" style="color: var(--success); margin-bottom: 12px">
      📍 Localização atual capturada
    </p>

    <template v-if="cadastrandoCliente">
      <NovoClienteForm @criado="clienteCadastrado" @cancelar="cadastrandoCliente = false" />
    </template>

    <template v-else-if="!clienteSelecionado">
      <div style="display: flex; gap: 8px; margin-bottom: 12px">
        <input
          v-model="termoBusca"
          type="text"
          placeholder="Buscar cliente por nome, CNPJ ou cidade"
          style="flex: 1; padding: 12px; border-radius: 8px; border: 1px solid var(--border)"
        />
        <button type="button" class="btn-secondary" style="white-space: nowrap" @click="cadastrandoCliente = true">
          + Novo cliente
        </button>
      </div>

      <p v-if="clientesStore.carregando">Buscando...</p>
      <p v-else-if="clientesStore.resultados.length === 0" class="card">Nenhum cliente encontrado.</p>

      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li
          v-for="c in clientesStore.resultados"
          :key="c.id"
          class="card"
          style="cursor: pointer"
          @click="selecionarCliente(c)"
        >
          <strong>{{ c.nome }}</strong>
          <div style="color: var(--text-muted); font-size: 14px">
            {{ c.cidade || 'Endereço desconhecido' }}{{ c.estado ? ' - ' + c.estado : '' }}
          </div>
        </li>
      </ul>
    </template>

    <template v-else>
      <div class="card" style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center">
        <div>
          <strong>{{ clienteSelecionado.nome }}</strong>
          <div style="color: var(--text-muted); font-size: 14px">{{ clienteSelecionado.cidade }}</div>
        </div>
        <button type="button" class="btn-secondary" style="padding: 6px 12px" @click="trocarCliente">Trocar</button>
      </div>

      <div class="card" style="display: flex; flex-direction: column; gap: 10px">
        <label>
          Tipo de serviço
          <input
            v-model="tipoServico"
            type="text"
            placeholder="Ex: Manutenção de câmara fria"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          />
        </label>

        <label>
          Descrição
          <textarea
            v-model="descricao"
            rows="4"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          />
        </label>

        <label>
          Prioridade
          <select
            v-model="prioridade"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          >
            <option value="BAIXA">Baixa</option>
            <option value="MEDIA">Média</option>
            <option value="ALTA">Alta</option>
            <option value="URGENTE">Urgente</option>
          </select>
        </label>

        <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>
        <button class="btn" :disabled="criando" @click="criarOs">
          {{ criando ? 'Criando...' : 'Criar OS' }}
        </button>
      </div>
    </template>
  </div>
</template>
