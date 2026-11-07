import type { ReactNode } from 'react'

export interface Announcement {
  n: number
  text: string
}

/**
 * The one persistent role="status" in <main>: it outlives the warm-up panel, so "Pronto pra
 * conversar." is still spoken after the panel is removed. It carries the warm-up sentences, the
 * undo confirmation and (as children) the typing indicator. Not atomic: only the new piece is read.
 */
export function StatusRegion({ said, children }: { said: Announcement | null; children?: ReactNode }) {
  return (
    <div role="status" aria-atomic="false" className="mx-auto w-full max-w-2xl px-4">
      {/* A new key per sentence, so saying the same text twice is still an addition. */}
      {said && (
        <span key={said.n} className="sr-only">
          {said.text}
        </span>
      )}
      {children}
    </div>
  )
}
