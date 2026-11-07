// Vitest setup: jest-dom matchers, cleanup, and the browser APIs jsdom lacks.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

let pointer: 'fine' | 'coarse' = 'fine'
/** The pointer `(pointer: fine)` media queries see; resets to fine before each test. */
export const setPointer = (p: 'fine' | 'coarse') => {
  pointer = p
}

beforeEach(() => {
  pointer = 'fine'
  sessionStorage.clear()
})
afterEach(cleanup)

window.matchMedia = (query: string) => ({
  matches: query.includes('pointer') && query.includes(pointer),
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
})

globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Radix Select scrolls and captures the pointer; jsdom has neither.
Element.prototype.scrollIntoView = () => {}
Element.prototype.hasPointerCapture = () => false
Element.prototype.setPointerCapture = () => {}
Element.prototype.releasePointerCapture = () => {}
