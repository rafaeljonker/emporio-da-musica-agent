import { describe, expect, it } from 'vitest'
import { HttpError, SessionExpired } from '@/api/client'
import type { Product } from '@/api/types'
import { copy } from '@/copy'
import { describedBy, failureField, firstInvalid, loadFailure, productSummary, withSaved } from './catalog'

const c = copy.catalog
const product = (id: number, over: Partial<Product> = {}) =>
  ({ id, name: `P${id}`, category: 'Violões', price: '899.90', stock: 3, status: 'active', ...over }) as Product

describe('describedBy', () => {
  it('joins the hint and error ids', () =>
    expect(describedBy('specs', 'h', 'e')).toBe('catalog-specs-hint catalog-specs-error'))
  it('is undefined with neither', () => expect(describedBy('name')).toBeUndefined())
})

describe('firstInvalid', () => {
  it('follows the form order', () => expect(firstInvalid({ specs: 'x', price: 'x' })).toBe('price'))
  it('is undefined without errors', () => expect(firstInvalid({})).toBeUndefined())
})

describe('failureField', () => {
  it.each([
    [c.errors.categoryId, 'categoryId'],
    [c.nameTaken, 'name'],
    [c.full, null],
    [c.promoClaim, null],
  ])('maps %s to %s', (message, want) => expect(failureField(message)).toBe(want))
})

describe('loadFailure', () => {
  it('is null without errors or on a session expiry', () => {
    expect(loadFailure(null, null)).toBeNull()
    expect(loadFailure(new SessionExpired(), null)).toBeNull()
  })
  it('says unavailable on a 503, else load failed', () => {
    expect(loadFailure(null, new HttpError(503, null))).toBe(c.unavailable)
    expect(loadFailure(new SessionExpired(), new HttpError(500, null))).toBe(c.loadFailed)
  })
})

describe('withSaved', () => {
  it('puts the saved product first, replacing its row', () =>
    expect(withSaved([product(1), product(2)], product(2, { name: 'new' })).map((p) => p.name)).toEqual(['new', 'P1']))
})

describe('productSummary', () => {
  it('omits the active status', () => expect(productSummary(product(1))).toBe(`Violões · R$ 899,90 · ${c.stockValue(3)}`))
  it('shows another status', () =>
    expect(productSummary(product(1, { status: 'discontinued' }))).toContain(c.statuses.discontinued))
})
