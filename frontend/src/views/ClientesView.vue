<script setup>
import { onMounted, ref } from 'vue'
import { useClientesStore } from '../stores/clientes'
import NovoClienteForm from '../components/NovoClienteForm.vue'

const store = useClientesStore()

const termo = ref('')
const form = ref(null) // null = fechado | {} = novo | cliente = editando
let debounce = null

function buscar() {
  clearTimeout(debounce)
  debounce = setTimeout(() => store.buscar(termo.value), 300)
}

function novo() {
  form.value = {}
}

function editar(cliente) {
  form.value = cliente
}

function aoSalvar() {
  form.value = null
  store.buscar(termo.value)
}

function linhaEndereco(c) {
  return [c.endereco, [c.cidade, c.estado].filter(Boolean).join('/')].filter(Boolean).join(' — ')
}

onMounted(() => store.buscar())
</script>

<template>
  <div class="top-bar">
    <strong>Clientes</strong>
    <button
      v-if="!form"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      @click="novo"
    >
      + Novo
    </button>
  </div>

  <div class="content">
    <NovoClienteForm
      v-if="form"
      :cliente="form.id ? form : null"
      @criado="aoSalvar"
      @cancelar="form = null"
    />

    <template v-else>
      <input
        v-model="termo"
        type="search"
        placeholder="Buscar por nome, documento ou cidade"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 12px"
        @input="buscar"
      />

      <p v-if="store.carregando && !store.resultados.length">Carregando...</p>
      <p v-else-if="!store.resultados.length" style="color: var(--text-muted)">
        Nenhum cliente {{ termo ? 'para essa busca' : 'cadastrado' }}.
      </p>

      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li
          v-for="c in store.resultados"
          :key="c.id"
          class="card"
          style="cursor: pointer"
          @click="editar(c)"
        >
          <div style="display: flex; justify-content: space-between; gap: 8px">
            <strong>{{ c.nome }}</strong>
            <span style="color: var(--text-muted); font-size: 13px">{{ c.documento }}</span>
          </div>
          <div v-if="linhaEndereco(c)" style="color: var(--text-muted); font-size: 14px">
            {{ linhaEndereco(c) }}
          </div>
          <div v-if="c.telefone" style="color: var(--text-muted); font-size: 14px">
            📞 {{ c.telefone }}
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>
