// Pure helpers behind the Catálogo view models.
import type { Product } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { formatPrice, type ProductFields } from './form'

const c = copy.catalog
/** Form order: a failed submit focuses the first field in error. */
const ORDER: (keyof ProductFields)[] = ['name', 'categoryId', 'description', 'price', 'stock', 'status', 'specs']

export const fieldId = (field: keyof ProductFields) => `catalog-${field}`

/** The hint and error ids for aria-describedby, or undefined when there are neither. */
export function describedBy(field: keyof ProductFields, hint?: string, error?: string): string | undefined {
  const ids = [hint && `${fieldId(field)}-hint`, error && `${fieldId(field)}-error`].filter(Boolean).join(' ')
  return ids || undefined
}

export const firstInvalid = (errors: Partial<Record<keyof ProductFields, unknown>>) => ORDER.find((f) => errors[f])

/** A saved product goes first, replacing its older row. */
export const withSaved = (list: Product[], product: Product) => [product, ...list.filter((p) => p.id !== product.id)]

/** "Violões · R$ 899,90 · 3 em estoque", plus the status when not active. */
export const productSummary = (p: Product) =>
  [p.category, formatPrice(p.price), c.stockValue(p.stock), p.status !== 'active' && c.statuses[p.status]]
    .filter(Boolean)
    .join(' · ')
