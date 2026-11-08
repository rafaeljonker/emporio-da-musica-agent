// Session expiry, told once: any 401 outside login calls notifySessionExpired(); the app listens.
const listeners = new Set<() => void>()

export function notifySessionExpired(): void {
  for (const listener of listeners) listener()
}

/** Subscribes `listener`; returns the unsubscribe (an effect cleanup). */
export function onSessionExpired(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
