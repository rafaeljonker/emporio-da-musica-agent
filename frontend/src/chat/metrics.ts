import type { TurnMetricsView } from '@/api/types'

export interface TurnRecord {
  metrics: TurnMetricsView
  /** Client-side: from send to the last bubble appended (pacing included). */
  screenMs: number
}

const brl4 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
const oneDecimal = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** The backend sends cost as a decimal string ("0.0042"); null means not measured yet. */
export const formatBRL = (value: string | null) => (value === null ? 'não medido' : `R$ ${brl4.format(Number(value))}`)

export const formatSeconds = (ms: number) => `${oneDecimal.format(ms / 1000)} s`

/** Summed in ten-thousandths of a real (the backend's precision), so no float drift; null when none was measured. */
export function totalCost(turns: TurnRecord[]): string | null {
  const known = turns.map((t) => t.metrics.cost_brl).filter((c) => c !== null)
  if (turns.length && !known.length) return null
  return (known.reduce((sum, c) => sum + Math.round(Number(c) * 10_000), 0) / 10_000).toFixed(4)
}

export function summary(turns: TurnRecord[]): string {
  const n = turns.length
  if (!n) return 'Métricas'
  return `Métricas · ${n} ${n === 1 ? 'resposta' : 'respostas'} · ${formatBRL(totalCost(turns))}`
}

export const historyLine = (n: number, t: TurnRecord) =>
  `Resposta ${n} · ${formatSeconds(t.screenMs)} · ${formatBRL(t.metrics.cost_brl)} · ${t.metrics.action}`
