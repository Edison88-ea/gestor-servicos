<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePontoStore } from '../stores/ponto'
import { useAuthStore } from '../stores/auth'
import { dataLocalISO, formatarMinutos } from '../utils/tempo'
import SeletorFuncionario from '../components/SeletorFuncionario.vue'

// 'pessoal' = o próprio cartão, sem seletor (quem bate ponto).
// 'equipe'  = cartão de qualquer funcionário, com seletor (gestão).
const props = defineProps({ escopo: { type: String, default: 'pessoal' } })
const ehEquipe = computed(() => props.escopo === 'equipe')

const store = usePontoStore()
const auth = useAuthStore()
const router = useRouter()

function exportar() {
  window.print()
}

const hoje = new Date()
const mesReferencia = ref(new Date(hoje.getFullYear(), hoje.getMonth(), 1))
const espelho = ref(null)
const carregando = ref(false)
const erro = ref('')
const modo = ref('completo') // 'resumido' | 'completo'
const funcionarioSel = ref('') // '' = o próprio usuário (gestão pode ver outros)
const nomeFuncionario = ref('')

// Tela: dia mais recente no topo (uso diário no celular). A lista é invertida
// de fato — o DOM segue essa ordem, então leitor de tela e foco acompanham.
// Na impressão o CSS reinverte para a ordem cronológica (padrão de cartão).
// Dias futuros (fim do mês corrente) não entram: cartão de ponto só mostra o
// que já aconteceu.
const diasExibicao = computed(() =>
  espelho.value ? espelho.value.dias.filter((d) => !d.futuro).reverse() : [],
)

const nomeNoCabecalho = computed(
  () =>
    nomeFuncionario.value ||
    (auth.user?.first_name ? `${auth.user.first_name} ${auth.user.last_name}` : auth.user?.username),
)

const rotuloMes = computed(() =>
  mesReferencia.value.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
)

function formatarHora(iso) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatarData(isoData) {
  return new Date(`${isoData}T00:00:00`).toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
  })
}

function statusDia(dia) {
  if (dia.futuro) return 'futuro'
  if (dia.folga && dia.registros.length === 0) return 'ok'
  if (dia.registros.length === 0) return 'alerta'
  if (dia.falta_minutos > 0 || dia.em_aberto) return 'alerta'
  return 'ok'
}

function paresDeHorarios(registros) {
  const pares = []
  for (let i = 0; i < registros.length; i += 2) {
    const a = registros[i]
    const b = registros[i + 1]
    pares.push(`${formatarHora(a.registrado_em)} - ${b ? formatarHora(b.registrado_em) : 'X'}`)
  }
  return pares.join(' • ')
}

// Na visão da equipe não há "meu cartão" pra cair em cima — quem é gestão pode
// nem bater ponto. Sem funcionário escolhido, não busca nada.
const aguardandoFuncionario = computed(() => ehEquipe.value && !funcionarioSel.value)

async function carregarMes() {
  if (aguardandoFuncionario.value) {
    espelho.value = null
    return
  }
  carregando.value = true
  erro.value = ''
  const inicio = mesReferencia.value
  const fim = new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0)
  try {
    espelho.value = await store.buscarEspelho({
      dataInicio: dataLocalISO(inicio),
      dataFim: dataLocalISO(fim),
      funcionario: ehEquipe.value ? funcionarioSel.value : undefined,
    })
  } catch {
    erro.value = 'Não foi possível carregar o cartão de ponto.'
  } finally {
    carregando.value = false
  }
}

function mudarMes(delta) {
  mesReferencia.value = new Date(
    mesReferencia.value.getFullYear(),
    mesReferencia.value.getMonth() + delta,
    1
  )
}

watch([mesReferencia, funcionarioSel], carregarMes, { immediate: true })
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>{{ ehEquipe ? 'Ponto da Equipe' : 'Meu Cartão Ponto' }}</strong>
    <button type="button" style="border: none; background: none; color: var(--accent); font-weight: 600" @click="exportar">
      Exportar
    </button>
  </div>

  <div class="content">
    <div class="somente-impressao" style="display: none; margin-bottom: 12px">
      <strong style="font-size: 18px">{{ nomeNoCabecalho }}</strong>
      <div>Cartão Ponto — <span style="text-transform: capitalize">{{ rotuloMes }}</span></div>
    </div>

    <SeletorFuncionario
      v-if="ehEquipe"
      v-model="funcionarioSel"
      rotulo-vazio="Selecione um funcionário"
      @trocou="nomeFuncionario = $event || ''"
    />

    <p v-if="aguardandoFuncionario" class="card" style="color: var(--text-muted)">
      Escolha um funcionário para ver o cartão de ponto.
    </p>

    <template v-else>
    <div class="ocultar-impressao card" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
      <button class="btn-secondary" style="padding: 6px 12px" @click="mudarMes(-1)">‹</button>
      <strong style="text-transform: capitalize">{{ rotuloMes }}</strong>
      <button class="btn-secondary" style="padding: 6px 12px" @click="mudarMes(1)">›</button>
    </div>

    <div class="ocultar-impressao" style="display: flex; gap: 8px; margin-bottom: 16px">
      <button
        type="button"
        :class="modo === 'resumido' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="modo = 'resumido'"
      >
        Resumido
      </button>
      <button
        type="button"
        :class="modo === 'completo' ? 'btn' : 'btn-secondary'"
        style="flex: 1; padding: 8px"
        @click="modo = 'completo'"
      >
        Completo
      </button>
    </div>

    <p v-if="carregando">Carregando...</p>
    <p v-else-if="erro" style="color: var(--danger)">{{ erro }}</p>

    <template v-else-if="espelho">
      <div class="card" style="margin-bottom: 16px">
        <div style="text-align: center">
          <div style="color: var(--text-muted); font-size: 14px">Horas trabalhadas no mês</div>
          <div style="font-size: 28px; font-weight: 700">{{ formatarMinutos(espelho.total_minutos) }}</div>
        </div>
        <div style="display: flex; justify-content: space-around; margin-top: 12px; text-align: center">
          <div>
            <div style="color: var(--text-muted); font-size: 12px">Extras</div>
            <strong style="color: #0ca30c">{{ formatarMinutos(espelho.total_extra_minutos) }}</strong>
          </div>
          <div>
            <div style="color: var(--text-muted); font-size: 12px">Faltas</div>
            <strong style="color: #d03b3b">{{ formatarMinutos(espelho.total_falta_minutos) }}</strong>
          </div>
          <div>
            <div style="color: var(--text-muted); font-size: 12px">Saldo</div>
            <strong :style="{ color: espelho.saldo_minutos >= 0 ? '#0ca30c' : '#d03b3b' }">
              {{ espelho.saldo_minutos > 0 ? '+' : '' }}{{ formatarMinutos(espelho.saldo_minutos) }}
            </strong>
          </div>
        </div>
        <div
          v-if="espelho.total_noturno_minutos"
          style="text-align: center; margin-top: 8px; font-size: 12px; color: var(--text-muted)"
        >
          Noturno (22h–5h): {{ formatarMinutos(espelho.total_noturno_minutos) }}
        </div>
      </div>

      <ul class="lista-dias" style="list-style: none; padding: 0; gap: 8px">
        <li v-for="dia in diasExibicao" :key="dia.data" class="card">
          <div style="display: flex; align-items: center; gap: 8px">
            <span v-if="statusDia(dia) === 'ok'" style="color: #0ca30c; font-size: 18px">✓</span>
            <span v-else-if="statusDia(dia) === 'alerta'" style="color: #d03b3b; font-size: 18px">!</span>
            <span v-else style="color: var(--text-muted); font-size: 18px">·</span>
            <strong style="text-transform: capitalize; flex: 1">{{ formatarData(dia.data) }}</strong>
            <span v-if="!dia.futuro" :style="{ color: dia.saldo_minutos >= 0 ? '#0ca30c' : '#d03b3b', fontWeight: 600 }">
              {{ dia.saldo_minutos > 0 ? '+' : '' }}{{ formatarMinutos(dia.saldo_minutos) }}
            </span>
          </div>
          <div
            v-if="!dia.futuro && (dia.extra_minutos || dia.falta_minutos || dia.noturno_minutos)"
            style="display: flex; gap: 12px; margin-top: 4px; font-size: 13px; padding-left: 26px"
          >
            <span v-if="dia.extra_minutos" style="color: #0ca30c">Extra {{ formatarMinutos(dia.extra_minutos) }}</span>
            <span v-if="dia.falta_minutos" style="color: #d03b3b">Falta {{ formatarMinutos(dia.falta_minutos) }}</span>
            <span v-if="dia.noturno_minutos" style="color: var(--text-muted)">Not. {{ formatarMinutos(dia.noturno_minutos) }}</span>
          </div>
          <div v-if="modo === 'completo'" style="margin-top: 6px; font-size: 13px; color: var(--text-muted)">
            <span v-if="dia.futuro"></span>
            <span v-else-if="dia.folga && dia.registros.length === 0">Folga</span>
            <span v-else-if="dia.registros.length === 0">Nenhum ponto registrado</span>
            <span v-else>
              {{ paresDeHorarios(dia.registros) }}
              <span v-if="dia.em_aberto" style="color: var(--warning)"> (em aberto)</span>
            </span>
          </div>
        </li>
      </ul>
    </template>
    </template>
  </div>
</template>

<style scoped>
/* O DOM já vem com o dia mais recente primeiro (ver `diasExibicao`). Na
   impressão, um cartão de ponto é cronológico — só aí reinvertemos. */
.lista-dias {
  display: flex;
  flex-direction: column;
}
@media print {
  .lista-dias {
    flex-direction: column-reverse;
  }
}
</style>
