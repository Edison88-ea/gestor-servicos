<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificacoesStore } from '../stores/notificacoes'

defineProps({ aberto: { type: Boolean, default: false } })
const emit = defineEmits(['fechar'])

const store = useNotificacoesStore()
const router = useRouter()

function formatarData(iso) {
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function abrir(notificacao) {
  if (!notificacao.lida) await store.marcarLida(notificacao.id)
  emit('fechar')
  if (notificacao.link) router.push(notificacao.link)
}

onMounted(() => {
  store.carregar()
})
</script>

<template>
  <div v-if="aberto" style="position: fixed; inset: 0; z-index: 2000">
    <div style="position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5)" @click="emit('fechar')" />

    <div
      style="position: absolute; top: 0; right: 0; bottom: 0; width: 85%; max-width: 340px; background: var(--surface); overflow-y: auto; box-shadow: -4px 0 16px rgba(0,0,0,0.2)"
    >
      <div style="padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center">
        <strong>Notificações</strong>
        <button
          v-if="store.naoLidas > 0"
          type="button"
          style="border: none; background: none; color: var(--accent); font-size: 13px"
          @click="store.marcarTodasLidas()"
        >
          Marcar todas como lidas
        </button>
      </div>

      <p v-if="store.itens.length === 0" style="padding: 16px; color: var(--text-muted)">Nenhuma notificação.</p>

      <button
        v-for="n in store.itens"
        :key="n.id"
        type="button"
        style="display: block; width: 100%; text-align: left; border: none; border-bottom: 1px solid var(--border); padding: 14px 16px; background: none"
        :style="{ background: n.lida ? 'none' : 'var(--accent-bg, rgba(37,99,235,0.08))' }"
        @click="abrir(n)"
      >
        <div style="font-size: 14px; color: var(--text)">{{ n.mensagem }}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px">{{ formatarData(n.criado_em) }}</div>
      </button>
    </div>
  </div>
</template>
