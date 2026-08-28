<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Logo3D from './Logo3D.vue'

defineProps({ aberto: { type: Boolean, default: false } })
const emit = defineEmits(['fechar'])

const auth = useAuthStore()
const router = useRouter()

function formatarHora(valor) {
  return valor ? valor.slice(0, 5) : null
}

function irPara(rota) {
  emit('fechar')
  router.push(rota)
}

function sair() {
  emit('fechar')
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div v-if="aberto" style="position: fixed; inset: 0; z-index: 2000">
    <div style="position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5)" @click="emit('fechar')" />

    <div
      style="position: absolute; top: 0; left: 0; bottom: 0; width: 85%; max-width: 320px; background: var(--surface); overflow-y: auto; box-shadow: 4px 0 16px rgba(0,0,0,0.2); padding-bottom: env(safe-area-inset-bottom)"
    >
      <div style="padding: 20px 16px; padding-top: calc(20px + env(safe-area-inset-top)); border-bottom: 1px solid var(--border)">
        <div style="display: flex; align-items: center; gap: 10px">
          <Logo3D :tamanho="36" />
          <strong style="font-size: 20px">3D Sistemas</strong>
        </div>
        <span
          style="display: inline-block; margin-top: 8px; padding: 3px 10px; border-radius: 999px; background: var(--accent); color: white; font-size: 12px; font-weight: 600"
        >
          Portal do Funcionário
        </span>
      </div>

      <div style="padding: 16px; border-bottom: 1px solid var(--border)">
        <strong style="display: block; font-size: 17px">
          {{ auth.user?.first_name ? `${auth.user.first_name} ${auth.user.last_name}` : auth.user?.username }}
        </strong>
        <span v-if="auth.user?.cargo" style="color: var(--text-muted); font-size: 14px; display: block">{{ auth.user.cargo }}</span>
        <span v-if="auth.user?.periodo1_inicio" style="color: var(--text-muted); font-size: 13px; display: block; margin-top: 4px">
          Período 1: {{ formatarHora(auth.user.periodo1_inicio) }} - {{ formatarHora(auth.user.periodo1_fim) }}
        </span>
        <span v-if="auth.user?.periodo2_inicio" style="color: var(--text-muted); font-size: 13px; display: block">
          Período 2: {{ formatarHora(auth.user.periodo2_inicio) }} - {{ formatarHora(auth.user.periodo2_fim) }}
        </span>
      </div>

      <nav style="padding: 8px 0; display: flex; flex-direction: column">
        <button v-if="auth.user?.papel !== 'TECNICO'" type="button" class="item-menu" @click="irPara('/gestor')">Painel</button>
        <button type="button" class="item-menu" @click="irPara('/')">Bater Ponto</button>
        <button type="button" class="item-menu" @click="irPara('/ponto/indicadores')">Indicadores</button>
        <button type="button" class="item-menu" @click="irPara('/ponto/espelho')">Cartão Ponto</button>
        <button type="button" class="item-menu" @click="irPara('/ponto/solicitacoes')">Solicitações</button>
        <button type="button" class="item-menu" @click="irPara('/ordens-servico')">Ordens de Serviço</button>
      </nav>

      <div style="border-top: 1px solid var(--border); padding: 8px 0">
        <button type="button" class="item-menu" style="color: var(--danger)" @click="sair">Sair</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.item-menu {
  text-align: left;
  background: none;
  border: none;
  padding: 14px 16px;
  font-size: 15px;
  color: var(--text);
  width: 100%;
}
.item-menu:active {
  background: var(--bg);
}
</style>
