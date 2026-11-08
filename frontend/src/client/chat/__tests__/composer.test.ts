import { describe, expect, it } from 'vitest'
import { appendQuestion } from '@/client/chat/domain/composer'

describe('appendQuestion', () => {
  it('fills an empty composer', () => expect(appendQuestion('  ', 'Vocês têm?')).toBe('Vocês têm?'))
  it('keeps a draft and adds the question on a new line', () =>
    expect(appendQuestion('Oi, tudo bem?', 'Vocês têm?')).toBe('Oi, tudo bem?\nVocês têm?'))
})
