// The one place an API error becomes pt-BR text. Chat and warm-up need none: their state picks the text.
import type { ApiError, ApiErrorCode } from '@/client/shared/lib/api'
import { copy } from '@/client/shared/lib/copy'

export type ErrorContext = 'login' | 'catalogLoad' | 'catalogSave'

export function errorMessage(error: ApiError, context: ErrorContext): string {
  const c = copy.catalog
  switch (context) {
    case 'login':
      // 429 too_many_attempts reads as network on purpose: the fields are not the problem.
      return error.code === 'invalid_credentials' ? copy.login.invalid : copy.login.network
    case 'catalogLoad':
      return error.status === 503 || error.code === 'catalog_unavailable' ? c.unavailable : c.loadFailed
    case 'catalogSave':
      return saveMessage(error)
  }
}

// By status first, whatever the code: a proxy 503 with no detail still reads "unavailable".
function saveMessage({ code, status }: ApiError): string {
  const c = copy.catalog
  if (code === 'unauthenticated') return copy.login.expired
  if (status === 429) return c.tooMany
  if (status === 409) return c.full
  if (status === 404) return c.notFound
  if (status === 503) return c.unavailable
  if (status === 422) {
    if (code === 'unknown_category') return c.errors.categoryId
    if (code === 'name_taken_by_store') return c.nameTaken
    if (code === 'promo_claim') return c.promoClaim
    return c.invalid
  }
  return c.failed
}

/** The form field a save error belongs to; null for a form-level error. */
export function fieldFor(code: ApiErrorCode): 'categoryId' | 'name' | null {
  if (code === 'unknown_category') return 'categoryId'
  if (code === 'name_taken_by_store') return 'name'
  return null
}
