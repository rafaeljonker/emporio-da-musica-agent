import { describe, expect, it } from 'vitest'
import { ceil10, firstReplyNote, formatElapsed, isLongWait } from './format'

describe('warm-up formatting', () => {
  it('ceil10 rounds up to the next ten', () => {
    expect([0, 1, 26, 30, 31].map(ceil10)).toEqual([0, 10, 30, 30, 40])
  })

  it('formatElapsed switches to minutes after 60 s', () => {
    expect(formatElapsed(12)).toBe('Esperando há 12 s')
    expect(formatElapsed(59)).toBe('Esperando há 59 s')
    expect(formatElapsed(65)).toBe('Esperando há 1 min 05 s')
    expect(formatElapsed(600)).toBe('Esperando há 10 min 00 s')
  })

  it('long wait is twice the rounded expected', () => {
    // expected 26 s rounds to 30 s, so the long wait starts after 60 s
    expect(isLongWait(60, 26)).toBe(false)
    expect(isLongWait(61, 26)).toBe(true)
  })

  it('first reply note falls back without p50', () => {
    expect(firstReplyNote(2)).toBe('uns 2 s')
    expect(firstReplyNote(2.43)).toBe('uns 2,4 s')
    expect(firstReplyNote(null)).toBe('poucos segundos')
  })
})
