<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import client from '../api/client'
import { useSolicitacoesPontoStore } from '../stores/solicitacoesPonto'
import { dataLocalISO } from '../utils/tempo'

const router = useRouter()
const store = useSolicitacoesPontoStore()

const TIPOS_PONTO = [
  { valor: 'ENTRADA', rotulo: 'Entrada' },
  { valor: 'SAIDA_INTERVALO', rotulo: 'Saída p/ intervalo' },
  { valor: 'VOLTA_INTERVALO', rotulo: 'Volta do intervalo' },
  { valor: 'SAIDA', rotulo: 'Saída' },
]

const tipo = ref('AJUSTE_DIA')
const dataReferencia = ref(dataLocalISO())
const descricao = ref('')
const enviando = ref(false)
const carregandoDia = ref(false)
const erro = ref('')

// pontos do dia: [{ tipo, horario }]
const pontos = ref([])

function hhmm(iso) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

async function carregarDia() {
  if (tipo.value !== 'AJUSTE_DIA') return
  carregandoDia.value = true
  erro.value = ''
  try {
    const { data } = await client.get('/registros-ponto/', {
      params: { data_inicio: dataReferencia.value, data_fim: dataReferencia.value },
    })
    const lista = data.results ?? data
    pontos.value = lista
      .map((r) => ({ tipo: r.tipo, horario: hhmm(r.registrado_em) }))
      .sort((a, b) => a.horario.localeCompare(b.horario))
  } catch {
    erro.value = 'Não foi possível carregar os pontos do dia.'
  } finally {
    carregandoDia.value = false
  }
}

watch([tipo, dataReferencia], carregarDia, { immediate: true })

function proximoTipoSugerido() {
  const ordem = ['ENTRADA', 'SAIDA_INTERVALO', 'VOLTA_INTERVALO', 'SAIDA']
  const usados = pontos.value.map((p) => p.tipo)
  return ordem.find((t) => !usados.includes(t)) || 'ENTRADA'
}
function addPonto() {
  pontos.value.push({ tipo: proximoTipoSugerido(), horario: '' })
}
function removePonto(i) {
  pontos.value.splice(i, 1)
}

async function enviar() {
  erro.value = ''
  if (!descricao.value.trim()) {
    erro.value = 'Descreva o motivo do ajuste.'
    return
  }

  const payload = {
    tipo: tipo.value,
    data_referencia: dataReferencia.value,
    descricao: descricao.value,
  }

  if (tipo.value === 'AJUSTE_DIA') {
    const limpos = pontos.value
      .filter((p) => p.horario)
      .map((p) => ({ tipo: p.tipo, horario: p.horario }))
    if (!limpos.length) {
      erro.value = 'Adicione pelo menos um ponto (ou use "Justificar ausência").'
      return
    }
    payload.pontos_propostos = limpos
  }

  enviando.value = true
  try {
    await store.criar(payload)
    router.replace('/ponto/solicitacoes')
  } catch (e) {
    erro.value = e?.response?.data
      ? `Não foi possível enviar: ${JSON.stringify(e.response.data)}`
      : 'Não foi possível enviar. Verifique a conexão.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Ajustar Ponto</strong>
  </div>

  <div class="content">
    <p style="color: var(--text-muted); font-size: 14px; margin-top: 0">
      Use quando esqueceu de bater o ponto ou bateu errado. O ajuste passa pela aprovação da empresa.
    </p>

    <div class="card" style="display: flex; flex-direction: column; gap: 12px">
      <label>
        Tipo
        <select v-model="tipo" class="campo">
          <option value="AJUSTE_DIA">Corrigir os pontos do dia</option>
          <option value="JUSTIFICATIVA_AUSENCIA">Justificar ausência (não trabalhei)</option>
        </select>
      </label>

      <label>
        Data
        <input v-model="dataReferencia" type="date" class="campo" :max="dataLocalISO()" />
      </label>

      <template v-if="tipo === 'AJUSTE_DIA'">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px">
            <strong style="font-size: 14px">Pontos do dia</strong>
            <button type="button" class="add" @click="addPonto">+ ponto</button>
          </div>
          <p v-if="carregandoDia" style="color: var(--text-muted); font-size: 13px; margin: 0">Carregando…</p>
          <p v-else-if="!pontos.length" style="color: var(--text-muted); font-size: 13px; margin: 0">
            Nenhum ponto registrado nesse dia. Toque em <strong>+ ponto</strong> para adicionar.
          </p>
          <div v-for="(p, i) in pontos" :key="i" class="linha-ponto">
            <select v-model="p.tipo" class="campo">
              <option v-for="t in TIPOS_PONTO" :key="t.valor" :value="t.valor">{{ t.rotulo }}</option>
            </select>
            <input v-model="p.horario" type="time" class="campo" />
            <button type="button" class="rem" @click="removePonto(i)" aria-label="Remover">✕</button>
          </div>
        </div>
      </template>

      <label>
        {{ tipo === 'AJUSTE_DIA' ? 'Motivo do ajuste' : 'Motivo da ausência' }}
        <textarea v-model="descricao" rows="3" class="campo" placeholder="Ex.: esqueci de bater a saída para o almoço" />
      </label>

      <p v-if="erro" style="color: var(--danger); margin: 0">{{ erro }}</p>
      <button class="btn" :disabled="enviando" @click="enviar">
        {{ enviando ? 'Enviando…' : 'Enviar' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.campo {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  margin-top: 4px;
}
.linha-ponto {
  display: grid;
  grid-template-columns: 1fr 110px auto;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}
.linha-ponto .campo {
  margin-top: 0;
}
.add {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--accent);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 600;
}
.rem {
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 16px;
  padding: 6px 4px;
}
</style>
