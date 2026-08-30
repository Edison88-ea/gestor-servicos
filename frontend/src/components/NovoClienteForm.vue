<script setup>
import { ref } from 'vue'
import client from '../api/client'

const props = defineProps({
  // Quando informado, o formulário edita esse cliente (PATCH) em vez de criar.
  cliente: { type: Object, default: null },
})
const emit = defineEmits(['criado', 'cancelar'])

const nome = ref(props.cliente?.nome ?? '')
const documento = ref(props.cliente?.documento ?? '')
const telefone = ref(props.cliente?.telefone ?? '')
const cidade = ref(props.cliente?.cidade ?? '')
const estado = ref(props.cliente?.estado ?? '')
const endereco = ref(props.cliente?.endereco ?? '')
const salvando = ref(false)
const erro = ref('')

async function salvar() {
  erro.value = ''
  if (!nome.value.trim()) {
    erro.value = 'Informe o nome do cliente.'
    return
  }
  salvando.value = true
  const payload = {
    nome: nome.value,
    documento: documento.value,
    telefone: telefone.value,
    cidade: cidade.value,
    estado: estado.value,
    endereco: endereco.value,
  }
  try {
    const { data } = props.cliente
      ? await client.patch(`/clientes/${props.cliente.id}/`, payload)
      : await client.post('/clientes/', payload)
    emit('criado', data)
  } catch {
    erro.value = 'Não foi possível salvar o cliente. Verifique a conexão e tente novamente.'
  } finally {
    salvando.value = false
  }
}
</script>

<template>
  <div class="card" style="display: flex; flex-direction: column; gap: 10px">
    <h2 style="margin: 0">{{ props.cliente ? 'Editar cliente' : 'Novo cliente' }}</h2>

    <label>
      Nome *
      <input
        v-model="nome"
        type="text"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
      />
    </label>

    <label>
      CPF/CNPJ
      <input
        v-model="documento"
        type="text"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
      />
    </label>

    <label>
      Telefone
      <input
        v-model="telefone"
        type="text"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
      />
    </label>

    <label>
      Endereço
      <input
        v-model="endereco"
        type="text"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
      />
    </label>

    <div style="display: flex; gap: 10px">
      <label style="flex: 2">
        Cidade
        <input
          v-model="cidade"
          type="text"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
        />
      </label>
      <label style="flex: 1">
        UF
        <input
          v-model="estado"
          type="text"
          maxlength="2"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px; text-transform: uppercase"
        />
      </label>
    </div>

    <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>

    <div style="display: flex; gap: 10px">
      <button type="button" class="btn-secondary" style="flex: 1" @click="emit('cancelar')">Cancelar</button>
      <button type="button" class="btn" style="flex: 1" :disabled="salvando" @click="salvar">
        {{ salvando ? 'Salvando...' : 'Salvar cliente' }}
      </button>
    </div>
  </div>
</template>
