import { useCallback, useEffect, useRef, useState } from 'react'
import { enqueue, load, save, undo, type QueuedMessage } from './queue'

/**
 * Lines typed during warm-up, kept in sessionStorage. After a reload they are queued again;
 * after a re-login (`restoreToComposer`) they go back into the composer and are not sent.
 * Flushed exactly once, as one message joined by "\n", when `ready` turns true. The stored copy
 * is cleared only once `send` resolves with the session still valid, so an expiry during the
 * flush POST keeps the text for the next login.
 */
export function useQueuedMessage(
  ready: boolean,
  send: (text: string) => Promise<boolean>,
  restoreToComposer: boolean,
) {
  const [initial] = useState(() => {
    const stored = load()
    return restoreToComposer
      ? { queued: null, restored: stored ? undo(stored) : '' }
      : { queued: stored, restored: '' }
  })
  const [queued, setQueued] = useState<QueuedMessage | null>(initial.queued)
  const flushed = useRef(false)
  useEffect(() => {
    if (!flushed.current) save(queued)
  }, [queued])

  useEffect(() => {
    if (!ready || !queued || flushed.current) return
    flushed.current = true
    setQueued(null)
    void send(undo(queued)).then((sessionOk) => sessionOk && save(null))
  }, [ready, queued, send])

  /** Queues `line`; false (the line would pass the 1000-char cap) keeps it in the composer. */
  const add = useCallback(
    (line: string) => {
      const next = enqueue(queued, line)
      if (next) setQueued(next)
      return next !== null
    },
    [queued],
  )
  /** Removes the queue and returns its text for the composer. */
  const take = useCallback(() => {
    setQueued(null)
    return queued ? undo(queued) : ''
  }, [queued])

  return { queued, restored: initial.restored, add, take }
}
