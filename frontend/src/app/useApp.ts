import { useEffect, useEffectEvent, useState } from 'react'
import { useMe } from '@/client/auth/useCases/session/useMe'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import { onSessionExpired } from '@/client/shared/lib/session'

export type Session =
  | { state: 'checking' }
  | { state: 'signedOut'; expired: boolean }
  // fromLogin: a fresh login (e.g. after expiry), not a reload with a live cookie.
  | { state: 'signedIn'; warm: WarmStatus; fromLogin: boolean; customerId: number | null }

export type AppView = Session & { signedIn: (warm: WarmStatus) => void; signedOut: () => void }

/** The session: `me()` decides it after a reload; login, logout and expiry change it after. */
export function useApp(): AppView {
  const me = useMe()
  // Set by a transition; until the first one the session is what `me()` said.
  const [changed, setChanged] = useState<Session | null>(null)
  const session: Session =
    changed ??
    (me.state === 'pending'
      ? { state: 'checking' }
      : me.state === 'success'
        ? { state: 'signedIn', warm: me.me.warm, fromLogin: false, customerId: me.me.customer_id }
        : { state: 'signedOut', expired: false })

  // Any 401 mid-session signs out with the "expired" line; a 401 from the first `me()` is a plain sign-out.
  const expire = useEffectEvent(() => {
    if (session.state === 'signedIn') setChanged({ state: 'signedOut', expired: true })
  })
  useEffect(() => onSessionExpired(expire), [])

  return {
    ...session,
    // Login starts anonymous (the server resets customer_id).
    signedIn: (warm) => setChanged({ state: 'signedIn', warm, fromLogin: true, customerId: null }),
    signedOut: () => setChanged({ state: 'signedOut', expired: false }),
  }
}
