<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFuncionariosStore } from '../stores/funcionarios'
import FuncionarioForm from '../components/FuncionarioForm.vue'

const router = useRouter()
const store = useFuncionariosStore()

const dados = ref(null)
const erro = ref('')

onMounted(async () => {
  try {
    dados.value = await store.meusDados()
  } catch {
    erro.value = 'Não foi possível carregar seus dados.'
  }
})

function sair() {
  if (window.history.state?.back != null) router.back()
  else router.push('/')
}
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="sair">← Voltar</button>
    <strong>Meus dados</strong>
  </div>

  <div class="content">
    <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>
    <p v-else-if="!dados" style="color: var(--text-muted)">Carregando...</p>
    <template v-else>
      <p style="color: var(--text-muted); font-size: 13px; margin-top: 0">
        Para corrigir qualquer informação, fale com o RH.
      </p>
      <FuncionarioForm :funcionario="dados" somente-leitura @cancelar="sair" />
    </template>
  </div>
</template>
