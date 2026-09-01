// Reduz uma foto antes de enviar: no 4G do técnico, uma foto de 3-4 MB da
// câmera do celular vira 20+ MB numa OS com 6 fotos. Redimensiona para no
// máximo 1600px no maior lado e recomprime como JPEG ~72% — o suficiente para
// uma foto de serviço, tipicamente 300-600 KB.

const MAX_LADO = 1600
const QUALIDADE = 0.72
const JA_PEQUENA = 900 * 1024

function trocarExtensaoParaJpg(nome) {
  const base = (nome || 'foto').replace(/\.[^.]+$/, '')
  return `${base}.jpg`
}

async function carregarBitmap(arquivo) {
  if (window.createImageBitmap) {
    // 'from-image': respeita a orientação EXIF (fotos do iPhone vêm giradas).
    return createImageBitmap(arquivo, { imageOrientation: 'from-image' })
  }
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = URL.createObjectURL(arquivo)
  })
}

export async function comprimirImagem(
  arquivo,
  { maxLado = MAX_LADO, qualidade = QUALIDADE } = {},
) {
  if (!arquivo || !arquivo.type || !arquivo.type.startsWith('image/')) return arquivo

  try {
    const bitmap = await carregarBitmap(arquivo)
    const largura = bitmap.width
    const altura = bitmap.height
    const escala = Math.min(1, maxLado / Math.max(largura, altura))

    // Já é pequena e não precisa reduzir: não mexe.
    if (escala >= 1 && arquivo.size < JA_PEQUENA) {
      bitmap.close?.()
      return arquivo
    }

    const w = Math.max(1, Math.round(largura * escala))
    const h = Math.max(1, Math.round(altura * escala))
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    canvas.getContext('2d').drawImage(bitmap, 0, 0, w, h)
    bitmap.close?.()

    const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', qualidade))
    if (!blob || blob.size >= arquivo.size) return arquivo // não melhorou: mantém

    return new File([blob], trocarExtensaoParaJpg(arquivo.name), {
      type: 'image/jpeg',
      lastModified: Date.now(),
    })
  } catch {
    // formato que o canvas não decodifica (ex.: HEIC) ou erro qualquer:
    // envia o original.
    return arquivo
  }
}
