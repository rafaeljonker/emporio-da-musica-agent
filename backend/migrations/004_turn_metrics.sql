CREATE TABLE turn_metrics (
    id bigserial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),
    thread_id text NOT NULL, provider text NOT NULL, model text NOT NULL, scope text NOT NULL,
    input_tokens int NOT NULL, output_tokens int NOT NULL, cached_tokens int NOT NULL DEFAULT 0,
    llm_calls smallint NOT NULL, tools text[] NOT NULL DEFAULT '{}',
    ms_total int NOT NULL, ms_guard int NOT NULL, ms_llm int NOT NULL, ms_tools int NOT NULL,
    cost_brl numeric(10,6), trace_id text);
CREATE INDEX turn_metrics_thread_idx ON turn_metrics (thread_id, created_at);
