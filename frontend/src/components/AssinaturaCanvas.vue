<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SignaturePad from 'signature_pad'

const canvasEl = ref(null)
let pad = null

function redimensionar() {
  const canvas = canvasEl.value
  if (!canvas) return
  const proporcao = Math.max(window.devicePixelRatio || 1, 1)
  const dadosAnteriores = pad && !pad.isEmpty() ? pad.toData() : null
  canvas.width = canvas.offsetWidth * proporcao
  canvas.height = canvas.offsetHeight * proporcao
  canvas.getContext('2d').scale(proporcao, proporcao)
  if (dadosAnteriores) pad.fromData(dadosAnteriores)
}

function limpar() {
  pad?.clear()
}

function vazio() {
  return pad ? pad.isEmpty() : true
}

function dataUrlParaBlob(dataUrl) {
  const [cabecalho, base64] = dataUrl.split(',')
  const mime = cabecalho.match(/:(.*?);/)?.[1] || 'image/png'
  const bin = atob(base64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type: mime })
}

function paraArquivo() {
  return new Promise((resolve, reject) => {
    const canvas = canvasEl.value
    if (!canvas) {
      resolve(null)
      return
    }
    try {
      // No iOS o toBlob às vezes chama o callback com null; nesse caso
      // caímos para toDataURL (síncrono e confiável) e convertemos na mão.
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
          return
        }
        try {
          resolve(dataUrlParaBlob(canvas.toDataURL('image/png')))
        } catch (erro) {
          reject(erro)
        }
      }, 'image/png')
    } catch {
      try {
        resolve(dataUrlParaBlob(canvas.toDataURL('image/png')))
      } catch (erro) {
        reject(erro)
      }
    }
  })
}

defineExpose({ limpar, vazio, paraArquivo })

onMounted(() => {
  pad = new SignaturePad(canvasEl.value, { backgroundColor: 'rgb(255, 255, 255)' })
  redimensionar()
  window.addEventListener('resize', redimensionar)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', redimensionar)
  pad?.off()
})
</script>

<template>
  <div>
    <canvas
      ref="canvasEl"
      style="width: 100%; height: 160px; border: 1px dashed var(--border); border-radius: 8px; touch-action: none"
    />
    <button type="button" class="btn-secondary" style="margin-top: 6px; padding: 6px 12px; border-radius: 8px" @click="limpar">
      Limpar assinatura
    </button>
  </div>
</template>
