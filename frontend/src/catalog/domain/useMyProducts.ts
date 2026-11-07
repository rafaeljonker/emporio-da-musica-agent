import { useEffect, useState } from 'react'
import { myProducts } from '@/api/client'
import type { Product } from '@/api/types'
import { mergeById } from './form'

/**
 * The visitor's products, loaded while `enabled`. `data` is null until this opening's list
 * arrives; `load` changes on each opening and retry; a retry in the same opening keeps the rows already shown first.
 */
export function useMyProducts(enabled: boolean, opening: number, load: number) {
  const [loaded, setLoaded] = useState<{ opening: number; list: Product[] } | null>(null)
  const [failed, setFailed] = useState<{ load: number; error: unknown } | null>(null)

  useEffect(() => {
    if (!enabled) return
    let live = true
    myProducts().then(
      (list) =>
        live &&
        setLoaded((shown) => ({ opening, list: shown?.opening === opening ? mergeById(shown.list, list) : list })),
      (error) => live && setFailed({ load, error }),
    )
    return () => {
      live = false
    }
  }, [enabled, opening, load])

  return { data: loaded?.opening === opening ? loaded.list : null, error: failed?.load === load ? failed.error : null }
}
