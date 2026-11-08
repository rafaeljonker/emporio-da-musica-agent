import { useEffect, useState } from 'react'
import { me, type ApiError } from '@/client/shared/lib/api'
import type { Me } from '@/client/shared/lib/apiTypes'

export type MeView = { state: 'pending' } | { state: 'error'; error: ApiError } | { state: 'success'; me: Me }

/** GET /api/auth/me once: the cookie is the session, and this tells whether it is still valid. */
export function useMe(): MeView {
  const [view, setView] = useState<MeView>({ state: 'pending' })
  useEffect(() => {
    let live = true
    void me().then((res) => {
      if (live) setView(res.ok ? { state: 'success', me: res.data } : { state: 'error', error: res.error })
    })
    return () => {
      live = false
    }
  }, [])
  return view
}
