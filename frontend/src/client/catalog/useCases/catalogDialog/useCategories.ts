import { useEffect, useState } from 'react'
import { catalogCategories, type ApiError } from '@/client/shared/lib/api'
import type { Category } from '@/client/shared/lib/apiTypes'

/** `data` is the last list that arrived ([] before any): it stays on screen while a load runs or fails. */
export type CategoriesView = { data: Category[] } & (
  | { state: 'pending' }
  | { state: 'error'; error: ApiError }
  | { state: 'success' }
)

/** The categories for the select, loaded while `enabled`; `load` changes on each opening and retry. */
export function useCategories(enabled: boolean, load: number): CategoriesView {
  const [data, setData] = useState<Category[]>([])
  const [settled, setSettled] = useState<{ load: number; error: ApiError | null } | null>(null)

  useEffect(() => {
    if (!enabled) return
    let live = true
    void catalogCategories().then((res) => {
      if (!live) return
      if (res.ok) setData(res.data)
      setSettled({ load, error: res.ok ? null : res.error })
    })
    return () => {
      live = false
    }
  }, [enabled, load])

  if (settled?.load !== load) return { data, state: 'pending' }
  return settled.error ? { data, state: 'error', error: settled.error } : { data, state: 'success' }
}
