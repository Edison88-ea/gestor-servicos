<script setup>
import { onMounted, ref } from 'vue'
import { useOrdensServicoStore } from '../stores/ordensServico'

const emit = defineEmits(['fechar', 'copiar'])
const store = useOrdensServicoStore()

const itens = ref([])
const carregando = ref(true)
const erro = ref('')

onMounted(async () => {
  try {
    itens.value = await store.relatosAnteriores()
  } catch {
    erro.value = 'Não foi possível carregar as OS anteriores.'
  } finally {
    carregando.value = false
  }
})

function resumo(relato) {
  const partes = []
  if (relato.local) partes.push(relato.local)
  const nServ = (relato.servicos || []).filter((s) => s && s.trim()).length
  const nMat = (relato.materiais || []).filter((m) => m.descricao && m.descricao.trim()).length
  if (nServ) partes.push(`${nServ} serviço(s)`)
  if (nMat) partes.push(`${nMat} material(is)`)
  return partes.join(' · ')
}

function escolher(item) {
  emit('copiar', item.relato)
  emit('fechar')
}
</script>

<template>
  <div class="overlay" @click.self="emit('fechar')">
    <div class="folha">
      <div class="cabecalho">
        <strong>Copiar de uma OS anterior</strong>
        <button type="button" class="fechar" @click="emit('fechar')" aria-label="Fechar">✕</button>
      </div>

      <p v-if="carregando" class="msg">Carregando…</p>
      <p v-else-if="erro" class="msg erro">{{ erro }}</p>
      <p v-else-if="!itens.length" class="msg">Nenhuma OS concluída com relato ainda.</p>

      <ul v-else class="lista">
        <li v-for="item in itens" :key="item.id">
          <button type="button" class="item" @click="escolher(item)">
            <div class="linha1">
              <span>{{ item.numero }} — {{ item.cliente_nome }}</span>
              <span class="data">{{ new Date(item.data_conclusao).toLocaleDateString('pt-BR') }}</span>
            </div>
            <div class="linha2">{{ item.tipo_servico }}</div>
            <div v-if="resumo(item.relato)" class="linha3">{{ resumo(item.relato) }}</div>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.folha {
  width: 100%;
  max-width: 480px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--surface);
  border-radius: 16px 16px 0 0;
  padding: 16px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom));
}
.cabecalho {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.fechar {
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 18px;
  padding: 4px 8px;
}
.msg {
  color: var(--text-muted);
  margin: 16px 0;
}
.msg.erro {
  color: var(--danger);
}
.lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.linha1 {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}
.data {
  color: var(--text-muted);
  font-weight: 400;
  flex-shrink: 0;
}
.linha2 {
  font-size: 13px;
  color: var(--text-muted);
}
.linha3 {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
