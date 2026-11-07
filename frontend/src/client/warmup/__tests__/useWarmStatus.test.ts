import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useWarmStatus } from '@/client/warmup/useCases/warmupStatus/useWarmStatus'
import { warm } from '@/test-support/fixtures'
import { jsonResponse } from '@/test-support/sse'

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))

/** fetch answers each call with the next reply; the last one repeats. */
function replies(...rs: (() => Promise<Response>)[]) {
  const fetch = vi.fn(() => {
    const next = rs.length > 1 ? rs.shift() : rs[0]
    return next ? next() : offline()
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
const offline = () => Promise.reject(new TypeError('Failed to fetch'))
const status = (over: Parameters<typeof warm>[0]) => () => Promise.resolve(jsonResponse(200, warm(over)))

describe('useWarmStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers({
      toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'performance', 'Date'],
    })
  })
  afterEach(() => vi.useRealTimers())

  it('polls at once without a seed, then every second, and stops on ready', async () => {
    const fetch = replies(status({ elapsed_seconds: 3 }), status({ stage: 'ready', elapsed_seconds: 4 }))
    const { result } = renderHook(() => useWarmStatus(null))
    expect(result.current.state).toBe('checking')

    await advance(0)
    expect(result.current).toMatchObject({ state: 'polling', elapsed: 3 })
    await advance(1000)
    expect(result.current).toMatchObject({ state: 'ready', status: { stage: 'ready' } })
    await advance(5000)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('three failed polls set networkError and a good poll clears it', async () => {
    replies(offline, offline, offline, status({}))
    const seed = warm()
    const { result } = renderHook(() => useWarmStatus(seed))
    await advance(2000)
    expect(result.current.networkError).toBe(false)
    await advance(1000)
    expect(result.current.networkError).toBe(true)
    await advance(1000)
    expect(result.current).toMatchObject({ state: 'polling', networkError: false })
  })

  it('polls never overlap', async () => {
    const fetch = replies(() => new Promise<Response>(() => {}))
    renderHook(() => useWarmStatus(null))
    await advance(10_000)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('elapsed counts up and never decreases when a poll reports less', async () => {
    replies(status({ elapsed_seconds: 11 }))
    const seed = warm({ elapsed_seconds: 12 })
    const { result } = renderHook(() => useWarmStatus(seed))
    expect(result.current.elapsed).toBe(12)
    await advance(1000)
    expect(result.current.elapsed).toBe(13)
    await advance(3000)
    expect(result.current.elapsed).toBe(14)
  })

  it('an expired session stops polling', async () => {
    const fetch = replies(() => Promise.resolve(jsonResponse(401, { detail: 'unauthenticated' })))
    renderHook(() => useWarmStatus(null))
    await advance(5000)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('retry after failed re-anchors elapsed and polls again', async () => {
    const fetch = replies(status({ elapsed_seconds: 40 }))
    const seed = warm({ stage: 'failed', elapsed_seconds: 30 })
    const { result } = renderHook(() => useWarmStatus(seed))
    await advance(5000)
    expect(fetch).not.toHaveBeenCalled()

    await act(() => result.current.retry())
    expect(result.current).toMatchObject({ state: 'polling', elapsed: 40 })
    await advance(1000)
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
