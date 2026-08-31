<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useObrasStore } from '../stores/obras'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()
const store = useObrasStore()

const obra = ref(null)
const etapas = ref([]) // { id?, nome, tipo_ponto, localizacao, meta, _novo?, _removida? }
const tiposPonto = ref([])
const erro = ref('')
const salvando = ref(false)

function linhaVazia() {
  return { nome: '', tipo_ponto: '', localizacao: '', meta: 1, _novo: true }
}

function adicionar() {
  etapas.value.push(linhaVazia())
}

function remover(i) {
  const e = etapas.value[i]
  if (e._novo) etapas.value.splice(i, 1)
  else e._removida = !e._removida
}

async function salvar() {
  erro.value = ''
  const ativas = etapas.value.filter((e) => !e._removida)
  if (ativas.some((e) => !e.nome.trim())) {
    erro.value = 'Toda etapa precisa de um nome.'
    return
  }
  salvando.value = true
  try {
    for (const [i, e] of etapas.value.entries()) {
      const payload = {
        nome: e.nome.trim(),
        tipo_ponto: e.tipo_ponto,
        localizacao: e.localizacao,
        meta: Number(e.meta) || 1,
        ordem: i,
      }
      if (e._removida && e.id) {
        await store.removerEtapa(e.id)
      } else if (e._novo) {
        await store.criarEtapa({ ...payload, projeto: obra.value.id })
      } else if (e.id) {
        await store.atualizarEtapa(e.id, payload)
      }
    }
    router.replace(`/obras/${props.id}`)
  } catch {
    erro.value = 'Não foi possível salvar todas as etapas. Recarregue e confira.'
  } finally {
    salvando.value = false
  }
}

onMounted(async () => {
  const o = await store.carregarOpcoes()
  if (o) tiposPonto.value = o.tipos_ponto
  try {
    obra.value = await store.buscar(props.id)
    etapas.value = (obra.value.etapas || []).map((e) => ({
      id: e.id,
      nome: e.nome,
      tipo_ponto: e.tipo_ponto || '',
      localizacao: e.localizacao || '',
      meta: e.meta,
    }))
    if (!etapas.value.length) adicionar()
  } catch {
    erro.value = 'Não foi possível carregar a obra.'
  }
})
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Etapas / metas</strong>
  </div>

  <div class="content">
    <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>
    <p v-if="obra" style="color: var(--text-muted); margin-top: 0">{{ obra.nome }}</p>

    <div
      v-for="(e, i) in etapas"
      :key="e.id || 'novo-' + i"
      class="card"
      style="margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px"
      :style="{ opacity: e._removida ? 0.45 : 1 }"
    >
      <div style="display: flex; gap: 8px">
        <input
          v-model="e.nome"
          type="text"
          placeholder="Nome da etapa (ex: Pontos de rede)"
          :disabled="e._removida"
          style="flex: 1; padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
        />
        <button
          type="button"
          class="btn-secondary"
          style="padding: 6px 10px"
          @click="remover(i)"
        >
          {{ e._removida ? '↺' : '✕' }}
        </button>
      </div>

      <div style="display: flex; gap: 8px">
        <select
          v-model="e.tipo_ponto"
          :disabled="e._removida"
          style="flex: 1; padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
        >
          <option value="">Tipo de ponto…</option>
          <option v-for="t in tiposPonto" :key="t.valor" :value="t.valor">{{ t.rotulo }}</option>
        </select>
        <input
          v-model.number="e.meta"
          type="number"
          min="1"
          :disabled="e._removida"
          style="width: 84px; padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
        />
      </div>

      <input
        v-model="e.localizacao"
        type="text"
        placeholder="Localização / linha (ex: Patagonia - Alternador)"
        :disabled="e._removida"
        style="padding: 9px; border-radius: 8px; border: 1px solid var(--border)"
      />
    </div>

    <button type="button" class="btn-secondary" style="width: 100%; margin-bottom: 12px" @click="adicionar">
      + Adicionar etapa
    </button>

    <button class="btn" style="width: 100%" :disabled="salvando" @click="salvar">
      {{ salvando ? 'Salvando...' : 'Salvar etapas' }}
    </button>
  </div>
</template>
