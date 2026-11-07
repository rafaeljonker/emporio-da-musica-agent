import { useCallback, useEffect, useEffectEvent, useState } from 'react'
import { enqueue, load, save, undo } from '@/client/warmup/domain/queue'

type Queue = { state: 'empty' } | { state: 'queued'; lines: string[] } | { state: 'flushed' }

export type QueuedMessageView = Queue & {
  /** Text a re-login puts back into the composer ('' when none). */
  restored: string
  /** Queues `line`; false (the line would pass the 1000-char cap) keeps it in the composer. */
  add: (line: string) => boolean
  /** Removes the queue and returns its text for the composer. */
  take: () => string
}

const EMPTY: Queue = { state: 'empty' }
const toQueue = (lines: string[] | undefined): Queue => (lines ? { state: 'queued', lines } : EMPTY)

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
): QueuedMessageView {
  const [initial] = useState(() => {
    const stored = load()
    return restoreToComposer
      ? { queue: EMPTY, restored: stored ? undo(stored) : '' }
      : { queue: toQueue(stored?.lines), restored: '' }
  })
  const [queue, setQueue] = useState<Queue>(initial.queue)

  // sessionStorage mirrors the queue; once flushed, only a confirmed send clears it.
  useEffect(() => {
    if (queue.state !== 'flushed') save(queue.state === 'queued' ? { lines: queue.lines } : null)
  }, [queue])

  const flush = useEffectEvent((lines: string[]) => {
    setQueue({ state: 'flushed' })
    void send(undo({ lines })).then((sessionOk) => sessionOk && save(null))
  })
  // On the next task, so a cleanup (Strict Mode's remount, `ready` flipping back) cancels it:
  // the POST goes out exactly once.
  const lines = queue.state === 'queued' ? queue.lines : null
  useEffect(() => {
    if (!ready || !lines) return
    const timer = setTimeout(() => flush(lines), 0)
    return () => clearTimeout(timer)
  }, [ready, lines])

  const add = useCallback(
    (line: string) => {
      const next = enqueue(queue.state === 'queued' ? { lines: queue.lines } : null, line)
      if (next) setQueue(toQueue(next.lines))
      return next !== null
    },
    [queue],
  )
  const take = useCallback(() => {
    setQueue(EMPTY)
    return queue.state === 'queued' ? undo(queue) : ''
  }, [queue])

  return { ...queue, restored: initial.restored, add, take }
}
