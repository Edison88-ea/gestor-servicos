<script setup>
import { onMounted, reactive, ref } from 'vue'
import client from '../api/client'
import { useFuncionariosStore } from '../stores/funcionarios'

const props = defineProps({
  // null = novo; objeto = editando esse funcionário
  funcionario: { type: Object, default: null },
  somenteLeitura: { type: Boolean, default: false },
})
const emit = defineEmits(['salvo', 'cancelar'])

const store = useFuncionariosStore()

const PAPEIS = [
  ['TECNICO', 'Técnico'],
  ['ENCARREGADO', 'Encarregado'],
  ['GESTOR', 'Gestor'],
  ['RH', 'RH'],
  ['ADMIN', 'Administrador'],
]
const ESTADO_CIVIL = [
  ['', '—'],
  ['SOLTEIRO', 'Solteiro(a)'],
  ['CASADO', 'Casado(a)'],
  ['DIVORCIADO', 'Divorciado(a)'],
  ['VIUVO', 'Viúvo(a)'],
  ['UNIAO_ESTAVEL', 'União estável'],
]
const GENERO = [
  ['', '—'],
  ['MASCULINO', 'Masculino'],
  ['FEMININO', 'Feminino'],
  ['OUTRO', 'Outro'],
  ['NAO_INFORMAR', 'Prefiro não informar'],
]

const f = props.funcionario
const form = reactive({
  username: f?.username ?? '',
  password: '',
  papel: f?.papel ?? 'TECNICO',
  first_name: f?.first_name ?? '',
  last_name: f?.last_name ?? '',
  email: f?.email ?? '',
  telefone: f?.telefone ?? '',
  data_nascimento: f?.data_nascimento ?? '',
  estado_civil: f?.estado_civil ?? '',
  genero: f?.genero ?? '',
  nome_mae: f?.nome_mae ?? '',
  cpf: f?.cpf ?? '',
  rg: f?.rg ?? '',
  pis: f?.pis ?? '',
  ctps_numero: f?.ctps_numero ?? '',
  ctps_serie: f?.ctps_serie ?? '',
  cep: f?.cep ?? '',
  logradouro: f?.logradouro ?? '',
  numero_endereco: f?.numero_endereco ?? '',
  complemento: f?.complemento ?? '',
  bairro: f?.bairro ?? '',
  cidade: f?.cidade ?? '',
  estado: f?.estado ?? '',
  cargo: f?.cargo ?? '',
  encarregado_responsavel: f?.encarregado_responsavel ?? '',
  data_admissao: f?.data_admissao ?? '',
  data_desligamento: f?.data_desligamento ?? '',
  salario: f?.salario ?? '',
  registra_ponto: f?.registra_ponto ?? true,
  periodo1_inicio: (f?.periodo1_inicio ?? '').slice(0, 5),
  periodo1_fim: (f?.periodo1_fim ?? '').slice(0, 5),
  periodo2_inicio: (f?.periodo2_inicio ?? '').slice(0, 5),
  periodo2_fim: (f?.periodo2_fim ?? '').slice(0, 5),
  banco: f?.banco ?? '',
  agencia: f?.agencia ?? '',
  conta: f?.conta ?? '',
  pix: f?.pix ?? '',
  contato_emergencia_nome: f?.contato_emergencia_nome ?? '',
  contato_emergencia_telefone: f?.contato_emergencia_telefone ?? '',
  contato_emergencia_parentesco: f?.contato_emergencia_parentesco ?? '',
})

const encarregados = ref([])
const salvando = ref(false)
const inativando = ref(false)
const erro = ref('')
const mostrarSenha = ref(false)

function nomeDe(u) {
  return u.first_name ? `${u.first_name} ${u.last_name}`.trim() : u.username
}

onMounted(async () => {
  if (props.somenteLeitura) return
  try {
    const { data } = await client.get('/usuarios/', { params: { papel: 'ENCARREGADO' } })
    encarregados.value = (data.results ?? data).filter((u) => u.id !== f?.id)
  } catch {
    // sem os encarregados o campo vira texto vazio; não bloqueia salvar
  }
})

function montarPayload() {
  const p = { ...form }
  // datas/horas/números vazios viram null (o back rejeita '')
  for (const k of [
    'data_nascimento', 'data_admissao', 'data_desligamento', 'salario',
    'periodo1_inicio', 'periodo1_fim', 'periodo2_inicio', 'periodo2_fim',
    'encarregado_responsavel',
  ]) {
    if (p[k] === '' || p[k] == null) p[k] = null
  }
  if (!p.password) delete p.password
  return p
}

async function salvar() {
  erro.value = ''
  if (!form.username.trim()) {
    erro.value = 'Informe o usuário de acesso.'
    return
  }
  if (!form.first_name.trim()) {
    erro.value = 'Informe o nome.'
    return
  }
  salvando.value = true
  try {
    const salvo = props.funcionario
      ? await store.atualizar(props.funcionario.id, montarPayload())
      : await store.criar(montarPayload())
    emit('salvo', salvo)
  } catch (e) {
    const d = e?.response?.data
    erro.value =
      (d && typeof d === 'object' && Object.values(d).flat()[0]) ||
      'Não foi possível salvar. Verifique os dados e tente de novo.'
  } finally {
    salvando.value = false
  }
}

async function inativar() {
  if (!props.funcionario) return
  if (!window.confirm(`Desligar ${nomeDe(form)}? Ele perde o acesso, mas o histórico é mantido.`)) return
  inativando.value = true
  erro.value = ''
  try {
    await store.inativar(props.funcionario.id)
    emit('salvo', null)
  } catch {
    erro.value = 'Não foi possível desligar o funcionário.'
  } finally {
    inativando.value = false
  }
}

async function reativar() {
  if (!props.funcionario) return
  inativando.value = true
  erro.value = ''
  try {
    const salvo = await store.atualizar(props.funcionario.id, { is_active: true, data_desligamento: null })
    emit('salvo', salvo)
  } catch {
    erro.value = 'Não foi possível reativar o funcionário.'
  } finally {
    inativando.value = false
  }
}
</script>

<template>
  <form class="func-form" :class="{ ro: somenteLeitura }" @submit.prevent="salvar">
    <div v-if="funcionario && !funcionario.is_active" class="aviso-inativo">
      Funcionário desligado{{ funcionario.data_desligamento ? ` em ${new Date(funcionario.data_desligamento + 'T00:00:00').toLocaleDateString('pt-BR')}` : '' }}.
    </div>

    <fieldset v-if="!somenteLeitura">
      <legend>Acesso</legend>
      <div class="grade">
        <label>Usuário *<input v-model="form.username" type="text" autocapitalize="none" /></label>
        <label>
          {{ funcionario ? 'Nova senha (deixe em branco para manter)' : 'Senha inicial *' }}
          <span style="display: flex; gap: 6px">
            <input
              v-model="form.password"
              :type="mostrarSenha ? 'text' : 'password'"
              autocomplete="new-password"
              style="flex: 1"
            />
            <button
              type="button"
              class="btn-secondary"
              style="padding: 0 10px; font-size: 13px"
              @click="mostrarSenha = !mostrarSenha"
            >
              {{ mostrarSenha ? 'Ocultar' : 'Mostrar' }}
            </button>
          </span>
        </label>
        <label>Papel<select v-model="form.papel">
          <option v-for="[v, r] in PAPEIS" :key="v" :value="v">{{ r }}</option>
        </select></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Identificação</legend>
      <div class="grade">
        <label>Nome *<input v-model="form.first_name" type="text" :disabled="somenteLeitura" /></label>
        <label>Sobrenome<input v-model="form.last_name" type="text" :disabled="somenteLeitura" /></label>
        <label>E-mail<input v-model="form.email" type="email" :disabled="somenteLeitura" /></label>
        <label>Telefone<input v-model="form.telefone" type="tel" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Dados pessoais</legend>
      <div class="grade">
        <label>Data de nascimento<input v-model="form.data_nascimento" type="date" :disabled="somenteLeitura" /></label>
        <label>Estado civil<select v-model="form.estado_civil" :disabled="somenteLeitura">
          <option v-for="[v, r] in ESTADO_CIVIL" :key="v" :value="v">{{ r }}</option>
        </select></label>
        <label>Gênero<select v-model="form.genero" :disabled="somenteLeitura">
          <option v-for="[v, r] in GENERO" :key="v" :value="v">{{ r }}</option>
        </select></label>
        <label>Nome da mãe<input v-model="form.nome_mae" type="text" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Documentos</legend>
      <div class="grade">
        <label>CPF<input v-model="form.cpf" type="text" :disabled="somenteLeitura" /></label>
        <label>RG<input v-model="form.rg" type="text" :disabled="somenteLeitura" /></label>
        <label>PIS/NIS<input v-model="form.pis" type="text" :disabled="somenteLeitura" /></label>
        <label>CTPS nº<input v-model="form.ctps_numero" type="text" :disabled="somenteLeitura" /></label>
        <label>CTPS série<input v-model="form.ctps_serie" type="text" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Endereço</legend>
      <div class="grade">
        <label>CEP<input v-model="form.cep" type="text" :disabled="somenteLeitura" /></label>
        <label class="col2">Logradouro<input v-model="form.logradouro" type="text" :disabled="somenteLeitura" /></label>
        <label>Número<input v-model="form.numero_endereco" type="text" :disabled="somenteLeitura" /></label>
        <label>Complemento<input v-model="form.complemento" type="text" :disabled="somenteLeitura" /></label>
        <label>Bairro<input v-model="form.bairro" type="text" :disabled="somenteLeitura" /></label>
        <label>Cidade<input v-model="form.cidade" type="text" :disabled="somenteLeitura" /></label>
        <label>UF<input v-model="form.estado" type="text" maxlength="2" style="text-transform: uppercase" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Contrato</legend>
      <div class="grade">
        <label>Cargo<input v-model="form.cargo" type="text" :disabled="somenteLeitura" /></label>
        <label v-if="somenteLeitura">Encarregado responsável
          <input type="text" :value="funcionario?.encarregado_responsavel_nome || '—'" disabled />
        </label>
        <label v-else>Encarregado responsável<select v-model="form.encarregado_responsavel">
          <option value="">—</option>
          <option v-for="e in encarregados" :key="e.id" :value="e.id">{{ nomeDe(e) }}</option>
        </select></label>
        <label>Data de admissão<input v-model="form.data_admissao" type="date" :disabled="somenteLeitura" /></label>
        <label>Salário<input v-model="form.salario" type="number" step="0.01" min="0" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Jornada (segunda a sexta)</legend>
      <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
        <input v-model="form.registra_ponto" type="checkbox" :disabled="somenteLeitura" style="width: auto" />
        Registra ponto
      </label>
      <p class="dica" style="margin-top: 0">
        Desmarque para quem não bate ponto (sócios, diretoria). Continua tendo acesso ao sistema.
      </p>
      <div v-if="form.registra_ponto" class="grade">
        <label>Período 1 — início<input v-model="form.periodo1_inicio" type="time" :disabled="somenteLeitura" /></label>
        <label>Período 1 — fim<input v-model="form.periodo1_fim" type="time" :disabled="somenteLeitura" /></label>
        <label>Período 2 — início<input v-model="form.periodo2_inicio" type="time" :disabled="somenteLeitura" /></label>
        <label>Período 2 — fim<input v-model="form.periodo2_fim" type="time" :disabled="somenteLeitura" /></label>
      </div>
      <p v-if="form.registra_ponto" class="dica">Deixe o período 2 em branco se o funcionário tiver só um turno.</p>
    </fieldset>

    <fieldset>
      <legend>Dados bancários</legend>
      <div class="grade">
        <label>Banco<input v-model="form.banco" type="text" :disabled="somenteLeitura" /></label>
        <label>Agência<input v-model="form.agencia" type="text" :disabled="somenteLeitura" /></label>
        <label>Conta<input v-model="form.conta" type="text" :disabled="somenteLeitura" /></label>
        <label>Chave PIX<input v-model="form.pix" type="text" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Contato de emergência</legend>
      <div class="grade">
        <label>Nome<input v-model="form.contato_emergencia_nome" type="text" :disabled="somenteLeitura" /></label>
        <label>Telefone<input v-model="form.contato_emergencia_telefone" type="tel" :disabled="somenteLeitura" /></label>
        <label>Parentesco<input v-model="form.contato_emergencia_parentesco" type="text" :disabled="somenteLeitura" /></label>
      </div>
    </fieldset>

    <p v-if="erro" style="color: var(--danger)">{{ erro }}</p>

    <div v-if="somenteLeitura" style="display: flex; margin-top: 8px">
      <button type="button" class="btn-secondary" style="flex: 1" @click="emit('cancelar')">Voltar</button>
    </div>
    <div v-else style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px">
      <button type="button" class="btn-secondary" style="flex: 1; min-width: 120px" @click="emit('cancelar')">Cancelar</button>
      <button
        v-if="funcionario && funcionario.is_active"
        type="button"
        class="btn-secondary"
        style="flex: 1; min-width: 120px; color: var(--danger)"
        :disabled="inativando"
        @click="inativar"
      >
        Desligar
      </button>
      <button
        v-if="funcionario && !funcionario.is_active"
        type="button"
        class="btn-secondary"
        style="flex: 1; min-width: 120px"
        :disabled="inativando"
        @click="reativar"
      >
        Reativar
      </button>
      <button type="submit" class="btn" style="flex: 2; min-width: 160px" :disabled="salvando">
        {{ salvando ? 'Salvando...' : funcionario ? 'Salvar alterações' : 'Cadastrar funcionário' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.func-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
fieldset {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px 14px;
}
legend {
  font-weight: 600;
  font-size: 14px;
  padding: 0 6px;
}
.grade {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px 12px;
}
.grade .col2 {
  grid-column: span 2;
}
label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  color: var(--text-muted);
  gap: 4px;
}
input,
select {
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 15px;
}
input:disabled,
select:disabled {
  background: var(--bg);
  color: var(--text);
  opacity: 1;
}
.dica {
  font-size: 12px;
  color: var(--text-muted);
  margin: 8px 0 0;
}
.aviso-inativo {
  background: var(--danger);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
}
</style>
