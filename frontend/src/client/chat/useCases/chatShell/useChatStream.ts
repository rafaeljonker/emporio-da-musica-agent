import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '@/client/shared/lib/api'
import type { ChatEvent } from '@/client/shared/lib/apiTypes'
import { createPacer } from '@/client/chat/domain/pacing'
import { initialTurn, reduceTurn, type TurnState } from '@/client/chat/domain/turn'

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

/**
 * Sends one message per turn; resolves false only when the session expired. The server does not sleep (ruling R5): each bubble waits its
 * `delay_ms` here, in arrival order, with typing still on, and is appended only when complete.
 */
export function useChatStream() {
  const [entries, setEntries] = useState<Entry[]>([])
  const busy = entries.some((e) => isExchange(e) && e.turn.status === 'streaming')
  // Aborted on unmount (e.g. Sair): the fetch stops and no paced bubble lands afterwards.
  const controller = useRef<AbortController | null>(null)
  useEffect(() => {
    const c = new AbortController()
    controller.current = c
    return () => c.abort()
  }, [])

  const send = useCallback(
    async (text: string, resend = false): Promise<boolean> => {
      const id = crypto.randomUUID()
      const t0 = performance.now()
      setEntries((xs) => [...xs, { id, text, sentAt: new Date(), turn: initialTurn, resend }])
      const apply = (e: ChatEvent) =>
        setEntries((xs) =>
          xs.map((x) =>
            x.id !== id || !isExchange(x)
              ? x
              : {
                  ...x,
                  turn: reduceTurn(x.turn, e),
                  repliedAt: e.type === 'done' ? new Date() : x.repliedAt,
                  screenMs: e.type === 'bubble' ? performance.now() - t0 : x.screenMs,
                },
          ),
        )

      const signal = controller.current!.signal
      const pacer = createPacer(apply, signal)

      const res = await streamChat(text, pacer.push, signal)
      if (!res.ok) {
        if (signal.aborted) return true
        if (res.error.code === 'unauthenticated') return false
      }
      await pacer.drained()
      // A dropped stream or a refused request (409, 429, network) ends the turn as an error.
      if (!pacer.ended && !signal.aborted) apply({ type: 'error', partial: pacer.shown > 0 })
      return true
    },
    [],
  )

  /** "Manda de novo?": drops that error line and sends the same text once more. */
  const resend = useCallback(
    (id: string) => {
      const failed = entries.find((e) => e.id === id)
      if (!failed || !isExchange(failed) || failed.retried || busy) return
      setEntries((xs) => xs.map((x) => (x.id === id ? { ...x, retried: true } : x)))
      void send(failed.text, true)
    },
    [entries, busy, send],
  )

  const addDivider = useCallback(
    (divider: string) => setEntries((xs) => [...xs, { id: crypto.randomUUID(), divider }]),
    [],
  )

  return { entries, busy, send, resend, addDivider }
}
