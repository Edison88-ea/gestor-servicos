<!-- frontend/src/views/PendenciasView.vue -->
<script setup>
import { computed } from 'vue'
import { useOsOfflineStore } from '../stores/osOffline'
import { useClientesStore } from '../stores/clientes'
import { usePontoStore } from '../stores/ponto'

const osOffline = useOsOfflineStore()
const clientes = useClientesStore()
const ponto = usePontoStore()

const itens = computed(() => {
  const lista = []

  for (const os of osOffline.locais) {
    lista.push({
      chave: `os-${os.id}`,
      titulo: os.numero || 'OS não enviada',
      detalhe: os.cliente_nome || os.tipo_servico,
      erro: os.erroSync || '',
    })
  }
  for (const acao of osOffline.acoesPendentes) {
    lista.push({
      chave: `os-acao-${acao.osId}-${acao.tipo}-${acao.criadoEm}`,
      titulo: `OS #${acao.osId} — ${acao.tipo}`,
      detalhe: '',
      erro: acao.erroSync || '',
    })
  }
  for (const c of clientes.pendentes) {
    lista.push({
      chave: `cliente-${c.id}`,
      titulo: c.nome,
      detalhe: 'Cliente novo',
      erro: c.erroSync || '',
    })
  }
  for (const r of ponto.filaOffline) {
    lista.push({
      chave: `ponto-${r.tipo}-${r.registrado_em}`,
      titulo: `Ponto — ${r.tipo}`,
      detalhe: new Date(r.registrado_em).toLocaleString('pt-BR'),
      erro: r.erroSync || '',
    })
  }
  for (const r of ponto.rejeitados) {
    lista.push({
      chave: `ponto-rejeitado-${r.tipo}-${r.registrado_em}`,
      titulo: `Ponto recusado — ${r.tipo}`,
      detalhe: new Date(r.registrado_em).toLocaleString('pt-BR'),
      erro: r.motivo || 'Recusado pelo servidor',
    })
  }
  return lista
})

function tentarAgora() {
  clientes.sincronizar()
  osOffline.sincronizar()
  ponto.sincronizarFila()
}
</script>

<template>
  <div class="top-bar">
    <strong>Pendências</strong>
    <button type="button" style="border: none; background: none; color: var(--accent); font-weight: 600" @click="tentarAgora">
      Tentar agora
    </button>
  </div>

  <div class="content">
    <p v-if="itens.length === 0" style="color: var(--text-muted)">Nada pendente — tudo sincronizado.</p>

    <ul class="grid-cards">
      <li v-for="item in itens" :key="item.chave" class="card">
        <strong>{{ item.titulo }}</strong>
        <div v-if="item.detalhe" style="color: var(--text-muted); font-size: 14px">{{ item.detalhe }}</div>
        <div v-if="item.erro" style="color: var(--warning); font-size: 13px; margin-top: 4px">⚠ {{ item.erro }}</div>
        <div v-else style="color: var(--text-muted); font-size: 13px; margin-top: 4px">aguardando envio</div>
      </li>
    </ul>
  </div>
</template>
