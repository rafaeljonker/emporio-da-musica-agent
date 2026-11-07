import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useCatalogDialog } from '@/client/catalog/useCases/catalogDialog/useCatalogDialog'
import { copy } from '@/client/shared/lib/copy'
import { product } from '@/test-support/fixtures'
import { jsonResponse } from '@/test-support/sse'

const c = copy.catalog
const CATEGORIES = [{ id: 3, name: 'Cordas' }]

/** fetch by path: each path answers with its next reply; the last one repeats. */
function routes(table: Record<string, (() => Promise<Response>)[]>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string) => {
      const rs = table[path]
      const next = rs.length > 1 ? rs.shift() : rs[0]
      return next()
    }),
  )
}
const json = (status: number, body?: unknown) => () => Promise.resolve(jsonResponse(status, body))

function setup() {
  const onAsk = vi.fn()
  const hook = renderHook(() => useCatalogDialog({ onAsk }))
  act(() => hook.result.current.onOpenChange(true))
  return { ...hook, onAsk }
}

describe('useCatalogDialog', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('shows the load failure alert, and a retry clears it', async () => {
    routes({
      '/api/catalog/categories': [json(503), json(200, CATEGORIES)],
      '/api/catalog/products/mine': [json(200, [])],
    })
    const { result } = setup()
    await waitFor(() => expect(result.current.alert).toBe(c.unavailable))

    act(() => result.current.retry())
    expect(result.current.alert).toBeNull()
    await waitFor(() => expect(result.current.categories).toEqual(CATEGORIES))
    expect(result.current.mine).toEqual({ state: 'ready', products: [] })
  })

  it('a save shows the saved panel and focuses its heading', async () => {
    routes({ '/api/catalog/categories': [json(200, CATEGORIES)], '/api/catalog/products/mine': [json(200, [])] })
    const heading = document.body.appendChild(document.createElement('h3'))
    heading.id = 'catalog-saved'
    heading.tabIndex = -1
    const { result } = setup()

    act(() => result.current.onSaved(product({ name: 'Ukulele' }), false))
    expect(result.current.panel).toEqual({ state: 'saved', name: 'Ukulele', edited: false })
    expect(document.activeElement).toBe(heading)
  })

  it('a row saved before the list arrives beats the late server list', async () => {
    let answer = (_: Response) => {}
    routes({
      '/api/catalog/categories': [json(200, CATEGORIES)],
      '/api/catalog/products/mine': [() => new Promise<Response>((resolve) => (answer = resolve))],
    })
    const { result } = setup()

    act(() => result.current.onSaved(product({ id: 1, name: 'new' }), true))
    await act(async () => answer(jsonResponse(200, [product({ id: 1, name: 'stale' }), product({ id: 2, name: 'P2' })])))
    await waitFor(() => expect(result.current.mine.state).toBe('ready'))
    if (result.current.mine.state === 'ready') expect(result.current.mine.products.map((p) => p.name)).toEqual(['new', 'P2'])
  })

  it('"Perguntar" hands the prompt over only as the dialog closes', async () => {
    routes({ '/api/catalog/categories': [json(200, CATEGORIES)], '/api/catalog/products/mine': [json(200, [])] })
    const { result, onAsk } = setup()
    act(() => result.current.onSaved(product({ name: 'Ukulele' }), false))

    act(() => result.current.ask())
    expect(result.current.open).toBe(false)
    expect(onAsk).not.toHaveBeenCalled()
    const close = new Event('focusout', { cancelable: true })
    result.current.onCloseAutoFocus(close)
    expect(close.defaultPrevented).toBe(true)
    expect(onAsk).toHaveBeenCalledWith(c.askPrompt('Ukulele'))

    const plain = new Event('focusout', { cancelable: true })
    result.current.onCloseAutoFocus(plain)
    expect(plain.defaultPrevented).toBe(false)
  })

  it('editing the same product again resets typed values (remounts the form)', async () => {
    const p = product()
    routes({ '/api/catalog/categories': [json(200, CATEGORIES)], '/api/catalog/products/mine': [json(200, [p])] })
    const { result } = setup()
    await waitFor(() => expect(result.current.mine.state).toBe('ready'))

    act(() => result.current.onEdit(p))
    const first = result.current.panel
    act(() => result.current.onEdit(p))
    expect(result.current.editing).toBe(p)
    expect(result.current.panel).toMatchObject({ state: 'form' })
    expect(result.current.panel).not.toEqual(first)
  })
})
