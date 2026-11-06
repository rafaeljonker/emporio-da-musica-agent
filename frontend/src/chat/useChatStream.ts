import { useCallback, useState } from 'react'
import { SessionExpired, streamChat } from '@/api/client'
import type { ChatEvent } from '@/api/types'
import { initialTurn, reduceTurn, type TurnState } from './turn'

export interface Exchange {
  id: string
  text: string
  sentAt: Date
  repliedAt?: Date
  turn: TurnState
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Sends one message per turn. The server does not sleep (ruling R5): each bubble waits its
 * `delay_ms` here, in arrival order, with typing still on, and is appended only when complete.
 */
export function useChatStream(onSessionExpired: () => void) {
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const busy = exchanges.at(-1)?.turn.status === 'streaming'

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

      // Per-turn queue: events apply in arrival order, each bubble after its own delay.
      const run = { queue: Promise.resolve(), shown: 0, ended: false }
      const enqueue = (e: ChatEvent) => {
        run.queue = run.queue.then(async () => {
          if (e.type === 'bubble') {
            await sleep(e.delay_ms)
            run.shown += 1
          }
          if (e.type === 'done' || e.type === 'error') run.ended = true
          apply(e)
        })
      }

      try {
        await streamChat(text, enqueue)
      } catch (err) {
        if (err instanceof SessionExpired) {
          onSessionExpired()
          return
        }
      }
      await run.queue
      // A dropped stream or a refused request (409, 429, network) ends the turn as an error.
      if (!run.ended) apply({ type: 'error', partial: run.shown > 0 })
    },
    [onSessionExpired],
  )

  return { exchanges, busy, send }
}
