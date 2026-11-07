import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import { SessionExpired } from '@/api/client'
import type { Product } from '@/api/types'
import { copy } from '@/copy'
import { loadFailure, withSaved } from '../domain/catalog'
import { mergeById } from '../domain/form'
import { useCategories } from '../domain/useCategories'
import { useMyProducts } from '../domain/useMyProducts'
import { focusField } from './focusField'

export interface CatalogDialogProps {
  /** "Perguntar ao assistente": the shell puts this text in the composer (not sent). */
  onAsk: (text: string) => void
  onSessionExpired: () => void
}

export function useCatalogDialog({ onAsk, onSessionExpired }: CatalogDialogProps) {
  const [open, setOpen] = useState(false)
  /** Bumped on each opening: the list starts over. */
  const [opening, setOpening] = useState(0)
  /** Bumped on each opening and by "Tentar de novo": a new load. */
  const [load, setLoad] = useState(0)
  /** Rows saved in this opening, newest first; they win over the server list. */
  const [savedRows, setSavedRows] = useState<Product[]>([])
  const [editing, setEditing] = useState<Product | null>(null)
  /** Bumped on each reset: remounts the form with fresh fields. */
  const [formKey, setFormKey] = useState(0)
  const [saved, setSaved] = useState<{ name: string; edited: boolean } | null>(null)
  const asking = useRef<string | null>(null)

  const categories = useCategories(open, load)
  const products = useMyProducts(open, opening, load)

  useEffect(() => {
    if (categories.error instanceof SessionExpired) onSessionExpired()
  }, [categories.error, onSessionExpired])
  useEffect(() => {
    if (products.error instanceof SessionExpired) onSessionExpired()
  }, [products.error, onSessionExpired])

  // The heading replaces the form on a save: the reader announces it.
  useEffect(() => {
    if (saved) document.getElementById('catalog-saved')?.focus()
  }, [saved])

  /** null until this opening's list arrives, unless a save landed first. */
  const mine = useMemo(
    () => (products.data === null && savedRows.length === 0 ? null : mergeById(savedRows, products.data ?? [])),
    [products.data, savedRows],
  )

  const reset = useCallback((product: Product | null = null) => {
    setFormKey((k) => k + 1)
    setSaved(null)
    setEditing(product)
    // "Cadastrar outro" and "Cancelar edição" unmount the button that had focus.
    focusField('name')
  }, [])

  const newProduct = useCallback(() => reset(), [reset])

  const onEdit = useCallback(
    (e: MouseEvent<HTMLButtonElement>) => {
      const product = mine?.find((p) => String(p.id) === e.currentTarget.dataset.id)
      if (!product) return
      reset(product)
      // After the form re-renders filled in.
      focusField('name', true)
    },
    [mine, reset],
  )

  const onSaved = useCallback((product: Product, edited: boolean) => {
    setSavedRows((rows) => withSaved(rows, product))
    setSaved({ name: product.name, edited })
    setEditing(null)
  }, [])

  const ask = useCallback(() => {
    if (!saved) return
    asking.current = copy.catalog.askPrompt(saved.name)
    setOpen(false)
  }, [saved])

  const retry = useCallback(() => setLoad((n) => n + 1), [])

  const onOpenChange = useCallback(
    (next: boolean) => {
      setOpen(next)
      if (next) {
        reset()
        setSavedRows([])
        setOpening((n) => n + 1)
        setLoad((n) => n + 1)
      }
    },
    [reset],
  )

  // "Perguntar ao assistente": focus goes to the composer instead of back to the trigger.
  const onCloseAutoFocus = useCallback(
    (e: Event) => {
      const text = asking.current
      asking.current = null
      if (text === null) return
      e.preventDefault()
      onAsk(text)
    },
    [onAsk],
  )

  return {
    open,
    editing,
    formKey,
    saved,
    mine,
    categories: categories.data,
    loadFailure: loadFailure(categories.error, products.error),
    onOpenChange,
    onCloseAutoFocus,
    retry,
    ask,
    newProduct,
    onEdit,
    onSaved,
  }
}
