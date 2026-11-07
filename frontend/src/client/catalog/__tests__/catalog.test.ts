import { describe, expect, it } from 'vitest'
import { describedBy, firstInvalid, productSummary, withSaved } from '@/client/catalog/domain/catalog'
import { copy } from '@/client/shared/lib/copy'
import { product as fixture } from '@/test-support/fixtures'

const c = copy.catalog
const product = (id: number, over: Parameters<typeof fixture>[0] = {}) =>
  fixture({ id, name: `P${id}`, category: 'Violões', price: '899.90', stock: 3, status: 'active', ...over })

describe('describedBy', () => {
  it('joins the hint and error ids', () =>
    expect(describedBy('specs', 'h', 'e')).toBe('catalog-specs-hint catalog-specs-error'))
  it('is undefined with neither', () => expect(describedBy('name')).toBeUndefined())
})

describe('firstInvalid', () => {
  it('follows the form order', () => expect(firstInvalid({ specs: 'x', price: 'x' })).toBe('price'))
  it('is undefined without errors', () => expect(firstInvalid({})).toBeUndefined())
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
