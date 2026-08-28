<script setup>
const emit = defineEmits(['estou-no-local', 'nao-estou-no-local', 'fechar'])
</script>

<template>
  <div
    style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: flex-end; justify-content: center; z-index: 50"
    @click.self="emit('fechar')"
  >
    <div class="card" style="width: 100%; max-width: 480px; border-radius: 16px 16px 0 0; margin: 0">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
        <h2 style="margin: 0">Nova tarefa</h2>
        <button
          type="button"
          style="border: none; background: none; font-size: 20px; color: var(--text-muted); line-height: 1; padding: 4px"
          @click="emit('fechar')"
        >
          ✕
        </button>
      </div>

      <button
        type="button"
        class="btn-secondary"
        style="width: 100%; display: flex; align-items: center; gap: 10px; padding: 14px; margin-bottom: 8px; text-align: left; border-radius: 10px"
        @click="emit('estou-no-local')"
      >
        <span>📍</span>
        <span style="flex: 1">Estou no local</span>
        <span style="color: var(--text-muted)">›</span>
      </button>

      <button
        type="button"
        class="btn-secondary"
        style="width: 100%; display: flex; align-items: center; gap: 10px; padding: 14px; text-align: left; border-radius: 10px"
        @click="emit('nao-estou-no-local')"
      >
        <span>🗓️</span>
        <span style="flex: 1">Não estou no local</span>
        <span style="color: var(--text-muted)">›</span>
      </button>
    </div>
  </div>
</template>
