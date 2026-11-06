import { Send } from 'lucide-react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { copy } from '@/copy'
import { MAX_CHARS } from '@/warmup/queue'

interface Props {
  busy: boolean
  /** false keeps the text in the composer (a full warm-up queue). */
  onSend: (text: string) => boolean
  /** Owned by the shell: undo and re-login put queued text back here. */
  text: string
  setText: (text: string) => void
  placeholder: string
}

export function Composer({ busy, onSend, text, setText, placeholder }: Props) {
  const blocked = busy || text.trim() === ''

  // Send keeps focus wherever the user activated it: aria-disabled, never disabled.
  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (blocked) return
    if (onSend(text.trim())) setText('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) submit(e)
  }

  return (
    <form
      aria-label={copy.chat.composerForm}
      onSubmit={submit}
      className="mx-auto flex w-full max-w-2xl items-end gap-2 px-4 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
    >
      <Textarea
        id="composer-input"
        aria-label={copy.chat.composerLabel}
        placeholder={placeholder}
        rows={1}
        maxLength={MAX_CHARS}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        // Pill at one line (half of 2.75rem); keeps rounded corners while it grows to 5 lines.
        className="max-h-[8.25rem] min-h-11 resize-none rounded-[1.375rem] px-4 py-2.5"
      />
      <Button type="submit" size="icon" aria-label={copy.chat.send} aria-disabled={blocked}>
        <Send size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
      </Button>
    </form>
  )
}
