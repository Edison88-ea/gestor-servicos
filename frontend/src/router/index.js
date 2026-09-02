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
import FuncionariosView from '../views/FuncionariosView.vue'
import MeusDadosView from '../views/MeusDadosView.vue'
import OrdensServicoView from '../views/OrdensServicoView.vue'
import NovaOrdemServicoView from '../views/NovaOrdemServicoView.vue'
import OrdemServicoDetalheView from '../views/OrdemServicoDetalheView.vue'
import ComprovanteOsView from '../views/ComprovanteOsView.vue'
import ClientesView from '../views/ClientesView.vue'
import ObrasView from '../views/ObrasView.vue'
import NovaObraView from '../views/NovaObraView.vue'
import ObraDetalheView from '../views/ObraDetalheView.vue'
import ObraEtapasView from '../views/ObraEtapasView.vue'
import RelatorioObraView from '../views/RelatorioObraView.vue'

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
  { path: '/funcionarios', name: 'funcionarios', component: FuncionariosView, meta: { auth: true, gestor: true } },
  { path: '/meus-dados', name: 'meus-dados', component: MeusDadosView, meta: { auth: true } },
  { path: '/clientes', name: 'clientes', component: ClientesView, meta: { auth: true } },
  { path: '/ordens-servico', name: 'ordens-servico', component: OrdensServicoView, meta: { auth: true } },
  { path: '/ordens-servico/nova', name: 'nova-ordem-servico', component: NovaOrdemServicoView, meta: { auth: true } },
  {
    path: '/ordens-servico/:id/comprovante',
    name: 'comprovante-os',
    component: ComprovanteOsView,
    meta: { auth: true },
    props: true,
  },
  {
    path: '/ordens-servico/:id',
    name: 'ordem-servico-detalhe',
    component: OrdemServicoDetalheView,
    meta: { auth: true },
    props: true,
  },
  { path: '/obras', name: 'obras', component: ObrasView, meta: { auth: true } },
  { path: '/obras/nova', name: 'nova-obra', component: NovaObraView, meta: { auth: true, obra: true } },
  {
    path: '/obras/:id/etapas',
    name: 'obra-etapas',
    component: ObraEtapasView,
    meta: { auth: true, obra: true },
    props: true,
  },
  {
    path: '/obras/:id/relatorio',
    name: 'obra-relatorio',
    component: RelatorioObraView,
    meta: { auth: true },
    props: true,
  },
  {
    path: '/obras/:id',
    name: 'obra-detalhe',
    component: ObraDetalheView,
    meta: { auth: true },
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const PAPEIS_GESTAO = ['GESTOR', 'RH', 'ADMIN']
const PAPEIS_OBRA = ['ENCARREGADO', 'GESTOR', 'ADMIN']

// Gestão (RH/gestor/dono) não bate ponto — a home deles é o Painel.
const paginaInicial = (papel) =>
  PAPEIS_GESTAO.includes(papel) ? { name: 'painel-gestor' } : { name: 'ponto' }

router.beforeEach((to) => {
  const auth = useAuthStore()
  const papel = auth.user?.papel
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return paginaInicial(papel)
  }
  if (to.name === 'ponto' && PAPEIS_GESTAO.includes(papel)) {
    return { name: 'painel-gestor' }
  }
  if (to.meta.gestor && !PAPEIS_GESTAO.includes(papel)) {
    return { name: 'ponto' }
  }
  if (to.meta.obra && !PAPEIS_OBRA.includes(papel)) {
    return paginaInicial(papel)
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
