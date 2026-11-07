import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useProductForm } from '@/client/catalog/useCases/productForm/useProductForm'
import type { Product } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { product } from '@/test-support/fixtures'
import { jsonResponse } from '@/test-support/sse'

const c = copy.catalog
type View = ReturnType<typeof useProductForm>

function setup(editing: Product | null = null) {
  const onSaved = vi.fn()
  const hook = renderHook(() => useProductForm({ editing, onSaved }))
  return { ...hook, onSaved }
}
const type = (view: View, field: 'name' | 'price', value: string) =>
  act(() => view.fields[field].onChange({ target: { name: field, value }, type: 'change' }))
const submit = (view: View) => act(() => view.onSubmit())
const replies = (res: () => Promise<Response>) => vi.stubGlobal('fetch', vi.fn(res))

/** The real input the form focuses by id. */
function input(id: string) {
  const el = document.body.appendChild(document.createElement('input'))
  el.id = id
  return el
}

describe('useProductForm', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('shows every message on submit and focuses the first invalid field', async () => {
    const name = input('catalog-name')
    const { result } = setup()

    await submit(result.current)
    expect(result.current.errors).toEqual({
      name: c.errors.name,
      categoryId: c.errors.categoryId,
      price: c.errors.price,
      stock: c.errors.stock,
    })
    await waitFor(() => expect(document.activeElement).toBe(name))
  })

  it('keeps an error while typing, until the next submit', async () => {
    const { result } = setup()
    await submit(result.current)

    await type(result.current, 'name', 'Violão Teste')
    expect(result.current.errors.name).toBe(c.errors.name)
  })

  it('saves an edited product and reports it', async () => {
    const saved = product({ name: 'Cavaquinho Novo' })
    const fetch = vi.fn(() => Promise.resolve(jsonResponse(200, saved)))
    vi.stubGlobal('fetch', fetch)
    const { result, onSaved } = setup(product())

    await submit(result.current)
    expect(fetch).toHaveBeenCalledWith('/api/catalog/products/1', expect.objectContaining({ method: 'PUT' }))
    expect(onSaved).toHaveBeenCalledWith(saved, true)
  })

  it('name_taken_by_store marks and focuses the name', async () => {
    const name = input('catalog-name')
    replies(() => Promise.resolve(jsonResponse(422, { detail: 'name_taken_by_store' })))
    const { result } = setup(product())

    await submit(result.current)
    expect(result.current.errors).toEqual({ name: c.nameTaken })
    expect(result.current.alert).toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(name))
  })

  it('promo_claim shows the form-level alert', async () => {
    replies(() => Promise.resolve(jsonResponse(422, { detail: 'promo_claim' })))
    const { result } = setup(product())

    await submit(result.current)
    expect(result.current.alert).toBe(c.promoClaim)
    expect(result.current.errors).toEqual({})
  })

  it('is saving while the request runs and ignores a second submit', async () => {
    let answer: (res: Response) => void = () => {}
    const fetch = vi.fn(() => new Promise<Response>((resolve) => (answer = resolve)))
    vi.stubGlobal('fetch', fetch)
    const { result } = setup(product())

    const first = result.current.onSubmit()
    await waitFor(() => expect(result.current.state).toBe('saving'))
    await submit(result.current)
    expect(fetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      answer(jsonResponse(200, product()))
      await first
    })
    expect(result.current.state).toBe('editing')
  })
})
