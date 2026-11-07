import { useEffect, useState } from 'react'
import { warmExpected, type ApiError } from '@/client/shared/lib/api'
import { ceil10 } from '@/client/warmup/domain/format'

/** `seconds` is 0 when the model is always ready (provider_api). */
export type WarmExpectedView =
  | { state: 'pending' }
  | { state: 'error'; error: ApiError }
  | { state: 'success'; seconds: number }

/** GET /api/warm/expected once: the same measured expectation the warm-up shows. */
export function useWarmExpected(): WarmExpectedView {
  const [view, setView] = useState<WarmExpectedView>({ state: 'pending' })
  useEffect(() => {
    let live = true
    void warmExpected().then((res) => {
      if (!live) return
      setView(
        res.ok
          ? { state: 'success', seconds: res.data.mode === 'provider_api' ? 0 : ceil10(res.data.expected_seconds) }
          : { state: 'error', error: res.error },
      )
    })
    return () => {
      live = false
    }
  }, [])
  return view
}
