import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { isExchange, type Entry, type Exchange } from '@/client/chat/domain/entries'
import { useChatStream } from '@/client/chat/useCases/chatShell/useChatStream'
import type { ChatEvent } from '@/client/shared/lib/apiTypes'
import { chatEvents } from '@/test-support/fixtures'
import { jsonResponse, sseResponse } from '@/test-support/sse'

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))
const bubble = (text: string, delay_ms: number): ChatEvent => ({ type: 'bubble', kind: 'text', text, delay_ms })
const exchanges = (entries: Entry[]) => entries.filter(isExchange)
const only = (entries: Entry[]): Exchange => {
  const [x] = exchanges(entries)
  if (!x) throw new Error('no exchange')
  return x
}
const replies = (...rs: (() => Promise<Response>)[]) => {
  const fetch = vi.fn(() => {
    const next = rs.length > 1 ? rs.shift() : rs[0]
    return next ? next() : Promise.reject(new TypeError('Failed to fetch'))
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
const stream = (events: ChatEvent[]) => () => Promise.resolve(sseResponse(events))

describe('useChatStream', () => {
  beforeEach(() => vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance', 'Date'] }))
  afterEach(() => vi.useRealTimers())

  it('shows each bubble only after its delay, then ends the turn', async () => {
    replies(stream([{ type: 'typing' }, bubble('Oi', 0), bubble('Temos sim', 900), { type: 'done', trace_id: 't' }]))
    const { result } = renderHook(() => useChatStream())

    act(() => void result.current.send('Tem violão?'))
    await advance(0)
    expect(only(result.current.entries).turn).toMatchObject({ bubbles: ['Oi'], typing: true })
    expect(result.current.busy).toBe(true)
    await advance(900)
    expect(only(result.current.entries).turn).toMatchObject({ bubbles: ['Oi', 'Temos sim'], status: 'done' })
    expect(result.current.busy).toBe(false)
  })

  it('ends a dropped stream as a partial error', async () => {
    replies(stream([{ type: 'typing' }, bubble('Oi', 0)]))
    const { result } = renderHook(() => useChatStream())

    act(() => void result.current.send('Tem violão?'))
    await advance(0)
    expect(only(result.current.entries).turn).toMatchObject({ status: 'failed', partial: true, typing: false })
  })

  it('applies nothing after unmount and leaves no timer', async () => {
    replies(stream([bubble('Oi', 5000), { type: 'done', trace_id: 't' }]))
    const { result, unmount } = renderHook(() => useChatStream())

    act(() => void result.current.send('Tem violão?'))
    await advance(100)
    unmount()
    await advance(0)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('resends a failed message once, and resolves false on an expired session', async () => {
    const fetch = replies(
      () => Promise.resolve(jsonResponse(409, { detail: 'turn_in_progress' })),
      stream(chatEvents('Oi')),
      () => Promise.resolve(jsonResponse(401, { detail: 'unauthenticated' })),
    )
    const { result } = renderHook(() => useChatStream())

    await act(() => result.current.send('Tem violão?'))
    const failed = only(result.current.entries)
    expect(failed.turn).toMatchObject({ status: 'failed', partial: false })

    act(() => result.current.resend(failed.id))
    act(() => result.current.resend(failed.id))
    await advance(0)
    expect(fetch).toHaveBeenCalledTimes(2)
    const [first, again] = exchanges(result.current.entries)
    expect(first?.retried).toBe(true)
    expect(again).toMatchObject({ text: 'Tem violão?', resend: true, turn: { status: 'done' } })

    let sent = true
    await act(async () => {
      sent = await result.current.send('Mais uma')
    })
    expect(sent).toBe(false)
  })

  it('ignores a resend while a reply is streaming', async () => {
    let open: (res: Response) => void = () => {}
    const fetch = replies(
      () => Promise.resolve(jsonResponse(429, { detail: 'too_many_messages' })),
      () => new Promise<Response>((resolve) => (open = resolve)),
    )
    const { result } = renderHook(() => useChatStream())
    await act(() => result.current.send('Primeira'))
    const failed = only(result.current.entries)

    act(() => void result.current.send('Segunda'))
    expect(result.current.busy).toBe(true)
    act(() => result.current.resend(failed.id))
    expect(fetch).toHaveBeenCalledTimes(2)
    await act(async () => open(sseResponse(chatEvents('Oi'))))
  })
})
