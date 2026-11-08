import { useEffect, useState } from 'react'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import { focusById, isFinePointer } from '@/client/shared/lib/focus'

const READY_LINGER_MS = 800 // the all-done list stays this long
const READY_FOCUS_MS = 2000 // "Pronto pra conversar." is spoken before any focus move

const focusOnBody = () => !document.activeElement || document.activeElement === document.body

/**
 * The warm-up panel's exit: true once it is gone. A reload after ready has no panel at all.
 * Focus moves only when it sits on the body, to the composer with a fine pointer (no soft
 * keyboard on touch), else to the log.
 */
export function useReadyHandoff(seed: WarmStatus | null, ready: boolean): boolean {
  const [readyOnArrival] = useState(seed?.stage === 'ready')
  const [panelGone, setPanelGone] = useState(readyOnArrival)
  // Opened ready (provider_api, or the model was already warm): no panel, no announcement to wait
  // for. Focus would sit on the body after the login form unmounted; never into the log.
  const [openedReady] = useState(readyOnArrival || seed?.mode === 'provider_api')

  useEffect(() => {
    if (openedReady && focusOnBody() && isFinePointer()) focusById('composer-input')
  }, [openedReady])

  useEffect(() => {
    if (!ready || readyOnArrival) return
    const close = setTimeout(() => setPanelGone(true), READY_LINGER_MS)
    // The removed panel leaves focus on the body.
    const focus = setTimeout(() => {
      if (focusOnBody()) focusById(isFinePointer() ? 'composer-input' : 'chat-log')
    }, READY_FOCUS_MS)
    return () => {
      clearTimeout(close)
      clearTimeout(focus)
    }
  }, [ready, readyOnArrival])

  return panelGone
}
