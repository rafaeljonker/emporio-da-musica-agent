import { useEffect, useRef, useState, type RefObject, type UIEvent } from 'react'
import { contentKey, userLines, type Entry } from '@/client/chat/domain/entries'
import { focusById } from '@/client/shared/lib/focus'

const NEAR_BOTTOM_PX = 80

export interface TranscriptProps {
  entries: Entry[]
  /** Lines typed during warm-up, shown as one pending group until the model is ready. */
  queued?: string[]
  /** A reply is being generated: dots after the last bubble. */
  typing: boolean
  onUndo: () => void
  onResend: (id: string) => void
}

/** `unseen`: content arrived while the reader was scrolled up; the pill offers a jump. */
export interface TranscriptView {
  state: 'following' | 'unseen'
  logRef: RefObject<HTMLDivElement | null>
  onScroll: (e: UIEvent<HTMLDivElement>) => void
  jumpToBottom: () => void
  resend: (id: string) => void
}

/**
 * Follows new content only when the reader is already near the bottom; otherwise offers the
 * pill. Sending a message always follows: the reader's own bubble must not land off screen.
 * Scrolling never moves focus.
 */
export function useTranscript({ entries, queued, typing, onResend }: TranscriptProps): TranscriptView {
  const logRef = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const sentLines = useRef(0)
  const [unseen, setUnseen] = useState(false)
  const key = contentKey(entries, queued?.length, typing)
  const lines = userLines(entries, queued?.length ?? 0)

  // Syncs the log's scroll position (measured DOM) with new content.
  useEffect(() => {
    const el = logRef.current
    if (!el) return
    if (lines > sentLines.current) nearBottom.current = true
    sentLines.current = lines
    if (nearBottom.current) el.scrollTop = el.scrollHeight
    else setUnseen(true)
  }, [key, lines])

  return {
    state: unseen ? 'unseen' : 'following',
    logRef,
    onScroll: (e) => {
      const el = e.currentTarget
      nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
      if (nearBottom.current) setUnseen(false)
    },
    jumpToBottom: () => {
      const el = logRef.current
      if (el) el.scrollTop = el.scrollHeight
      setUnseen(false)
      // The pill unmounts on click; focus goes to the composer, not the body.
      focusById('composer-input')
    },
    resend: (id) => {
      onResend(id)
      focusById('composer-input')
    },
  }
}
