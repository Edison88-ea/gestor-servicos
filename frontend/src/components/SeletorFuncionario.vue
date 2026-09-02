<script setup>
import { onMounted, ref, watch } from 'vue'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

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
    const { data } = await client.get('/usuarios/', {
      params: { papel: 'TECNICO,ENCARREGADO' },
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
      <option value="">Eu</option>
      <option v-for="f in funcionarios" :key="f.id" :value="String(f.id)">
        {{ nomeDe(f) }}
      </option>
    </select>
  </div>
</template>
