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
  if (!dbPromise) {
    const tentativa = abrirCru()
    dbPromise = tentativa
    // Uma abertura que falha NÃO pode desligar o IndexedDB pelo resto da
    // sessão. O caso real: outra aba ainda segura a versão antiga do banco, o
    // `onblocked` dispara e rejeita — mas segundos depois aquela aba recarrega
    // e a abertura passaria. Guardar a promise rejeitada faria toda chamada
    // seguinte reusar a mesma rejeição para sempre; descartando-a, a próxima
    // chamada tenta de novo do zero.
    tentativa.catch(() => {
      if (dbPromise === tentativa) dbPromise = null
    })
  }
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
