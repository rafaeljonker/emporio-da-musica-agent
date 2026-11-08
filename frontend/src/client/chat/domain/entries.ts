// The chat log: one entry per exchange or customer-switch divider, folded from SSE events.
import type { ChatEvent, DemoCustomer } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import type { TurnRecord } from './metrics'
import { reduceTurn, type TurnState } from './turn'

export interface Exchange {
  id: string
  text: string
  sentAt: Date
  repliedAt?: Date
  turn: TurnState
  /** From send to the last bubble appended, pacing included ("na tela"). */
  screenMs?: number
  /** A "Manda de novo?" resend: the user bubble is already on screen above. */
  resend?: boolean
  /** Its error line was replaced by a resend. */
  retried?: boolean
}

/** A quiet line in the log after a customer switch; the thread above it stays. */
export interface Divider {
  id: string
  divider: string
}

export type Entry = Exchange | Divider

export const isExchange = (e: Entry): e is Exchange => 'turn' in e

/** Folds one event into exchange `id`; `now` stamps the reply, `screenMs` times a bubble. */
export function applyEvent(entries: Entry[], id: string, event: ChatEvent, now: Date, screenMs: number): Entry[] {
  return entries.map((x) =>
    x.id !== id || !isExchange(x)
      ? x
      : {
          ...x,
          turn: reduceTurn(x.turn, event),
          repliedAt: event.type === 'done' ? now : x.repliedAt,
          screenMs: event.type === 'bubble' ? screenMs : x.screenMs,
        },
  )
}

/** A reply is being generated somewhere in the log. */
export const isTyping = (entries: Entry[]) => entries.some((e) => isExchange(e) && e.turn.typing)

/** Changes whenever the log's visible content grows, for scroll-follow. */
export const contentKey = (entries: Entry[], queued: number | undefined, typing: boolean) =>
  `${entries.map((e) => (isExchange(e) ? `${e.turn.bubbles.length}${e.turn.status}${e.retried}` : '-')).join()}:${queued}:${typing}`

/** Messages the reader sent (resends excluded), queued ones included. */
export const userLines = (entries: Entry[], queued: number) =>
  entries.filter((e) => isExchange(e) && !e.resend).length + queued

/** One record per reply with metrics; local mode costs R$ 0, as the panel says. */
export const toTurnRecords = (entries: Entry[], local: boolean): TurnRecord[] =>
  entries.flatMap((e): TurnRecord[] =>
    isExchange(e) && e.turn.metrics
      ? [{ metrics: local ? { ...e.turn.metrics, cost_brl: '0' } : e.turn.metrics, screenMs: e.screenMs ?? 0 }]
      : [],
  )

/** The divider after a switch: "Agora como Ana", or anonymous. */
export function dividerText(list: DemoCustomer[], id: number | null): string {
  const name = list.find((c) => c.id === id)?.name.split(' ')[0]
  return name ? copy.demo.nowAs(name) : copy.demo.nowAnonymous
}
