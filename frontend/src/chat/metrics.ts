import type { TurnMetricsView } from '@/api/types'

export interface TurnRecord {
  metrics: TurnMetricsView
  /** Client-side: from send to the last bubble appended (pacing included). */
  screenMs: number
}

export function formatBRL(_value: string | null): string {
  throw new Error('not implemented')
}

export function formatSeconds(_ms: number): string {
  throw new Error('not implemented')
}

export function summary(_turns: TurnRecord[]): string {
  throw new Error('not implemented')
}

export function historyLine(_n: number, _t: TurnRecord): string {
  throw new Error('not implemented')
}
