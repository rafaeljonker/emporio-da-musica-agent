// Test data builders; override any field.
import type { ChatEvent, Product, WarmStatus } from '@/client/shared/lib/apiTypes'

export const warm = (over: Partial<WarmStatus> = {}): WarmStatus => ({
  mode: 'modal_gpu',
  stage: 'server_starting',
  started_at: '2026-11-07T12:00:00Z',
  elapsed_seconds: 0,
  expected_seconds: 26,
  reply_p50_seconds: null,
  ...over,
})

export const product = (over: Partial<Product> = {}): Product => ({
  id: 1,
  name: 'Cavaquinho Teste',
  category_id: 3,
  category: 'Cordas',
  description: 'Bom pra roda de samba',
  price: '899.90',
  stock: 3,
  status: 'active',
  specs: { Cordas: 'aço' },
  ...over,
})

/** A complete turn: typing, one bubble per text, metrics, done. */
export const chatEvents = (...texts: string[]): ChatEvent[] => [
  { type: 'typing' },
  ...texts.map((text): ChatEvent => ({ type: 'bubble', kind: 'text', text, delay_ms: 0 })),
  {
    type: 'metrics',
    input_tokens: 10,
    output_tokens: 5,
    ms_model: 100,
    ms_guard: 1,
    ms_llm: 90,
    ms_tools: 0,
    cost_brl: null,
    cost_basis: 'fake',
    action: 'answer',
  },
  { type: 'done', trace_id: 't1' },
]
