<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const erro = ref('')
const carregando = ref(false)

async function entrar() {
  erro.value = ''
  carregando.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch {
    erro.value = 'Usuário ou senha inválidos.'
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <div class="content" style="display: flex; align-items: center; min-height: 100svh">
    <form class="card" style="width: 100%; display: flex; flex-direction: column; gap: 12px" @submit.prevent="entrar">
      <h2 style="margin: 0 0 8px">Gestor de Serviços</h2>
      <input v-model="username" placeholder="Usuário" autocomplete="username" required
        style="padding: 12px; border-radius: 8px; border: 1px solid var(--border)" />
      <input v-model="password" type="password" placeholder="Senha" autocomplete="current-password" required
        style="padding: 12px; border-radius: 8px; border: 1px solid var(--border)" />
      <p v-if="erro" style="color: var(--danger); margin: 0">{{ erro }}</p>
      <button class="btn" type="submit" :disabled="carregando">
        {{ carregando ? 'Entrando...' : 'Entrar' }}
      </button>
    </form>
  </div>
</template>
