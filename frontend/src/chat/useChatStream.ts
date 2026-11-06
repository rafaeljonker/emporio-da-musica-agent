import { useCallback, useEffect, useRef, useState } from 'react'
import { SessionExpired, streamChat } from '@/api/client'
import type { ChatEvent } from '@/api/types'
import { createPacer } from './pacing'
import { initialTurn, reduceTurn, type TurnState } from './turn'

export interface Exchange {
  id: string
  text: string
  sentAt: Date
  repliedAt?: Date
  turn: TurnState
}

/**
 * Sends one message per turn. The server does not sleep (ruling R5): each bubble waits its
 * `delay_ms` here, in arrival order, with typing still on, and is appended only when complete.
 */
export function useChatStream(onSessionExpired: () => void) {
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const busy = exchanges.at(-1)?.turn.status === 'streaming'
  // Aborted on unmount (e.g. Sair): the fetch stops and no paced bubble lands afterwards.
  const controller = useRef<AbortController | null>(null)
  useEffect(() => {
    const c = new AbortController()
    controller.current = c
    return () => c.abort()
  }, [])

  const send = useCallback(
    async (text: string) => {
      const id = crypto.randomUUID()
      setExchanges((xs) => [...xs, { id, text, sentAt: new Date(), turn: initialTurn }])
      const apply = (e: ChatEvent) =>
        setExchanges((xs) =>
          xs.map((x) =>
            x.id !== id
              ? x
              : { ...x, turn: reduceTurn(x.turn, e), repliedAt: e.type === 'done' ? new Date() : x.repliedAt },
          ),
        )

      const signal = controller.current!.signal
      const pacer = createPacer(apply, signal)

      try {
        await streamChat(text, pacer.push, signal)
      } catch (err) {
        if (signal.aborted) return
        if (err instanceof SessionExpired) {
          onSessionExpired()
          return
        }
      }
      await pacer.drained()
      // A dropped stream or a refused request (409, 429, network) ends the turn as an error.
      if (!pacer.ended && !signal.aborted) apply({ type: 'error', partial: pacer.shown > 0 })
    },
    [onSessionExpired],
  )

  return { exchanges, busy, send }
}
