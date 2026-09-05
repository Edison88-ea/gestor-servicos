<script setup>
import { onMounted, ref, watch } from 'vue'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

// `rotuloVazio` é o texto da opção sem seleção. Na visão pessoal isso não
// aparece; na visão da equipe vira "Selecione um funcionário", porque quem é
// gestão e não bate ponto (a dona) não tem cartão próprio pra cair em cima.
defineProps({ rotuloVazio: { type: String, default: 'Eu' } })
const modelo = defineModel({ type: [String, Number], default: '' })
const emit = defineEmits(['trocou'])
const auth = useAuthStore()

const ehGestao = ['GESTOR', 'RH', 'ADMIN'].includes(auth.user?.papel)
const funcionarios = ref([])

function nomeDe(f) {
  return f.first_name ? `${f.first_name} ${f.last_name}`.trim() : f.username
}

watch(modelo, (id) => {
  const f = funcionarios.value.find((x) => String(x.id) === String(id))
  emit('trocou', f ? nomeDe(f) : null)
})

onMounted(async () => {
  if (!ehGestao) return
  try {
    // Todo mundo que bate ponto — inclui a secretária (RH), que a gestão
    // também precisa acompanhar, e exclui quem não registra ponto.
    const { data } = await client.get('/usuarios/', {
      params: { registra_ponto: 'true' },
    })
    funcionarios.value = data.results ?? data
  } catch {
    // sem rede: some o seletor, mostra o próprio
  }
})
</script>

<template>
  <div v-if="ehGestao && funcionarios.length" class="ocultar-impressao" style="margin-bottom: 12px">
    <label style="font-size: 13px; color: var(--text-muted)">Funcionário</label>
    <select
      v-model="modelo"
      style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); margin-top: 4px"
    >
      <option value="">{{ rotuloVazio }}</option>
      <option v-for="f in funcionarios" :key="f.id" :value="String(f.id)">
        {{ nomeDe(f) }}
      </option>
    </select>
  </div>
</template>
