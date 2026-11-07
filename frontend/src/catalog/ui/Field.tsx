import type { ReactNode } from 'react'
import { Label } from '@/components/ui/label'
import { fieldId } from '../domain/catalog'
import type { ProductFields } from '../domain/form'

interface Props {
  field: keyof ProductFields
  label: string
  hint?: string
  error?: string
  /** The control, with id fieldId(field) and aria-describedby describedBy(field, hint, error). */
  children: ReactNode
}

/** Label, control, hint and error, tied with aria-describedby. */
export function Field({ field, label, hint, error, children }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={fieldId(field)}>{label}</Label>
      {children}
      {hint && (
        <p id={`${fieldId(field)}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${fieldId(field)}-error`} className="text-sm font-semibold text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
