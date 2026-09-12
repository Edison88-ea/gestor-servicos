<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { usePontoStore } from './stores/ponto'
import { useNotificacoesStore } from './stores/notificacoes'
import { useClientesStore } from './stores/clientes'
import { useOrdensServicoStore } from './stores/ordensServico'
import { useSincronizacaoStore } from './stores/sincronizacao'
import MenuLateral from './components/MenuLateral.vue'
import NavRail from './components/NavRail.vue'
import PainelNotificacoes from './components/PainelNotificacoes.vue'
import PwaAtualizacao from './components/PwaAtualizacao.vue'
import Logo3D from './components/Logo3D.vue'

const auth = useAuthStore()
const ponto = usePontoStore()
const notificacoes = useNotificacoesStore()
const clientes = useClientesStore()
const ordens = useOrdensServicoStore()
// Gatilhos e status agregado das três filas offline (ver stores/sincronizacao.js)
const sinc = useSincronizacaoStore()
const online = ref(navigator.onLine)
const menuAberto = ref(false)
const notificacoesAbertas = ref(false)
const ehGestao = computed(() => ['GESTOR', 'RH', 'ADMIN'].includes(auth.user?.papel))

const route = useRoute()
const router = useRouter()
const ROTAS_RAIZ = ['ponto', 'painel-gestor', 'login']
const podeVoltar = computed(
  () => auth.isAuthenticated && !!route.name && !ROTAS_RAIZ.includes(route.name),
)
function voltar() {
  if (window.history.state?.back != null) router.back()
  else router.push({ name: ehGestao.value ? 'painel-gestor' : 'ponto' })
}
let intervaloNotificacoes = null
let intervaloSincronizacao = null

// O ciclo em si (ordem clientes → OS → ponto e trava contra sobreposição) vive
// na store de sincronização, para o botão "Tentar agora" da tela Pendências
// disparar exatamente o mesmo ciclo, com a mesma trava.
const sincronizarTudo = () => sinc.sincronizarTudo()

function atualizarStatusRede() {
  online.value = navigator.onLine
  if (online.value) sincronizarTudo()
}

// O evento 'online' do navegador é pouco confiável no celular (dispara quando a
// interface de rede sobe, não quando há internet de fato). Então também
// tentamos sincronizar quando o app volta ao primeiro plano e num intervalo
// fixo — assim uma batida offline não fica presa se o 'online' não disparar.
function aoVoltarAoPrimeiroPlano() {
  if (document.visibilityState === 'visible') sincronizarTudo()
}

function pararPollNotificacoes() {
  if (intervaloNotificacoes) {
    clearInterval(intervaloNotificacoes)
    intervaloNotificacoes = null
  }
  if (intervaloSincronizacao) {
    clearInterval(intervaloSincronizacao)
    intervaloSincronizacao = null
  }
}

function iniciarPollNotificacoes() {
  if (intervaloNotificacoes) return
  notificacoes.atualizarContagem()
  intervaloNotificacoes = setInterval(() => {
    notificacoes.atualizarContagem()
  }, 60000)
  intervaloSincronizacao = setInterval(sincronizarTudo, 20000)
}

onMounted(() => {
  window.addEventListener('online', atualizarStatusRede)
  window.addEventListener('offline', atualizarStatusRede)
  document.addEventListener('visibilitychange', aoVoltarAoPrimeiroPlano)
})

// Liga/desliga o poll de notificações conforme o login, sem depender de reload.
watch(
  () => auth.isAuthenticated,
  async (autenticado) => {
    if (autenticado) {
      // iniciarStores() nunca rejeita: o `iniciar()` de cada store contém a
      // própria falha e fica não-iniciada (o ciclo de sincronização tenta de
      // novo). Assim uma falha de leitura do IndexedDB não pode mais impedir
      // o sincronizarTudo() e o poll de notificações desta sessão.
      await sinc.iniciarStores()
      sincronizarTudo()
      if (navigator.onLine) {
        auth.atualizarPerfil()
        // Aquece o cache para trabalhar offline depois: perfil, clientes,
        // ponto recente e a lista de OS.
        clientes.carregarTodosParaCache()
        ponto.carregarRegistrosHoje().catch(() => {})
        ordens.carregar().catch(() => {})
      }
      iniciarPollNotificacoes()
    } else {
      pararPollNotificacoes()
      notificacoes.naoLidas = 0
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('online', atualizarStatusRede)
  window.removeEventListener('offline', atualizarStatusRede)
  document.removeEventListener('visibilitychange', aoVoltarAoPrimeiroPlano)
  pararPollNotificacoes()
})
</script>

<template>
  <NavRail v-if="auth.isAuthenticated" @abrir-notificacoes="notificacoesAbertas = true" />

  <div class="main">
  <div v-if="auth.isAuthenticated" class="app-header">
    <button v-if="podeVoltar" type="button" aria-label="Voltar" style="border: none; background: none; font-size: 22px; padding: 4px 6px" @click="voltar">←</button>
    <button type="button" class="btn-menu" aria-label="Menu" style="border: none; background: none; font-size: 20px; padding: 4px 6px" @click="menuAberto = true">☰</button>
    <Logo3D :tamanho="22" />
    <strong style="font-size: 14px; flex: 1">3D Sistemas</strong>
    <button
      type="button"
      style="border: none; background: none; font-size: 20px; padding: 4px 6px; position: relative"
      @click="notificacoesAbertas = true"
    >
      🔔
      <span
        v-if="notificacoes.naoLidas > 0"
        style="position: absolute; top: 0; right: 0; background: var(--danger); color: white; border-radius: 999px; font-size: 10px; min-width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; padding: 0 3px"
      >
        {{ notificacoes.naoLidas > 9 ? '9+' : notificacoes.naoLidas }}
      </span>
    </button>
  </div>

  <div v-if="!online" class="offline-banner">
    Sem conexão — o que você fizer será enviado quando o sinal voltar
    <template v-if="sinc.pendentes">
      ({{ sinc.pendentes }} pendente(s))
    </template>
  </div>
  <RouterLink
    v-else-if="sinc.temErro"
    to="/pendencias"
    class="offline-banner"
    style="background: var(--danger); display: block; text-decoration: none; color: inherit"
  >
    Alguns envios falharam — toque para ver
  </RouterLink>
  <div
    v-else-if="sinc.sincronizandoAlgo"
    class="offline-banner"
    style="background: var(--accent)"
  >
    Sincronizando…
  </div>
  <RouterLink
    v-else-if="sinc.pendentes"
    to="/pendencias"
    class="offline-banner"
    style="background: var(--accent); display: block; text-decoration: none; color: inherit; cursor: pointer"
  >
    {{ sinc.pendentes }} item(ns) aguardando envio — toque pra ver ou tentar agora
  </RouterLink>

  <RouterView />

  <nav v-if="auth.isAuthenticated" class="bottom-nav">
    <RouterLink v-if="ehGestao" to="/gestor">Painel</RouterLink>
    <RouterLink v-else to="/">Ponto</RouterLink>
    <RouterLink to="/ordens-servico">Ordens de Serviço</RouterLink>
  </nav>
  </div>

  <MenuLateral :aberto="menuAberto" @fechar="menuAberto = false" />
  <PainelNotificacoes v-if="auth.isAuthenticated" :aberto="notificacoesAbertas" @fechar="notificacoesAbertas = false" />
  <PwaAtualizacao />
</template>
