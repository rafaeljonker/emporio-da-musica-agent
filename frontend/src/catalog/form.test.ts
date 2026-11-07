import { describe, expect, it } from 'vitest'
import { HttpError } from '@/api/client'
import { copy } from '@/copy'
import { errorCopy, parseSpecs, toPrice, validate, type ProductFields } from './form'

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
    [new HttpError(500), copy.catalog.failed],
    [new TypeError('Failed to fetch'), copy.catalog.failed],
  ])('maps %s', (err, want) => expect(errorCopy(err)).toBe(want))
})
