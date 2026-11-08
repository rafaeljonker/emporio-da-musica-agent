import { useEffect, useRef, useState, type RefObject } from 'react'
import type { TurnRecord } from '@/client/chat/domain/metrics'

export interface MetricsDetailsProps {
  turns: TurnRecord[]
  /** The measured cold start in seconds, once warm-up reached ready (not provider_api). */
  warmupSeconds: number | null
  local: boolean
}

export interface MetricsDetailsView {
  state: 'closed' | 'open'
  rootRef: RefObject<HTMLSpanElement | null>
  toggleRef: RefObject<HTMLButtonElement | null>
  toggle: () => void
  /** The latest reply's metrics, once there is one. */
  last: { state: 'none' } | ({ state: 'some' } & TurnRecord)
}

/** Closes on Escape (focus back to the toggle), outside click (focus stays put) and the toggle. */
export function useMetricsDetails({ turns }: MetricsDetailsProps): MetricsDetailsView {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLSpanElement>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)

  // Syncs with document keydown and pointerdown while open.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setOpen(false)
      // Back to the toggle, unless focus is somewhere else on purpose (e.g. typing in the composer).
      const at = document.activeElement
      if (!at || at === document.body || rootRef.current?.contains(at)) toggleRef.current?.focus()
    }
    // Outside click closes without moving focus: it goes wherever the click put it.
    const onDown = (e: PointerEvent) => {
      if (!(e.target instanceof Node && rootRef.current?.contains(e.target))) setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onDown)
    }
  }, [open])

  const latest = turns.at(-1)
  return {
    state: open ? 'open' : 'closed',
    rootRef,
    toggleRef,
    toggle: () => setOpen(!open),
    last: latest ? { state: 'some', ...latest } : { state: 'none' },
  }
}
