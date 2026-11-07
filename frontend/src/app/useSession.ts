import { useCallback, useEffect, useState } from 'react'
import { me } from '@/client/shared/lib/api'
import { onSessionExpired } from '@/client/shared/lib/session'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'

export type Session =
  | { status: 'checking' }
  | { status: 'signedOut'; expired?: boolean }
  // fromLogin: a fresh login (e.g. after expiry), not a reload with a live cookie.
  | { status: 'signedIn'; warm: WarmStatus; fromLogin: boolean; customerId: number | null }

/** The cookie is the session; `me()` tells whether it is still valid after a reload. */
export function useSession() {
  const [session, setSession] = useState<Session>({ status: 'checking' })

  useEffect(() => {
    void me().then((res) =>
      setSession(
        res.ok
          ? { status: 'signedIn', warm: res.data.warm, fromLogin: false, customerId: res.data.customer_id }
          : { status: 'signedOut' },
      ),
    )
  }, [])

  // Any 401 mid-session signs out with the "expired" line; a 401 from the first `me()` is a plain sign-out.
  useEffect(
    () =>
      onSessionExpired(() => setSession((s) => (s.status === 'signedIn' ? { status: 'signedOut', expired: true } : s))),
    [],
  )

  const signedIn = useCallback(
    // Login starts anonymous (the server resets customer_id).
    (warm: WarmStatus) => setSession({ status: 'signedIn', warm, fromLogin: true, customerId: null }),
    [],
  )
  const signedOut = useCallback(() => setSession({ status: 'signedOut' }), [])
  return { session, signedIn, signedOut }
}
