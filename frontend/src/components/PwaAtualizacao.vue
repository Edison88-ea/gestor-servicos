<script setup>
import { useRegisterSW } from 'virtual:pwa-register/vue'

// needRefresh vira true quando um novo service worker já baixou e está
// esperando para assumir. updateServiceWorker(true) ativa o SW novo e
// recarrega a página.
const { needRefresh, updateServiceWorker } = useRegisterSW()

function atualizar() {
  updateServiceWorker(true)
}

function adiar() {
  needRefresh.value = false
}
</script>

<template>
  <div v-if="needRefresh" class="pwa-toast" role="alert">
    <span>Nova versão disponível.</span>
    <div class="pwa-toast-acoes">
      <button type="button" class="pwa-toast-primary" @click="atualizar">Atualizar</button>
      <button type="button" class="pwa-toast-secundario" @click="adiar">Depois</button>
    </div>
  </div>
</template>

<style scoped>
.pwa-toast {
  position: fixed;
  left: 50%;
  bottom: calc(16px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: min(92vw, 420px);
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.pwa-toast-acoes {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.pwa-toast button {
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.pwa-toast-primary {
  background: var(--accent);
  color: var(--accent-contrast);
}

.pwa-toast-secundario {
  background: transparent;
  color: var(--text-muted);
}
</style>
