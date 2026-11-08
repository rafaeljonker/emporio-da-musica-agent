import { describe, expect, it } from 'vitest'
import type { ApiError, ApiErrorCode } from '@/client/shared/lib/api'
import { copy } from '@/client/shared/lib/copy'
import { errorMessage, fieldFor, type ErrorContext } from '@/client/shared/lib/errorMessage'

const e = (code: ApiErrorCode, status: number | null): ApiError => ({ code, status })
const c = copy.catalog

describe('errorMessage', () => {
  it.each<[string, ApiError, ErrorContext, string]>([
    ['invalid_credentials on login reads invalid', e('invalid_credentials', 401), 'login', copy.login.invalid],
    ['too_many_attempts on login reads network copy', e('too_many_attempts', 429), 'login', copy.login.network],
    ['network on login reads network copy', e('network', null), 'login', copy.login.network],
    ['5xx on login reads network copy', e('unknown', 500), 'login', copy.login.network],
    ['catalog_unavailable on load reads unavailable', e('catalog_unavailable', 503), 'catalogLoad', c.unavailable],
    ['status 503 without code reads unavailable', e('unknown', 503), 'catalogLoad', c.unavailable],
    ['network on load reads loadFailed', e('network', null), 'catalogLoad', c.loadFailed],
    ['500 on load reads loadFailed', e('unknown', 500), 'catalogLoad', c.loadFailed],
    ['too_many_writes on save reads tooMany', e('too_many_writes', 429), 'catalogSave', c.tooMany],
    ['catalog_full on save reads full', e('catalog_full', 409), 'catalogSave', c.full],
    ['unknown_category on save reads the category error', e('unknown_category', 422), 'catalogSave', c.errors.categoryId],
    ['not_found on save reads notFound', e('not_found', 404), 'catalogSave', c.notFound],
    ['name_taken_by_store on save reads nameTaken', e('name_taken_by_store', 422), 'catalogSave', c.nameTaken],
    ['promo_claim on save reads promoClaim', e('promo_claim', 422), 'catalogSave', c.promoClaim],
    ['invalid_fields on save reads invalid', e('invalid_fields', 422), 'catalogSave', c.invalid],
    ['422 without code on save reads invalid', e('unknown', 422), 'catalogSave', c.invalid],
    ['catalog_unavailable on save reads unavailable', e('catalog_unavailable', 503), 'catalogSave', c.unavailable],
    ['status 503 without code on save reads unavailable', e('unknown', 503), 'catalogSave', c.unavailable],
    ['unauthenticated on save reads expired', e('unauthenticated', 401), 'catalogSave', copy.login.expired],
    ['500 on save reads failed', e('unknown', 500), 'catalogSave', c.failed],
    ['json_required on save reads failed', e('json_required', 415), 'catalogSave', c.failed],
    ['network on save reads failed', e('network', null), 'catalogSave', c.failed],
  ])('%s', (_, error, context, want) => expect(errorMessage(error, context)).toBe(want))

  it('fieldFor names the field a save code belongs to', () => {
    expect(fieldFor('unknown_category')).toBe('categoryId')
    expect(fieldFor('name_taken_by_store')).toBe('name')
    expect(fieldFor('promo_claim')).toBeNull()
  })
})
