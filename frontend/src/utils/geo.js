// O GPS do celular devolve coordenadas com muitas casas decimais
// (ex.: -23.550519123456). O backend guarda como DecimalField com precisão
// limitada, então arredondamos antes de enviar — 6 casas ≈ 11 cm, mais que
// suficiente para confirmar que o técnico estava no local.

export function arredondarCoord(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return null
  return Number(Number(valor).toFixed(6))
}

export function arredondarMetros(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return null
  return Number(Number(valor).toFixed(1))
}
