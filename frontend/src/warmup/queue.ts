/** Messages typed during warm-up; sent once, joined by "\n", when the model is ready. */
export interface QueuedMessage {
  lines: string[]
}

const KEY = 'emporio.queued'

/** The backend's ChatIn limit, for one message and for the joined queue alike. */
export const MAX_CHARS = 1000

/** null when the joined text would pass MAX_CHARS: the line stays in the composer instead. */
export function enqueue(q: QueuedMessage | null, line: string): QueuedMessage | null {
  const lines = [...(q?.lines ?? []), line]
  return lines.join('\n').length > MAX_CHARS ? null : { lines }
}

export const undo = (q: QueuedMessage) => q.lines.join('\n')

export function load(): QueuedMessage | null {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as QueuedMessage | null
  } catch {
    return null
  }
}

export function save(q: QueuedMessage | null): void {
  if (q) sessionStorage.setItem(KEY, JSON.stringify(q))
  else sessionStorage.removeItem(KEY)
}
