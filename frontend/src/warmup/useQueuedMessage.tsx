import { useCallback, useEffect, useRef, useState } from 'react'
import { enqueue, load, save, undo, type QueuedMessage } from './queue'

/**
 * Lines typed during warm-up, kept in sessionStorage. After a reload they are queued again;
 * after a re-login (`restoreToComposer`) they go back into the composer and are not sent.
 * Flushed exactly once, as one message joined by "\n", when `ready` turns true.
 */
export function useQueuedMessage(ready: boolean, send: (text: string) => void, restoreToComposer: boolean) {
  const [initial] = useState(() => {
    const stored = load()
    return restoreToComposer
      ? { queued: null, restored: stored ? undo(stored) : '' }
      : { queued: stored, restored: '' }
  })
  const [queued, setQueued] = useState<QueuedMessage | null>(initial.queued)
  useEffect(() => save(queued), [queued])

  const flushed = useRef(false)
  useEffect(() => {
    if (!ready || !queued || flushed.current) return
    flushed.current = true
    setQueued(null)
    send(undo(queued))
  }, [ready, queued, send])

  // ponytail: customerId stays null until the customer selector lands (Task 8).
  const add = useCallback((line: string) => setQueued((q) => enqueue(q, line, null)), [])
  /** Removes the queue and returns its text for the composer. */
  const take = useCallback(() => {
    setQueued(null)
    return queued ? undo(queued) : ''
  }, [queued])

  return { queued, restored: initial.restored, add, take }
}
