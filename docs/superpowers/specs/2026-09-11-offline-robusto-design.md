# App totalmente offline em campo (OS, Clientes, Ponto) — design

## Contexto

O app já tem suporte offline parcial: `osOffline.js`, `clientes.js` e
`ponto.js` enfileiram escrita quando não há sinal. Um incidente recente
mostrou duas falhas sérias:

1. Uma OS criada offline ficou "presa" indefinidamente sem nenhum erro
   visível — causa raiz: o timeout do gunicorn (30s) era menor que o
   timeout de upload do front (60s), então o servidor derrubava a conexão
   sem responder, e o front tratava isso como "sem rede" e reenfileirava
   em silêncio, pra sempre. **Já corrigido** (gunicorn `--timeout 65`,
   commit `ddcd5c4`).
2. Depois de um logout forçado (refresh token na blacklist) seguido de uma
   troca de versão do PWA, uma OS pendente desapareceu do armazenamento
   local sem nunca ter sido enviada ao servidor — perda de dado real. A
   causa exata não foi confirmada (exigiria inspecionar o dispositivo
   diretamente), mas o armazenamento atual (localStorage, sujeito a esse
   tipo de situação) é a superfície de risco.

Este design cobre o que falta para o app "funcionar totalmente offline"
no que interessa ao técnico de campo, com a sincronização acontecendo tão
logo haja conexão, sem nunca perder ou esconder um envio.

## Escopo

**Dentro do escopo:** OS, Clientes (criar/editar/consultar) e Ponto —
os três fluxos que o técnico usa em campo. Os três já têm alguma fila
offline hoje; o trabalho é blindar e unificar a *visibilidade*, não
criar fila do zero.

**Fora do escopo:** Obras, Estoque, Funcionários, Solicitações de Ponto —
usados majoritariamente pelo gestor/RH, com sinal (escritório). Continuam
exigindo conexão, sem mudança neste trabalho.

**Não escolhido:** um motor de fila genérico único (unificando as 3
stores num só mecanismo). Foi considerado e descartado por ora — reforma
maior, mais arriscada logo após um incidente de perda de dado. Ver seção
"Abordagens consideradas".

## Abordagens consideradas

- **A — Motor único genérico de fila (IndexedDB)**: um módulo central
  guarda todo item pendente (OS/cliente/ponto) num formato comum; cada
  domínio só registra como executar sua ação. Mais elegante a longo
  prazo, mas exige reescrever as 3 stores de uma vez e migrar dados
  pendentes existentes sem perda no meio da troca. Risco maior, descartado
  por ora.
- **B — Reforçar as 3 stores existentes (escolhida)**: mantém a lógica de
  domínio de cada store como está (ela já é correta caso a caso — ex.:
  `ponto.js` já distingue corretamente recusa real de falha de rede);
  troca só o armazenamento (IndexedDB) e adiciona uma camada de
  visibilidade agregada por cima. Menor risco, incremental.
- **C — Background Sync API do navegador**: descartada — não existe no
  Safari/iOS, o aparelho real usado em campo.

## Componentes

### 1. Armazenamento: `utils/filaStorage.js`

Novo helper, mesmo espírito do `blobStore` já existente em `utils/idb.js`:
get/set por chave (string), mas em IndexedDB em vez de localStorage.
Usado pelas chaves que hoje vivem em localStorage:
`os_locais`, `os_acoes_pendentes`, `clientes_pendentes`,
`ponto_fila_offline`, `ponto_rejeitados`.

**Migração automática, uma vez**: na primeira carga após esta mudança,
qualquer valor ainda presente em localStorage sob essas chaves é lido,
gravado no IndexedDB, e só então removido do localStorage. Roda antes de
qualquer sincronização.

**Mudança estrutural**: como IndexedDB é assíncrono e o `state()` das
stores hoje carrega a fila de forma síncrona, cada store passa a:
- iniciar com a fila vazia no `state()`;
- ganhar uma ação `iniciar()` que faz a migração (se necessário) e carrega
  do IndexedDB;
- `App.vue` chama `iniciar()` das três stores uma vez, cedo (antes do
  primeiro `sincronizarTudo()`), e só então segue o fluxo normal.

**Blindagem do logout**: `auth.js#logout()` e o redirecionamento forçado
em `api/client.js` (refresh token rejeitado pelo servidor) **só** tocam em
`access_token` / `refresh_token` / `user`. Nunca iteram nem limpam
localStorage por inteiro, e nunca tocam no IndexedDB da fila. Isso é
garantido por teste automatizado (seção de testes), não só por comentário
no código.

### 2. Motor de sincronização: gatilhos centralizados

`sincronizarTudo()` (hoje dentro de `App.vue`, amarrado ao timer de 60s
do poll de notificações) passa a ser independente desse timer:

- Disparado por: evento `online`, `visibilitychange` (app volta ao
  primeiro plano), e um intervalo próprio de **20s** enquanto o app está
  aberto.
- Ordem fixa dentro do orquestrador: **clientes → OS → ponto** (OS pode
  depender de um cliente criado offline).
- Trava contra sobreposição: além dos flags `sincronizando` de cada
  store (já existem), o próprio `sincronizarTudo()` ganha uma trava para
  não rodar duas vezes ao mesmo tempo se dois gatilhos dispararem juntos.
- Retry simples, sem backoff exponencial: cada gatilho tenta de novo tudo
  que está pendente. Prioridade é confiabilidade e previsibilidade, não
  velocidade de detecção de rede.
- Gatilho manual: um botão "tentar agora", sempre visível (hoje só
  aparece quando há erro), chama o mesmo orquestrador.

### 3. Visibilidade: tela "Pendências"

- Tela nova, acessível pelo menu, com contador (mesmo padrão do sino de
  notificações). Lista, juntos: OS não enviadas, clientes não enviados,
  batidas de ponto não enviadas — cada item com status (`aguardando
  envio` / `erro: <mensagem>`) e um botão "tentar de novo" individual.
  É uma tela agregadora que **lê** das três stores existentes — não um
  motor novo.
- O banner no topo do app (já existente) passa a linkar para essa tela em
  vez de só mostrar um número.
- Paridade de mensagens: `osOffline.js` e `clientes.js` já mostram uma
  mensagem por item mesmo em falha de rede (corrigido no incidente
  anterior). `ponto.js` já trata corretamente recusa real (4xx →
  `rejeitados`, visível) vs. falha de rede (mantém na fila, sem
  descartar) — mas não expõe uma mensagem "tentando de novo
  automaticamente" por item de fila como as outras duas. Isso é
  nivelado, sem alterar a lógica de retry do `ponto.js`, que já está
  correta.

### 4. Testes automatizados (Vitest)

Frontend não tem nenhuma infraestrutura de teste hoje. Adiciona Vitest +
`fake-indexeddb` (simula IndexedDB em Node, sem navegador). Cobertura
focada no que já causou incidente — não é meta ter cobertura total do
app:

- Fila sobrevive a uma falha de rede no meio da sincronização (item
  continua lá, com mensagem, não some).
- Um item com erro não trava os outros da fila no mesmo ciclo (regressão
  corrigida no `clientes.js` no incidente anterior).
- `logout()` e o redirecionamento forçado por token expirado/blacklist
  não tocam na fila de pendências (IndexedDB).
- Migração localStorage → IndexedDB não perde item nenhum.
- Cliente criado offline: ao sincronizar, a OS que apontava pro id
  temporário é atualizada para o id real (`trocarClienteTmp`).

## Erros e casos de borda

- **Quota do IndexedDB estourada** (raro, mas possível com muitas fotos
  pendentes): mantém em memória nesta sessão só, como o código atual já
  faz para localStorage — sem lançar erro que interrompa o app.
- **Sincronização parcial** (ex.: cliente sincroniza mas OS falha
  depois): já tratado hoje via `os.sync` (progresso incremental) — sem
  mudança nesta parte.
- **Duas abas/sessões do mesmo usuário**: fora do escopo — o app não
  coordena entre abas hoje, e isso não piora nem melhora com esta
  mudança.

## Fora de escopo / não resolvido por este design

- A causa exata da perda de dado do incidente anterior não foi
  confirmada (precisaria de inspeção direta do dispositivo). Este design
  reduz a superfície de risco (armazenamento mais robusto, logout
  blindado, testes) mas não é uma prova formal de que o cenário exato de
  ontem nunca mais ocorrerá.
- Background Sync (retry com o app fechado) permanece fora, por não
  existir no Safari/iOS.
