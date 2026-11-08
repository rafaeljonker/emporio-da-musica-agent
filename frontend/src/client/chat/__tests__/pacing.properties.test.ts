import fc from 'fast-check'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPacer } from '@/client/chat/domain/pacing'
import type { ChatEvent } from '@/client/shared/lib/apiTypes'

fc.configureGlobal({ seed: 42, numRuns: 50 })

const delays = fc.array(fc.integer({ min: 0, max: 2000 }), { maxLength: 6 })
const bubble = (delay_ms: number, i: number): ChatEvent => ({ type: 'bubble', kind: 'text', text: `b${i}`, delay_ms })
const label = (e: ChatEvent) => (e.type === 'bubble' ? e.text : e.type)

describe('pacing properties', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('applies in push order, the terminal event last and once, at Σ delay_ms', async () => {
    await fc.assert(
      fc.asyncProperty(delays, async (ds) => {
        const applied: string[] = []
        const pacer = createPacer((e) => applied.push(label(e)), new AbortController().signal)
        const events: ChatEvent[] = [{ type: 'typing' }, ...ds.map(bubble), { type: 'done', trace_id: 't' }]
        events.forEach(pacer.push)
        const total = ds.reduce((a, b) => a + b, 0)

        if (total > 0) {
          await vi.advanceTimersByTimeAsync(total - 1)
          expect(applied).not.toContain('done')
        }
        await vi.advanceTimersByTimeAsync(total > 0 ? 1 : 0)
        await pacer.drained()
        expect(applied).toEqual(events.map(label))
        expect(pacer.shown).toBe(ds.length)
      }),
    )
  })

  it('applies nothing after abort, whenever it comes, and leaves no timer', async () => {
    await fc.assert(
      fc.asyncProperty(delays, fc.integer({ min: 0, max: 6000 }), async (ds, abortAt) => {
        const applied: string[] = []
        const controller = new AbortController()
        const pacer = createPacer((e) => applied.push(label(e)), controller.signal)
        ;[...ds.map(bubble), { type: 'done', trace_id: 't' } as const].forEach(pacer.push)

        await vi.advanceTimersByTimeAsync(abortAt)
        controller.abort()
        const seen = [...applied]
        await pacer.drained()
        expect(vi.getTimerCount()).toBe(0)
        await vi.advanceTimersByTimeAsync(20_000)
        expect(applied).toEqual(seen)
      }),
    )
  })
})
