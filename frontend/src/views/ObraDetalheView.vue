<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useObrasStore } from '../stores/obras'
import AssinaturaCanvas from '../components/AssinaturaCanvas.vue'
import Lightbox from '../components/Lightbox.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const lightbox = ref(null)
const router = useRouter()
const auth = useAuthStore()
const store = useObrasStore()

const obra = ref(null)
const erro = ref('')
const opcoes = ref(null)
const historicoAberto = ref(null) // id da etapa com histórico expandido
const salvandoStatus = ref(false)

const assinando = ref(false)
const assinaturaPad = ref(null)
const assinaturaPapel = ref('CIENTE')
const assinaturaNome = ref('')
const salvandoAssinatura = ref(false)

const PAPEL_ROTULO = {
  CIENTE: 'Ciente da alteração',
  SUPERVISOR: 'Supervisor de processos',
}

const podeGerenciar = computed(() => ['ENCARREGADO', 'GESTOR', 'ADMIN'].includes(auth.user?.papel))

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

function prazo(iso) {
  return iso ? new Date(iso + 'T00:00:00').toLocaleDateString('pt-BR') : '—'
}

function dataHora(iso) {
  return iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : ''
}

async function carregar() {
  try {
    obra.value = await store.buscar(props.id)
  } catch {
    erro.value = 'Não foi possível carregar a obra.'
  }
}

async function mudarProgresso(etapa, delta) {
  const novo = Math.max(0, Math.min(etapa.realizado + delta, etapa.meta))
  if (novo === etapa.realizado) return
  try {
    const atualizada = await store.atualizarProgresso(etapa.id, { realizado: novo })
    Object.assign(etapa, atualizada)
    recalcularTotais()
  } catch {
    erro.value = 'Não foi possível salvar o progresso.'
  }
}

async function definirProgresso(etapa, evento) {
  const valor = Number(evento.target.value)
  if (Number.isNaN(valor) || valor === etapa.realizado) return
  try {
    const atualizada = await store.atualizarProgresso(etapa.id, { realizado: valor })
    Object.assign(etapa, atualizada)
    recalcularTotais()
  } catch {
    erro.value = 'Não foi possível salvar o progresso.'
  }
}

async function enviarFoto(etapa, evento) {
  const arquivo = evento.target.files?.[0]
  if (!arquivo) return
  try {
    const foto = await store.adicionarFoto(etapa.id, arquivo)
    etapa.fotos = [foto, ...(etapa.fotos || [])]
  } catch {
    erro.value = 'Não foi possível enviar a foto.'
  } finally {
    evento.target.value = ''
  }
}

async function enviarPlanta(evento) {
  const arquivo = evento.target.files?.[0]
  if (!arquivo) return
  try {
    const planta = await store.adicionarPlanta(obra.value.id, arquivo)
    obra.value.plantas = [...(obra.value.plantas || []), planta]
  } catch {
    erro.value = 'Não foi possível enviar a planta.'
  } finally {
    evento.target.value = ''
  }
}

async function mudarStatus(evento) {
  salvandoStatus.value = true
  try {
    const atualizada = await store.atualizar(obra.value.id, { status: evento.target.value })
    obra.value.status = atualizada.status
  } catch {
    erro.value = 'Não foi possível mudar o status.'
  } finally {
    salvandoStatus.value = false
  }
}

async function salvarAssinatura() {
  if (!assinaturaNome.value.trim()) {
    erro.value = 'Informe o nome de quem está assinando.'
    return
  }
  if (assinaturaPad.value?.vazio()) {
    erro.value = 'A assinatura está em branco.'
    return
  }
  salvandoAssinatura.value = true
  try {
    const blob = await assinaturaPad.value.paraArquivo()
    const nova = await store.adicionarAssinatura(
      obra.value.id,
      { papel: assinaturaPapel.value, nome: assinaturaNome.value.trim() },
      blob,
    )
    obra.value.assinaturas = [...(obra.value.assinaturas || []), nova]
    assinando.value = false
    assinaturaNome.value = ''
    erro.value = ''
  } catch {
    erro.value = 'Não foi possível salvar a assinatura.'
  } finally {
    salvandoAssinatura.value = false
  }
}

function recalcularTotais() {
  const etapas = obra.value.etapas || []
  const meta = etapas.reduce((s, e) => s + e.meta, 0)
  const realizado = etapas.reduce((s, e) => s + e.realizado, 0)
  obra.value.total_meta = meta
  obra.value.total_realizado = realizado
  obra.value.progresso = meta ? Math.min(Math.round((realizado / meta) * 100), 100) : 0
}

onMounted(async () => {
  opcoes.value = await store.carregarOpcoes()
  await carregar()
})
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.push('/obras')">← Obras</button>
    <strong>Detalhe</strong>
    <button
      v-if="obra"
      type="button"
      style="border: none; background: none; color: var(--accent); font-weight: 600"
      @click="router.push(`/obras/${obra.id}/relatorio`)"
    >
      Relatório
    </button>
  </div>

  <p v-if="erro" style="padding: 16px; color: var(--danger)">{{ erro }}</p>

  <div v-if="obra" class="content">
    <section class="card" style="margin-bottom: 12px">
      <div style="display: flex; justify-content: space-between; gap: 8px">
        <strong style="font-size: 17px">{{ obra.nome }}</strong>
        <span style="color: var(--text-muted); font-size: 13px">{{ obra.numero }}</span>
      </div>
      <p v-if="obra.descricao" style="font-size: 14px; color: var(--text-muted); margin: 6px 0">
        {{ obra.descricao }}
      </p>

      <dl style="display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 8px 0 0; font-size: 14px">
        <dt style="color: var(--text-muted)">Responsável</dt><dd style="margin: 0">{{ obra.responsavel || '—' }}</dd>
        <dt style="color: var(--text-muted)">Tipo</dt><dd style="margin: 0">{{ obra.tipo_display }}</dd>
        <dt style="color: var(--text-muted)">Data da mudança</dt><dd style="margin: 0">{{ prazo(obra.data_mudanca) }}</dd>
        <dt style="color: var(--text-muted)">Término previsto</dt><dd style="margin: 0">{{ prazo(obra.data_termino_previsto) }}</dd>
      </dl>

      <div v-if="areasRotulos.length" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px">
        <span v-for="a in areasRotulos" :key="a" class="badge" style="background: var(--border); color: var(--text)">{{ a }}</span>
      </div>

      <label style="display: block; margin-top: 12px; font-size: 14px">
        Status
        <select
          :value="obra.status"
          :disabled="!podeGerenciar || salvandoStatus"
          style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          @change="mudarStatus"
        >
          <option v-for="(rotulo, valor) in STATUS_ROTULO" :key="valor" :value="valor">{{ rotulo }}</option>
        </select>
      </label>

      <div style="height: 10px; background: var(--border); border-radius: 999px; overflow: hidden; margin-top: 12px">
        <div
          :style="{
            width: obra.progresso + '%',
            height: '100%',
            background: obra.progresso >= 100 ? 'var(--success)' : 'var(--accent)',
          }"
        />
      </div>
      <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px">
        {{ obra.progresso }}% concluído · {{ obra.total_realizado }}/{{ obra.total_meta }} pontos
      </div>
    </section>

    <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 16px 0 8px">
      <h3 style="margin: 0">Etapas</h3>
      <RouterLink
        v-if="podeGerenciar && obra.etapas?.length"
        :to="`/obras/${obra.id}/etapas`"
        style="font-size: 13px"
      >
        Editar
      </RouterLink>
    </div>
    <p v-if="!obra.etapas?.length" style="color: var(--text-muted)">
      Nenhuma etapa.
      <RouterLink v-if="podeGerenciar" :to="`/obras/${obra.id}/etapas`">Definir metas</RouterLink>
    </p>

    <div
      v-for="etapa in obra.etapas"
      :key="etapa.id"
      class="card"
      style="margin-bottom: 10px"
    >
      <div style="display: flex; justify-content: space-between; gap: 8px">
        <strong>{{ etapa.nome }}</strong>
        <span
          class="badge"
          :style="{
            background: etapa.concluida ? 'var(--success)' : 'var(--border)',
            color: etapa.concluida ? 'white' : 'var(--text)',
          }"
        >
          {{ etapa.realizado }}/{{ etapa.meta }}
        </span>
      </div>
      <div v-if="etapa.tipo_ponto_display || etapa.localizacao" style="font-size: 13px; color: var(--text-muted); margin-top: 2px">
        {{ [etapa.tipo_ponto_display, etapa.localizacao].filter(Boolean).join(' · ') }}
      </div>

      <div style="display: flex; align-items: center; gap: 8px; margin-top: 10px">
        <button class="btn-secondary" style="padding: 6px 14px; font-size: 18px" @click="mudarProgresso(etapa, -1)">−</button>
        <input
          type="number"
          :value="etapa.realizado"
          min="0"
          :max="etapa.meta"
          style="width: 64px; text-align: center; padding: 8px; border-radius: 8px; border: 1px solid var(--border)"
          @change="definirProgresso(etapa, $event)"
        />
        <button class="btn-secondary" style="padding: 6px 14px; font-size: 18px" @click="mudarProgresso(etapa, 1)">+</button>

        <label class="btn-secondary" style="margin-left: auto; padding: 6px 12px; font-size: 13px">
          📷 Foto
          <input type="file" accept="image/*" capture="environment" style="display: none" @change="enviarFoto(etapa, $event)" />
        </label>
      </div>

      <div v-if="etapa.fotos?.length" style="display: flex; gap: 6px; overflow-x: auto; margin-top: 10px">
        <img
          v-for="f in etapa.fotos"
          :key="f.id"
          :src="f.imagem"
          :alt="f.legenda"
          style="height: 64px; width: 64px; object-fit: cover; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; flex: 0 0 auto"
          @click="lightbox.abrir(f.imagem, f.legenda)"
        />
      </div>

      <button
        v-if="etapa.historico?.length"
        type="button"
        style="border: none; background: none; color: var(--accent); font-size: 13px; margin-top: 8px; padding: 0"
        @click="historicoAberto = historicoAberto === etapa.id ? null : etapa.id"
      >
        {{ historicoAberto === etapa.id ? 'Ocultar' : 'Ver' }} histórico ({{ etapa.historico.length }})
      </button>
      <ul
        v-if="historicoAberto === etapa.id"
        style="margin: 6px 0 0; padding-left: 16px; font-size: 13px; color: var(--text-muted)"
      >
        <li v-for="h in etapa.historico" :key="h.id">
          {{ dataHora(h.data) }} — {{ h.quantidade_anterior }}→{{ h.quantidade_nova }}
          <template v-if="h.usuario_nome"> ({{ h.usuario_nome }})</template>
          <template v-if="h.observacao"> · {{ h.observacao }}</template>
        </li>
      </ul>
    </div>

    <h3 style="margin: 16px 0 8px">Plantas</h3>
    <div style="display: flex; flex-wrap: wrap; gap: 8px">
      <a
        v-for="p in obra.plantas"
        :key="p.id"
        :href="p.arquivo"
        target="_blank"
        class="card"
        style="padding: 10px 12px; font-size: 14px; text-decoration: none; color: var(--accent)"
      >
        📄 Folha {{ p.pagina || '?' }}<template v-if="p.descricao"> — {{ p.descricao }}</template>
      </a>
      <label v-if="podeGerenciar" class="btn-secondary" style="padding: 10px 12px; font-size: 14px">
        + Anexar planta
        <input type="file" accept=".pdf,image/*" style="display: none" @change="enviarPlanta" />
      </label>
    </div>

    <h3 style="margin: 16px 0 8px">Assinaturas</h3>
    <div
      v-for="a in obra.assinaturas"
      :key="a.id"
      class="card"
      style="margin-bottom: 8px; display: flex; gap: 12px; align-items: center"
    >
      <img
        :src="a.assinatura"
        :alt="a.nome"
        style="height: 48px; border: 1px solid var(--border); border-radius: 4px; background: white"
      />
      <div style="font-size: 14px">
        <strong>{{ a.nome }}</strong>
        <div style="color: var(--text-muted); font-size: 12px">{{ a.papel_display }}</div>
      </div>
    </div>

    <div v-if="assinando" class="card" style="display: flex; flex-direction: column; gap: 8px">
      <select
        v-model="assinaturaPapel"
        style="padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
      >
        <option v-for="(rotulo, valor) in PAPEL_ROTULO" :key="valor" :value="valor">{{ rotulo }}</option>
      </select>
      <input
        v-model="assinaturaNome"
        type="text"
        placeholder="Nome de quem assina"
        style="padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
      />
      <AssinaturaCanvas ref="assinaturaPad" />
      <div style="display: flex; gap: 8px">
        <button class="btn" style="flex: 1" :disabled="salvandoAssinatura" @click="salvarAssinatura">
          {{ salvandoAssinatura ? 'Salvando...' : 'Salvar assinatura' }}
        </button>
        <button class="btn-secondary" @click="assinando = false">Cancelar</button>
      </div>
    </div>
    <button
      v-else
      type="button"
      class="btn-secondary"
      style="width: 100%"
      @click="assinando = true"
    >
      + Coletar assinatura
    </button>
  </div>

  <Lightbox ref="lightbox" />
</template>
