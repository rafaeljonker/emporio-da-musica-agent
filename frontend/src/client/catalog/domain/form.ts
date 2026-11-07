// Pure helpers for the Catálogo dialog; the bounds mirror emporio.api.catalog.ProductIn.
import type { Product, ProductBody, ProductStatus } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'

export interface ProductFields {
  name: string
  categoryId: string
  description: string
  /** As typed: "1.234,50", "1234.5" or "R$ 12". */
  price: string
  stock: string
  status: ProductStatus
  /** One "Chave: valor" per line. */
  specs: string
}

export type FieldErrors = Partial<Record<keyof ProductFields, string>>

export const EMPTY: ProductFields = {
  name: '',
  categoryId: '',
  description: '',
  price: '',
  stock: '',
  status: 'active',
  specs: '',
}

const MAX_SPECS = 20
// Mirrors emporio.api.catalog: zero-width marks and bidi controls, which render unlike they read.
const INVISIBLE = '\u200b-\u200f\u202a-\u202e\u2066-\u2069'
/** One line: no C0 control, DEL or invisible mark. */
const LINE = new RegExp(`^[^\\u0000-\\u001f\\u007f${INVISIBLE}]*$`)
/** Free text: also keeps tab and line breaks. */
const TEXT = new RegExp(`^[^\\u0000-\\u0008\\u000b\\u000c\\u000e-\\u001f\\u007f${INVISIBLE}]*$`)
const STATUSES: readonly ProductStatus[] = ['active', 'discontinued', 'coming_soon']
// Integer part with pt-BR thousand dots ("1.234") or plain ("1234"), then , or . and 1-2 cents digits.
const PRICE = /^(\d{1,3}(?:\.\d{3})+|\d+)(?:[,.](\d{1,2}))?$/

/** pt-BR or dot input to the API's decimal string ("1234.50"); null when invalid or ≤ 0. */
export function toPrice(text: string): string | null {
  const m = PRICE.exec(text.trim().replace(/^R\$\s*/i, ''))
  if (!m) return null
  const units = m[1].replaceAll('.', '').replace(/^0+(?=\d)/, '')
  const cents = (m[2] ?? '').padEnd(2, '0')
  if (units.length > 6 || (units === '0' && cents === '00')) return null
  return `${units}.${cents}`
}

const brl = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
/** "1234.50" → "1.234,50", for the price input. */
export const priceInput = (decimal: string) => brl.format(Number(decimal))
/** "1234.50" → "R$ 1.234,50". */
export const formatPrice = (decimal: string) => `R$ ${priceInput(decimal)}`

/** One "Chave: valor" per line, blank lines skipped; null past 20 lines or on a malformed line. */
export function parseSpecs(text: string): Record<string, string> | null {
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length > MAX_SPECS) return null
  const specs: Record<string, string> = {}
  for (const line of lines) {
    const at = line.indexOf(':')
    const key = line.slice(0, at).trim()
    const value = line.slice(at + 1).trim()
    if (at < 0 || !key || !value || key.length > 40 || value.length > 120) return null
    if (!LINE.test(key) || !LINE.test(value)) return null
    specs[key] = value
  }
  return specs
}

export function validate(fields: ProductFields): { body?: ProductBody; errors: FieldErrors } {
  const e = copy.catalog.errors
  const errors: FieldErrors = {}
  const name = fields.name.trim()
  const description = fields.description.trim()
  const price = toPrice(fields.price)
  const stock = Number(fields.stock)
  const specs = parseSpecs(fields.specs)
  if (name.length < 2 || name.length > 120 || !LINE.test(name)) errors.name = e.name
  if (!/^[1-9]\d{0,8}$/.test(fields.categoryId)) errors.categoryId = e.categoryId
  if (description.length > 2000 || !TEXT.test(description)) errors.description = e.description
  if (price === null) errors.price = e.price
  if (!/^\d{1,6}$/.test(fields.stock.trim()) || stock > 100_000) errors.stock = e.stock
  if (specs === null) errors.specs = e.specs
  if (Object.keys(errors).length || price === null || specs === null || !STATUSES.includes(fields.status)) {
    return { errors }
  }
  const body = { name, category_id: Number(fields.categoryId), description, price, stock, status: fields.status, specs }
  return { body, errors }
}

/** A saved product back into the form, for "Editar". */
export const toFields = (p: Product): ProductFields => ({
  name: p.name,
  categoryId: String(p.category_id),
  description: p.description,
  price: priceInput(p.price),
  stock: String(p.stock),
  status: p.status,
  specs: Object.entries(p.specs)
    .map(([k, v]) => `${k}: ${v}`)
    .join('\n'),
})

/** The open-time list arriving after a save: rows on screen win, new server rows go after them. */
export function mergeById<T extends { id: number }>(local: T[], server: T[]): T[] {
  const seen = new Set(local.map((p) => p.id))
  return [...local, ...server.filter((p) => !seen.has(p.id))]
}

/** "Perguntar ao assistente" never discards a draft: the question goes on a new line after it. */
export const appendQuestion = (draft: string, question: string) =>
  draft.trim() ? `${draft.trimEnd()}\n${question}` : question
