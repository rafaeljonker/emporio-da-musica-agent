import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { load, save } from '@/client/warmup/domain/queue'
import { useQueuedMessage } from '@/client/warmup/useCases/queuedMessage/useQueuedMessage'

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))

function setup({ restore = false, sessionOk = true, ready = false } = {}) {
  const send = vi.fn(async (_text: string) => sessionOk)
  const hook = renderHook(({ ready }) => useQueuedMessage(ready, send, restore), {
    initialProps: { ready },
    reactStrictMode: true,
  })
  return { send, ...hook }
}

describe('useQueuedMessage', () => {
  beforeEach(() => vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] }))
  afterEach(() => vi.useRealTimers())

  it('queues lines while warming and refuses one past the cap', () => {
    const { result } = setup()
    expect(result.current.state).toBe('empty')
    act(() => void result.current.add('Oi'))
    act(() => void result.current.add('Tem C40?'))
    expect(result.current).toMatchObject({ state: 'queued', lines: ['Oi', 'Tem C40?'] })
    expect(load()).toEqual({ lines: ['Oi', 'Tem C40?'] })
    let added = true
    act(() => void (added = result.current.add('x'.repeat(1000))))
    expect(added).toBe(false)
  })

  it('take empties the queue and returns its text', () => {
    save({ lines: ['Oi', 'Tem C40?'] })
    const { result } = setup()
    let text = ''
    act(() => void (text = result.current.take()))
    expect(text).toBe('Oi\nTem C40?')
    expect(result.current.state).toBe('empty')
    expect(load()).toBeNull()
  })

  it('flushes exactly once when ready, as one message, then clears storage', async () => {
    save({ lines: ['Oi', 'Tem C40?'] })
    const { result, send, rerender } = setup()
    expect(result.current).toMatchObject({ state: 'queued', lines: ['Oi', 'Tem C40?'] })

    rerender({ ready: true })
    await advance(0)
    rerender({ ready: true })
    await advance(0)
    expect(send).toHaveBeenCalledTimes(1)
    expect(send).toHaveBeenCalledWith('Oi\nTem C40?')
    expect(result.current.state).toBe('flushed')
    expect(load()).toBeNull()
  })

  it('flushes once when ready on mount, under Strict Mode remounting effects', async () => {
    save({ lines: ['Oi'] })
    const { send } = setup({ ready: true })
    await advance(0)
    expect(send).toHaveBeenCalledTimes(1)
  })

  it('keeps text on unauthenticated', async () => {
    save({ lines: ['Oi'] })
    const { send, rerender } = setup({ sessionOk: false })
    rerender({ ready: true })
    await advance(0)
    expect(send).toHaveBeenCalledTimes(1)
    expect(load()).toEqual({ lines: ['Oi'] })
  })

  it('restores to the composer after a re-login and sends nothing', async () => {
    save({ lines: ['Oi', 'Tem C40?'] })
    const { result, send, rerender } = setup({ restore: true })
    expect(result.current).toMatchObject({ state: 'empty', restored: 'Oi\nTem C40?' })
    rerender({ ready: true })
    await advance(0)
    expect(send).not.toHaveBeenCalled()
    expect(load()).toBeNull()
  })
})
