import { useEffect, useState } from 'react'
import { catalogCategories } from '@/api/client'
import type { Category } from '@/api/types'

/** The categories for the select, loaded while `enabled`; `load` changes on each opening and retry. The last list stays while a load runs. */
export function useCategories(enabled: boolean, load: number) {
  const [data, setData] = useState<Category[]>([])
  const [failed, setFailed] = useState<{ load: number; error: unknown } | null>(null)

  useEffect(() => {
    if (!enabled) return
    let live = true
    catalogCategories().then(
      (list) => live && setData(list),
      (error) => live && setFailed({ load, error }),
    )
    return () => {
      live = false
    }
  }, [enabled, load])

  return { data, error: failed?.load === load ? failed.error : null }
}
