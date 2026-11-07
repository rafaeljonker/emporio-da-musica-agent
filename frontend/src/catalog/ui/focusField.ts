import { fieldId } from '../domain/catalog'
import type { ProductFields } from '../domain/form'

/** Focuses a form field after the next re-render (an error shown, a form filled or remounted). */
export const focusField = (field: keyof ProductFields, scroll = false) =>
  requestAnimationFrame(() => {
    const el = document.getElementById(fieldId(field))
    if (scroll) el?.scrollIntoView({ block: 'center' })
    el?.focus()
  })
