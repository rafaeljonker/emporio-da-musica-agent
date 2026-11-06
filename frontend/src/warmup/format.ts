const decimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export const ceil10 = (seconds: number) => Math.ceil(seconds / 10) * 10

/** "12 s", then "1 min 05 s" after 60 s (the pinned line uses it bare). */
export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`
}

/** Counts up, never down. */
export const formatElapsed = (seconds: number) => `Esperando há ${formatDuration(seconds)}`

export const isLongWait = (elapsed: number, expected: number) => elapsed > 2 * ceil10(expected)

/** The measured first-bubble p50; no number when there is none yet (or it rounds to 0). */
export const firstReplyNote = (p50: number | null) =>
  p50 === null || p50 < 0.05 ? 'poucos segundos' : `uns ${decimal.format(p50)} s`
