<script setup>
import { ref } from 'vue'

const aberto = ref(false)
const src = ref('')
const legenda = ref('')

function abrir(url, texto = '') {
  src.value = url
  legenda.value = texto
  aberto.value = true
}
function fechar() {
  aberto.value = false
}
defineExpose({ abrir })
</script>

<template>
  <Teleport to="body">
    <div
      v-if="aberto"
      style="position: fixed; inset: 0; z-index: 3000; background: rgba(0, 0, 0, 0.92); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px"
      @click="fechar"
    >
      <button
        type="button"
        aria-label="Fechar"
        style="position: absolute; top: 12px; right: 12px; border: none; background: none; color: #fff; font-size: 30px; padding: 8px 12px; line-height: 1"
        @click.stop="fechar"
      >
        ✕
      </button>
      <img
        :src="src"
        :alt="legenda"
        style="max-width: 100%; max-height: 84vh; object-fit: contain; border-radius: 8px"
        @click.stop
      />
      <div v-if="legenda" style="color: #fff; margin-top: 12px; font-size: 14px; text-align: center">
        {{ legenda }}
      </div>
    </div>
  </Teleport>
</template>
