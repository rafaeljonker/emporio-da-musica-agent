import { describe, expect, it } from 'vitest'
import type { TurnMetricsView } from '@/api/types'
import { formatBRL, formatSeconds, historyLine, summary, type TurnRecord } from './metrics'

const view = (cost_brl: string | null, action = 'sem ferramenta'): TurnMetricsView => ({
  input_tokens: 1284,
  output_tokens: 96,
  ms_model: 2400,
  ms_guard: 120,
  ms_llm: 2000,
  ms_tools: 210,
  cost_brl,
  cost_basis: 'Estimado pelo preço de lista do provedor',
  action,
})
const turn = (cost: string | null, screenMs = 4100, action?: string): TurnRecord => ({
  metrics: view(cost, action),
  screenMs,
})

describe('metrics formatting', () => {
  it('formatBRL uses comma and four decimals', () => {
    expect(formatBRL('0.0042')).toBe('R$ 0,0042')
    expect(formatBRL('1.5')).toBe('R$ 1,5000')
    expect(formatSeconds(2400)).toBe('2,4 s')
  })

  it('summary pluralizes and sums cost', () => {
    expect(summary([])).toBe('Métricas')
    expect(summary([turn('0.0042')])).toBe('Métricas · 1 resposta · R$ 0,0042')
    expect(summary([turn('0.0042'), turn('0.0031'), turn('0.0045')])).toBe('Métricas · 3 respostas · R$ 0,0118')
  })

  it('history line uses screen time and action', () => {
    expect(historyLine(3, turn('0.0042', 4100, 'busca no catálogo'))).toBe(
      'Resposta 3 · 4,1 s · R$ 0,0042 · busca no catálogo',
    )
  })

  it('null cost reads não medido', () => {
    expect(formatBRL(null)).toBe('não medido')
    expect(summary([turn(null), turn(null)])).toBe('Métricas · 2 respostas · não medido')
  })
})
