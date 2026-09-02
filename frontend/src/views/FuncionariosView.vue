<script setup>
import { onMounted, ref } from 'vue'
import { useFuncionariosStore } from '../stores/funcionarios'
import FuncionarioForm from '../components/FuncionarioForm.vue'

const store = useFuncionariosStore()

const termo = ref('')
const incluirInativos = ref(false)
const form = ref(null) // null = lista | {} = novo | funcionário = editando
let debounce = null

const PAPEL_ROTULO = {
  TECNICO: 'Técnico',
  ENCARREGADO: 'Encarregado',
  GESTOR: 'Gestor',
  RH: 'RH',
  ADMIN: 'Admin',
}

function recarregar() {
  store.buscar(termo.value, incluirInativos.value)
}

function buscar() {
  clearTimeout(debounce)
  debounce = setTimeout(recarregar, 300)
}

function nomeDe(u) {
  return u.nome_completo || u.first_name || u.username
}

function aoSalvar() {
  form.value = null
  recarregar()
}

onMounted(recarregar)
</script>

<template>
  <div class="top-bar">
    <strong>{{ form ? (form.id ? 'Editar funcionário' : 'Novo funcionário') : 'Funcionários' }}</strong>
    <button
      v-if="!form"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      @click="form = {}"
    >
      + Novo
    </button>
  </div>

  <div class="content">
    <FuncionarioForm
      v-if="form"
      :funcionario="form.id ? form : null"
      @salvo="aoSalvar"
      @cancelar="form = null"
    />

    <template v-else>
      <input
        v-model="termo"
        type="search"
        placeholder="Buscar por nome, usuário, CPF ou cargo"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 10px"
        @input="buscar"
      />
      <label style="display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--text-muted); margin-bottom: 12px">
        <input v-model="incluirInativos" type="checkbox" @change="recarregar" />
        Mostrar desligados
      </label>

      <p v-if="store.carregando && !store.lista.length">Carregando...</p>
      <p v-else-if="!store.lista.length" style="color: var(--text-muted)">
        Nenhum funcionário {{ termo ? 'para essa busca' : 'cadastrado' }}.
      </p>

      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
        <li
          v-for="u in store.lista"
          :key="u.id"
          class="card"
          style="cursor: pointer"
          @click="form = u"
        >
          <div style="display: flex; justify-content: space-between; gap: 8px; align-items: baseline">
            <strong>
              {{ nomeDe(u) }}
              <span v-if="!u.is_active" style="color: var(--danger); font-size: 12px; font-weight: 400"> · desligado</span>
            </strong>
            <span class="badge" style="background: var(--border); color: var(--text)">{{ PAPEL_ROTULO[u.papel] || u.papel }}</span>
          </div>
          <div v-if="u.cargo" style="color: var(--text-muted); font-size: 14px">{{ u.cargo }}</div>
          <div v-if="u.telefone" style="color: var(--text-muted); font-size: 14px">📞 {{ u.telefone }}</div>
        </li>
      </ul>
    </template>
  </div>
</template>
