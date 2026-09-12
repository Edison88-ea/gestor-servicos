# App totalmente offline em campo (OS, Clientes, Ponto) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a fila offline de OS/Clientes/Ponto durável (IndexedDB em vez de localStorage), com sincronização disparada de forma centralizada e confiável, e visibilidade unificada de tudo que está pendente — sem nunca perder ou esconder um envio.

**Architecture:** As três stores existentes (`osOffline.js`, `clientes.js`, `ponto.js`) mantêm sua lógica de domínio; só trocam o armazenamento da fila de localStorage para IndexedDB via um helper novo e comum (`utils/filaStorage.js`, por cima de um `filaStore` genérico em `utils/idb.js`). `App.vue` centraliza os gatilhos de sincronização (antes amarrados ao timer de notificações) e uma tela nova (`PendenciasView.vue`) agrega a visão de tudo que está pendente nas três stores.

**Tech Stack:** Vue 3 + Pinia + Vite + IndexedDB (via `utils/idb.js`) + Vitest (novo, com `fake-indexeddb` e `jsdom`) para testes.

**Spec:** `docs/superpowers/specs/2026-09-11-offline-robusto-design.md`

## Global Constraints

- Escopo: só OS, Clientes e Ponto. Obras/Estoque/Funcionários/Solicitações de Ponto ficam de fora — sem mudança.
- Não criar um motor de fila genérico único — cada store (`osOffline.js`, `clientes.js`, `ponto.js`) mantém sua própria lógica de domínio; só o armazenamento é compartilhado.
- Nenhuma chamada de rede em teste automatizado — `client` (axios) é sempre mockado.
- `ponto.js#registrosRecentes`, `clientes.js#todos`/`resultados` (cache de leitura) **continuam em localStorage** — só as filas de *escrita pendente* migram para IndexedDB: `os_locais`, `os_acoes_pendentes`, `clientes_pendentes`, `ponto_fila_offline`, `ponto_rejeitados`.
- Intervalo do gatilho periódico de sincronização: 20 segundos.
- Testes automatizados cobrem só o que está listado na spec (fila/durabilidade) — não é meta cobertura total do app. Wiring de componentes Vue (App.vue, PendenciasView.vue, menu) é validado manualmente — não há harness de teste de componente neste projeto e não faz parte deste trabalho criar um.

---

### Task 1: Infraestrutura de testes (Vitest)

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.js`
- Create: `frontend/src/test/setup.js`
- Create: `frontend/src/test/smoke.test.js`

**Interfaces:**
- Produces: comando `npm test` (via `vitest run`) rodável a partir de `frontend/`; `fake-indexeddb` e `jsdom` disponíveis em todo teste.

- [ ] **Step 1: Instalar dependências de teste**

Run: `cd frontend && npm install -D vitest jsdom fake-indexeddb`

- [ ] **Step 2: Criar `frontend/src/test/setup.js`**

```js
// Roda antes de cada arquivo de teste: registra um IndexedDB de verdade (em
// memória) e garante que testes que dependem de rede nunca vazam para fora
// (client.js é sempre mockado nos testes que o usam — ver stores/*.test.js).
import 'fake-indexeddb/auto'
```

- [ ] **Step 3: Criar `frontend/vitest.config.js`**

```js
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
  },
})
```

- [ ] **Step 4: Adicionar script `test` em `frontend/package.json`**

No bloco `"scripts"`, adicionar (mantendo os já existentes `dev`/`build`/`preview`):

```json
"test": "vitest run"
```

- [ ] **Step 5: Criar um teste de fumaça — `frontend/src/test/smoke.test.js`**

```js
import { describe, expect, it } from 'vitest'

describe('infraestrutura de teste', () => {
  it('roda e enxerga o IndexedDB fake', () => {
    expect(typeof indexedDB).toBe('object')
    expect(typeof indexedDB.open).toBe('function')
  })
})
```

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `cd frontend && npm test`
Expected: 1 arquivo, 1 teste, PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.js frontend/src/test/setup.js frontend/src/test/smoke.test.js
git commit -m "test: configura Vitest + fake-indexeddb no frontend"
```

---

### Task 2: `filaStore` genérico em `utils/idb.js`

O `idb.js` atual só tem um object store (`blobs`, versão 1 do banco). Esta task generaliza pra suportar um segundo object store (`fila`) sem quebrar o que já existe (fotos/assinaturas continuam funcionando, mesmo em bancos já criados no aparelho do usuário).

**Files:**
- Modify: `frontend/src/utils/idb.js`
- Test: `frontend/src/utils/idb.test.js`

**Interfaces:**
- Produces: `filaStore.obter(chave): Promise<any|undefined>`, `filaStore.definir(chave, valor): Promise<void>`, `filaStore.remover(chave): Promise<void>` — exportados de `utils/idb.js`, ao lado do `blobStore` já existente.

- [ ] **Step 1: Escrever o teste (falhando)**

```js
// frontend/src/utils/idb.test.js
// @vitest-environment node
//
// Este arquivo roda em Node puro, não em jsdom (diferente do padrão do
// projeto). Motivo: o Blob do jsdom não é reconhecido pelo fake-indexeddb —
// grava algo, mas a leitura de volta vem como `{}` em vez do Blob de
// verdade. O Blob nativo do Node funciona corretamente com o
// fake-indexeddb. `filaStore`/`blobStore` não usam nenhuma API exclusiva de
// DOM, então rodar em Node aqui não perde cobertura nenhuma.
import { beforeEach, describe, expect, it } from 'vitest'
import { blobStore, filaStore } from './idb'

function novoNomeDb() {
  // Cada teste usa um banco isolado (nome único) — evita que a conexão
  // cacheada de um teste anterior interfira no próximo.
  return `teste-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

describe('filaStore', () => {
  it('guarda e lê um valor por chave', async () => {
    await filaStore.definir('minha-chave', [{ a: 1 }])
    const valor = await filaStore.obter('minha-chave')
    expect(valor).toEqual([{ a: 1 }])
  })

  it('retorna undefined para chave inexistente', async () => {
    const valor = await filaStore.obter('nao-existe-' + Math.random())
    expect(valor).toBeUndefined()
  })

  it('remove um valor', async () => {
    await filaStore.definir('pra-remover', [1, 2, 3])
    await filaStore.remover('pra-remover')
    const valor = await filaStore.obter('pra-remover')
    expect(valor).toBeUndefined()
  })
})

describe('blobStore (não regride com a mudança)', () => {
  it('continua guardando e lendo blobs', async () => {
    const blob = new Blob(['conteudo'], { type: 'text/plain' })
    await blobStore.salvar('blob-teste', blob)
    const lido = await blobStore.ler('blob-teste')
    expect(lido.size).toBe(blob.size)
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npm test -- idb.test.js`
Expected: FAIL — `filaStore` não existe ainda (`filaStore is not defined` / import undefined).

- [ ] **Step 3: Reescrever `frontend/src/utils/idb.js`**

```js
// Armazenamento em IndexedDB: blobs (fotos, assinaturas) e a fila de
// pendências offline (OS, clientes, ponto). localStorage não guarda
// binário e é frágil demais pra fila crítica de sincronização —
// IndexedDB resolve os dois casos.

const DB = 'gestor-servicos'
const VERSAO_DB = 2
const STORE_BLOBS = 'blobs'
const STORE_FILA = 'fila'
let dbPromise = null

function abrirCru() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, VERSAO_DB)
    req.onupgradeneeded = () => {
      // Banco já existente (versão 1, só com 'blobs') ganha o store novo sem
      // perder o que já tinha; banco novo ganha os dois de uma vez.
      if (!req.result.objectStoreNames.contains(STORE_BLOBS)) {
        req.result.createObjectStore(STORE_BLOBS)
      }
      if (!req.result.objectStoreNames.contains(STORE_FILA)) {
        req.result.createObjectStore(STORE_FILA)
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
    req.onblocked = () => reject(new Error('IndexedDB bloqueado'))
  })
}

function abrir() {
  if (!dbPromise) dbPromise = abrirCru()
  return dbPromise
}

async function recriar() {
  // Banco em estado ruim (ex.: sem algum dos object stores). Apaga e refaz.
  dbPromise = null
  await new Promise((resolve) => {
    const req = indexedDB.deleteDatabase(DB)
    req.onsuccess = req.onerror = req.onblocked = () => resolve()
  })
  return abrir()
}

async function comStore(nome, modo, fn) {
  let db = await abrir()
  if (!db.objectStoreNames.contains(nome)) {
    db = await recriar()
  }
  return new Promise((resolve, reject) => {
    let tx
    try {
      tx = db.transaction(nome, modo)
    } catch (e) {
      reject(e)
      return
    }
    const req = fn(tx.objectStore(nome))
    tx.oncomplete = () => resolve(req?.result)
    tx.onerror = () => reject(tx.error)
    tx.onabort = () => reject(tx.error)
  })
}

export const blobStore = {
  salvar: (chave, blob) => comStore(STORE_BLOBS, 'readwrite', (s) => s.put(blob, chave)),
  ler: (chave) => comStore(STORE_BLOBS, 'readonly', (s) => s.get(chave)),
  remover: (chave) => comStore(STORE_BLOBS, 'readwrite', (s) => s.delete(chave)),
}

// Fila de pendências offline (OS, clientes, ponto): valores JSON-clonáveis
// (arrays/objetos simples), guardados por chave.
export const filaStore = {
  obter: (chave) => comStore(STORE_FILA, 'readonly', (s) => s.get(chave)),
  definir: (chave, valor) => comStore(STORE_FILA, 'readwrite', (s) => s.put(valor, chave)),
  remover: (chave) => comStore(STORE_FILA, 'readwrite', (s) => s.delete(chave)),
}

export function novaChaveBlob(prefixo = 'blob') {
  return `${prefixo}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

// Copia os bytes para um Blob novo. Guardar um File direto no IndexedDB às
// vezes volta vazio (a referência ao arquivo do <input> "solta" depois que o
// input é limpo); um Blob com os bytes copiados não tem esse problema.
export async function paraBlobPersistente(arquivo) {
  const buffer = await arquivo.arrayBuffer()
  return new Blob([buffer], { type: arquivo.type || 'application/octet-stream' })
}
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd frontend && npm test -- idb.test.js`
Expected: 4 testes, PASS.

- [ ] **Step 5: Rodar o build do front pra garantir que nada quebrou**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/idb.js frontend/src/utils/idb.test.js
git commit -m "feat: adiciona filaStore (IndexedDB) ao lado do blobStore existente"
```

---

### Task 3: `utils/filaStorage.js` — carregar/salvar com migração automática

**Files:**
- Create: `frontend/src/utils/filaStorage.js`
- Test: `frontend/src/utils/filaStorage.test.js`

**Interfaces:**
- Consumes: `filaStore` de `./idb` (Task 2).
- Produces: `carregarFila(chave: string, valorPadrao = []): Promise<any>`, `salvarFila(chave: string, valor: any): Promise<void>` — usados pelas três stores nas próximas tasks.

- [ ] **Step 1: Escrever o teste (falhando)**

```js
// frontend/src/utils/filaStorage.test.js
import { beforeEach, describe, expect, it } from 'vitest'
import { carregarFila, salvarFila } from './filaStorage'

describe('carregarFila / salvarFila', () => {
  it('retorna o valor padrão quando não há nada salvo', async () => {
    const valor = await carregarFila('chave-vazia-' + Math.random(), [])
    expect(valor).toEqual([])
  })

  it('salva e recupera o mesmo valor', async () => {
    const chave = 'chave-teste-' + Math.random()
    await salvarFila(chave, [{ id: 1 }, { id: 2 }])
    const valor = await carregarFila(chave)
    expect(valor).toEqual([{ id: 1 }, { id: 2 }])
  })

  it('migra automaticamente um valor antigo do localStorage, uma vez só', async () => {
    const chave = 'chave-migracao-' + Math.random()
    localStorage.setItem(chave, JSON.stringify([{ id: 'antigo' }]))

    const valor = await carregarFila(chave)
    expect(valor).toEqual([{ id: 'antigo' }])
    // migrado: não fica mais no localStorage
    expect(localStorage.getItem(chave)).toBeNull()

    // uma segunda leitura não depende mais do localStorage
    const segunda = await carregarFila(chave)
    expect(segunda).toEqual([{ id: 'antigo' }])
  })

  it('localStorage com JSON inválido não quebra — usa o valor padrão', async () => {
    const chave = 'chave-invalida-' + Math.random()
    localStorage.setItem(chave, '{ isso não é json')
    const valor = await carregarFila(chave, [])
    expect(valor).toEqual([])
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npm test -- filaStorage.test.js`
Expected: FAIL — módulo `./filaStorage` não existe.

- [ ] **Step 3: Criar `frontend/src/utils/filaStorage.js`**

```js
import { filaStore } from './idb'

// Migração automática, uma vez: se a fila ainda não existir no IndexedDB mas
// houver algo salvo no localStorage sob essa chave (versão antiga do app),
// move os dados pro IndexedDB e apaga do localStorage. Daí em diante o
// localStorage nunca mais é a fonte de verdade para essa chave.
export async function carregarFila(chave, valorPadrao = []) {
  const doIdb = await filaStore.obter(chave)
  if (doIdb !== undefined) return doIdb

  const bruto = localStorage.getItem(chave)
  if (bruto == null) return valorPadrao

  let migrado = valorPadrao
  try {
    migrado = JSON.parse(bruto)
  } catch {
    migrado = valorPadrao
  }
  await filaStore.definir(chave, migrado)
  localStorage.removeItem(chave)
  return migrado
}

export async function salvarFila(chave, valor) {
  await filaStore.definir(chave, valor)
}
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd frontend && npm test -- filaStorage.test.js`
Expected: 4 testes, PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/filaStorage.js frontend/src/utils/filaStorage.test.js
git commit -m "feat: helper de fila offline em IndexedDB com migração automática do localStorage"
```

---

### Task 4: `osOffline.js` — migrar para IndexedDB

**Files:**
- Modify: `frontend/src/stores/osOffline.js`
- Modify: `frontend/src/stores/ordensServico.js:107,127,143,184` (adicionar `await` nas chamadas a `enfileirarAcao`)
- Modify: `frontend/src/stores/clientes.js:146` (adicionar `await` na chamada a `trocarClienteTmp`)
- Test: `frontend/src/stores/osOffline.test.js`

**Interfaces:**
- Consumes: `carregarFila`, `salvarFila` de `../utils/filaStorage` (Task 3).
- Produces: `useOsOfflineStore().iniciar(): Promise<void>` (nova ação — precisa ser chamada antes de qualquer outra ação da store; idempotente). Todas as ações que escrevem (`criarLocal`, `aplicarLocal`, `enfileirarAcao`, `trocarClienteTmp`, `descartarComErro`) passam a retornar `Promise` (antes eram síncronas) — quem já fazia `return offline.X(...)` dentro de função `async` não muda; quem chamava sem `await`/`return` precisa passar a usar `await`.

- [ ] **Step 1: Escrever os testes (falhando)**

```js
// frontend/src/stores/osOffline.test.js
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import client from '../api/client'
import { useOsOfflineStore } from './osOffline'

// navigator.onLine é getter-only em jsdom — Object.defineProperty é a forma
// confiável de sobrescrever em teste (atribuição direta pode ser ignorada
// em silêncio dependendo da versão do jsdom).
function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  definirOnline(true)
})

describe('osOffline — durabilidade', () => {
  it('iniciar() carrega o estado vazio quando não há nada salvo', async () => {
    const store = useOsOfflineStore()
    await store.iniciar()
    expect(store.locais).toEqual([])
    expect(store.acoesPendentes).toEqual([])
  })

  it('criarLocal + sincronizar com sucesso remove a OS da fila local', async () => {
    client.post.mockResolvedValueOnce({ data: { id: 42 } }) // criação

    const store = useOsOfflineStore()
    await store.iniciar()
    const os = await store.criarLocal({ cliente: 5, tipo_servico: 'Teste', descricao: 'x' })
    expect(store.locais).toHaveLength(1)

    await store.sincronizar()
    expect(store.locais).toHaveLength(0)
    expect(client.post).toHaveBeenCalledWith('/ordens-servico/', expect.objectContaining({ cliente: 5 }))
  })

  it('falha sem resposta HTTP mantém a OS na fila, com mensagem, e não trava as outras', async () => {
    const semResposta = new Error('Network Error') // sem e.response, como um timeout/conexão derrubada
    client.post
      .mockRejectedValueOnce(semResposta) // 1ª OS falha ao criar
      .mockResolvedValueOnce({ data: { id: 99 } }) // 2ª OS cria com sucesso

    const store = useOsOfflineStore()
    await store.iniciar()
    await store.criarLocal({ cliente: 1, tipo_servico: 'A', descricao: 'a' })
    await store.criarLocal({ cliente: 2, tipo_servico: 'B', descricao: 'b' })

    await store.sincronizar()

    expect(store.locais).toHaveLength(1) // só a que falhou continua
    expect(store.locais[0].erroSync).toMatch(/Falha de conexão/)
    expect(store.temErro).toBe(true)
  })

  it('persiste no IndexedDB entre instâncias da store (sobrevive a um "reload")', async () => {
    const store1 = useOsOfflineStore()
    await store1.iniciar()
    await store1.criarLocal({ cliente: 1, tipo_servico: 'A', descricao: 'a' })

    // simula reabrir o app: nova instância de Pinia, nova store
    setActivePinia(createPinia())
    const store2 = useOsOfflineStore()
    await store2.iniciar()
    expect(store2.locais).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npm test -- osOffline.test.js`
Expected: FAIL — `store.iniciar is not a function` (ação ainda não existe).

- [ ] **Step 3: Editar `frontend/src/stores/osOffline.js`**

Remover as funções locais `carregar`/`salvar` (linhas 8-17 do arquivo atual) e o import fica:

```js
import { defineStore } from 'pinia'
import client from '../api/client'
import { blobStore, novaChaveBlob, paraBlobPersistente } from '../utils/idb'
import { carregarFila, salvarFila } from '../utils/filaStorage'

const KEY_LOCAIS = 'os_locais'
const KEY_ACOES = 'os_acoes_pendentes'
```

(`novoTmpId`, `mensagemFalha`, `osLocalVazia` continuam exatamente como estão.)

Trocar o `state()` e adicionar `iniciado`:

```js
export const useOsOfflineStore = defineStore('osOffline', {
  state: () => ({
    locais: [],
    acoesPendentes: [],
    sincronizando: false,
    iniciado: false,
  }),
```

Trocar `_persistir` e adicionar `iniciar`:

```js
    async iniciar() {
      if (this.iniciado) return
      this.iniciado = true
      this.locais = await carregarFila(KEY_LOCAIS)
      this.acoesPendentes = await carregarFila(KEY_ACOES)
    },

    async _persistir() {
      await salvarFila(KEY_LOCAIS, this.locais)
      await salvarFila(KEY_ACOES, this.acoesPendentes)
    },
```

Tornar `trocarClienteTmp`, `criarLocal`, `aplicarLocal`, `enfileirarAcao`, `descartarComErro` `async` e adicionar `await` antes de cada `this._persistir()`:

```js
    async trocarClienteTmp(tmpId, realId) {
      let mudou = false
      for (const os of this.locais) {
        if (os.cliente === tmpId) {
          os.cliente = realId
          mudou = true
        }
      }
      if (mudou) await this._persistir()
    },

    // --- criação/edição local (usadas quando offline ou a OS é tmp_) ---

    async criarLocal(dados) {
      const os = osLocalVazia(dados)
      this.locais.unshift(os)
      await this._persistir()
      return os
    },

    async aplicarLocal(id, mudancas) {
      const os = this.local(id)
      if (!os) return null
      Object.assign(os, mudancas)
      await this._persistir()
      return os
    },
```

Em `adicionarFotoLocal` e `concluirLocal` (já `async`), trocar `this._persistir()` por `await this._persistir()`.

```js
    async enfileirarAcao(osId, tipo, payload = {}, blobChave = null) {
      this.acoesPendentes.push({
        osId,
        tipo,
        payload,
        blobChave,
        criadoEm: new Date().toISOString(),
        erroSync: '',
      })
      await this._persistir()
    },
```

Em `_enviarOsLocal` e `_enviarAcao` (já `async`), trocar **todas** as ocorrências de `this._persistir()` por `await this._persistir()` (são 5 no total: após criar a OS, após iniciar, dentro do loop de fotos, após remover a OS com sucesso, e no `catch` de cada uma das duas funções).

```js
    async descartarComErro() {
      this.locais = this.locais.filter((o) => !o.erroSync)
      this.acoesPendentes = this.acoesPendentes.filter((a) => !a.erroSync)
      await this._persistir()
    },
```

- [ ] **Step 4: Atualizar os chamadores que não fazem `return`/`await`**

Em `frontend/src/stores/ordensServico.js`, adicionar `await` antes das 4 chamadas a `offline.enfileirarAcao(...)` (linhas 107, 127, 143, 184 do arquivo atual). Exemplo (linha 107, dentro de `iniciar()`):

```js
      } catch (erro) {
        if (semRede(erro)) {
          await offline.enfileirarAcao(id, 'iniciar')
          return this._otimista(id, { status: 'EM_ANDAMENTO' })
        }
        throw erro
      }
```

(o mesmo padrão para as chamadas em `pausar()`, `retomar()` e `concluir()`.)

Em `frontend/src/stores/clientes.js:146`, trocar:

```js
          osOffline.trocarClienteTmp(local.id, data.id)
```

por:

```js
          await osOffline.trocarClienteTmp(local.id, data.id)
```

(Esta segunda mudança será revisitada na Task 5, que mexe no resto de `clientes.js`.)

- [ ] **Step 5: Rodar e confirmar que os testes passam**

Run: `cd frontend && npm test -- osOffline.test.js`
Expected: 4 testes, PASS.

- [ ] **Step 6: Rodar o build do front**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/stores/osOffline.js frontend/src/stores/osOffline.test.js frontend/src/stores/ordensServico.js frontend/src/stores/clientes.js
git commit -m "feat: fila de OS offline passa a viver em IndexedDB (osOffline.js)"
```

---

### Task 5: `clientes.js` — migrar `pendentes` para IndexedDB

**Files:**
- Modify: `frontend/src/stores/clientes.js`
- Test: `frontend/src/stores/clientes.test.js`

**Interfaces:**
- Consumes: `carregarFila`, `salvarFila` de `../utils/filaStorage`; `useOsOfflineStore().trocarClienteTmp` (agora `async`, Task 4).
- Produces: `useClientesStore().iniciar(): Promise<void>` (nova ação, idempotente).
- Nota: `todos`/`resultados` (cache de leitura, chave `clientes_cache`) **continuam em localStorage**, síncronos — só `pendentes` (chave `clientes_pendentes`) migra.

- [ ] **Step 1: Escrever os testes (falhando)**

```js
// frontend/src/stores/clientes.test.js
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))
vi.mock('./osOffline', () => ({
  useOsOfflineStore: () => ({ trocarClienteTmp: vi.fn() }),
}))

import client from '../api/client'
import { useClientesStore } from './clientes'

// navigator.onLine é getter-only em jsdom — Object.defineProperty é a forma
// confiável de sobrescrever em teste (atribuição direta pode ser ignorada
// em silêncio dependendo da versão do jsdom).
function definirOnline(valor) {
  Object.defineProperty(navigator, 'onLine', { value: valor, configurable: true })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  definirOnline(true)
})

describe('clientes — durabilidade e fila', () => {
  it('iniciar() carrega pendentes vazio quando não há nada salvo', async () => {
    const store = useClientesStore()
    await store.iniciar()
    expect(store.pendentes).toEqual([])
  })

  it('criar offline enfileira e persiste entre instâncias da store', async () => {
    definirOnline(false)

    const store1 = useClientesStore()
    await store1.iniciar()
    await store1.criar({ nome: 'Cliente Teste' })
    expect(store1.pendentes).toHaveLength(1)

    setActivePinia(createPinia())
    const store2 = useClientesStore()
    await store2.iniciar()
    expect(store2.pendentes).toHaveLength(1)
    expect(store2.pendentes[0].nome).toBe('Cliente Teste')
  })

  it('um cliente pendente que falha sem resposta HTTP não trava os outros da fila', async () => {
    definirOnline(true)
    const store = useClientesStore()
    await store.iniciar()

    // dois pendentes já enfileirados (simulando estado offline anterior)
    store.pendentes = [
      { id: 'tmp_cli_1', _local: true, nome: 'Um' },
      { id: 'tmp_cli_2', _local: true, nome: 'Dois' },
    ]

    client.post
      .mockRejectedValueOnce(new Error('Network Error')) // 'Um' falha sem resposta
      .mockResolvedValueOnce({ data: { id: 501, nome: 'Dois' } }) // 'Dois' sincroniza

    await store.sincronizar()

    expect(store.pendentes).toHaveLength(1)
    expect(store.pendentes[0].nome).toBe('Um')
    expect(store.pendentes[0].erroSync).toMatch(/Falha de conexão/)
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npm test -- clientes.test.js`
Expected: FAIL — `store.iniciar is not a function`.

- [ ] **Step 3: Editar `frontend/src/stores/clientes.js`**

Import novo:

```js
import { defineStore } from 'pinia'
import client from '../api/client'
import { useOsOfflineStore } from './osOffline'
import { carregarFila, salvarFila } from '../utils/filaStorage'

const KEY = 'clientes_cache'
const PENDENTES_KEY = 'clientes_pendentes'
```

(As funções `ler`/`salvar` locais continuam existindo — ainda são usadas para `KEY`/`todos`. `novoTmpId`, `filtrar`, `comPendentes` não mudam.)

`state()` e `_persistir`:

```js
  state: () => ({
    resultados: [],
    todos: ler(KEY), // lista completa em cache, para busca offline
    pendentes: [], // clientes cadastrados sem sinal, aguardando envio
    carregando: false,
    sincronizando: false,
    iniciado: false,
  }),
  actions: {
    async iniciar() {
      if (this.iniciado) return
      this.iniciado = true
      this.pendentes = await carregarFila(PENDENTES_KEY)
      // um cliente pendente carregado agora também precisa aparecer na busca
      this.todos = comPendentes(this.todos, this.pendentes)
    },

    async _persistir() {
      salvar(KEY, this.todos) // cache de leitura: continua síncrono em localStorage
      await salvarFila(PENDENTES_KEY, this.pendentes)
    },
```

`_inserirLocal` e `_substituir` passam a `async`:

```js
    async _inserirLocal(c) {
      this.todos = [c, ...this.todos.filter((x) => x.id !== c.id)]
      this.resultados = [c, ...this.resultados.filter((x) => x.id !== c.id)]
      await this._persistir()
    },

    async _substituir(idAntigo, novo) {
      const troca = (lista) => lista.map((c) => (c.id === idAntigo ? novo : c))
      this.todos = troca(this.todos)
      this.resultados = troca(this.resultados)
      await this._persistir()
    },
```

Em `buscar()`, `criar()`, `atualizar()` e `sincronizar()`, adicionar `await` em toda chamada a `this._inserirLocal(...)` e `this._substituir(...)` que hoje não tem (são chamadas como statement solto, sem `return`/`await`). Ex. em `criar()`:

```js
    async criar(payload) {
      if (navigator.onLine) {
        try {
          const { data } = await client.post('/clientes/', payload)
          await this._inserirLocal(data)
          return data
        } catch (e) {
          if (e.response) throw e
        }
      }
      const local = { id: novoTmpId(), _local: true, ...payload }
      this.pendentes.push(local)
      await this._inserirLocal(local)
      return local
    },
```

Em `atualizar()`:

```js
    async atualizar(id, payload) {
      if (String(id).startsWith('tmp_')) {
        const p = this.pendentes.find((c) => c.id === id)
        if (p) Object.assign(p, payload)
        const atualizado = { ...(p || { id, _local: true }), ...payload }
        await this._substituir(id, atualizado)
        return atualizado
      }
      if (!navigator.onLine) {
        const e = new Error('offline')
        e.offline = true
        throw e
      }
      const { data } = await client.patch(`/clientes/${id}/`, payload)
      await this._substituir(id, data)
      return data
    },
```

Em `sincronizar()`:

```js
    async sincronizar() {
      if (this.sincronizando || !navigator.onLine || !this.pendentes.length) return
      this.sincronizando = true
      const osOffline = useOsOfflineStore()
      const restantes = []
      for (const local of this.pendentes) {
        try {
          const { id, _local, erroSync, ...payload } = local
          const { data } = await client.post('/clientes/', payload)
          await this._substituir(local.id, data)
          await osOffline.trocarClienteTmp(local.id, data.id)
        } catch (e) {
          local.erroSync = e.response
            ? e.response.data?.detail || `Erro ${e.response.status}`
            : 'Falha de conexão ao enviar — tentando de novo automaticamente'
          restantes.push(local)
        }
      }
      this.pendentes = restantes
      await this._persistir()
      this.sincronizando = false
    },
```

`carregarTodosParaCache()` não muda (só mexe em `todos`/`KEY`, que continuam em localStorage).

- [ ] **Step 4: Rodar e confirmar que os testes passam**

Run: `cd frontend && npm test -- clientes.test.js`
Expected: 3 testes, PASS.

- [ ] **Step 5: Rodar todos os testes e o build**

Run: `cd frontend && npm test && npm run build`
Expected: todos os testes (Tasks 1-5) PASS; build conclui sem erro.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/clientes.js frontend/src/stores/clientes.test.js
git commit -m "feat: fila de clientes offline passa a viver em IndexedDB (clientes.js)"
```

---

### Task 6: `ponto.js` — migrar fila/rejeitados para IndexedDB + paridade de mensagem

**Files:**
- Modify: `frontend/src/stores/ponto.js`
- Test: `frontend/src/stores/ponto.test.js`

**Interfaces:**
- Consumes: `carregarFila`, `salvarFila` de `../utils/filaStorage`.
- Produces: `usePontoStore().iniciar(): Promise<void>` (nova ação, idempotente).
- Nota: `registrosRecentes` (cache de leitura, chave `ponto_recentes`) **continua em localStorage** — só `filaOffline` (`ponto_fila_offline`) e `rejeitados` (`ponto_rejeitados`) migram.

- [ ] **Step 1: Escrever os testes (falhando)**

```js
// frontend/src/stores/ponto.test.js
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn(), get: vi.fn() },
}))

import client from '../api/client'
import { usePontoStore } from './ponto'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

describe('ponto — durabilidade da fila', () => {
  it('iniciar() carrega fila e rejeitados vazios quando não há nada salvo', async () => {
    const store = usePontoStore()
    await store.iniciar()
    expect(store.filaOffline).toEqual([])
    expect(store.rejeitados).toEqual([])
  })

  it('uma batida enfileirada por falta de rede persiste entre instâncias da store', async () => {
    client.post.mockRejectedValueOnce(new Error('Network Error'))

    const store1 = usePontoStore()
    await store1.iniciar()
    const resultado = await store1.registrarPonto('ENTRADA')
    expect(resultado).toBe('na_fila')
    expect(store1.filaOffline).toHaveLength(1)

    setActivePinia(createPinia())
    const store2 = usePontoStore()
    await store2.iniciar()
    expect(store2.filaOffline).toHaveLength(1)
  })

  it('falha de rede na sincronização mostra mensagem no item, sem descartar', async () => {
    client.post.mockRejectedValueOnce(new Error('Network Error'))
    const store = usePontoStore()
    await store.iniciar()
    await store1_enfileirarDireto(store)

    await store.sincronizarFila()

    expect(store.filaOffline).toHaveLength(1)
    expect(store.filaOffline[0].erroSync).toMatch(/tentando de novo/i)
  })
})

// helper local: enfileira uma batida sem passar pelo registrarPonto (que já
// faria uma chamada de rede própria)
async function store1_enfileirarDireto(store) {
  store.filaOffline.push({
    tipo: 'ENTRADA',
    registrado_em: new Date().toISOString(),
    origem_offline: true,
  })
  await store._persistirFila()
}
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd frontend && npm test -- ponto.test.js`
Expected: FAIL — `store.iniciar` e `store._persistirFila` não existem ainda.

- [ ] **Step 3: Editar `frontend/src/stores/ponto.js`**

Import novo:

```js
import { defineStore } from 'pinia'
import client from '../api/client'
import { dataLocalISO } from '../utils/tempo'
import { arredondarCoord, arredondarMetros } from '../utils/geo'
import { carregarFila, salvarFila } from '../utils/filaStorage'
```

(`ontemISO`, `QUEUE_KEY`, `REJEITADOS_KEY`, `RECENTES_KEY`, `carregar`/`salvar` locais, `deveManterNaFila` continuam como estão — `carregar`/`salvar` seguem usados só para `RECENTES_KEY`.)

`state()`:

```js
  state: () => ({
    registrosRecentes: carregar(RECENTES_KEY),
    filaOffline: [],
    rejeitados: [],
    sincronizando: false,
    iniciado: false,
  }),
```

Novas ações `iniciar()` e `_persistirFila()`, e `_enfileirar` vira `async`:

```js
    async iniciar() {
      if (this.iniciado) return
      this.iniciado = true
      this.filaOffline = await carregarFila(QUEUE_KEY)
      this.rejeitados = await carregarFila(REJEITADOS_KEY)
    },

    async _persistirFila() {
      await salvarFila(QUEUE_KEY, this.filaOffline)
    },

    async _persistirRejeitados() {
      await salvarFila(REJEITADOS_KEY, this.rejeitados)
    },

    async _enfileirar(registro) {
      const jaTem = this.filaOffline.some(
        (r) => r.tipo === registro.tipo && r.registrado_em === registro.registrado_em,
      )
      if (!jaTem) {
        this.filaOffline.push(registro)
        await this._persistirFila()
      }
    },
```

Em `registrarPonto`, adicionar `await` antes de `this._enfileirar(...)`.

Em `sincronizarFila`, adicionar por item um campo `erroSync` de falha de rede (paridade com OS/clientes) sem mudar a lógica de retry/rejeição existente, e trocar as gravações diretas em `localStorage` pelas novas ações assíncronas:

```js
    async sincronizarFila() {
      if (this.sincronizando || this.filaOffline.length === 0) return
      this.sincronizando = true

      const pendentes = [...this.filaOffline].sort(
        (a, b) => new Date(a.registrado_em) - new Date(b.registrado_em),
      )

      const restantes = []
      let servidorIndisponivel = false

      for (const registro of pendentes) {
        if (servidorIndisponivel) {
          restantes.push(registro)
          continue
        }
        try {
          await client.post('/registros-ponto/', registro)
        } catch (error) {
          if (deveManterNaFila(error)) {
            restantes.push({
              ...registro,
              erroSync: error.response
                ? `Erro ${error.response.status} — tentando de novo automaticamente`
                : 'Falha de conexão ao enviar — tentando de novo automaticamente',
            })
            servidorIndisponivel = true
          } else if (error.response?.data?.duplicado) {
            // já chegou por outro caminho — só descarta
          } else {
            const erroTipo = error.response?.data?.tipo
            const motivo =
              (Array.isArray(erroTipo) ? erroTipo[0] : erroTipo) ||
              error.response?.data?.detail ||
              'Batida recusada pelo servidor.'
            this.rejeitados.push({
              ...registro,
              motivo,
              rejeitado_em: new Date().toISOString(),
            })
            await this._persistirRejeitados()
          }
        }
      }

      this.filaOffline = restantes
      await this._persistirFila()
      this.sincronizando = false

      if (restantes.length === 0) {
        try {
          await this.carregarRegistrosHoje()
        } catch {
          // ficou offline de novo; recarrega numa próxima
        }
      }
    },
```

Em `descartarRejeitado` e `reenviarRejeitado`, trocar `salvar(REJEITADOS_KEY, this.rejeitados)` por `await this._persistirRejeitados()` (tornando ambas `async` — `descartarRejeitado` hoje não é `async`, precisa virar).

- [ ] **Step 4: Rodar e confirmar que os testes passam**

Run: `cd frontend && npm test -- ponto.test.js`
Expected: 3 testes, PASS.

- [ ] **Step 5: Rodar todos os testes e o build**

Run: `cd frontend && npm test && npm run build`
Expected: todos PASS; build sem erro.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/ponto.js frontend/src/stores/ponto.test.js
git commit -m "feat: fila de ponto offline passa a viver em IndexedDB + mensagem de erro por item"
```

---

### Task 7: Garantir que login/logout nunca tocam a fila offline

**Files:**
- Modify: `frontend/src/stores/auth.js` (só se o teste revelar um problema — ver Step 3)
- Modify: `frontend/src/api/client.js` (idem)
- Test: `frontend/src/stores/auth.test.js`

**Interfaces:**
- Nenhuma interface nova — task só de proteção/regressão.

- [ ] **Step 1: Escrever o teste**

```js
// frontend/src/stores/auth.test.js
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { filaStore } from '../utils/idb'

vi.mock('axios', async (importOriginal) => {
  const real = await importOriginal()
  return { ...real, default: { ...real.default, post: vi.fn().mockRejectedValue(new Error('sem rede')) } }
})

import { useAuthStore } from './auth'

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('logout não apaga fila offline pendente', () => {
  it('logout() só remove as chaves de sessão, nunca a fila do IndexedDB', async () => {
    await filaStore.definir('os_locais', [{ id: 'tmp_1' }])
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('refresh_token', 'r')
    localStorage.setItem('user', '{}')

    const auth = useAuthStore()
    auth.logout()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()

    const fila = await filaStore.obter('os_locais')
    expect(fila).toEqual([{ id: 'tmp_1' }])
  })
})
```

- [ ] **Step 2: Rodar**

Run: `cd frontend && npm test -- auth.test.js`
Expected: PASS já de imediato — `auth.js#logout()` hoje só mexe em `access_token`/`refresh_token`/`user`, nunca em IndexedDB. Este teste é uma trava de regressão, não uma correção.

Se o teste falhar (algo em `auth.js` mudou ou já tocava em mais chaves do que deveria), corrija `logout()` em `frontend/src/stores/auth.js` para remover **só** essas três chaves, e rode de novo até passar.

- [ ] **Step 3: Auditar manualmente o redirecionamento forçado em `api/client.js`**

Ler `frontend/src/api/client.js` (bloco do interceptor de resposta, refresh de token) e confirmar que o trecho que roda quando o servidor rejeita o refresh:

```js
        if (refreshError.response) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
        }
```

continua removendo só essas três chaves (nenhum `localStorage.clear()`, nenhum loop sobre chaves). Não precisa de teste automatizado aqui (é `window.location.href`, não testável em jsdom de forma значativa) — confirmação por leitura é suficiente; se houver qualquer divergência, corrigir para remover só essas três chaves.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/auth.test.js
git commit -m "test: trava de regressão — logout nunca apaga a fila offline pendente"
```

---

### Task 8: `App.vue` — gatilhos centralizados + inicialização das filas

**Files:**
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `iniciar()` de `osOffline`, `clientes`, `ponto` (Tasks 4-6).

- [ ] **Step 1: Chamar `iniciar()` das três stores antes de qualquer sincronização**

No `<script setup>` de `App.vue`, dentro do `watch(() => auth.isAuthenticated, ...)` (bloco `if (autenticado) { ... }`), ANTES da chamada a `sincronizarTudo()`, adicionar:

```js
    if (autenticado) {
      await Promise.all([osOffline.iniciar(), clientes.iniciar(), ponto.iniciar()])
      sincronizarTudo()
      if (navigator.onLine) {
        auth.atualizarPerfil()
        clientes.carregarTodosParaCache()
        ponto.carregarRegistrosHoje().catch(() => {})
        ordens.carregar().catch(() => {})
      }
      iniciarPollNotificacoes()
    } else {
```

(o `watch` callback precisa virar `async (autenticado) => { ... }` para o `await` funcionar.)

- [ ] **Step 2: Desacoplar `sincronizarTudo()` do timer de notificações e adicionar intervalo próprio + trava contra sobreposição**

Substituir o bloco de `iniciarPollNotificacoes`/`intervaloNotificacoes` e a função `sincronizarTudo` por:

```js
let intervaloNotificacoes = null
let intervaloSincronizacao = null
let sincronizando = false

async function sincronizarTudo() {
  if (sincronizando || !navigator.onLine || !auth.isAuthenticated) return
  sincronizando = true
  try {
    ponto.sincronizarFila()
    // clientes primeiro: uma OS criada offline pode apontar para um cliente
    // criado offline, que precisa ganhar id real antes de a OS subir.
    await clientes.sincronizar()
    await osOffline.sincronizar()
  } finally {
    sincronizando = false
  }
}

function pararPollNotificacoes() {
  if (intervaloNotificacoes) {
    clearInterval(intervaloNotificacoes)
    intervaloNotificacoes = null
  }
  if (intervaloSincronizacao) {
    clearInterval(intervaloSincronizacao)
    intervaloSincronizacao = null
  }
}

function iniciarPollNotificacoes() {
  if (intervaloNotificacoes) return
  notificacoes.atualizarContagem()
  intervaloNotificacoes = setInterval(() => {
    notificacoes.atualizarContagem()
  }, 60000)
  intervaloSincronizacao = setInterval(sincronizarTudo, 20000)
}
```

(`ponto.sincronizarFila()` não precisa de `await` aqui — já não precisava antes; mantém o comportamento existente de rodar em paralelo, sem bloquear clientes/OS.)

- [ ] **Step 3: Botão "tentar agora" sempre visível + link pra tela de Pendências**

No template, o bloco dos banners (`v-if="!online"` / `v-else-if="osOffline.temErro"` / etc.) ganha um link pra nova rota e um botão manual mesmo sem erro. Trocar:

```html
  <div v-if="!online" class="offline-banner">
    Sem conexão — o que você fizer será enviado quando o sinal voltar
    <template v-if="osOffline.pendentes || ponto.filaOffline.length">
      ({{ osOffline.pendentes + ponto.filaOffline.length }} pendente(s))
    </template>
  </div>
  <div
    v-else-if="osOffline.temErro"
    class="offline-banner"
    style="background: var(--danger); cursor: pointer"
    @click="osOffline.sincronizar()"
  >
    Alguns envios falharam — toque para tentar de novo
  </div>
  <div
    v-else-if="osOffline.sincronizando || ponto.sincronizando"
    class="offline-banner"
    style="background: var(--accent)"
  >
    Sincronizando…
  </div>
  <div v-else-if="osOffline.pendentes || ponto.filaOffline.length" class="offline-banner" style="background: var(--accent)">
    {{ osOffline.pendentes + ponto.filaOffline.length }} item(ns) aguardando envio
  </div>
```

por:

```html
  <div v-if="!online" class="offline-banner">
    Sem conexão — o que você fizer será enviado quando o sinal voltar
    <template v-if="osOffline.pendentes || ponto.filaOffline.length">
      ({{ osOffline.pendentes + ponto.filaOffline.length }} pendente(s))
    </template>
  </div>
  <RouterLink
    v-else-if="osOffline.temErro"
    to="/pendencias"
    class="offline-banner"
    style="background: var(--danger); display: block; text-decoration: none; color: inherit"
  >
    Alguns envios falharam — toque para ver
  </RouterLink>
  <div
    v-else-if="osOffline.sincronizando || ponto.sincronizando"
    class="offline-banner"
    style="background: var(--accent)"
  >
    Sincronizando…
  </div>
  <RouterLink
    v-else-if="osOffline.pendentes || ponto.filaOffline.length"
    to="/pendencias"
    class="offline-banner"
    style="background: var(--accent); display: block; text-decoration: none; color: inherit; cursor: pointer"
  >
    {{ osOffline.pendentes + ponto.filaOffline.length }} item(ns) aguardando envio — toque pra ver ou tentar agora
  </RouterLink>
```

(o gatilho manual "tentar agora" já existe de fato dentro da tela de Pendências, feita na Task 9 — o banner passa a linkar pra lá em vez de disparar o retry direto no toque, o que também resolve o toque acidental disparar uma sincronização sem o usuário ver o que está pendente.)

- [ ] **Step 4: Verificação manual**

Rodar `cd frontend && npm run build && npm run preview`, abrir o app, logar, e confirmar:
- Sem erro no console relacionado a `iniciar is not a function` ou similar.
- O banner de pendências (se houver algo pendente) ainda aparece e leva a algum lugar (a tela de Pendências só existe a partir da Task 9 — por ora é esperado dar 404 ou tela em branco; será corrigido lá).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: centraliza gatilhos de sincronização e inicializa as filas offline no boot do app"
```

---

### Task 9: Tela "Pendências" + navegação

**Files:**
- Create: `frontend/src/views/PendenciasView.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/composables/useNavGroups.js`
- Modify: `frontend/src/components/NavRail.vue`
- Modify: `frontend/src/components/MenuLateral.vue`

**Interfaces:**
- Consumes: `useOsOfflineStore()`, `useClientesStore()`, `usePontoStore()` (getters `pendentes`/`locais`/`acoesPendentes`/`filaOffline`/`rejeitados`).

- [ ] **Step 1: Criar a view**

```vue
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
      chave: `ponto-${r.registrado_em}`,
      titulo: `Ponto — ${r.tipo}`,
      detalhe: new Date(r.registrado_em).toLocaleString('pt-BR'),
      erro: r.erroSync || '',
    })
  }
  for (const r of ponto.rejeitados) {
    lista.push({
      chave: `ponto-rejeitado-${r.registrado_em}`,
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
```

- [ ] **Step 2: Adicionar a rota**

Em `frontend/src/router/index.js`, junto aos outros imports estáticos:

```js
import PendenciasView from '../views/PendenciasView.vue'
```

E na lista `routes`, junto às rotas de nível superior (perto de `/clientes`):

```js
  { path: '/pendencias', name: 'pendencias', component: PendenciasView, meta: { auth: true } },
```

- [ ] **Step 3: Adicionar item de menu com contador**

Em `frontend/src/composables/useNavGroups.js`, importar as três stores de pendência e calcular o total:

```js
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useOsOfflineStore } from '../stores/osOffline'
import { useClientesStore } from '../stores/clientes'
import { usePontoStore } from '../stores/ponto'
```

Dentro de `useNavGroups()`, antes do `return computed(...)`:

```js
  const osOffline = useOsOfflineStore()
  const clientes = useClientesStore()
  const ponto = usePontoStore()
```

E dentro do `computed`, calcular o contador e adicionar o item ao grupo "Operação" (antes de `Clientes`, por ser o mais urgente pro técnico ver):

```js
    const pendencias = osOffline.pendentes + clientes.pendentes.length + ponto.filaOffline.length

    grupos.push({
      titulo: 'Operação',
      itens: [
        { rotulo: 'Ordens de serviço', to: '/ordens-servico' },
        { rotulo: 'Pendências', to: '/pendencias', contador: pendencias || null },
        { rotulo: 'Obras', to: '/obras' },
        ...(podeEstoque ? [{ rotulo: 'Estoque', to: '/estoque' }] : []),
        { rotulo: 'Clientes', to: '/clientes' },
        ...(!ehGestao ? [{ rotulo: 'Meus dados', to: '/meus-dados' }] : []),
      ],
    })
```

- [ ] **Step 4: Renderizar o contador em `NavRail.vue`**

Trocar:

```html
        <RouterLink v-for="item in g.itens" :key="item.to" :to="item.to" class="nr-item">
          {{ item.rotulo }}
        </RouterLink>
```

por:

```html
        <RouterLink v-for="item in g.itens" :key="item.to" :to="item.to" class="nr-item" style="display: flex; align-items: center; justify-content: space-between">
          {{ item.rotulo }}
          <span v-if="item.contador" class="nr-badge" style="position: static">{{ item.contador > 9 ? '9+' : item.contador }}</span>
        </RouterLink>
```

- [ ] **Step 5: Renderizar o contador em `MenuLateral.vue`**

Trocar:

```html
          <button
            v-for="item in g.itens"
            :key="item.to"
            type="button"
            class="item-menu"
            @click="irPara(item.to)"
          >
            {{ item.rotulo }}
          </button>
```

por:

```html
          <button
            v-for="item in g.itens"
            :key="item.to"
            type="button"
            class="item-menu"
            style="display: flex; align-items: center; justify-content: space-between"
            @click="irPara(item.to)"
          >
            {{ item.rotulo }}
            <span
              v-if="item.contador"
              style="background: var(--danger); color: #fff; border-radius: 999px; font-size: 11px; min-width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; padding: 0 4px"
            >{{ item.contador > 9 ? '9+' : item.contador }}</span>
          </button>
```

- [ ] **Step 6: Verificação manual**

Rodar `cd frontend && npm run build && npm run preview`, logar, forçar um item pendente (ex.: desligar a rede do navegador via DevTools e criar/editar algo), e confirmar:
- O item "Pendências" aparece no menu com o número certo.
- A tela `/pendencias` lista o item, com "aguardando envio".
- O botão "Tentar agora" dispara a sincronização (voltar a rede antes de tocar).
- O banner no topo do app leva pra `/pendencias` ao tocar.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/PendenciasView.vue frontend/src/router/index.js frontend/src/composables/useNavGroups.js frontend/src/components/NavRail.vue frontend/src/components/MenuLateral.vue
git commit -m "feat: tela de Pendências agregando OS, clientes e ponto offline, com contador no menu"
```

---

### Task 10: Verificação final e PR

- [ ] **Step 1: Rodar a suíte inteira do frontend**

Run: `cd frontend && npm test`
Expected: todos os testes das Tasks 1-7, PASS.

- [ ] **Step 2: Build de produção**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro/aviso novo.

- [ ] **Step 3: Suíte do backend (garantir que nada foi tocado por engano)**

Run: `cd backend && python manage.py test` (ativar o virtualenv do projeto antes, se houver um)
Expected: 81/81 (ou o número atual) continuam passando — nenhum arquivo de backend foi tocado neste plano.

- [ ] **Step 4: Checklist manual de campo (sem servidor — modo avião)**

Com o app já logado uma vez (perfil em cache):
1. Ativar modo avião.
2. Criar uma OS nova (cliente novo, direto na tela de Nova OS).
3. Bater um ponto.
4. Conferir que "Pendências" mostra os dois itens.
5. Desativar o modo avião e esperar até 20s (ou tocar "Tentar agora" em Pendências).
6. Confirmar que os dois itens somem da lista e a OS aparece com número real em "Ordens de Serviço".

- [ ] **Step 5: Abrir PR**

```bash
git push origin feature/desktop-responsivo
gh pr create --base main --title "Offline robusto: fila em IndexedDB + tela de Pendências" --body "$(cat <<'EOF'
## Summary
- Fila de pendências de OS, Clientes e Ponto passa de localStorage para IndexedDB (mais durável), com migração automática e sem perda de dado já pendente.
- Sincronização centralizada em App.vue, com gatilho próprio (20s) independente do poll de notificações.
- Nova tela "Pendências" agrega tudo que está aguardando envio nas três áreas, com contador no menu e retry manual.
- Testes automatizados (Vitest, novo no frontend) cobrindo a fila e a durabilidade — o que causou o incidente anterior.

## Test plan
- [x] `npm test` (frontend) — suíte nova, todos os testes passam
- [x] `npm run build` (frontend) — sem erro
- [x] `python manage.py test` (backend) — sem regressão
- [ ] Checklist manual de campo em modo avião (ver plano)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Não fazer merge/deploy sem o usuário revisar e aprovar explicitamente** — isso afeta produção e o histórico recente já teve um incidente de perda de dado; a confirmação humana aqui é deliberada, não uma formalidade.
