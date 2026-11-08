import { useCallback, useEffect, useRef, useState } from 'react'
import { applyEvent, isExchange, type Entry } from '@/client/chat/domain/entries'
import { createPacer } from '@/client/chat/domain/pacing'
import { initialTurn } from '@/client/chat/domain/turn'
import { streamChat } from '@/client/shared/lib/api'
import type { ChatEvent } from '@/client/shared/lib/apiTypes'

export interface ChatStreamView {
  entries: Entry[]
  /** A reply is streaming: send and resend wait. */
  busy: boolean
  /** Resolves false only when the session expired (the queue keeps its text). */
  send: (text: string, resend?: boolean) => Promise<boolean>
  resend: (id: string) => void
  addDivider: (divider: string) => void
}

/**
 * Sends one message per turn. The server does not sleep (ruling R5): each bubble waits its
 * `delay_ms` here, in arrival order, with typing still on, and is appended only when complete.
 */
export function useChatStream(): ChatStreamView {
  const [entries, setEntries] = useState<Entry[]>([])
  const busy = entries.some((e) => isExchange(e) && e.turn.status === 'streaming')
  // Aborted on unmount (e.g. Sair): the fetch stops and no paced bubble lands afterwards.
  const controller = useRef(new AbortController())
  useEffect(() => {
    const c = new AbortController()
    controller.current = c
    return () => c.abort()
  }, [])

  const send = useCallback(async (text: string, resend = false): Promise<boolean> => {
    const id = crypto.randomUUID()
    const t0 = performance.now()
    setEntries((xs) => [...xs, { id, text, sentAt: new Date(), turn: initialTurn, resend }])
    const apply = (e: ChatEvent) => setEntries((xs) => applyEvent(xs, id, e, new Date(), performance.now() - t0))

    const signal = controller.current.signal
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
  }, [])

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
