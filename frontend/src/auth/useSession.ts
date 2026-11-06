import { useCallback, useEffect, useState } from 'react'
import { me } from '@/api/client'
import type { WarmStatus } from '@/api/types'

export type Session =
  | { status: 'checking' }
  | { status: 'signedOut'; expired?: boolean }
  // fromLogin: a fresh login (e.g. after expiry), not a reload with a live cookie.
  | { status: 'signedIn'; warm: WarmStatus; fromLogin: boolean; customerId: number | null }

/** The cookie is the session; `me()` tells whether it is still valid after a reload. */
export function useSession() {
  const [session, setSession] = useState<Session>({ status: 'checking' })

  useEffect(() => {
    me().then(
      ({ warm, customer_id }) => setSession({ status: 'signedIn', warm, fromLogin: false, customerId: customer_id }),
      () => setSession({ status: 'signedOut' }),
    )
  }, [])

  const signedIn = useCallback(
    // Login starts anonymous (the server resets customer_id).
    (warm: WarmStatus) => setSession({ status: 'signedIn', warm, fromLogin: true, customerId: null }),
    [],
  )
  const signedOut = useCallback(() => setSession({ status: 'signedOut' }), [])
  const expired = useCallback(() => setSession({ status: 'signedOut', expired: true }), [])
  return { session, signedIn, signedOut, expired }
}
