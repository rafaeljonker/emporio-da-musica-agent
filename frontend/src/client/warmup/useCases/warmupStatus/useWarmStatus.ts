import { useCallback, useEffect, useRef, useState } from 'react'
import { startWarm, warmStatus } from '@/client/shared/lib/api'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import { countUp } from '@/client/warmup/domain/format'

const POLL_MS = 1000
const NETWORK_FAILURES = 3

const settled = (s: WarmStatus | null) => s?.stage === 'ready' || s?.stage === 'failed'

/**
 * Polls GET /api/warm/status every second until `ready` or `failed`. The stage only ever comes
 * from the server; `elapsed` is the last good poll's `elapsed_seconds` plus the time since that
 * poll, and never goes back (the tick interval only re-renders).
 */
export function useWarmStatus(seed: WarmStatus | null) {
  const [status, setStatus] = useState(seed)
  const [elapsed, setElapsed] = useState(seed?.elapsed_seconds ?? 0)
  const [networkError, setNetworkError] = useState(false)
  const anchor = useRef<{ base: number; at: number } | null>(null)
  const done = settled(status)

  const anchorTo = useCallback((s: WarmStatus) => {
    const a = { base: s.elapsed_seconds, at: performance.now() }
    anchor.current = a
    setElapsed((shown) => countUp(a.base, 0, shown))
  }, [])

  useEffect(() => {
    if (done) return
    anchor.current ??= { base: seed?.elapsed_seconds ?? 0, at: performance.now() }
    const run = { stopped: false, failures: 0, timer: undefined as ReturnType<typeof setTimeout> | undefined }
    const tick = setInterval(() => {
      const a = anchor.current
      if (a) setElapsed((shown) => countUp(a.base, performance.now() - a.at, shown))
    }, POLL_MS)
    // Sequential polls: a slow response never overlaps the next request.
    const poll = async () => {
      const res = await warmStatus()
      if (run.stopped) return
      if (res.ok) {
        run.failures = 0
        setNetworkError(false)
        setStatus(res.data)
        anchorTo(res.data)
      } else {
        // An expired session stops polling (the app signs out).
        if (res.error.code === 'unauthenticated') return
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
  }, [done, seed, anchorTo])

  /** Failed only: POST /api/warm again; the server keeps `started_at`, so the timer resumes. */
  const retry = useCallback(async () => {
    const res = await startWarm()
    // A failure leaves `failed` on screen; the button is still there.
    if (!res.ok) return
    setStatus(res.data)
    anchorTo(res.data)
  }, [anchorTo])

  return { status, elapsed, networkError, retry }
}
