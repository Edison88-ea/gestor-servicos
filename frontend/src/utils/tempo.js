// Data local (YYYY-MM-DD) - toISOString() converte pra UTC e pode "pular"
// pro dia seguinte à noite em fusos negativos como o do Brasil.
export function dataLocalISO(data = new Date()) {
  const ano = data.getFullYear()
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${ano}-${mes}-${dia}`
}

export function formatarMinutos(minutos) {
  const sinal = minutos < 0 ? '-' : ''
  const abs = Math.abs(Math.round(minutos))
  const h = Math.floor(abs / 60)
  const m = abs % 60
  return `${sinal}${h}:${String(m).padStart(2, '0')}`
}
