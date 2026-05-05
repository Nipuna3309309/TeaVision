export function money(value = 0) {
  const n = Number(value ?? 0)
  return `Rs. ${n.toLocaleString('en-LK', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export function integer(value = 0) {
  const n = Number(value ?? 0)
  return n.toLocaleString('en-LK', {
    maximumFractionDigits: 0,
  })
}

export function percent(value = 0) {
  const n = Number(value ?? 0)
  return `${n.toFixed(2)}%`
}