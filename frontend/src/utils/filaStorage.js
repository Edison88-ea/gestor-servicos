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

// Arrays/objetos de uma store Pinia são Proxies reativos — o algoritmo de
// structured clone do IndexedDB não sabe cloná-los (DataCloneError), mesmo
// que os dados por trás sejam simples. O round-trip por JSON os reduz a
// dados planos antes de gravar, sem exigir que quem chama saiba disso.
export async function salvarFila(chave, valor) {
  await filaStore.definir(chave, JSON.parse(JSON.stringify(valor)))
}
