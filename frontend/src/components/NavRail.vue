<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificacoesStore } from '../stores/notificacoes'
import { useNavGroups } from '../composables/useNavGroups'
import Logo3D from './Logo3D.vue'

const emit = defineEmits(['abrir-notificacoes'])

const auth = useAuthStore()
const notificacoes = useNotificacoesStore()
const router = useRouter()
const grupos = useNavGroups()

const nome = computed(() => {
  const u = auth.user
  if (!u) return ''
  return u.first_name ? `${u.first_name} ${u.last_name}`.trim() : u.username
})

function sair() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="nav-rail">
    <div class="nr-topo">
      <Logo3D :tamanho="30" />
      <strong>3D Sistemas</strong>
      <button type="button" class="nr-sino" aria-label="Notificações" @click="emit('abrir-notificacoes')">
        🔔
        <span v-if="notificacoes.naoLidas > 0" class="nr-badge">
          {{ notificacoes.naoLidas > 9 ? '9+' : notificacoes.naoLidas }}
        </span>
      </button>
    </div>

    <nav class="nr-nav">
      <template v-for="g in grupos" :key="g.titulo">
        <div class="nr-grupo">{{ g.titulo }}</div>
        <RouterLink v-for="item in g.itens" :key="item.to" :to="item.to" class="nr-item" style="display: flex; align-items: center; justify-content: space-between">
          {{ item.rotulo }}
          <span v-if="item.contador" class="nr-badge" style="position: static">{{ item.contador > 9 ? '9+' : item.contador }}</span>
        </RouterLink>
      </template>
    </nav>

    <div class="nr-rodape">
      <div class="nr-usuario">
        <strong>{{ nome }}</strong>
        <span v-if="auth.user?.cargo">{{ auth.user.cargo }}</span>
      </div>
      <button type="button" class="nr-item nr-sair" @click="sair">Sair</button>
    </div>
  </aside>
</template>

<style scoped>
.nav-rail {
  padding: 16px 0;
  gap: 4px;
}
.nr-topo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 18px 16px;
}
.nr-topo strong {
  font-size: 17px;
  flex: 1;
}
.nr-sino {
  border: none;
  background: none;
  font-size: 18px;
  position: relative;
  padding: 4px;
}
.nr-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: var(--danger);
  color: #fff;
  border-radius: 999px;
  font-size: 10px;
  min-width: 15px;
  height: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
}
.nr-nav {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 4px 10px;
}
.nr-grupo {
  padding: 14px 8px 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.nr-item {
  display: block;
  text-align: left;
  text-decoration: none;
  padding: 9px 10px;
  border-radius: 8px;
  font-size: 14.5px;
  color: var(--text);
  border: none;
  background: none;
  width: 100%;
  cursor: pointer;
}
.nr-item:hover {
  background: var(--bg);
}
.nr-item.router-link-active {
  background: var(--accent);
  color: var(--accent-contrast);
  font-weight: 600;
}
.nr-rodape {
  padding: 12px 18px 0;
  border-top: 1px solid var(--border);
  margin: 8px 12px 0;
}
.nr-usuario {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  margin-bottom: 8px;
}
.nr-usuario span {
  color: var(--text-muted);
}
.nr-sair {
  color: var(--danger);
}
.nr-sair:hover {
  background: var(--bg);
}
</style>
