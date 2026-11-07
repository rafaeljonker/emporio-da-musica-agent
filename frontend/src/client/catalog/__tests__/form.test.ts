import { describe, expect, it } from 'vitest'
import { HttpError, SessionExpired } from '@/client/shared/lib/api'
import { copy } from '@/client/shared/lib/copy'
import { appendQuestion, errorCopy, mergeById, parseSpecs, toPrice, validate, type ProductFields } from '@/client/catalog/domain/form'

describe('toPrice', () => {
  it.each([
    ['1.234,50', '1234.50'],
    ['1234.5', '1234.50'],
    ['899,90', '899.90'],
    ['R$ 12', '12.00'],
    [' 7,5 ', '7.50'],
  ])('reads %s as %s', (text, want) => expect(toPrice(text)).toBe(want))

  it.each(['0', 'abc', '0,001', '', '-5', '1.234.567,00', '12,345'])('rejects %s', (text) =>
    expect(toPrice(text)).toBeNull(),
  )
})

describe('parseSpecs', () => {
  it('reads one "Chave: valor" per line, skipping blank lines', () => {
    expect(parseSpecs('Cordas: nylon\n\n Tampo : abeto ')).toEqual({ Cordas: 'nylon', Tampo: 'abeto' })
  })
  it('keeps colons inside the value', () => expect(parseSpecs('Escala: 1:1')).toEqual({ Escala: '1:1' }))
  it('allows none', () => expect(parseSpecs('  ')).toEqual({}))
  it('rejects more than 20 lines', () => {
    const lines = Array.from({ length: 21 }, (_, i) => `K${i}: v`).join('\n')
    expect(parseSpecs(lines)).toBeNull()
  })
  it('rejects a line without a colon', () => expect(parseSpecs('Cordas: nylon\nsem dois pontos')).toBeNull())
  it('rejects an empty key or value', () => expect(parseSpecs(': nylon')).toBeNull())
  it.each(['Cor\u0007: preto', 'Cor: pre\u200bto', 'Cor: \u202epreto', 'Co\tr: preto'])(
    'rejects control or invisible characters in %j',
    (line) => expect(parseSpecs(line)).toBeNull(),
  )
})

const valid: ProductFields = {
  name: 'Cavaquinho Teste',
  categoryId: '3',
  description: 'Bom pra roda de samba',
  price: '899,90',
  stock: '3',
  status: 'active',
  specs: 'Cordas: aço',
}

describe('validate', () => {
  it('flags an empty name', () => {
    const { body, errors } = validate({ ...valid, name: '  ' })
    expect(body).toBeUndefined()
    expect(errors.name).toBe(copy.catalog.errors.name)
  })
  it('flags every bad field at once', () => {
    const { errors } = validate({ ...valid, categoryId: '', price: '0', stock: '-1', specs: 'x' })
    expect(Object.keys(errors).sort()).toEqual(['categoryId', 'price', 'specs', 'stock'])
  })
  it.each(['Violão\u0000', 'Vio\u200blão', 'Violão\u2066x', 'Violão\nx', 'Vio\u007flão'])(
    'flags a name with %j',
    (name) => expect(validate({ ...valid, name }).errors.name).toBe(copy.catalog.errors.name),
  )
  it('keeps line breaks and tabs in the description but not other controls', () => {
    expect(validate({ ...valid, description: 'Linha 1\nLinha 2\r\n\tfim' }).errors).toEqual({})
    expect(validate({ ...valid, description: 'bip\u0007' }).errors.description).toBe(copy.catalog.errors.description)
    expect(validate({ ...valid, description: 'oi\u200f' }).errors.description).toBe(copy.catalog.errors.description)
  })
  it('builds the body with the price as a decimal string', () => {
    const { body, errors } = validate(valid)
    expect(errors).toEqual({})
    expect(body).toEqual({
      name: 'Cavaquinho Teste',
      category_id: 3,
      description: 'Bom pra roda de samba',
      price: '899.90',
      stock: 3,
      status: 'active',
      specs: { Cordas: 'aço' },
    })
  })
})

describe('errorCopy', () => {
  it.each([
    [new HttpError(429, 'too_many_writes'), copy.catalog.tooMany],
    [new HttpError(409, 'catalog_full'), copy.catalog.full],
    [new HttpError(422, 'unknown_category'), copy.catalog.errors.categoryId],
    [new HttpError(404, 'not_found'), copy.catalog.notFound],
    [new HttpError(422, 'name_taken_by_store'), copy.catalog.nameTaken],
    [new HttpError(422, 'promo_claim'), copy.catalog.promoClaim],
    [new HttpError(422, [{ type: 'string_pattern_mismatch', loc: ['body', 'name'] }]), copy.catalog.invalid],
    [new HttpError(422), copy.catalog.invalid],
    [new HttpError(503, 'catalog_unavailable'), copy.catalog.unavailable],
    [new SessionExpired(), copy.login.expired],
    [new HttpError(500), copy.catalog.failed],
    [new TypeError('Failed to fetch'), copy.catalog.failed],
  ])('maps %s', (err, want) => expect(errorCopy(err)).toBe(want))
})

describe('rejection copy', () => {
  it('has no trailing period', () => {
    for (const text of [copy.catalog.nameTaken, copy.catalog.promoClaim]) expect(text).toMatch(/[^.]$/)
  })
})

describe('mergeById', () => {
  const row = (id: number, name = `P${id}`) => ({ id, name })
  it('keeps the rows already on screen and adds only new server rows after them', () => {
    const local = [row(3, 'just saved'), row(1, 'edited')]
    expect(mergeById(local, [row(2), row(1, 'stale')])).toEqual([row(3, 'just saved'), row(1, 'edited'), row(2)])
  })
  it('takes the server list when nothing is on screen', () => expect(mergeById([], [row(2), row(1)])).toEqual([row(2), row(1)]))
})

describe('appendQuestion', () => {
  it('fills an empty composer', () => expect(appendQuestion('  ', 'Vocês têm?')).toBe('Vocês têm?'))
  it('keeps a draft and adds the question on a new line', () =>
    expect(appendQuestion('Oi, tudo bem?', 'Vocês têm?')).toBe('Oi, tudo bem?\nVocês têm?'))
})
