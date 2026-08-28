<script setup>
import { ref, watch } from 'vue'
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
