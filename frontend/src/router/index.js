import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Views importadas estaticamente (sem code-splitting por rota). O app é
// pequeno e roda em celular com rede ruim / túnel de dev — carregar chunk sob
// demanda a cada navegação causava "Importing a module script failed" e a tela
// simplesmente não trocava. Um bundle só é mais confiável aqui.
import LoginView from '../views/LoginView.vue'
import PontoView from '../views/PontoView.vue'
import EspelhoPontoView from '../views/EspelhoPontoView.vue'
import IndicadoresView from '../views/IndicadoresView.vue'
import SolicitacoesPontoView from '../views/SolicitacoesPontoView.vue'
import NovaSolicitacaoPontoView from '../views/NovaSolicitacaoPontoView.vue'
import PainelGestorView from '../views/PainelGestorView.vue'
import OrdensServicoView from '../views/OrdensServicoView.vue'
import NovaOrdemServicoView from '../views/NovaOrdemServicoView.vue'
import OrdemServicoDetalheView from '../views/OrdemServicoDetalheView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/', name: 'ponto', component: PontoView, meta: { auth: true } },
  { path: '/ponto/espelho', name: 'espelho-ponto', component: EspelhoPontoView, meta: { auth: true } },
  { path: '/ponto/indicadores', name: 'indicadores-ponto', component: IndicadoresView, meta: { auth: true } },
  { path: '/ponto/solicitacoes', name: 'solicitacoes-ponto', component: SolicitacoesPontoView, meta: { auth: true } },
  {
    path: '/ponto/solicitacoes/nova',
    name: 'nova-solicitacao-ponto',
    component: NovaSolicitacaoPontoView,
    meta: { auth: true },
  },
  { path: '/gestor', name: 'painel-gestor', component: PainelGestorView, meta: { auth: true, gestor: true } },
  { path: '/ordens-servico', name: 'ordens-servico', component: OrdensServicoView, meta: { auth: true } },
  { path: '/ordens-servico/nova', name: 'nova-ordem-servico', component: NovaOrdemServicoView, meta: { auth: true } },
  {
    path: '/ordens-servico/:id',
    name: 'ordem-servico-detalhe',
    component: OrdemServicoDetalheView,
    meta: { auth: true },
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'ponto' }
  }
  if (to.meta.gestor && auth.user?.papel === 'TECNICO') {
    return { name: 'ponto' }
  }
})

// Rede de segurança: se ainda assim um módulo falhar ao carregar (SW velho,
// deploy no meio da navegação), recarrega a página em vez de deixar a tela
// travada sem feedback.
router.onError((erro) => {
  const msg = String(erro?.message || '')
  if (/Importing a module script failed|Failed to fetch dynamically imported module|error loading dynamically imported module/i.test(msg)) {
    window.location.reload()
  }
})

export default router
