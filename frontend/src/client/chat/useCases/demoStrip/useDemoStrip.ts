import type { ReactNode } from 'react'
import { dividerText } from '@/client/chat/domain/entries'
import { setIdentity } from '@/client/shared/lib/api'
import type { DemoCustomer } from '@/client/shared/lib/apiTypes'
import { useCustomers } from './useCustomers'

export const ANON = 'anon'

export interface DemoStripProps {
  customerId: number | null
  /** After PUT /api/identity succeeded (the server rotated the session): the shell adds the divider. */
  onSwitched: (customerId: number | null, divider: string) => void
  children: ReactNode
}

/** Every state lists anonymous; the customers join once they arrive. */
export interface DemoStripView {
  customers: { state: 'loading' } | { state: 'failed' } | { state: 'ready'; list: DemoCustomer[] }
  /** The select's value: the customer id, or ANON. */
  value: string
  change: (value: string) => Promise<void>
}

export function useDemoStrip({ customerId, onSwitched }: DemoStripProps): DemoStripView {
  const loaded = useCustomers()
  const list = loaded.state === 'success' ? loaded.data : []

  return {
    customers:
      loaded.state === 'pending' ? { state: 'loading' } : loaded.state === 'error' ? { state: 'failed' } : { state: 'ready', list },
    value: customerId === null ? ANON : String(customerId),
    // Selection follows the server: it changes only after the PUT succeeds. Focus never moves (SC 3.2.2).
    change: async (value) => {
      const id = value === ANON ? null : Number(value)
      if (!(await setIdentity(id)).ok) return
      onSwitched(id, dividerText(list, id))
    },
  }
}
