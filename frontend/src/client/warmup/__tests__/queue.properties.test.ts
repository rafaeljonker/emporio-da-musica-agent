import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { enqueue, load, MAX_CHARS, save, undo, type QueuedMessage } from '@/client/warmup/domain/queue'

fc.configureGlobal({ seed: 42 })

const line = fc.string({ maxLength: 600 })
const queue: fc.Arbitrary<QueuedMessage> = fc.array(fc.string({ maxLength: 200 }), { minLength: 1, maxLength: 5 })
  .filter((lines) => lines.join('\n').length <= MAX_CHARS)
  .map((lines) => ({ lines }))

describe('queue properties', () => {
  it('enqueue refuses exactly when the joined text passes the cap', () => {
    fc.assert(
      fc.property(fc.option(queue, { nil: null }), line, (q, l) => {
        const joined = q ? `${undo(q)}\n${l}` : l
        const next = enqueue(q, l)
        expect(next === null).toBe(joined.length > MAX_CHARS)
        if (next) expect(undo(next).length).toBeLessThanOrEqual(MAX_CHARS)
      }),
    )
  })

  it('undo after enqueue appends the line on a new line', () => {
    fc.assert(
      fc.property(queue, line, (q, l) => {
        const next = enqueue(q, l)
        if (next) expect(undo(next)).toBe(`${undo(q)}\n${l}`)
      }),
    )
  })

  it('load after save round-trips', () => {
    fc.assert(
      fc.property(fc.option(queue, { nil: null }), (q) => {
        save(q)
        expect(load()).toEqual(q)
      }),
    )
  })
})
