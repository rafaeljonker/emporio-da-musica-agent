import { describe, expect, it, vi } from 'vitest'
import { createProduct, login, me, streamChat, updateProduct } from '@/client/shared/lib/api'
import { onSessionExpired } from '@/client/shared/lib/session'
import { jsonResponse } from '@/test-support/sse'
import { product } from '@/test-support/fixtures'

const body = { ...product(), id: undefined, category: undefined }

describe('api client', () => {
  it('maps detail string to code', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(409, { detail: 'catalog_full' })))
    expect(await createProduct(body)).toEqual({ ok: false, error: { code: 'catalog_full', status: 409 } })

    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(429, { detail: 'too_many_messages' })))
    expect(await streamChat('oi', () => {})).toEqual({ ok: false, error: { code: 'too_many_messages', status: 429 } })
  })

  it('maps 422 detail list to invalid_fields', async () => {
    const detail = [{ type: 'string_pattern_mismatch', loc: ['body', 'name'] }]
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(422, { detail })))
    expect(await updateProduct(1, body)).toEqual({ ok: false, error: { code: 'invalid_fields', status: 422 } })
  })

  it('network TypeError is network with null status', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    expect(await me()).toEqual({ ok: false, error: { code: 'network', status: null } })
  })

  it('notifies session expiry once per 401 except login', async () => {
    const expired = vi.fn()
    const off = onSessionExpired(expired)
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(401, { detail: 'unauthenticated' })))
    expect(await me()).toEqual({ ok: false, error: { code: 'unauthenticated', status: 401 } })
    expect(expired).toHaveBeenCalledTimes(1)
    await createProduct(body)
    expect(expired).toHaveBeenCalledTimes(2)
    off()
  })

  it('login 401 is invalid_credentials without notifying', async () => {
    const expired = vi.fn()
    const off = onSessionExpired(expired)
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(401, { detail: 'invalid_credentials' })))
    expect(await login('a@b.c', 'x')).toEqual({ ok: false, error: { code: 'invalid_credentials', status: 401 } })
    expect(expired).not.toHaveBeenCalled()
    off()
  })
})
