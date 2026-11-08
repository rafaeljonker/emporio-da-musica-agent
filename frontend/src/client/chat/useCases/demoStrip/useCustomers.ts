import { useEffect, useState } from 'react'
import { customers, type ApiError } from '@/client/shared/lib/api'
import type { DemoCustomer } from '@/client/shared/lib/apiTypes'

export type CustomersView =
  | { state: 'pending' }
  | { state: 'error'; error: ApiError }
  | { state: 'success'; data: DemoCustomer[] }

/** GET /api/customers once: the demo identities for "Conversar como…". */
export function useCustomers(): CustomersView {
  const [view, setView] = useState<CustomersView>({ state: 'pending' })
  useEffect(() => {
    let live = true
    void customers().then((res) => {
      if (live) setView(res.ok ? { state: 'success', data: res.data } : { state: 'error', error: res.error })
    })
    return () => {
      live = false
    }
  }, [])
  return view
}
