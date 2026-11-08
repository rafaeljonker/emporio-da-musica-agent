import { describe, expect, it } from 'vitest'
import type { ChatEvent } from '@/client/shared/lib/apiTypes'
import { initialTurn, reduceTurn } from '@/client/chat/domain/turn'

const bubble = (text: string, delay_ms = 0): ChatEvent => ({ type: 'bubble', kind: 'text', text, delay_ms })
const run = (events: ChatEvent[]) => events.reduce(reduceTurn, initialTurn)

describe('reduceTurn', () => {
  it('bubble events append in order', () => {
    const s = run([{ type: 'typing' }, bubble('Oi!'), bubble('Tudo bem?', 900)])
    expect(s.bubbles).toEqual(['Oi!', 'Tudo bem?'])
    expect(s.typing).toBe(true)
    expect(s.status).toBe('streaming')
  })

  it('done stops typing and keeps traceId', () => {
    const s = run([{ type: 'typing' }, bubble('Oi!'), { type: 'done', trace_id: 't-1' }])
    expect(s).toMatchObject({ typing: false, status: 'done', traceId: 't-1', bubbles: ['Oi!'] })
  })

  it('error before any bubble is not partial', () => {
    const s = run([{ type: 'typing' }, { type: 'error', partial: false }])
    expect(s).toMatchObject({ typing: false, status: 'failed', partial: false, bubbles: [] })
  })

  it('error after a bubble is partial and keeps bubbles', () => {
    const s = run([{ type: 'typing' }, bubble('Oi!'), { type: 'error', partial: true }])
    expect(s).toMatchObject({ typing: false, status: 'failed', partial: true, bubbles: ['Oi!'] })
  })
})
