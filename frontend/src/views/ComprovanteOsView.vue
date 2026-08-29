<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOrdensServicoStore } from '../stores/ordensServico'
import { formatarMinutos } from '../utils/tempo'

// Nome que aparece no cabeçalho do comprovante. Trocar pelo nome da empresa.
const EMPRESA = 'Gestor de Serviços'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useOrdensServicoStore()
const router = useRouter()

const ordem = ref(null)
const erro = ref('')
const imprimindo = ref(false)

const STATUS_ROTULO = {
  ABERTA: 'Aberta',
  ATRIBUIDA: 'Atribuída',
  EM_ANDAMENTO: 'Em andamento',
  PAUSADA: 'Pausada',
  CONCLUIDA: 'Concluída',
  CANCELADA: 'Cancelada',
}
const PRIORIDADE_ROTULO = { BAIXA: 'Baixa', MEDIA: 'Média', ALTA: 'Alta', URGENTE: 'Urgente' }

function dataHora(iso) {
  return iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

const totalPausasMin = computed(() => {
  const pausas = ordem.value?.pausas || []
  let ms = 0
  for (const p of pausas) {
    if (p.iniciada_em && p.retomada_em) {
      ms += new Date(p.retomada_em) - new Date(p.iniciada_em)
    }
  }
  return Math.round(ms / 60000)
})

const tempoTrabalhadoMin = computed(() => {
  const o = ordem.value
  if (!o?.data_inicio || !o?.data_conclusao) return null
  const bruto = Math.round((new Date(o.data_conclusao) - new Date(o.data_inicio)) / 60000)
  return Math.max(bruto - totalPausasMin.value, 0)
})

const relatoLinhas = computed(() => (ordem.value?.observacoes_tecnico || '').split('\n'))

const checklistFeito = computed(() =>
  (ordem.value?.checklist || []).filter((i) => i && typeof i === 'object'),
)

const enderecoCliente = computed(() => {
  const c = ordem.value?.cliente_detalhe
  if (!c) return ''
  return [c.endereco, [c.cidade, c.estado].filter(Boolean).join('/')].filter(Boolean).join(' - ')
})

async function carregar() {
  try {
    ordem.value = await store.buscar(props.id)
    if (!ordem.value) erro.value = 'OS não encontrada.'
  } catch {
    erro.value = 'Não foi possível carregar a OS.'
  }
}

async function imprimir() {
  imprimindo.value = true
  // Espera as imagens (fotos/assinatura) baixarem, senão o PDF sai sem elas.
  const imgs = Array.from(document.querySelectorAll('.comprovante img'))
  await Promise.all(
    imgs.map((img) =>
      img.complete
        ? null
        : new Promise((resolve) => {
            img.onload = img.onerror = resolve
          }),
    ),
  )
  imprimindo.value = false
  window.print()
}

onMounted(carregar)
</script>

<template>
  <div class="top-bar ocultar-impressao">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Comprovante</strong>
    <button
      v-if="ordem"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      :disabled="imprimindo"
      @click="imprimir"
    >
      {{ imprimindo ? 'Preparando...' : 'Imprimir / PDF' }}
    </button>
  </div>

  <p v-if="erro" style="padding: 16px; color: var(--danger)">{{ erro }}</p>

  <div v-else-if="ordem" class="content comprovante">
    <header style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px">
      <div>
        <div style="font-size: 18px; font-weight: 700">{{ EMPRESA }}</div>
        <div style="color: var(--text-muted); font-size: 13px">Comprovante de Atendimento</div>
      </div>
      <div style="text-align: right">
        <div style="font-size: 20px; font-weight: 700">{{ ordem.numero }}</div>
        <div style="color: var(--text-muted); font-size: 13px">{{ STATUS_ROTULO[ordem.status] || ordem.status }}</div>
      </div>
    </header>

    <section class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Cliente</h3>
      <div style="font-weight: 600">{{ ordem.cliente_nome }}</div>
      <div v-if="ordem.cliente_detalhe?.documento" style="font-size: 14px">
        CPF/CNPJ: {{ ordem.cliente_detalhe.documento }}
      </div>
      <div v-if="enderecoCliente" style="font-size: 14px">{{ enderecoCliente }}</div>
      <div v-if="ordem.cliente_detalhe?.telefone" style="font-size: 14px">
        Tel.: {{ ordem.cliente_detalhe.telefone }}
      </div>
    </section>

    <section class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Atendimento</h3>
      <dl style="display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 0; font-size: 14px">
        <dt style="color: var(--text-muted)">Tipo de serviço</dt><dd style="margin: 0">{{ ordem.tipo_servico }}</dd>
        <dt style="color: var(--text-muted)">Prioridade</dt><dd style="margin: 0">{{ PRIORIDADE_ROTULO[ordem.prioridade] || ordem.prioridade }}</dd>
        <dt style="color: var(--text-muted)">Técnico</dt><dd style="margin: 0">{{ ordem.tecnico_nome || '—' }}</dd>
        <dt style="color: var(--text-muted)">Aberta em</dt><dd style="margin: 0">{{ dataHora(ordem.criado_em) }}</dd>
        <dt v-if="ordem.data_agendada" style="color: var(--text-muted)">Agendada para</dt>
        <dd v-if="ordem.data_agendada" style="margin: 0">{{ dataHora(ordem.data_agendada) }}</dd>
        <dt style="color: var(--text-muted)">Início</dt><dd style="margin: 0">{{ dataHora(ordem.data_inicio) }}</dd>
        <dt style="color: var(--text-muted)">Conclusão</dt><dd style="margin: 0">{{ dataHora(ordem.data_conclusao) }}</dd>
        <template v-if="tempoTrabalhadoMin != null">
          <dt style="color: var(--text-muted)">Tempo trabalhado</dt>
          <dd style="margin: 0">
            {{ formatarMinutos(tempoTrabalhadoMin) }}
            <span v-if="totalPausasMin > 0" style="color: var(--text-muted)">
              (pausas: {{ formatarMinutos(totalPausasMin) }})
            </span>
          </dd>
        </template>
      </dl>
      <p v-if="ordem.descricao" style="margin: 10px 0 0; font-size: 14px">
        <span style="color: var(--text-muted)">Descrição: </span>{{ ordem.descricao }}
      </p>
      <p v-if="ordem.latitude_abertura != null" style="margin: 8px 0 0; font-size: 13px; color: var(--text-muted)">
        📍 Aberta no local do cliente ({{ ordem.latitude_abertura }}, {{ ordem.longitude_abertura }})
      </p>
    </section>

    <section v-if="ordem.pausas?.length" class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Pausas</h3>
      <ul style="margin: 0; padding-left: 18px; font-size: 14px">
        <li v-for="p in ordem.pausas" :key="p.id">
          {{ p.motivo_display }} — {{ dataHora(p.iniciada_em) }}
          <template v-if="p.retomada_em"> até {{ dataHora(p.retomada_em) }}</template>
          <template v-else> (não retomada)</template>
          <template v-if="p.observacao"> · {{ p.observacao }}</template>
        </li>
      </ul>
    </section>

    <section v-if="ordem.observacoes_tecnico" class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Relato do serviço</h3>
      <p v-for="(linha, i) in relatoLinhas" :key="i" style="margin: 0 0 2px; font-size: 14px; min-height: 1em">
        {{ linha }}
      </p>
    </section>

    <section v-if="checklistFeito.length" class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Checklist</h3>
      <ul style="margin: 0; padding-left: 18px; font-size: 14px">
        <li v-for="(item, i) in checklistFeito" :key="i">
          {{ item.feito || item.ok || item.concluido ? '☑' : '☐' }} {{ item.texto || item.descricao || item.item }}
        </li>
      </ul>
    </section>

    <section v-if="ordem.fotos?.length" class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Fotos ({{ ordem.fotos.length }})</h3>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px">
        <figure v-for="foto in ordem.fotos" :key="foto.id" style="margin: 0; break-inside: avoid">
          <img
            :src="foto.imagem"
            :alt="foto.legenda"
            style="width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 6px; border: 1px solid var(--border)"
          />
          <figcaption v-if="foto.legenda" style="font-size: 12px; color: var(--text-muted)">
            {{ foto.legenda }}
          </figcaption>
        </figure>
      </div>
    </section>

    <section v-if="ordem.assinatura_cliente" class="card" style="margin-bottom: 12px; break-inside: avoid">
      <h3 style="margin: 0 0 8px">Assinatura do cliente</h3>
      <img
        :src="ordem.assinatura_cliente"
        alt="Assinatura do cliente"
        style="max-width: 280px; border: 1px solid var(--border); border-radius: 6px"
      />
    </section>

    <footer style="margin-top: 16px; font-size: 12px; color: var(--text-muted)">
      Emitido em {{ dataHora(new Date().toISOString()) }}
      <span v-if="ordem.criado_por_nome"> · OS aberta por {{ ordem.criado_por_nome }}</span>
    </footer>
  </div>
</template>
