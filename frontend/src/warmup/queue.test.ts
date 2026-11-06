import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enqueue, load, save, undo } from './queue'

describe('queued message', () => {
  beforeEach(() => {
    const store = new Map<string, string>()
    vi.stubGlobal('sessionStorage', {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
      removeItem: (k: string) => void store.delete(k),
    })
  })
  afterEach(() => vi.unstubAllGlobals())

  it('undo joins queued lines with newline', () => {
    const q = enqueue(enqueue(null, 'Oi'), 'Quanto tá o C40?')
    expect(q).toEqual({ lines: ['Oi', 'Quanto tá o C40?'] })
    expect(undo(q)).toBe('Oi\nQuanto tá o C40?')
  })

  it('queued message survives reload via sessionStorage', () => {
    save(enqueue(null, 'Oi'))
    expect(sessionStorage.getItem('emporio.queued')).not.toBeNull()
    expect(load()).toEqual({ lines: ['Oi'] })
    save(null)
    expect(load()).toBeNull()
  })
})
