import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const GESTAO = ['GESTOR', 'RH', 'ADMIN']
const ESTOQUE = ['GESTOR', 'ADMIN']

/**
 * Itens de navegação, agrupados e já filtrados pelo papel do usuário.
 * Usado pelo menu lateral do celular (MenuLateral) e pela barra fixa do
 * desktop (NavRail) — uma fonte só, sem risco de os dois desalinharem.
 */
export function useNavGroups() {
  const auth = useAuthStore()

  return computed(() => {
    const papel = auth.user?.papel
    const ehGestao = GESTAO.includes(papel)
    const podeEstoque = ESTOQUE.includes(papel)
    // "Bate ponto" não decorre do papel (a secretária é RH e bate; a dona é
    // gestão e não). Cache antigo do /me pode não ter o campo — assume que sim.
    const registraPonto = auth.user?.registra_ponto !== false

    const grupos = []

    if (registraPonto) {
      grupos.push({
        titulo: 'Meu ponto',
        itens: [
          { rotulo: 'Bater ponto', to: '/' },
          { rotulo: 'Meu cartão ponto', to: '/ponto/espelho' },
          { rotulo: 'Meus indicadores', to: '/ponto/indicadores' },
          ...(!ehGestao ? [{ rotulo: 'Minhas solicitações', to: '/ponto/solicitacoes' }] : []),
        ],
      })
    }

    if (ehGestao) {
      grupos.push({
        titulo: 'Gestão',
        itens: [
          { rotulo: 'Painel', to: '/gestor' },
          { rotulo: 'Ponto da equipe', to: '/gestao/ponto/espelho' },
          { rotulo: 'Indicadores da equipe', to: '/gestao/ponto/indicadores' },
          { rotulo: 'Solicitações', to: '/ponto/solicitacoes' },
          { rotulo: 'Funcionários', to: '/funcionarios' },
        ],
      })
    }

    grupos.push({
      titulo: 'Operação',
      itens: [
        { rotulo: 'Ordens de serviço', to: '/ordens-servico' },
        { rotulo: 'Obras', to: '/obras' },
        ...(podeEstoque ? [{ rotulo: 'Estoque', to: '/estoque' }] : []),
        { rotulo: 'Clientes', to: '/clientes' },
        ...(!ehGestao ? [{ rotulo: 'Meus dados', to: '/meus-dados' }] : []),
      ],
    })

    return grupos
  })
}
