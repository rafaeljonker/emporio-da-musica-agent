import { useCallback, useEffect, useState } from 'react'
import { me } from '@/api/client'
import type { WarmStatus } from '@/api/types'

export type Session =
  | { status: 'checking' }
  | { status: 'signedOut' }
  | { status: 'signedIn'; warm: WarmStatus }

/** The cookie is the session; `me()` tells whether it is still valid after a reload. */
export function useSession() {
  const [session, setSession] = useState<Session>({ status: 'checking' })

  useEffect(() => {
    me().then(
      ({ warm }) => setSession({ status: 'signedIn', warm }),
      () => setSession({ status: 'signedOut' }),
    )
  }, [])

  const signedIn = useCallback((warm: WarmStatus) => setSession({ status: 'signedIn', warm }), [])
  const signedOut = useCallback(() => setSession({ status: 'signedOut' }), [])
  return { session, signedIn, signedOut }
}
