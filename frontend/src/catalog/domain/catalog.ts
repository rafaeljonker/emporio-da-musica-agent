// Pure helpers behind the Catálogo view models.
import { SessionExpired } from '@/api/client'
import type { Product } from '@/api/types'
import { copy } from '@/copy'
import { errorCopy, formatPrice, type FieldErrors, type ProductFields } from './form'

const c = copy.catalog
/** Form order: a failed submit focuses the first field in error. */
const ORDER: (keyof ProductFields)[] = ['name', 'categoryId', 'description', 'price', 'stock', 'status', 'specs']

export const fieldId = (field: keyof ProductFields) => `catalog-${field}`

/** The hint and error ids for aria-describedby, or undefined when there are neither. */
export function describedBy(field: keyof ProductFields, hint?: string, error?: string): string | undefined {
  const ids = [hint && `${fieldId(field)}-hint`, error && `${fieldId(field)}-error`].filter(Boolean).join(' ')
  return ids || undefined
}

export const firstInvalid = (errors: FieldErrors) => ORDER.find((f) => errors[f])

/** The field a save failure belongs to, or null when it shows under the form. */
export function failureField(message: string): 'categoryId' | 'name' | null {
  if (message === c.errors.categoryId) return 'categoryId'
  if (message === c.nameTaken) return 'name'
  return null
}

/** The alert above the form when the categories or the list fail; null on none or a session expiry. */
export function loadFailure(...errors: unknown[]): string | null {
  const err = errors.find((e) => e && !(e instanceof SessionExpired))
  if (!err) return null
  return errorCopy(err) === c.unavailable ? c.unavailable : c.loadFailed
}

/** A saved product goes first, replacing its older row. */
export const withSaved = (list: Product[], product: Product) => [product, ...list.filter((p) => p.id !== product.id)]

/** "Violões · R$ 899,90 · 3 em estoque", plus the status when not active. */
export const productSummary = (p: Product) =>
  [p.category, formatPrice(p.price), c.stockValue(p.stock), p.status !== 'active' && c.statuses[p.status]]
    .filter(Boolean)
    .join(' · ')
