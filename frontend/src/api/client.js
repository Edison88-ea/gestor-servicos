import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  // Sem timeout, uma requisição num sinal ruim fica pendurada por minutos e a
  // tela parece travada. 20s é folgado para o uso normal; ao estourar, o axios
  // rejeita sem `response`, então o app trata como "sem conexão" e enfileira.
  timeout: 20000,
})

// Uploads (fotos da OS, assinatura do cliente) são multipart e sobem por 4G
// de campo — 20s estoura fácil e o técnico vê "verifique a conexão" mesmo com
// o servidor tendo recebido tudo. Dá mais fôlego quando o corpo é um FormData.
const TIMEOUT_UPLOAD = 60000

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    config.timeout = TIMEOUT_UPLOAD
  }
  return config
})

let isRefreshing = false
let pendingRequests = []

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    if (response && response.status === 401 && !config._retry) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        return Promise.reject(error)
      }
      config._retry = true

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push(() => resolve(client(config)))
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post('/api/auth/token/refresh/', {
          refresh: refreshToken,
        })
        localStorage.setItem('access_token', data.access)
        pendingRequests.forEach((cb) => cb())
        pendingRequests = []
        return client(config)
      } catch (refreshError) {
        // Só desloga se o servidor REJEITOU o refresh (token inválido/expirado).
        // Falha de rede (sem `response`) não pode deslogar — deixaria o técnico
        // preso fora do app, em campo, sem sinal. Nesse caso só rejeita e deixa
        // cada tela cair no cache offline.
        if (refreshError.response) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export default client
