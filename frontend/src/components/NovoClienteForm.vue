<script setup>
import { ref } from 'vue'
import client from '../api/client'

const emit = defineEmits(['criado', 'cancelar'])

const nome = ref('')
const documento = ref('')
const telefone = ref('')
const cidade = ref('')
const estado = ref('')
const endereco = ref('')
const salvando = ref(false)
const erro = ref('')

async function salvar() {
  erro.value = ''
  if (!nome.value.trim()) {
    erro.value = 'Informe o nome do cliente.'
    return
  }
  salvando.value = true
  try {
    const { data } = await client.post('/clientes/', {
      nome: nome.value,
      documento: documento.value,
      telefone: telefone.value,
      cidade: cidade.value,
      estado: estado.value,
      endereco: endereco.value,
    })
    emit('criado', data)
  } catch {
    erro.value = 'Não foi possível cadastrar o cliente. Verifique a conexão e tente novamente.'
  } finally {
    salvando.value = false
  }
}
</script>

<template>
  <div class="card" style="display: flex; flex-direction: column; gap: 10px">
    <h2 style="margin: 0">Novo cliente</h2>

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
