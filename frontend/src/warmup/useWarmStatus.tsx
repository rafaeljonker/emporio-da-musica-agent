import { useCallback, useEffect, useState } from 'react'
import { SessionExpired, startWarm, warmStatus } from '@/api/client'
import type { WarmStatus } from '@/api/types'

const POLL_MS = 1000
const NETWORK_FAILURES = 3

const settled = (s: WarmStatus | null) => s?.stage === 'ready' || s?.stage === 'failed'

/**
 * Polls GET /api/warm/status every second until `ready` or `failed`. The stage only ever comes
 * from the server; `elapsed` is the server's `elapsed_seconds` plus local ticks since that poll.
 */
export function useWarmStatus(seed: WarmStatus | null, onSessionExpired: () => void) {
  const [status, setStatus] = useState(seed)
  const [ticks, setTicks] = useState(0)
  const [networkError, setNetworkError] = useState(false)
  const done = settled(status)

  useEffect(() => {
    if (done) return
    const run = { stopped: false, failures: 0, timer: undefined as ReturnType<typeof setTimeout> | undefined }
    const tick = setInterval(() => setTicks((t) => t + 1), POLL_MS)
    // Sequential polls: a slow response never overlaps the next request.
    const poll = async () => {
      try {
        const next = await warmStatus()
        if (run.stopped) return
        run.failures = 0
        setNetworkError(false)
        setStatus(next)
        setTicks(0)
      } catch (err) {
        if (run.stopped) return
        if (err instanceof SessionExpired) return onSessionExpired()
        run.failures += 1
        if (run.failures >= NETWORK_FAILURES) setNetworkError(true)
      }
      run.timer = setTimeout(poll, POLL_MS)
    }
    run.timer = setTimeout(poll, seed ? POLL_MS : 0)
    return () => {
      run.stopped = true
      clearInterval(tick)
      clearTimeout(run.timer)
    }
  }, [done, seed, onSessionExpired])

  /** Failed only: POST /api/warm again; the server keeps `started_at`, so the timer resumes. */
  const retry = useCallback(async () => {
    try {
      setStatus(await startWarm())
      setTicks(0)
    } catch (err) {
      if (err instanceof SessionExpired) onSessionExpired()
      // Anything else leaves `failed` on screen; the button is still there.
    }
  }, [onSessionExpired])

  const elapsed = (status?.elapsed_seconds ?? 0) + (done ? 0 : ticks)
  return { status, elapsed, networkError, retry }
}
