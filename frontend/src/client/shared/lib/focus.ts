/** Focuses the element with `id`, if it is on the page. */
export const focusById = (id: string) => document.getElementById(id)?.focus()

/** A mouse or trackpad: focusing a text field opens no soft keyboard. */
export const isFinePointer = () => matchMedia('(pointer: fine)').matches
