// Armazenamento simples de blobs (fotos, assinatura) para uso offline.
// localStorage não guarda binário; IndexedDB guarda.

const DB = 'gestor-servicos'
const STORE = 'blobs'
let dbPromise = null

function abrirCru() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1)
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE)
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
  // Banco em estado ruim (ex.: sem o objectStore). Apaga e refaz.
  dbPromise = null
  await new Promise((resolve) => {
    const req = indexedDB.deleteDatabase(DB)
    req.onsuccess = req.onerror = req.onblocked = () => resolve()
  })
  return abrir()
}

async function comStore(modo, fn) {
  let db = await abrir()
  if (!db.objectStoreNames.contains(STORE)) {
    db = await recriar()
  }
  return new Promise((resolve, reject) => {
    let tx
    try {
      tx = db.transaction(STORE, modo)
    } catch (e) {
      reject(e)
      return
    }
    const req = fn(tx.objectStore(STORE))
    tx.oncomplete = () => resolve(req?.result)
    tx.onerror = () => reject(tx.error)
    tx.onabort = () => reject(tx.error)
  })
}

export const blobStore = {
  salvar: (chave, blob) => comStore('readwrite', (s) => s.put(blob, chave)),
  ler: (chave) => comStore('readonly', (s) => s.get(chave)),
  remover: (chave) => comStore('readwrite', (s) => s.delete(chave)),
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
