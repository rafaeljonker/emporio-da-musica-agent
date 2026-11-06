// Mirrors the backend contracts (emporio.api: auth, identity, chat; warm arrives in Task 6).

export type WarmMode = 'modal_gpu' | 'local_cpu' | 'provider_api'
export type WarmStage = 'server_starting' | 'model_loading' | 'ready' | 'failed'

export interface WarmStatus {
  mode: WarmMode
  stage: WarmStage
  started_at: string
  elapsed_seconds: number
  expected_seconds: number
  reply_p50_seconds: number | null
}

export interface WarmExpected {
  mode: WarmMode
  expected_seconds: number
}

export interface Me {
  customer_id: number | null
  warm: WarmStatus
}

export interface DemoCustomer {
  id: number
  name: string
  city: string
}

export interface TurnMetricsView {
  input_tokens: number
  output_tokens: number
  ms_model: number
  ms_guard: number
  ms_llm: number
  ms_tools: number
  cost_brl: string | null
  cost_basis: string
  action: string
}

export type ChatEvent =
  | { type: 'typing' }
  | { type: 'bubble'; kind: 'text'; text: string; delay_ms: number }
  | ({ type: 'metrics' } & TurnMetricsView)
  | { type: 'done'; trace_id: string }
  | { type: 'error'; partial: boolean }
