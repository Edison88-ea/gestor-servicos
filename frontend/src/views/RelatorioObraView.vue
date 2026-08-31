<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useObrasStore } from '../stores/obras'

const EMPRESA = '3D Sistemas'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useObrasStore()
const router = useRouter()

const obra = ref(null)
const opcoes = ref(null)
const erro = ref('')
const imprimindo = ref(false)

const STATUS_ROTULO = {
  PLANEJADO: 'Planejado',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDO: 'Concluído',
  CANCELADO: 'Cancelado',
}

const areasRotulos = computed(() => {
  if (!obra.value || !opcoes.value) return []
  const mapa = Object.fromEntries(opcoes.value.areas_afetadas.map((a) => [a.valor, a.rotulo]))
  return (obra.value.areas_afetadas || []).map((c) => mapa[c] || c)
})

function data(iso) {
  return iso ? new Date(iso + 'T00:00:00').toLocaleDateString('pt-BR') : '—'
}

function dataHora(iso) {
  return iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

async function carregar() {
  try {
    opcoes.value = await store.carregarOpcoes()
    obra.value = await store.buscar(props.id)
  } catch {
    erro.value = 'Não foi possível carregar a obra.'
  }
}

async function imprimir() {
  imprimindo.value = true
  const imgs = Array.from(document.querySelectorAll('.relatorio img'))
  await Promise.all(
    imgs.map((img) =>
      img.complete ? null : new Promise((r) => { img.onload = img.onerror = r }),
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
    <strong>Relatório</strong>
    <button
      v-if="obra"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      :disabled="imprimindo"
      @click="imprimir"
    >
      {{ imprimindo ? 'Preparando...' : 'Imprimir / PDF' }}
    </button>
  </div>

  <p v-if="erro" style="padding: 16px; color: var(--danger)">{{ erro }}</p>

  <div v-else-if="obra" class="content relatorio">
    <header style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px">
      <div>
        <div style="font-size: 18px; font-weight: 700">{{ EMPRESA }}</div>
        <div style="color: var(--text-muted); font-size: 13px">Relatório de Obra — Mudança de Layout</div>
      </div>
      <div style="text-align: right">
        <div style="font-size: 20px; font-weight: 700">{{ obra.numero }}</div>
        <div style="color: var(--text-muted); font-size: 13px">{{ STATUS_ROTULO[obra.status] || obra.status }}</div>
      </div>
    </header>

    <section class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">{{ obra.nome }}</h3>
      <p v-if="obra.descricao" style="font-size: 14px; margin: 0 0 8px">{{ obra.descricao }}</p>
      <dl style="display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 0; font-size: 14px">
        <dt style="color: var(--text-muted)">Responsável</dt><dd style="margin: 0">{{ obra.responsavel || '—' }}</dd>
        <dt style="color: var(--text-muted)">Tipo de mudança</dt><dd style="margin: 0">{{ obra.tipo_display }}</dd>
        <dt style="color: var(--text-muted)">Data da mudança</dt><dd style="margin: 0">{{ data(obra.data_mudanca) }}</dd>
        <dt style="color: var(--text-muted)">Término previsto</dt><dd style="margin: 0">{{ data(obra.data_termino_previsto) }}</dd>
        <dt v-if="obra.data_conclusao" style="color: var(--text-muted)">Concluída em</dt>
        <dd v-if="obra.data_conclusao" style="margin: 0">{{ data(obra.data_conclusao) }}</dd>
        <dt style="color: var(--text-muted)">Áreas afetadas</dt>
        <dd style="margin: 0">{{ areasRotulos.join(', ') || '—' }}</dd>
      </dl>
    </section>

    <section class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Progresso ({{ obra.progresso }}%)</h3>
      <table style="width: 100%; border-collapse: collapse; font-size: 13px">
        <thead>
          <tr style="text-align: left; border-bottom: 1px solid var(--border)">
            <th style="padding: 4px 6px">Etapa</th>
            <th style="padding: 4px 6px">Tipo</th>
            <th style="padding: 4px 6px">Local</th>
            <th style="padding: 4px 6px; text-align: right">Feito / Meta</th>
            <th style="padding: 4px 6px; text-align: right">%</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in obra.etapas" :key="e.id" style="border-bottom: 1px solid var(--border)">
            <td style="padding: 4px 6px">{{ e.nome }}</td>
            <td style="padding: 4px 6px">{{ e.tipo_ponto_display || '—' }}</td>
            <td style="padding: 4px 6px">{{ e.localizacao || '—' }}</td>
            <td style="padding: 4px 6px; text-align: right">{{ e.realizado }} / {{ e.meta }}</td>
            <td style="padding: 4px 6px; text-align: right">{{ e.porcentagem }}%</td>
          </tr>
          <tr style="font-weight: 700">
            <td colspan="3" style="padding: 6px">Total</td>
            <td style="padding: 6px; text-align: right">{{ obra.total_realizado }} / {{ obra.total_meta }}</td>
            <td style="padding: 6px; text-align: right">{{ obra.progresso }}%</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="obra.plantas?.length" class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 8px">Plantas anexadas</h3>
      <ul style="margin: 0; padding-left: 18px; font-size: 14px">
        <li v-for="p in obra.plantas" :key="p.id">
          Folha {{ p.pagina || '?' }}<template v-if="p.descricao"> — {{ p.descricao }}</template>
        </li>
      </ul>
    </section>

    <section
      v-for="etapa in obra.etapas.filter((e) => e.fotos?.length)"
      :key="'fotos-' + etapa.id"
      class="card"
      style="margin-bottom: 12px"
    >
      <h3 style="margin: 0 0 8px">Fotos — {{ etapa.nome }}</h3>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px">
        <figure v-for="foto in etapa.fotos" :key="foto.id" style="margin: 0; break-inside: avoid">
          <img
            :src="foto.imagem"
            :alt="foto.legenda"
            style="width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 6px; border: 1px solid var(--border)"
          />
          <figcaption v-if="foto.legenda" style="font-size: 12px; color: var(--text-muted)">{{ foto.legenda }}</figcaption>
        </figure>
      </div>
    </section>

    <section v-if="obra.assinaturas?.length" class="card" style="margin-bottom: 12px; break-inside: avoid">
      <h3 style="margin: 0 0 8px">Assinaturas</h3>
      <div style="display: flex; flex-wrap: wrap; gap: 16px">
        <div v-for="a in obra.assinaturas" :key="a.id" style="break-inside: avoid">
          <img
            :src="a.assinatura"
            :alt="a.nome"
            style="max-width: 220px; border: 1px solid var(--border); border-radius: 6px; display: block"
          />
          <div style="font-size: 13px; margin-top: 4px"><strong>{{ a.nome }}</strong></div>
          <div style="font-size: 12px; color: var(--text-muted)">
            {{ a.papel_display }} · {{ dataHora(a.assinado_em) }}
          </div>
        </div>
      </div>
    </section>

    <footer style="margin-top: 16px; font-size: 12px; color: var(--text-muted)">
      Emitido em {{ dataHora(new Date().toISOString()) }}
      <span v-if="obra.criado_por_nome"> · obra cadastrada por {{ obra.criado_por_nome }}</span>
    </footer>
  </div>
</template>
