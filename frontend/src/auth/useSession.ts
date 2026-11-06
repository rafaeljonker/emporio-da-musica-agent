import { useCallback, useEffect, useState } from 'react'
import { me } from '@/api/client'
import type { WarmStatus } from '@/api/types'

export type Session =
  | { status: 'checking' }
  | { status: 'signedOut' }
  // fromLogin: a fresh login (e.g. after expiry), not a reload with a live cookie.
  | { status: 'signedIn'; warm: WarmStatus; fromLogin: boolean }

/** The cookie is the session; `me()` tells whether it is still valid after a reload. */
export function useSession() {
  const [session, setSession] = useState<Session>({ status: 'checking' })

  useEffect(() => {
    me().then(
      ({ warm }) => setSession({ status: 'signedIn', warm, fromLogin: false }),
      () => setSession({ status: 'signedOut' }),
    )
  }, [])

  const signedIn = useCallback(
    (warm: WarmStatus) => setSession({ status: 'signedIn', warm, fromLogin: true }),
    [],
  )
  const signedOut = useCallback(() => setSession({ status: 'signedOut' }), [])
  return { session, signedIn, signedOut }
}
