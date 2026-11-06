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
    const q = enqueue(enqueue(null, 'Oi', null), 'Quanto tá o C40?', 14)
    expect(q).toEqual({ lines: ['Oi', 'Quanto tá o C40?'], customerId: 14 })
    expect(undo(q)).toBe('Oi\nQuanto tá o C40?')
  })

  it('queued message survives reload via sessionStorage', () => {
    save(enqueue(null, 'Oi', null))
    expect(sessionStorage.getItem('emporio.queued')).not.toBeNull()
    expect(load()).toEqual({ lines: ['Oi'], customerId: null })
    save(null)
    expect(load()).toBeNull()
  })
})
