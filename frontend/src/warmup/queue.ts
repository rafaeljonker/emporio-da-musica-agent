/** Messages typed during warm-up; sent once, joined by "\n", when the model is ready. */
export interface QueuedMessage {
  lines: string[]
}

const KEY = 'emporio.queued'

export const enqueue = (q: QueuedMessage | null, line: string): QueuedMessage => ({
  lines: [...(q?.lines ?? []), line],
})

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
