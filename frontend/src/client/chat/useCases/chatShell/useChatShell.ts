import { useCallback, useMemo, useState } from 'react'
import { appendQuestion } from '@/client/chat/domain/composer'
import { isTyping, toTurnRecords, type Entry } from '@/client/chat/domain/entries'
import type { TurnRecord } from '@/client/chat/domain/metrics'
import { logout } from '@/client/shared/lib/api'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { focusById } from '@/client/shared/lib/focus'
import { save } from '@/client/warmup/domain/queue'
import type { Announcement } from '@/client/warmup/ui/StatusRegion'
import { useQueuedMessage } from '@/client/warmup/useCases/queuedMessage/useQueuedMessage'
import type { WarmupStatusProps } from '@/client/warmup/useCases/warmupStatus/useWarmupStatus'
import { useWarmStatus } from '@/client/warmup/useCases/warmupStatus/useWarmStatus'
import { useChatStream } from './useChatStream'
import { useReadyHandoff } from './useReadyHandoff'

export interface ChatShellProps {
  warm: WarmStatus | null
  fromLogin: boolean
  customerId: number | null
  onSignedOut: () => void
}

export type ChatShellView = {
  entries: Entry[]
  typing: boolean
  busy: boolean
  text: string
  setText: (text: string) => void
  /** The shared live region's last sentence. */
  said: Announcement | null
  /** Lines typed during warm-up, shown as one pending group. */
  queued: string[] | undefined
  customerId: number | null
  turns: TurnRecord[]
  /** The measured cold start; null until ready (and always for provider_api). */
  warmupSeconds: number | null
  /** Local mode runs on the user's machine: cost is R$ 0. */
  local: boolean
  /** Returns false to keep the text in the composer (a full warm-up queue). */
  onSend: (text: string) => boolean
  ask: (question: string) => void
  undo: () => void
  resend: (id: string) => void
  signOut: () => void
  onSwitched: (customerId: number | null, divider: string) => void
} & (
  | { state: 'warming'; warmup: WarmupStatusProps; localNotice: false; showEmpty: false }
  | { state: 'chat'; warmup: null; localNotice: boolean; showEmpty: boolean }
)

export function useChatShell({ warm, fromLogin, customerId: initialCustomer, onSignedOut }: ChatShellProps): ChatShellView {
  const { entries, busy, send, resend, addDivider } = useChatStream()
  const { status, elapsed, networkError, retry } = useWarmStatus(warm)
  const [customerId, setCustomerId] = useState(initialCustomer)
  const [said, setSaid] = useState<Announcement | null>(null)
  const announce = useCallback((text: string) => setSaid((s) => ({ n: (s?.n ?? 0) + 1, text })), [])
  const panelGone = useReadyHandoff(warm, status?.stage === 'ready')

  // provider_api never warms, whatever the seed said.
  const warming = !panelGone && status?.mode !== 'provider_api'
  const queue = useQueuedMessage(!warming, send, fromLogin)
  const [text, setText] = useState(queue.restored)

  const local = status?.mode === 'local_cpu'
  const turns = useMemo(() => toTurnRecords(entries, local), [entries, local])
  const queued = queue.state === 'queued' ? queue.lines : undefined

  // "Perguntar ao assistente": the question waits in the composer after any draft, caret at the
  // end; never sent.
  const ask = useCallback((question: string) => {
    setText((draft) => appendQuestion(draft, question))
    requestAnimationFrame(() => {
      const input = document.getElementById('composer-input')
      if (!(input instanceof HTMLTextAreaElement)) return
      input.focus()
      input.setSelectionRange(input.value.length, input.value.length)
    })
  }, [])

  const base = {
    entries,
    typing: isTyping(entries),
    busy,
    text,
    setText,
    said,
    queued,
    customerId,
    turns,
    warmupSeconds:
      status?.stage === 'ready' && status.mode !== 'provider_api' ? Math.round(status.elapsed_seconds) : null,
    local,
    ask,
    undo: () => {
      const back = queue.take()
      setText(text ? `${back}\n${text}` : back)
      announce(copy.warmup.undone)
      focusById('composer-input')
    },
    resend,
    // Back to login even if the logout request fails (offline, 5xx). Sair drops a queued message;
    // an expired session keeps it for the next login.
    signOut: () => {
      save(null)
      void logout().then(onSignedOut)
    },
    onSwitched: (id: number | null, divider: string) => {
      setCustomerId(id)
      addDivider(divider)
    },
  }
  if (warming)
    return {
      ...base,
      state: 'warming',
      onSend: queue.add,
      warmup: { status, elapsed, networkError, compact: !!queued, onRetry: retry, announce },
      localNotice: false,
      showEmpty: false,
    }
  return {
    ...base,
    state: 'chat',
    onSend: (t) => {
      void send(t)
      return true
    },
    warmup: null,
    localNotice: local,
    showEmpty: !entries.length && !queued,
  }
}
