<script setup>
defineProps({
  // altura em px; a largura acompanha a proporção do logo (240x176)
  tamanho: { type: Number, default: 32 },
  cor: { type: String, default: '#5b84c4' },
})
</script>

<template>
  <svg
    :height="tamanho"
    :width="Math.round((tamanho * 240) / 176)"
    viewBox="0 0 240 176"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-label="3D Sistemas"
  >
    <g
      fill="none"
      :stroke="cor"
      stroke-width="13"
      stroke-linejoin="round"
      stroke-linecap="round"
    >
      <path d="M150 130 C172 130 189 114 189 93 C189 75 176 61 158 59 C157 36 138 18 115 18 C99 18 85 27 78 41" />
      <path d="M64 144 C42 144 24 126 24 103 C24 84 37 69 55 65 C57 38 80 18 107 18 C129 18 148 31 156 51 C177 50 194 67 194 89 C194 112 176 130 153 130 Z" />
    </g>
    <text
      x="106"
      y="110"
      text-anchor="middle"
      font-family="Arial Black, Arial, Helvetica, sans-serif"
      font-weight="900"
      font-size="68"
      letter-spacing="-4"
      :fill="cor"
    >3D</text>
  </svg>
</template>
