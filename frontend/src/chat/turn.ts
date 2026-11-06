import type { ChatEvent, TurnMetricsView } from '@/api/types'

export interface TurnState {
  bubbles: string[]
  typing: boolean
  status: 'streaming' | 'done' | 'failed'
  partial: boolean
  metrics?: TurnMetricsView
  traceId?: string
}

export const initialTurn: TurnState = { bubbles: [], typing: false, status: 'streaming', partial: false }

/** One agent reply, folded from its SSE events (bubbles arrive here already paced). */
export function reduceTurn(state: TurnState, event: ChatEvent): TurnState {
  switch (event.type) {
    case 'typing':
      return { ...state, typing: true }
    case 'bubble':
      return { ...state, bubbles: [...state.bubbles, event.text] }
    case 'metrics': {
      const { type: _, ...metrics } = event
      return { ...state, metrics }
    }
    case 'done':
      return { ...state, typing: false, status: 'done', traceId: event.trace_id }
    case 'error':
      return { ...state, typing: false, status: 'failed', partial: event.partial }
  }
}
