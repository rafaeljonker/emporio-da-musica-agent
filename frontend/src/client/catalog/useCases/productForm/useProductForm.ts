import { zodResolver } from '@hookform/resolvers/zod'
import type { BaseSyntheticEvent } from 'react'
import { useForm, type Control, type UseFormRegisterReturn } from 'react-hook-form'
import { describedBy, firstInvalid } from '@/client/catalog/domain/catalog'
import { EMPTY, priceInput, productSchema, toFields, toPrice, type ProductFields } from '@/client/catalog/domain/form'
import { createProduct, updateProduct } from '@/client/shared/lib/api'
import type { Product, ProductBody } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { errorMessage, fieldFor } from '@/client/shared/lib/errorMessage'
import { focusField } from './focusField'

const c = copy.catalog

export interface ProductFormProps {
  /** The product "Editar" opened; null adds a new one. The form remounts (key) on each change. */
  editing: Product | null
  onSaved: (product: Product, edited: boolean) => void
  /** Owned by the dialog: a save started before a close and reopen still blocks this form. */
  saving: boolean
  onSaving: (saving: boolean) => void
}

type TextField = 'name' | 'description' | 'price' | 'stock' | 'specs'
type ErrorField = Exclude<keyof ProductFields, 'status'>

export type ProductFormView = {
  fields: { [F in TextField]: UseFormRegisterReturn<F> }
  /** For the two selects (category, status). */
  control: Control<ProductFields, unknown, ProductBody>
  errors: Partial<Record<ErrorField, string>>
  describedBy: Record<ErrorField, string | undefined>
  /** A save failure that belongs to no field. */
  alert: string | null
  onSubmit: (e?: BaseSyntheticEvent) => Promise<void>
} & ({ state: 'editing' } | { state: 'saving' })

/**
 * The add/edit form. The schema owns every rule and message; errors show on submit and stay
 * while typing until the next submit. A save error lands on its field or as the form's alert.
 */
export function useProductForm({ editing, onSaved, saving, onSaving }: ProductFormProps): ProductFormView {
  const { register, control, handleSubmit, formState, getValues, setValue, setError } = useForm<
    ProductFields,
    unknown,
    ProductBody
  >({
    resolver: zodResolver(productSchema),
    mode: 'onSubmit',
    reValidateMode: 'onSubmit',
    // Focus waits for the error to render (focusField), so the reader announces it with the field.
    shouldFocusError: false,
    defaultValues: editing ? toFields(editing) : EMPTY,
  })
  const { errors: found, isSubmitting } = formState
  const busy = isSubmitting || saving

  const save = async (body: ProductBody) => {
    onSaving(true)
    const res = editing ? await updateProduct(editing.id, body) : await createProduct(body)
    onSaving(false)
    if (res.ok) return onSaved(res.data, !!editing)
    // An expired session signs out (the app listens).
    if (res.error.code === 'unauthenticated') return
    const message = errorMessage(res.error, 'catalogSave')
    const field = fieldFor(res.error.code)
    if (field) {
      setError(field, { type: 'server', message })
      focusField(field)
    } else setError('root.server', { type: 'server', message })
  }
  const submit = handleSubmit(save, (invalid) => {
    const first = firstInvalid(invalid)
    if (first) focusField(first)
  })

  const errors = {
    name: found.name?.message,
    categoryId: found.categoryId?.message,
    description: found.description?.message,
    price: found.price?.message,
    stock: found.stock?.message,
    specs: found.specs?.message,
  }
  return {
    state: busy ? 'saving' : 'editing',
    fields: {
      name: register('name'),
      description: register('description'),
      // Shown as BRL once it parses: "1234.5" becomes "1.234,50".
      price: register('price', {
        onBlur: () => {
          const price = toPrice(getValues('price'))
          if (price) setValue('price', priceInput(price))
        },
      }),
      stock: register('stock'),
      specs: register('specs'),
    },
    control,
    errors,
    describedBy: {
      name: describedBy('name', undefined, errors.name),
      categoryId: describedBy('categoryId', undefined, errors.categoryId),
      description: describedBy('description', c.descriptionHint, errors.description),
      price: describedBy('price', undefined, errors.price),
      stock: describedBy('stock', undefined, errors.stock),
      specs: describedBy('specs', c.specsHint, errors.specs),
    },
    alert: found.root?.server?.message ?? null,
    onSubmit: (e) => {
      // aria-disabled, not disabled: the button stays focusable, so a second submit is ignored here.
      if (!busy) return submit(e)
      e?.preventDefault()
      return Promise.resolve()
    },
  }
}
