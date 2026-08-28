<script setup>
import { onMounted } from 'vue'
import { useCatalogoStore } from '../stores/catalogo'

// `relato` é um objeto reativo do pai; este componente edita os campos dele
// diretamente (formulário filho). Estrutura:
// { local, servicos: [str], materiais: [{descricao, quantidade, unidade}], equipe: [str], observacoes }
const props = defineProps({
  relato: { type: Object, required: true },
})

const catalogo = useCatalogoStore()
onMounted(() => catalogo.carregar())

const UNIDADES = ['', 'un', 'm', 'm²', 'pç', 'cx', 'kg', 'L', 'rolo']

function addServico() {
  props.relato.servicos.push('')
}
function removeServico(i) {
  props.relato.servicos.splice(i, 1)
}

function addMaterial() {
  props.relato.materiais.push({ descricao: '', quantidade: '', unidade: '' })
}
function removeMaterial(i) {
  props.relato.materiais.splice(i, 1)
}
function aoEscolherMaterial(m) {
  // preenche a unidade automaticamente se o material veio do catálogo
  if (!m.unidade) {
    const u = catalogo.unidadeDe(m.descricao)
    if (u) m.unidade = u
  }
}

function addPessoa() {
  props.relato.equipe.push('')
}
function removePessoa(i) {
  props.relato.equipe.splice(i, 1)
}
</script>

<template>
  <div class="relato">
    <datalist id="cat-servicos">
      <option v-for="s in catalogo.servicos" :key="s.descricao" :value="s.descricao" />
    </datalist>
    <datalist id="cat-materiais">
      <option v-for="m in catalogo.materiais" :key="m.descricao" :value="m.descricao" />
    </datalist>

    <label class="campo">
      <span>Local / área</span>
      <input v-model="relato.local" type="text" placeholder="Ex.: Gem BSUV, Sala de químicos, IP04" />
    </label>

    <div class="secao">
      <div class="secao-titulo">
        <span>Serviços executados</span>
        <button type="button" class="add" @click="addServico">+ serviço</button>
      </div>
      <p v-if="!relato.servicos.length" class="vazio">Nenhum serviço adicionado.</p>
      <div v-for="(s, i) in relato.servicos" :key="i" class="linha">
        <input
          :value="s"
          list="cat-servicos"
          placeholder="Ex.: Instalação de infraestrutura para 3 pontos de rede TI"
          @input="relato.servicos[i] = $event.target.value"
        />
        <button type="button" class="rem" @click="removeServico(i)" aria-label="Remover">✕</button>
      </div>
    </div>

    <div class="secao">
      <div class="secao-titulo">
        <span>Materiais</span>
        <button type="button" class="add" @click="addMaterial">+ material</button>
      </div>
      <p v-if="!relato.materiais.length" class="vazio">Nenhum material adicionado.</p>
      <div v-for="(m, i) in relato.materiais" :key="i" class="linha-material">
        <input
          v-model="m.descricao"
          list="cat-materiais"
          type="text"
          placeholder="Descrição"
          class="mat-desc"
          @change="aoEscolherMaterial(m)"
        />
        <input v-model="m.quantidade" type="text" inputmode="decimal" placeholder="Qtd" class="mat-qtd" />
        <select v-model="m.unidade" class="mat-un">
          <option v-for="u in UNIDADES" :key="u" :value="u">{{ u || '—' }}</option>
        </select>
        <button type="button" class="rem" @click="removeMaterial(i)" aria-label="Remover">✕</button>
      </div>
    </div>

    <div class="secao">
      <div class="secao-titulo">
        <span>Equipe</span>
        <button type="button" class="add" @click="addPessoa">+ pessoa</button>
      </div>
      <div v-for="(p, i) in relato.equipe" :key="i" class="linha">
        <input
          :value="p"
          type="text"
          placeholder="Nome"
          @input="relato.equipe[i] = $event.target.value"
        />
        <button type="button" class="rem" @click="removePessoa(i)" aria-label="Remover">✕</button>
      </div>
    </div>

    <label class="campo">
      <span>Observações (opcional)</span>
      <textarea v-model="relato.observacoes" rows="2" placeholder="Qualquer coisa que não se encaixe acima" />
    </label>
  </div>
</template>

<style scoped>
.relato {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.campo {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}
.secao {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.secao-titulo {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
}
.vazio {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}
.linha {
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.linha-material {
  display: grid;
  grid-template-columns: 1fr 64px 72px auto;
  gap: 6px;
  align-items: center;
}
input,
textarea,
select {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
}
textarea {
  resize: vertical;
}
.add {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--accent);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 600;
}
.rem {
  flex-shrink: 0;
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 16px;
  padding: 8px 4px;
  line-height: 1;
}
</style>
