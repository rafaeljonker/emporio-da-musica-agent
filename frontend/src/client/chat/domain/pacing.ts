import type { ChatEvent } from '@/client/shared/lib/apiTypes'

/** Resolves after `ms`, or at once when aborted (clearing the timer). */
function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve()
    const done = () => {
      clearTimeout(timer)
      signal.removeEventListener('abort', done)
      resolve()
    }
    const timer = setTimeout(done, ms)
    signal.addEventListener('abort', done)
  })
}

/**
 * Ordered per-turn queue (ruling R5: the server does not sleep). Each bubble waits its own
 * `delay_ms` before it is applied; later events, the terminal one included, wait behind it.
 * After abort nothing more is applied.
 */
export function createPacer(apply: (e: ChatEvent) => void, signal: AbortSignal) {
  let queue = Promise.resolve()
  const pacer = {
    shown: 0,
    ended: false,
    push(e: ChatEvent) {
      queue = queue.then(async () => {
        if (e.type === 'bubble') await sleep(e.delay_ms, signal)
        if (signal.aborted) return
        if (e.type === 'bubble') pacer.shown += 1
        if (e.type === 'done' || e.type === 'error') pacer.ended = true
        apply(e)
      })
    },
    drained: () => queue,
  }
  return pacer
}
