<script setup>
import { computed, onMounted, ref } from 'vue'
import { usePontoStore } from '../stores/ponto'
import { useAuthStore } from '../stores/auth'
import MapaLocalizacao from '../components/MapaLocalizacao.vue'

const ponto = usePontoStore()
const auth = useAuthStore()
const registrando = ref(false)
const registrosCarregados = ref(false)
const mensagem = ref('')
const mensagemErro = ref(false)
const justificativa = ref('')
const localizacaoAtual = ref({})

const tipos = [
  { valor: 'ENTRADA', rotulo: 'Entrada' },
  { valor: 'SAIDA_INTERVALO', rotulo: 'Saída Intervalo' },
  { valor: 'VOLTA_INTERVALO', rotulo: 'Volta Intervalo' },
  { valor: 'SAIDA', rotulo: 'Saída' },
]

// A partir do último ponto do dia, o que faz sentido bater em seguida.
const TRANSICOES = {
  '': ['ENTRADA'],
  ENTRADA: ['SAIDA_INTERVALO', 'SAIDA'],
  SAIDA_INTERVALO: ['VOLTA_INTERVALO'],
  VOLTA_INTERVALO: ['SAIDA_INTERVALO', 'SAIDA'],
  SAIDA: ['ENTRADA'],
}

const GUARDA_JORNADA_MS = 24 * 60 * 60 * 1000

// Estado atual da sequência de ponto, considerando batidas de ontem+hoje e a
// fila offline. Uma jornada pode ter virado a noite (Entrada ontem, Saída hoje);
// mas se ficou aberta 24h+ é Saída esquecida e o estado volta a "" (Entrada).
const ultimoTipo = computed(() => {
  const todos = [...ponto.registrosRecentes, ...ponto.filaOffline]
    .filter((r) => r.registrado_em)
    .slice()
    .sort((a, b) => new Date(a.registrado_em) - new Date(b.registrado_em))

  let anterior = ''
  let inicioJornada = null
  for (const r of todos) {
    const quando = new Date(r.registrado_em)
    if (inicioJornada && quando - inicioJornada >= GUARDA_JORNADA_MS) {
      anterior = ''
      inicioJornada = null
    }
    if (r.tipo === 'ENTRADA') inicioJornada = quando
    else if (r.tipo === 'SAIDA') inicioJornada = null
    anterior = r.tipo
  }
  // jornada ainda aberta há 24h+ agora = Saída esquecida
  if (inicioJornada && Date.now() - inicioJornada >= GUARDA_JORNADA_MS) return ''
  return anterior
})

const tiposPermitidos = computed(() => TRANSICOES[ultimoTipo.value] || [])
const proximoTipo = computed(() => tiposPermitidos.value[0] || 'ENTRADA')

function aoAtualizarLocalizacao(dados) {
  localizacaoAtual.value = dados
}

async function bater(tipo) {
  registrando.value = true
  mensagem.value = ''
  mensagemErro.value = false
  try {
    const resultado = await ponto.registrarPonto(tipo, {
      ...localizacaoAtual.value,
      justificativa: justificativa.value,
    })
    justificativa.value = ''
    mensagem.value =
      resultado === 'enviado'
        ? 'Ponto registrado!'
        : 'Ponto guardado — será enviado automaticamente assim que houver conexão.'
  } catch (e) {
    const detalhe = e?.response?.data
    mensagemErro.value = true
    mensagem.value =
      detalhe?.tipo?.[0] || detalhe?.detail || 'Não foi possível registrar. Tente novamente.'
  } finally {
    registrando.value = false
  }
}

onMounted(async () => {
  if (navigator.onLine) {
    try {
      await ponto.carregarRegistrosHoje()
      registrosCarregados.value = true
    } catch {
      // fica sem trava de sequência; o backend valida no envio
    }
  }
})
</script>

<template>
  <div class="top-bar">
    <strong>Olá, {{ auth.user?.first_name || auth.user?.username }}</strong>
    <button class="btn-secondary" style="border: none; background: none; color: var(--text-muted)"
      @click="auth.logout(); $router.push('/login')">Sair</button>
  </div>

  <div class="content">
    <h2>Bater ponto</h2>

    <div class="card" style="margin-bottom: 16px">
      <MapaLocalizacao @atualizacao="aoAtualizarLocalizacao" />
    </div>

    <p
      v-if="mensagem"
      :style="{
        padding: '10px 12px',
        borderRadius: '8px',
        marginBottom: '12px',
        fontWeight: 600,
        background: mensagemErro ? 'var(--danger)' : 'var(--success)',
        color: 'white',
      }"
    >
      {{ mensagem }}
    </p>

    <div class="card" style="display: grid; gap: 10px; margin-bottom: 16px">
      <button
        v-for="t in tipos"
        :key="t.valor"
        class="btn"
        :class="{ 'btn-secondary': t.valor !== proximoTipo }"
        :disabled="registrando || (registrosCarregados && !tiposPermitidos.includes(t.valor))"
        @click="bater(t.valor)"
      >
        {{ t.rotulo }}
      </button>

      <p v-if="registrosCarregados && proximoTipo" style="color: var(--text-muted); font-size: 13px; margin: 0">
        Próxima batida esperada: <strong>{{ tipos.find((t) => t.valor === proximoTipo)?.rotulo }}</strong>
      </p>

      <textarea
        v-model="justificativa"
        placeholder="Justificativa (opcional)"
        rows="2"
        style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border)"
      />
    </div>

    <h2>Registros de hoje</h2>
    <div v-if="ponto.registrosHoje.length === 0" class="card">Nenhum registro ainda.</div>
    <ul v-else style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px">
      <li v-for="r in ponto.registrosHoje" :key="r.id" class="card">
        <div style="display: flex; justify-content: space-between">
          <span>{{ tipos.find((t) => t.valor === r.tipo)?.rotulo }}</span>
          <span>{{ new Date(r.registrado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) }}</span>
        </div>
        <div v-if="r.endereco" style="color: var(--text-muted); font-size: 13px; margin-top: 4px">📍 {{ r.endereco }}</div>
      </li>
    </ul>

    <p v-if="ponto.filaOffline.length" style="color: var(--warning)">
      {{ ponto.filaOffline.length }} registro(s) aguardando sincronização.
    </p>

    <div
      v-if="ponto.rejeitados.length"
      class="card"
      style="border-left: 4px solid var(--danger); margin-top: 8px"
    >
      <strong>Batidas recusadas pelo servidor</strong>
      <p style="color: var(--text-muted); font-size: 13px; margin: 4px 0 10px">
        Estas batidas não foram registradas. Tente enviar de novo; se continuar
        recusando, abra uma solicitação de ajuste para o gestor.
      </p>
      <ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 10px">
        <li v-for="(r, i) in ponto.rejeitados" :key="i" style="border-top: 1px solid var(--border); padding-top: 8px">
          <div style="display: flex; justify-content: space-between">
            <span>{{ tipos.find((t) => t.valor === r.tipo)?.rotulo }}</span>
            <span>{{ new Date(r.registrado_em).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
          <div style="color: var(--danger); font-size: 13px; margin-top: 2px">{{ r.motivo }}</div>
          <div style="display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap">
            <button
              class="btn"
              style="flex: 1; font-size: 13px; min-width: 110px"
              :disabled="ponto.sincronizando"
              @click="ponto.reenviarRejeitado(i)"
            >
              Tentar de novo
            </button>
            <RouterLink
              to="/ponto/solicitacoes/nova"
              class="btn-secondary"
              style="flex: 1; text-align: center; text-decoration: none; font-size: 13px; min-width: 110px"
            >
              Abrir ajuste
            </RouterLink>
            <button
              class="btn-secondary"
              style="flex: 1; font-size: 13px; min-width: 90px"
              @click="ponto.descartarRejeitado(i)"
            >
              Descartar
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div style="display: flex; gap: 8px; margin-top: 16px">
      <RouterLink to="/ponto/indicadores" class="btn-secondary" style="flex: 1; display: block; text-align: center; text-decoration: none">
        Indicadores
      </RouterLink>
      <RouterLink to="/ponto/espelho" class="btn-secondary" style="flex: 1; display: block; text-align: center; text-decoration: none">
        Cartão Ponto
      </RouterLink>
    </div>
    <RouterLink to="/ponto/solicitacoes" class="btn-secondary" style="display: block; text-align: center; text-decoration: none; margin-top: 8px">
      Solicitações
    </RouterLink>
  </div>
</template>
