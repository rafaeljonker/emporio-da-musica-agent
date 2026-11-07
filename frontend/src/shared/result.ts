/** An expected failure as a value: callers branch on `ok`, nothing throws. */
export type Result<T, E> = { ok: true; data: T } | { ok: false; error: E }

export const ok = <T>(data: T): { ok: true; data: T } => ({ ok: true, data })
export const err = <E>(error: E): { ok: false; error: E } => ({ ok: false, error })
