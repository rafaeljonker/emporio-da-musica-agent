import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChatEvent } from '@/api/types'
import { createPacer } from './pacing'

const bubble = (text: string, delay_ms: number): ChatEvent => ({ type: 'bubble', kind: 'text', text, delay_ms })
const label = (e: ChatEvent) => (e.type === 'bubble' ? e.text : e.type)

describe('createPacer', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('appends bubbles in order after their delay_ms and the terminal event last', async () => {
    const applied: string[] = []
    const pacer = createPacer((e) => applied.push(label(e)), new AbortController().signal)
    for (const e of [{ type: 'typing' } as ChatEvent, bubble('a', 0), bubble('b', 900), { type: 'done', trace_id: 't' } as ChatEvent])
      pacer.push(e)

    await vi.advanceTimersByTimeAsync(0)
    expect(applied).toEqual(['typing', 'a'])
    await vi.advanceTimersByTimeAsync(899)
    expect(applied).toEqual(['typing', 'a'])
    await vi.advanceTimersByTimeAsync(1)
    expect(applied).toEqual(['typing', 'a', 'b', 'done'])
    await pacer.drained()
    expect(pacer.shown).toBe(2)
    expect(pacer.ended).toBe(true)
  })

  it('applies nothing after abort and leaves no timer pending', async () => {
    const applied: string[] = []
    const controller = new AbortController()
    const pacer = createPacer((e) => applied.push(label(e)), controller.signal)
    pacer.push(bubble('a', 500))
    pacer.push({ type: 'done', trace_id: 't' })
    controller.abort()
    await pacer.drained()
    expect(vi.getTimerCount()).toBe(0)
    await vi.advanceTimersByTimeAsync(1000)
    expect(applied).toEqual([])
  })
})
