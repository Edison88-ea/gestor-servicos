<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const emit = defineEmits(['atualizacao'])

const mapaEl = ref(null)
const endereco = ref('')
const erro = ref('')
const carregando = ref(true)
const online = ref(navigator.onLine)

let mapa = null
let marcador = null
let circuloPrecisao = null
let watchId = null
let ultimaGeocodificacao = { lat: null, lng: null, em: 0 }
let destruido = false

const iconePosicao = L.divIcon({
  className: '',
  html: '<div style="width:16px;height:16px;border-radius:50%;background:#2563eb;border:3px solid white;box-shadow:0 0 4px rgba(0,0,0,0.4)"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
})

function distanciaMetros(lat1, lon1, lat2, lon2) {
  const R = 6371000
  const rad = Math.PI / 180
  const dLat = (lat2 - lat1) * rad
  const dLon = (lon2 - lon1) * rad
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

async function geocodificarSeNecessario(lat, lng) {
  const agora = Date.now()
  const moveuBastante =
    ultimaGeocodificacao.lat == null || distanciaMetros(lat, lng, ultimaGeocodificacao.lat, ultimaGeocodificacao.lng) > 25
  const tempoPassou = agora - ultimaGeocodificacao.em > 8000
  if (!moveuBastante && !tempoPassou) return

  ultimaGeocodificacao = { lat, lng, em: agora }
  try {
    // Nominatim (OpenStreetMap): serviço público gratuito, adequado para o
    // baixo volume de um app interno. Em caso de crescimento de uso,
    // considerar um provedor dedicado ou instância própria.
    const resposta = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`
    )
    if (!resposta.ok || destruido) return
    const dados = await resposta.json()
    endereco.value = dados.display_name || ''
    emit('atualizacao', { latitude: lat, longitude: lng, endereco: endereco.value })
  } catch {
    // sem internet ou serviço indisponível: segue sem endereço, não é bloqueante
  }
}

function atualizarPosicao(posicao) {
  if (destruido) return
  carregando.value = false
  erro.value = ''
  const { latitude, longitude, accuracy } = posicao.coords

  if (!mapa) {
    mapa = L.map(mapaEl.value, { zoomControl: false, attributionControl: false }).setView([latitude, longitude], 17)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapa)
    marcador = L.marker([latitude, longitude], { icon: iconePosicao }).addTo(mapa)
    circuloPrecisao = L.circle([latitude, longitude], { radius: accuracy, color: '#2563eb', fillOpacity: 0.1, weight: 1 }).addTo(mapa)
    setTimeout(() => {
      if (!destruido) mapa.invalidateSize()
    }, 100)
  } else {
    marcador.setLatLng([latitude, longitude])
    circuloPrecisao.setLatLng([latitude, longitude]).setRadius(accuracy)
    mapa.setView([latitude, longitude])
  }

  emit('atualizacao', { latitude, longitude, precisao: accuracy, endereco: endereco.value })
  geocodificarSeNecessario(latitude, longitude)
}

onMounted(() => {
  if (!navigator.geolocation) {
    erro.value = 'Geolocalização não é suportada neste dispositivo.'
    carregando.value = false
    return
  }
  watchId = navigator.geolocation.watchPosition(
    atualizarPosicao,
    () => {
      carregando.value = false
      erro.value = 'Não foi possível obter sua localização. Verifique a permissão do navegador.'
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
  )
})

onBeforeUnmount(() => {
  destruido = true
  if (watchId != null) navigator.geolocation.clearWatch(watchId)
  mapa?.remove()
})
</script>

<template>
  <div>
    <div ref="mapaEl" style="width: 100%; height: 200px; border-radius: 8px; overflow: hidden; background: var(--border)" />
    <p v-if="carregando" style="color: var(--text-muted); font-size: 13px; margin: 6px 0 0">Obtendo localização...</p>
    <p v-else-if="erro" style="color: var(--warning); font-size: 13px; margin: 6px 0 0">{{ erro }}</p>
    <p v-else-if="endereco" style="color: var(--text-muted); font-size: 13px; margin: 6px 0 0">📍 {{ endereco }}</p>
    <p v-else style="color: var(--text-muted); font-size: 13px; margin: 6px 0 0">
      📍 Localização capturada<span v-if="!online"> (endereço será buscado quando houver sinal)</span>
    </p>
  </div>
</template>
