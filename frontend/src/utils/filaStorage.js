import { filaStore } from './idb'

// Migração automática, uma vez: se a fila ainda não existir no IndexedDB mas
// houver algo salvo no localStorage sob essa chave (versão antiga do app),
// move os dados pro IndexedDB e apaga do localStorage. Daí em diante o
// localStorage nunca mais é a fonte de verdade para essa chave.
//
// Contrato de erro: uma falha de LEITURA do IndexedDB é propagada (rejeita).
// Quem chama é o `iniciar()` das stores, que nesse caso deixa a store
// *não-iniciada* e sem mexer no state — o próximo gatilho de sincronização
// tenta de novo. Engolir a falha aqui e devolver `valorPadrao` seria pior que
// o bug original: a store acharia que a fila está vazia e a primeira gravação
// sobrescreveria, com `[]`, a fila que estava durável em disco.
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
  try {
    await filaStore.definir(chave, migrado)
    // Só sai do localStorage depois de estar gravado no IndexedDB.
    localStorage.removeItem(chave)
  } catch (e) {
    // Não conseguiu gravar no IndexedDB: mantém o valor no localStorage para
    // a migração ser tentada de novo numa próxima carga — mas devolve os
    // dados já lidos, então a sessão atual funciona normalmente.
    console.warn(`[filaStorage] falha ao migrar "${chave}" para o IndexedDB`, e)
  }
  return migrado
}

// Arrays/objetos de uma store Pinia são Proxies reativos — o algoritmo de
// structured clone do IndexedDB não sabe cloná-los (DataCloneError), mesmo
// que os dados por trás sejam simples. O round-trip por JSON os reduz a
// dados planos antes de gravar, sem exigir que quem chama saiba disso.
//
// Nunca lança: uma gravação que falha (quota estourada, IndexedDB bloqueado
// por outra aba, transação abortada) mantém os dados só em memória nesta
// sessão, como o app já fazia com o localStorage. É o comportamento previsto
// no design ("Erros e casos de borda") e é o que garante a invariante de
// `osOffline#_enviarOsLocal`/`#_enviarAcao`: elas tratam a própria falha via
// `erroSync` e não lançam — o que seria falso se o persist lançasse.
export async function salvarFila(chave, valor) {
  try {
    await filaStore.definir(chave, JSON.parse(JSON.stringify(valor)))
  } catch (e) {
    console.warn(`[filaStorage] falha ao gravar "${chave}" no IndexedDB`, e)
  }
}
