<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOrdensServicoStore } from '../stores/ordensServico'
import { useAuthStore } from '../stores/auth'
import AssinaturaCanvas from '../components/AssinaturaCanvas.vue'
import RelatoOs from '../components/RelatoOs.vue'
import ModalCopiarRelato from '../components/ModalCopiarRelato.vue'

const MOTIVOS_PAUSA = [
  { valor: 'ALMOCO', rotulo: 'Almoço' },
  { valor: 'FALTA_MATERIAL', rotulo: 'Falta de material' },
  { valor: 'AGUARDANDO_CLIENTE', rotulo: 'Aguardando cliente' },
  { valor: 'OUTRO', rotulo: 'Outro' },
]

function relatoVazio() {
  return { local: '', servicos: [''], materiais: [], equipe: [], observacoes: '' }
}

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useOrdensServicoStore()
const auth = useAuthStore()
const router = useRouter()

const ordem = ref(null)
const relato = reactive(relatoVazio())
const processando = ref(false)
const erro = ref('')
const assinaturaRef = ref(null)

const enviandoFoto = ref(false)
const erroFoto = ref('')
const inputFotoRef = ref(null)

const mostrarFormPausa = ref(false)
const motivoPausa = ref('ALMOCO')
const observacaoPausa = ref('')
const erroPausa = ref('')

const mostrarCopiar = ref(false)

function aplicarRelatoCopiado(copiado) {
  const base = relatoVazio()
  Object.assign(relato, {
    local: copiado.local || '',
    servicos: Array.isArray(copiado.servicos) && copiado.servicos.length ? [...copiado.servicos] : base.servicos,
    materiais: Array.isArray(copiado.materiais) ? copiado.materiais.map((m) => ({ ...m })) : [],
    equipe: Array.isArray(copiado.equipe) && copiado.equipe.length ? [...copiado.equipe] : relato.equipe,
    observacoes: copiado.observacoes || '',
  })
}

const pausaAtual = computed(() =>
  ordem.value?.pausas?.find((p) => !p.retomada_em) || null
)

function nomeUsuario() {
  const u = auth.user
  if (!u) return ''
  return u.first_name ? `${u.first_name} ${u.last_name}`.trim() : u.username
}

async function carregar() {
  try {
    ordem.value = await store.buscar(props.id)
  } catch {
    erro.value = 'Não foi possível carregar a OS (sem conexão e sem cópia local).'
    return
  }
  if (!ordem.value) {
    erro.value = 'OS não encontrada.'
    return
  }
  const salvo = ordem.value.relato
  Object.assign(relato, relatoVazio(), salvo && typeof salvo === 'object' ? salvo : {})
  if (!relato.servicos.length) relato.servicos.push('')
  if (!relato.equipe.length && nomeUsuario()) relato.equipe.push(nomeUsuario())
}

async function iniciar() {
  processando.value = true
  try {
    ordem.value = await store.iniciar(props.id)
  } finally {
    processando.value = false
  }
}

async function pausar() {
  processando.value = true
  erroPausa.value = ''
  try {
    ordem.value = await store.pausar(props.id, {
      motivo: motivoPausa.value,
      observacao: observacaoPausa.value,
    })
    mostrarFormPausa.value = false
    observacaoPausa.value = ''
  } catch {
    erroPausa.value = 'Não foi possível pausar a OS. Verifique a conexão.'
  } finally {
    processando.value = false
  }
}

async function retomar() {
  processando.value = true
  try {
    ordem.value = await store.retomar(props.id)
  } finally {
    processando.value = false
  }
}

async function concluir() {
  processando.value = true
  erro.value = ''

  let assinatura = null
  try {
    if (assinaturaRef.value && !assinaturaRef.value.vazio()) {
      assinatura = await assinaturaRef.value.paraArquivo()
    }
  } catch (e) {
    console.error('Falha ao gerar a assinatura', e)
    erro.value = 'Não foi possível processar a assinatura. Tente assinar novamente.'
    processando.value = false
    return
  }

  try {
    ordem.value = await store.concluir(props.id, {
      relato: { ...relato },
      assinatura_cliente: assinatura,
    })
  } catch (e) {
    console.error('Falha ao concluir a OS', e)
    erro.value = e?.response?.data
      ? `Não foi possível concluir a OS: ${JSON.stringify(e.response.data)}`
      : 'Não foi possível concluir a OS. Verifique a conexão.'
  } finally {
    processando.value = false
  }
}

async function selecionarFoto(event) {
  const arquivos = Array.from(event.target.files || [])
  if (!arquivos.length) return
  enviandoFoto.value = true
  erroFoto.value = ''
  try {
    for (const arquivo of arquivos) {
      const foto = await store.adicionarFoto(props.id, arquivo)
      ordem.value.fotos.push(foto)
    }
  } catch {
    erroFoto.value = 'Não foi possível enviar a foto. Verifique a conexão e tente novamente.'
  } finally {
    enviandoFoto.value = false
    if (inputFotoRef.value) inputFotoRef.value.value = ''
  }
}

onMounted(carregar)
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong v-if="ordem">{{ ordem.numero || 'Nova OS' }}</strong>
  </div>

  <p v-if="erro && !ordem" style="padding: 16px; color: var(--danger)">{{ erro }}</p>

  <div class="content" v-if="ordem">
    <div v-if="ordem.offline" class="offline-banner" style="border-radius: 8px; margin-bottom: 12px">
      Esta OS foi criada offline e ainda não foi enviada.
    </div>
    <div class="card" style="margin-bottom: 16px">
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span class="badge" :class="`badge-${ordem.status.toLowerCase()}`">{{ ordem.status }}</span>
      </div>
      <h2 style="margin: 0 0 4px">{{ ordem.cliente_nome }}</h2>
      <p style="color: var(--text-muted); margin: 0 0 12px">{{ ordem.tipo_servico }}</p>
      <p>{{ ordem.descricao }}</p>
      <p v-if="ordem.latitude_abertura != null" style="color: var(--text-muted); font-size: 13px; margin-top: 8px">
        📍 Aberta no local do cliente
      </p>
    </div>

    <button
      v-if="ordem.status === 'ATRIBUIDA'"
      class="btn"
      style="width: 100%; margin-bottom: 16px"
      :disabled="processando"
      @click="iniciar"
    >
      Iniciar atendimento
    </button>

    <div v-if="ordem.status === 'PAUSADA'" class="card" style="margin-bottom: 16px; border-color: var(--warning)">
      <strong>OS pausada</strong>
      <p v-if="pausaAtual" style="margin: 4px 0 0; color: var(--text-muted); font-size: 14px">
        {{ pausaAtual.motivo_display }}<template v-if="pausaAtual.observacao"> — {{ pausaAtual.observacao }}</template>
        <br />
        desde {{ new Date(pausaAtual.iniciada_em).toLocaleString('pt-BR') }}
      </p>
      <button class="btn" style="width: 100%; margin-top: 12px" :disabled="processando" @click="retomar">
        Retomar atendimento
      </button>
    </div>

    <div v-if="ordem.status === 'EM_ANDAMENTO'" style="margin-bottom: 16px">
      <button
        v-if="!mostrarFormPausa"
        type="button"
        class="btn-secondary"
        style="width: 100%"
        :disabled="processando"
        @click="mostrarFormPausa = true"
      >
        Pausar OS
      </button>

      <div v-else class="card" style="display: flex; flex-direction: column; gap: 10px">
        <label>
          Motivo da pausa
          <select
            v-model="motivoPausa"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          >
            <option v-for="m in MOTIVOS_PAUSA" :key="m.valor" :value="m.valor">{{ m.rotulo }}</option>
          </select>
        </label>
        <label>
          Observação (opcional)
          <textarea
            v-model="observacaoPausa"
            rows="2"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          />
        </label>
        <p v-if="erroPausa" style="color: var(--danger); margin: 0">{{ erroPausa }}</p>
        <div style="display: flex; gap: 8px">
          <button class="btn" style="flex: 1" :disabled="processando" @click="pausar">Confirmar pausa</button>
          <button
            type="button"
            class="btn-secondary"
            :disabled="processando"
            @click="mostrarFormPausa = false"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <div v-if="['ATRIBUIDA', 'EM_ANDAMENTO', 'PAUSADA', 'CONCLUIDA'].includes(ordem.status)" class="card" style="margin-bottom: 16px">
      <h2 style="margin: 0 0 10px">Fotos</h2>

      <div
        v-if="ordem.fotos.length"
        style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px"
      >
        <a v-for="foto in ordem.fotos" :key="foto.id" :href="foto.imagem" target="_blank">
          <img :src="foto.imagem" :alt="foto.legenda" style="width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px" />
        </a>
      </div>
      <p v-else style="color: var(--text-muted); margin: 0 0 12px">Nenhuma foto enviada ainda.</p>

      <p v-if="erroFoto" style="color: var(--danger)">{{ erroFoto }}</p>

      <button
        v-if="ordem.status !== 'CONCLUIDA'"
        type="button"
        class="btn-secondary"
        :disabled="enviandoFoto"
        @click="inputFotoRef.click()"
      >
        {{ enviandoFoto ? 'Enviando...' : '+ Adicionar fotos' }}
      </button>
      <input
        ref="inputFotoRef"
        type="file"
        accept="image/*"
        multiple
        style="display: none"
        @change="selecionarFoto"
      />
    </div>

    <div v-if="ordem.status === 'EM_ANDAMENTO'" class="card" style="display: flex; flex-direction: column; gap: 16px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <h2 style="margin: 0">Relato do serviço</h2>
        <button type="button" class="btn-secondary" style="padding: 6px 12px; border-radius: 8px; font-size: 13px" @click="mostrarCopiar = true">
          Copiar de outra OS
        </button>
      </div>
      <RelatoOs :relato="relato" />

      <div>
        Assinatura do cliente
        <AssinaturaCanvas ref="assinaturaRef" style="margin-top: 4px" />
      </div>

      <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>
      <button class="btn" :disabled="processando" @click="concluir">Concluir OS</button>
    </div>

    <ModalCopiarRelato
      v-if="mostrarCopiar"
      @fechar="mostrarCopiar = false"
      @copiar="aplicarRelatoCopiado"
    />

    <div v-if="ordem.status === 'CONCLUIDA'" class="card">
      <p><strong>Concluída em:</strong> {{ new Date(ordem.data_conclusao).toLocaleString('pt-BR') }}</p>
      <div v-if="ordem.observacoes_tecnico" style="margin: 8px 0">
        <strong>Relato:</strong>
        <pre style="white-space: pre-wrap; font: inherit; margin: 4px 0 0">{{ ordem.observacoes_tecnico }}</pre>
      </div>
      <div v-if="ordem.assinatura_cliente">
        <strong>Assinatura do cliente:</strong>
        <img :src="ordem.assinatura_cliente" alt="Assinatura do cliente" style="max-width: 100%; border: 1px solid var(--border); border-radius: 8px; margin-top: 6px" />
      </div>
    </div>
  </div>
</template>
