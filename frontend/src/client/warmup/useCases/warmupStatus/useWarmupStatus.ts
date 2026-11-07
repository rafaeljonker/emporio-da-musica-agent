import { useEffect, useEffectEvent, useRef, useState, type RefObject } from 'react'
import type { WarmStage, WarmStatus } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { isLongWait } from '@/client/warmup/domain/format'

const t = copy.warmup

export interface WarmupStatusProps {
  status: WarmStatus | null
  elapsed: number
  networkError: boolean
  /** A message is queued: below md the panel collapses to one pinned line. */
  compact: boolean
  onRetry: () => Promise<void>
  announce: (text: string) => void
}

export type WarmupStatusView = {
  elapsed: number
  networkError: boolean
  compact: boolean
  /** The mode's one waiting stage: "Ligando o modelo" (GPU) or "Carregando o modelo" (local). */
  waiting: string
  local: boolean
  /** The two-item stage list: the waiting stage, then "Pronto pra conversar". */
  steps: readonly { label: string; step: 'done' | 'current' | 'pending' }[]
  titleRef: RefObject<HTMLHeadingElement | null>
  retryRef: RefObject<HTMLButtonElement | null>
  retry: () => void
} & ({ state: 'checking'; status: null } | { state: 'waiting' | 'long' | 'ready' | 'failed'; status: WarmStatus })

/** What was last spoken; `n` grows only when there is something new to say. */
interface Announced {
  stage: WarmStage | undefined
  long: boolean
  n: number
  text: string
}

export function useWarmupStatus({
  status,
  elapsed,
  networkError,
  compact,
  onRetry,
  announce,
}: WarmupStatusProps): WarmupStatusView {
  const titleRef = useRef<HTMLHeadingElement>(null)
  const retryRef = useRef<HTMLButtonElement>(null)
  const stage = status?.stage
  const local = status?.mode === 'local_cpu'
  const waiting = local ? t.stages.model_loading : t.stages.server_starting
  const long = !!status && stage !== 'ready' && stage !== 'failed' && isLongWait(elapsed, status.expected_seconds)

  // Stage changes are spoken (not the first stage: the h2 and list are already on screen), and
  // the long wait once until a retry. Adjusted while rendering; the effect below only speaks.
  const [announced, setAnnounced] = useState<Announced>({ stage, long: false, n: 0, text: '' })
  let next = announced
  if (stage !== next.stage) {
    const text = stage === 'ready' ? t.ready : stage && stage !== 'failed' ? `${waiting}.` : null
    next = text ? { ...next, stage, n: next.n + 1, text } : { ...next, stage }
  }
  if (long && !next.long) next = { ...next, long: true, n: next.n + 1, text: t.longWait(waiting) }
  if (next !== announced) setAnnounced(next)

  const say = useEffectEvent(announce)
  useEffect(() => {
    if (announced.n > 0) say(announced.text)
  }, [announced.n, announced.text])

  useEffect(() => {
    if (networkError) say(t.network)
  }, [networkError])

  const failed = stage === 'failed'
  useEffect(() => {
    if (failed) retryRef.current?.focus()
  }, [failed])

  const retry = () => {
    setAnnounced((a) => ({ ...a, long: false }))
    titleRef.current?.focus()
    void onRetry()
  }

  const ready = stage === 'ready'
  const steps = [
    { label: waiting, step: ready ? 'done' : 'current' },
    { label: t.stages.ready, step: ready ? 'done' : 'pending' },
  ] as const
  const base = { elapsed, networkError, compact, waiting, local, steps, titleRef, retryRef, retry }
  if (!status) return { ...base, state: 'checking', status: null }
  const state = stage === 'ready' || stage === 'failed' ? stage : long ? 'long' : 'waiting'
  return { ...base, state, status }
}
