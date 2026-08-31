<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useObrasStore } from '../stores/obras'

const router = useRouter()
const store = useObrasStore()

const nome = ref('')
const descricao = ref('')
const responsavel = ref('')
const tipo = ref('INSTALACAO_PROJETO')
const dataMudanca = ref('')
const dataTermino = ref('')
const areas = ref([])
const salvando = ref(false)
const erro = ref('')

const opcoes = ref({ tipos: [], areas_afetadas: [] })

function alternarArea(codigo) {
  const i = areas.value.indexOf(codigo)
  if (i === -1) areas.value.push(codigo)
  else areas.value.splice(i, 1)
}

async function salvar() {
  erro.value = ''
  if (!nome.value.trim()) {
    erro.value = 'Informe o nome da obra.'
    return
  }
  salvando.value = true
  try {
    const obra = await store.criar({
      nome: nome.value.trim(),
      descricao: descricao.value,
      responsavel: responsavel.value,
      tipo: tipo.value,
      areas_afetadas: areas.value,
      data_mudanca: dataMudanca.value || null,
      data_termino_previsto: dataTermino.value || null,
    })
    router.replace(`/obras/${obra.id}/etapas`)
  } catch {
    erro.value = 'Não foi possível criar a obra. Tente novamente.'
  } finally {
    salvando.value = false
  }
}

onMounted(async () => {
  const o = await store.carregarOpcoes()
  if (o) opcoes.value = o
})
</script>

<template>
  <div class="top-bar">
    <button class="btn-secondary" style="border: none; background: none" @click="router.back()">← Voltar</button>
    <strong>Nova Obra</strong>
  </div>

  <div class="content">
    <div class="card" style="display: flex; flex-direction: column; gap: 12px">
      <label>
        Nome
        <input
          v-model="nome"
          type="text"
          placeholder="Ex: Volkswagen — Patagonia Alternador"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
        />
      </label>

      <label>
        Escopo
        <textarea
          v-model="descricao"
          rows="3"
          placeholder="Descrição do Termo de Mudança de Layout"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
        />
      </label>

      <label>
        Responsável
        <input
          v-model="responsavel"
          type="text"
          placeholder="Nome de quem responde pela mudança"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
        />
      </label>

      <label>
        Tipo de mudança
        <select
          v-model="tipo"
          style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
        >
          <option v-for="t in opcoes.tipos" :key="t.valor" :value="t.valor">{{ t.rotulo }}</option>
        </select>
      </label>

      <div style="display: flex; gap: 8px">
        <label style="flex: 1">
          Data da mudança
          <input
            v-model="dataMudanca"
            type="date"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          />
        </label>
        <label style="flex: 1">
          Término previsto
          <input
            v-model="dataTermino"
            type="date"
            style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
          />
        </label>
      </div>

      <div>
        <div style="margin-bottom: 6px">Áreas afetadas</div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px">
          <button
            v-for="a in opcoes.areas_afetadas"
            :key="a.valor"
            type="button"
            class="badge"
            :style="{
              cursor: 'pointer',
              border: '1px solid var(--border)',
              background: areas.includes(a.valor) ? 'var(--accent)' : 'var(--surface)',
              color: areas.includes(a.valor) ? 'white' : 'var(--text)',
            }"
            @click="alternarArea(a.valor)"
          >
            {{ a.rotulo }}
          </button>
        </div>
      </div>

      <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>
      <button class="btn" :disabled="salvando" @click="salvar">
        {{ salvando ? 'Criando...' : 'Criar e definir metas' }}
      </button>
    </div>
  </div>
</template>
