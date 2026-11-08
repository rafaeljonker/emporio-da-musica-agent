import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useApp } from '@/app/useApp'
import { notifySessionExpired } from '@/client/shared/lib/session'
import { warm } from '@/test-support/fixtures'
import { jsonResponse } from '@/test-support/sse'

const meReplies = (res: Response) => vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(res)))

describe('useApp', () => {
  it('goes from checking to signedIn when the cookie is live', async () => {
    meReplies(jsonResponse(200, { warm: warm(), customer_id: 14 }))
    const { result } = renderHook(() => useApp())
    expect(result.current.state).toBe('checking')

    await waitFor(() => expect(result.current.state).toBe('signedIn'))
    expect(result.current).toMatchObject({ fromLogin: false, customerId: 14, warm: warm() })
  })

  it('goes from checking to a plain signedOut on a 401 from me', async () => {
    meReplies(jsonResponse(401, { detail: 'unauthenticated' }))
    const { result } = renderHook(() => useApp())

    await waitFor(() => expect(result.current.state).toBe('signedOut'))
    expect(result.current).toMatchObject({ expired: false })
  })

  it('signs out as expired when a 401 arrives mid-session, and back in after login', async () => {
    meReplies(jsonResponse(200, { warm: warm(), customer_id: null }))
    const { result } = renderHook(() => useApp())
    await waitFor(() => expect(result.current.state).toBe('signedIn'))

    act(() => notifySessionExpired())
    expect(result.current).toMatchObject({ state: 'signedOut', expired: true })

    act(() => {
      if (result.current.state === 'signedOut') result.current.signedIn(warm({ stage: 'ready' }))
    })
    expect(result.current).toMatchObject({ state: 'signedIn', fromLogin: true, customerId: null })
  })
})
