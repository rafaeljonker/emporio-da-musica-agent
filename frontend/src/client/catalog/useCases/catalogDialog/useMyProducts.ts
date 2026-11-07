import { useEffect, useState } from 'react'
import { mergeById } from '@/client/catalog/domain/form'
import { myProducts, type ApiError } from '@/client/shared/lib/api'
import type { Product } from '@/client/shared/lib/apiTypes'

/** `data` is null until this opening's list arrives; a failed retry keeps the rows already shown. */
export type MyProductsView = { data: Product[] | null } & (
  | { state: 'pending' }
  | { state: 'error'; error: ApiError }
  | { state: 'success' }
)

/**
 * The visitor's products, loaded while `enabled`. `opening` changes on each opening (the list
 * starts over); `load` on each opening and retry (a retry merges into the rows already shown).
 */
export function useMyProducts(enabled: boolean, opening: number, load: number): MyProductsView {
  const [loaded, setLoaded] = useState<{ opening: number; list: Product[] } | null>(null)
  const [settled, setSettled] = useState<{ load: number; error: ApiError | null } | null>(null)

  useEffect(() => {
    if (!enabled) return
    let live = true
    void myProducts().then((res) => {
      if (!live) return
      const list = res.ok ? res.data : null
      if (list)
        setLoaded((shown) => ({ opening, list: shown?.opening === opening ? mergeById(shown.list, list) : list }))
      setSettled({ load, error: res.ok ? null : res.error })
    })
    return () => {
      live = false
    }
  }, [enabled, opening, load])

  const data = loaded?.opening === opening ? loaded.list : null
  if (settled?.load !== load) return { data, state: 'pending' }
  return settled.error ? { data, state: 'error', error: settled.error } : { data, state: 'success' }
}
