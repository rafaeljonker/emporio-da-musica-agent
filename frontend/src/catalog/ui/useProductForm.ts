import { useCallback, useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { SessionExpired } from '@/api/client'
import type { Product } from '@/api/types'
import { copy } from '@/copy'
import { describedBy, failureField, firstInvalid } from '../domain/catalog'
import { EMPTY, errorCopy, priceInput, toFields, toPrice, validate, type FieldErrors, type ProductFields } from '../domain/form'
import { saveProduct } from '../domain/saveProduct'
import { focusField } from './focusField'

export interface ProductFormProps {
  /** The product being edited, or null for a new one. The parent remounts the form to reset it. */
  editing: Product | null
  onSaved: (product: Product, edited: boolean) => void
  onCancelEdit: () => void
  onSessionExpired: () => void
}

const c = copy.catalog

type TextField = 'name' | 'description' | 'price' | 'stock' | 'specs'

export function useProductForm({ editing, onSaved, onSessionExpired }: ProductFormProps) {
  const [fields, setFields] = useState<ProductFields>(() => (editing ? toFields(editing) : EMPTY))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [failure, setFailure] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const onChange = useMemo(() => {
    const set = (field: keyof ProductFields) => (value: string) => setFields((f) => ({ ...f, [field]: value }))
    const input = (field: TextField) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => set(field)(e.target.value)
    return {
      name: input('name'),
      description: input('description'),
      price: input('price'),
      stock: input('stock'),
      specs: input('specs'),
      categoryId: set('categoryId'),
      status: set('status'),
    }
  }, [])

  // Shown as BRL once it parses: "1234.5" becomes "1.234,50".
  const onPriceBlur = useCallback(() => {
    const price = toPrice(fields.price)
    if (price) setFields((f) => ({ ...f, price: priceInput(price) }))
  }, [fields.price])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (saving) return
    const { body, errors: found } = validate(fields)
    setErrors(found)
    setFailure(null)
    if (!body) {
      const first = firstInvalid(found)
      if (first) focusField(first)
      return
    }
    setSaving(true)
    try {
      onSaved(await saveProduct(body, editing), !!editing)
    } catch (err) {
      if (err instanceof SessionExpired) {
        onSessionExpired()
        return
      }
      const message = errorCopy(err)
      const field = failureField(message)
      if (field) {
        setErrors({ [field]: message })
        focusField(field)
      } else setFailure(message)
    } finally {
      setSaving(false)
    }
  }

  const ariaDescribedBy = {
    name: describedBy('name', undefined, errors.name),
    categoryId: describedBy('categoryId', undefined, errors.categoryId),
    description: describedBy('description', c.descriptionHint, errors.description),
    price: describedBy('price', undefined, errors.price),
    stock: describedBy('stock', undefined, errors.stock),
    specs: describedBy('specs', c.specsHint, errors.specs),
  }

  return { fields, errors, failure, saving, ariaDescribedBy, onChange, onPriceBlur, onSubmit }
}
