// Roda antes de cada arquivo de teste: registra um IndexedDB de verdade (em
// memória) e garante que testes que dependem de rede nunca vazam para fora
// (client.js é sempre mockado nos testes que o usam — ver stores/*.test.js).
import 'fake-indexeddb/auto'
