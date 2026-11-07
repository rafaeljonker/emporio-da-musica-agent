import { useEffect, useRef, useState } from 'react'
import { withSaved } from '@/client/catalog/domain/catalog'
import { mergeById } from '@/client/catalog/domain/form'
import { focusField } from '@/client/catalog/useCases/productForm/focusField'
import type { Category, Product } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { errorMessage } from '@/client/shared/lib/errorMessage'
import { useCategories } from './useCategories'
import { useMyProducts } from './useMyProducts'

export interface CatalogDialogProps {
  /** "Perguntar ao assistente": the shell puts this text in the composer (not sent). */
  onAsk: (text: string) => void
}

type Saved = { name: string; edited: boolean }

export interface CatalogDialogView {
  open: boolean
  /** The product the form edits; null adds a new one. */
  editing: Product | null
  /** `formKey` remounts the form with fresh fields on each reset, even for the same product. */
  panel: { state: 'form'; formKey: number } | ({ state: 'saved' } & Saved)
  mine: { state: 'pending' } | { state: 'ready'; products: Product[] }
  /** The categories or the list failed to load; null on none or a session expiry. */
  alert: string | null
  categories: Category[]
  onOpenChange: (open: boolean) => void
  onCloseAutoFocus: (e: Event) => void
  retry: () => void
  ask: () => void
  newProduct: () => void
  onEdit: (product: Product) => void
  onSaved: (product: Product, edited: boolean) => void
}

/** "Catálogo": a dialog where a signed-in visitor adds and edits own products. */
export function useCatalogDialog({ onAsk }: CatalogDialogProps): CatalogDialogView {
  const [open, setOpen] = useState(false)
  /** Bumped on each opening: the list starts over. */
  const [opening, setOpening] = useState(0)
  /** Bumped on each opening and by "Tentar de novo": a new load. */
  const [load, setLoad] = useState(0)
  /** Rows saved in this opening, newest first; they win over the server list. */
  const [savedRows, setSavedRows] = useState<Product[]>([])
  const [editing, setEditing] = useState<Product | null>(null)
  const [formKey, setFormKey] = useState(0)
  const [saved, setSaved] = useState<Saved | null>(null)
  const asking = useRef<string | null>(null)

  const categories = useCategories(open, load)
  const products = useMyProducts(open, opening, load)

  // The heading replaces the form on a save: the reader announces it.
  useEffect(() => {
    if (saved) document.getElementById('catalog-saved')?.focus()
  }, [saved])

  const reset = (product: Product | null = null) => {
    setFormKey((k) => k + 1)
    setSaved(null)
    setEditing(product)
    // "Cadastrar outro" and "Cancelar edição" unmount the button that had focus.
    focusField('name')
  }

  // An expired session signs out (the app listens): no alert for it.
  const failure = [categories, products].find((r) => r.state === 'error' && r.error.code !== 'unauthenticated')

  return {
    open,
    editing,
    panel: saved ? { state: 'saved', ...saved } : { state: 'form', formKey },
    // A save may land first: the rows it put on screen win over the (older) server list.
    mine:
      products.data === null && savedRows.length === 0
        ? { state: 'pending' }
        : { state: 'ready', products: mergeById(savedRows, products.data ?? []) },
    alert: failure?.state === 'error' ? errorMessage(failure.error, 'catalogLoad') : null,
    categories: categories.data,
    onOpenChange: (next) => {
      setOpen(next)
      if (!next) return
      reset()
      setSavedRows([])
      setOpening((n) => n + 1)
      setLoad((n) => n + 1)
    },
    // "Perguntar ao assistente": focus goes to the composer instead of back to the trigger.
    onCloseAutoFocus: (e) => {
      const text = asking.current
      asking.current = null
      if (text === null) return
      e.preventDefault()
      onAsk(text)
    },
    retry: () => setLoad((n) => n + 1),
    ask: () => {
      if (!saved) return
      asking.current = copy.catalog.askPrompt(saved.name)
      setOpen(false)
    },
    newProduct: () => reset(),
    onEdit: (product) => {
      reset(product)
      // After the form re-renders filled in.
      focusField('name', true)
    },
    onSaved: (product, edited) => {
      setSavedRows((rows) => withSaved(rows, product))
      setSaved({ name: product.name, edited })
      setEditing(null)
    },
  }
}
