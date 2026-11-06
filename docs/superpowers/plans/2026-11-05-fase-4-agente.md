# Phase 4: The agent (tools, graph, providers, voice, tracing, MCP, evals) — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a working customer-service agent that answers in the store's pt-BR voice. It is a LangGraph `guard → agent ⇄ tools` graph over the phase 2–3 use cases, with:
- ten identity-safe tools;
- four providers behind one flag+key rule;
- bubbles and an AI-tell detector;
- mandatory Langfuse tracing;
- per-turn metrics;
- a Postgres checkpointer;
- a CLI;
- a FastMCP server over the same tools;
- a 16-case eval runnable per provider.

**Architecture:**
- **Pure layers:**
  - `support/domain` holds bubbles, tells, channel identity, thread ids and scope.
  - `support/application` holds the `HandleMessage` use case and the `AgentRunner`/`MetricsStore` ports.
- **Infrastructure** (`support/infrastructure/`) holds everything with LangChain/LangGraph/Langfuse/FastMCP: serializers, tools, prompts, guard, graph, provider factory, tracing, metrics store, checkpointer and MCP server.
- **Composition roots** live at the top level: `emporio/config.py` (settings), `emporio/bootstrap.py` (`build_agent`) and `emporio/cli.py`.
- **Tool calls:** the agent calls the tool functions in-process. FastMCP exposes the same functions to external clients.

**Tech stack:**
- langgraph 1.2, langgraph-checkpoint-postgres 3.2, langchain 1.4 / langchain-core 1.7;
- langchain-openai, langchain-google-genai, langchain-anthropic;
- fastmcp 4.1, langfuse 5.2 (server v4), pydantic-settings 2.16, psycopg-pool 3.3;
- pytest markers `postgres` and `eval`.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` §5, §7.2–7.6, §7.12. **Research + owner decisions (binding):** `docs/research/fase-4.md`. Also read the carried items in `.superpowers/sdd/2026-11-05-fase-3-rag-politicas/progress.md` (R6) and `.superpowers/reviews/2026-11-05-pr-4/verdict.md` rows 10–11.

## Global Constraints
- **Branch and commits:** branch `feat/agent`. TDD pairs `test(<scope>): … (red)` then `feat(<scope>): …`, with scopes `support`, `catalog`, `policies`, `db`, `config`, `build`, `ci`, `evals`. Scaffolding and config go in their own `chore`/`build` commit, never in a red commit. Subject ≤ 72 chars, imperative. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `--no-verify`, never amend, never `# noqa`. Pyright ignores are allowed only for untyped third-party calls.
- **Gates:** `make check` green on every non-red commit, offline, with no keys, no DB and no Langfuse server. `make test-pg` for `postgres` tests; `make evals` for `eval` tests.
- **New runtime dependencies** (floors): `langgraph>=1.2.20`, `langgraph-checkpoint-postgres>=3.2.0`, `langchain>=1.4.9`, `langchain-core>=1.7.6`, `langchain-openai>=1.7.4`, `langchain-google-genai>=4.4.3`, `langchain-anthropic>=1.7.10`, `fastmcp>=4.1.6`, `langfuse>=5.2.0`, `pydantic-settings>=2.16.2`. Do not add: `langchain-mcp-adapters` (archived), `langchain.mcp` client use, `create_react_agent`.
- **Layering:**
  - LangChain, LangGraph, Langfuse, FastMCP and pydantic live only in `support/infrastructure/**` and the top-level composition roots. They join the domain/shared and application denylists.
  - `emporio.config`, `emporio.bootstrap` and `emporio.cli` join the "Only infrastructure may use technical modules" contract.
  - Ruling R1 (this plan): `emporio.support.infrastructure.agent.serializers` and `…agent.tools` may import `emporio.{catalog,orders,policies}.{application,domain}`, and nothing else in support may. Add `ignore_imports` for exactly those two modules on the "Support infrastructure never imports another context's …" contract.
- **Identity:**
  - `customer_id` never appears in any model-visible or MCP tool schema. It reaches tools via `ToolRuntime[TurnContext]`.
  - `thread_id` is derived server-side from the channel identity: `"{channel}:customer:{id}"` or `"{channel}:anon:{session}"`.
  - Unknown order and wrong identity return the same tool text.
- **Tool outputs:**
  - Lean JSON. Money is formatted with `Money.format_brl()`: `R$ 2.199` for whole values, `R$ 2.089,05` with cents.
  - Every product is paired with its `PriceQuote`. Order data uses an allowlist and never includes `notes`.
  - Dates are `isoformat()`. Policy hits are flattened to `{section, title, text}`, top 5.
  - Each tool maps `DomainError` to one short pt-BR line.
- **Voice** (`.design/branding/emporio-da-musica/strategy/voice-and-tone.md`):
  - 1–3 bubbles separated by a blank line, at most one question, in the last bubble;
  - no em/en dash as punctuation, no markdown, no banned phrases, at most one `!`, no emoji;
  - the agent is "assistente da Empório", never a human name.
- **Providers:**
  - No flag → Gemma 4 31B on vLLM (`VLLM_BASE_URL`, `VLLM_API_KEY`). `--provider gemini|openai|anthropic` requires `GEMINI_API_KEY`|`OPENAI_API_KEY`|`ANTHROPIC_API_KEY`.
  - A flag without its key gives a clear startup error. No silent switch.
  - Defaults are `google/gemma-4-31B-it`, `gemini-3.8-flash`, `gpt-6-luna` and `claude-haiku-5-5`, overridable by env. Temperature 0.3. Gemma thinking stays off.
- **Langfuse is mandatory:**
  - `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` are required.
  - `LANGFUSE_TRACING_ENABLED=false`, `OTEL_SDK_DISABLED=true` and `LANGFUSE_SAMPLE_RATE<1` are rejected.
  - `auth_check()` runs at boot. There is a fresh `CallbackHandler` per turn with a seeded `trace_id`.
  - `session_id = thread_id`; `user_id` is a pseudonym, `cust-<hmac-sha256(customer_id, LANGFUSE_SALT)[:10]>` or `anon`. E-mail, phone and CPF are masked at export.
  - Tests inject a recording fake. There is no runtime fallback.
- **Clocks:** return windows use `FixedClock(STORE_TODAY)` (default 2026-02-20). `store_now` uses `SystemClock`.
- **Secrets:** keys only in `.env` (git-ignored) and Modal secrets. `.env.example` lists names only. Never print or copy key values.

## Review Focus
1. **Customer switch in "conversar como…"** (same session, new customer). Expected: a new `thread_id`, and the previous customer's orders are never in the history the model reads. Test: Task 5 `test_thread_id_differs_per_customer` and Task 8 `test_new_customer_gets_fresh_thread`.
2. **Model tries to pass `customer_id`, or asks for another customer's order.** Expected: the schema has no such field; a foreign order gives the same text as an unknown one. Test: Task 4 `test_no_tool_schema_exposes_customer_id` and `test_foreign_order_looks_unknown`.
3. **A tool raises (DB down, invalid installments, identity mismatch).** Expected: one short tool message and the turn continues; no crash, no stack trace to the model. Test: Task 4 `test_domain_errors_become_tool_text` and Task 7 `test_tool_error_does_not_abort_turn`.
4. **The model answers with an em dash, markdown or four bubbles.** Expected: `split_bubbles` caps at 3 and `ai_tells` reports every tell. Test: Task 5 `test_split_caps_at_three_bubbles` and `test_tells_detects_each_rule`.
5. **Startup without Langfuse or with tracing disabled.** Expected: a clear error naming the variables. Test: Task 9 `test_missing_langfuse_vars_fail_startup` and `test_disabling_vars_are_rejected`.

---

### Task 1: settings, provider factory, contracts

**Files:**
- Create: `backend/src/emporio/config.py`, `backend/src/emporio/support/infrastructure/llm/factory.py`
- Modify: `backend/pyproject.toml` (dependencies, contracts per Global Constraints incl. R1), `.env.example`
- Test: `backend/tests/unit/test_config.py`, `backend/tests/unit/support/test_llm_factory.py`

**Interfaces:**
- `class Provider(StrEnum): GEMMA="gemma"; GEMINI="gemini"; OPENAI="openai"; ANTHROPIC="anthropic"`
- `Settings` (pydantic-settings, `.env`) has these fields:
  - `provider: Provider = GEMMA`;
  - per-provider `model` overrides;
  - keys and `vllm_base_url`;
  - `database_url: str | None`;
  - `store_today: date = 2026-02-20`;
  - Langfuse fields;
  - `usd_brl: Decimal`;
  - `prices: dict[str, tuple[Decimal, Decimal]]` (USD per MTok in/out; empty for Gemma).
- `load_settings(provider: Provider | None = None) -> Settings` validates the flag+key rule. It raises `ConfigError(DomainError)` with a message naming the missing variable and the alternative providers.
- `make_chat_model(settings: Settings) -> BaseChatModel` uses `init_chat_model`: vLLM through `model_provider="openai"` with `base_url`, Gemini `google_genai` with `thinking_level="minimal"`, OpenAI, Anthropic. It does no network calls at construction.

- [ ] **Step 1: `build(backend)` commit:** dependencies, contracts (R1 `ignore_imports`, new denylist entries, new top-level modules in the technical-modules contract once they exist), `.env.example` names (`LLM_PROVIDER`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGFUSE_*`, `LANGFUSE_SALT`, `STORE_TODAY`, `USD_BRL`). `make check` green.
- [ ] **Step 2: failing tests:**
  - `test_default_provider_is_gemma_and_needs_vllm_url`;
  - `test_flag_without_key_raises_naming_variable` (parametrized over the three cloud providers);
  - `test_store_today_defaults_to_2026_02_20`;
  - `test_factory_builds_each_provider_without_network` (monkeypatched env; assert the class name and model id).
- [ ] **Step 3:** red commit `test(config): settings and provider factory (red)`. Implement, `make check`, then `feat(config): add settings and provider factory`.

### Task 2: pooled read adapters, `IndexUnavailable`, shared embedder

**Files:**
- Modify: `backend/src/emporio/db.py`, `policies/infrastructure/pg_policy_index.py`, `catalog/infrastructure/pg_product_index.py`, `backend/src/emporio/ingest.py`, the related tests
- Test: `backend/tests/integration/test_pool.py` (`postgres`), the existing index tests

**Interfaces:**
- `emporio.db.make_pool(url: str | None = None, *, min_size=1, max_size=4) -> ConnectionPool` with `kwargs={"autocommit": True}`, `configure=register_vector_if_available`, `check=ConnectionPool.check_connection`.
- `class IndexUnavailable(DomainError)` in `emporio/db.py`.
- `PgPolicyIndex(pool, embedder, *, hybrid=True)` and `PgProductIndex(pool, embedder)`:
  - reads use `with pool.connection() as conn`, with no `transaction()` around a single SELECT;
  - `replace_all` keeps one `with conn.transaction()`;
  - `psycopg.OperationalError` and `psycopg_pool.PoolTimeout` become `IndexUnavailable`.
- `ingest.py` builds one pool and one `E5Embedder`.

- [ ] **Step 1: failing tests** (`postgres`):
  - `test_concurrent_searches_share_pool`: 8 threads run `search` and `similar` at once on the same index objects, with no error;
  - `test_unreachable_db_raises_index_unavailable`: a pool against `postgresql://emporio:x@127.0.0.1:1/emporio_test` with `timeout=1`.
  - Update the existing index tests to pass a pool.
- [ ] **Step 2:** red commit, implement, then `make check`, `make test-pg`, `make db` (`policies: 25, products: 65`). Commit `feat(db): share a pooled autocommit connection across indexes`.

### Task 3: serializers (voice-ready lean JSON)

**Files:**
- Create: `backend/src/emporio/support/infrastructure/agent/serializers.py`
- Test: `backend/tests/unit/support/test_serializers.py`

**Interfaces** (pure functions, return `dict[str, object]`):
- `product_json(product: Product, quote: PriceQuote, category: str) -> dict`: keys `id, name, category, available, status, stock, price{table, final, promo_percent, pix}`. Money is formatted; `promo_percent` is an int or None; `pix` is None when a promotion is active.
- `search_json(result: Exact | Candidates | NoMatch, quotes: Mapping[int, PriceQuote], categories: Mapping[int, str], *, limit=8) -> dict`: `{"match": "exact"|"candidates"|"none", "products": [...]}`.
- `order_json(order: Order, product_names: Mapping[int, str]) -> dict`: allowlist `id, order_date, status, total, payment_method, tracking_code, estimated_delivery, items[{name, quantity}]`. **No `notes`.**
- `eligibility_json(e: ReturnEligibility) -> dict`: all fields in isoformat. It adds `legal_warranty_note` only when `reason == "defect_window_closed"`, with the exact text: `"A garantia legal de 90 dias para produto durável (CDC art. 26, II) pode valer: ofereça encaminhar para a equipe."`
- `policy_hits_json(hits) -> list[dict]` gives `[{section, title, text}]`.
- `store_json(s: StoreStatus) -> dict` gives `{open, now, next_opening, next_opening_weekday}`, with the weekday in pt-BR (`"segunda-feira"`…).
- `installments_json(plan: InstallmentPlan) -> dict`.

- [ ] **Step 1: failing tests**, one per function, using the catalog/orders factories:
  - `test_order_json_never_contains_notes`, with an order that has notes;
  - `test_pix_absent_with_active_promotion`;
  - `test_legal_warranty_note_only_when_defect_window_closed`;
  - `test_store_json_weekday_ptbr`;
  - `test_money_is_voice_formatted` (`R$ 2.199`, `R$ 2.089,05`).
- [ ] **Step 2:** red commit, then `feat(support): add tool serializers`.

### Task 4: the ten tools

**Files:**
- Create: `backend/src/emporio/support/infrastructure/agent/context.py`, `…/agent/tools.py`
- Test: `backend/tests/unit/support/test_tools.py`, `backend/tests/contract/test_tool_schemas.py`

**Interfaces:**
- `TurnContext(customer_id: int | None)`, a frozen dataclass.
- `Toolbox`, a frozen dataclass holding the use cases: `SearchProducts, RecommendProducts, GetProduct, ListPromotions, QuoteInstallments, ListCustomerOrders, GetOrderStatus, CheckReturnEligibility, StoreNow, SearchPolicies`, plus `CatalogRepository` for names and categories.
- `build_tools(box: Toolbox) -> list[BaseTool]`. Tool names and model-visible arguments, with descriptions in pt-BR and ≤ 2 lines:
  - `search_products(query: str, max_price: Decimal | None)`. On `none`, retry with `include_unavailable=True` so discontinued products are reported with their status.
  - `recommend_products(need: str)`
  - `get_product(product_id: int)`
  - `list_active_promotions()`
  - `calc_installments(total: Decimal, count: int | None)`
  - `list_my_orders()`, identified customers only. Anonymous gives the text "Peça o número do pedido e o e-mail ou telefone do cadastro."
  - `get_order_status(order_id: int, email_or_phone: str | None)`. Identified: an ownership check through the customer's orders. Anonymous: `email_or_phone` is required.
  - `check_return_eligibility(order_id: int, email_or_phone: str | None)`. Anonymous: verify via `GetOrderStatus`, then pass the order's own `customer_id`.
  - `store_now()`
  - `search_policies(question: str)`
- Each tool takes `runtime: ToolRuntime[TurnContext]`, which stays out of the schema.
- **Error texts** (exact):
  - `IdentityMismatch` / `OrderNotFound`: `"Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; peça para conferir o número e o e-mail ou telefone."`
  - `InvalidInstallments`: `"Esse parcelamento não é permitido para esse valor."` plus the allowed maximum.
  - `IndexUnavailable`: `"Busca indisponível agora; ofereça encaminhar para a equipe."`
  - `ProductNotFound`: `"Produto não encontrado."`

- [ ] **Step 1: failing tests** over in-memory repos (existing fakes) and `HashEmbedder`-free fake indexes:
  - `test_no_tool_schema_exposes_customer_id`: walk every `tool.tool_call_schema.model_json_schema()`;
  - `test_tool_schema_snapshot`: compare names and arguments against a committed JSON snapshot;
  - `test_foreign_order_looks_unknown`: identified customer 3 asks for order 5 and gets the same text as for order 999;
  - `test_anonymous_order_needs_identity`;
  - `test_domain_errors_become_tool_text` (parametrized over the four errors);
  - `test_search_reports_discontinued_product`;
  - `test_list_my_orders_newest_first`.
- [ ] **Step 2:** red commit, then `feat(support): add identity-safe agent tools`.

### Task 5: support domain (bubbles, tells, identity, scope)

**Files:**
- Create: `support/domain/bubbles.py`, `ai_tells.py`, `channel_identity.py`, `scope.py`
- Test: `backend/tests/unit/support/test_bubbles.py`, `test_ai_tells.py`, `test_channel_identity.py`

**Interfaces:**
- `split_bubbles(text: str) -> tuple[str, ...]`: split on blank lines, strip, drop empties. More than 3 parts are merged into the third.
- `class Tell(StrEnum)`: `EM_DASH, MARKDOWN, BANNED_PHRASE, TEXTSPEAK, EMOJI, EXCLAMATIONS, MULTIPLE_QUESTIONS, QUESTION_NOT_LAST, TOO_MANY_BUBBLES, LONG_BUBBLE`.
- `ai_tells(text: str) -> tuple[Tell, ...]`. Banned phrases are exactly the voice guide's list. `LONG_BUBBLE` triggers above 280 chars.
- `ChannelIdentity(channel: str, customer_id: int | None, session: str)` with `thread_id() -> str`.
- `class Scope(StrEnum): LOJA="loja"; ACESSORIO="acessorio"; FORA_DE_ESCOPO="fora_de_escopo"; ABUSO="abuso"`.

- [ ] **Step 1: failing tests:**
  - `test_split_caps_at_three_bubbles`;
  - `test_tells_detects_each_rule` (one parametrized case per `Tell`);
  - `test_clean_reply_has_no_tells`, using voice guide example 1;
  - `test_thread_id_differs_per_customer`;
  - `test_anonymous_thread_uses_session`.
- [ ] **Step 2:** red commit, then `feat(support): add bubbles, AI-tell detector and channel identity`.

### Task 6: prompts

**Files:**
- Create: `support/infrastructure/agent/prompts/persona.md`, `voice.md`, `tools.md`, `guard.md`, and `…/agent/prompt.py`
- Test: `backend/tests/unit/support/test_prompt.py`

**Interfaces:**
- `system_prompt(customer_name: str | None, today: date) -> str` returns one string: the static files concatenated, then a dynamic suffix (`Cliente: <nome>` or `Cliente: não identificado`, and `Hoje: <dd/mm/aaaa>`).
- `guard_prompt() -> str`.
- **Prompt content** (pt-BR):
  - Persona "assistente da Empório", with no human name. When asked "você é robô?", answer honestly and offer a person.
  - The voice guide's attributes and style rules, plus 3 of its examples.
  - The tool rules from the spike's prompt v2 (research §5): always use tools for price, stock, deadlines and orders; identified customer → `list_my_orders`; a promotion always shows original + % + final; read all 5 policy hits.
  - The carried rules: hedge Black Friday, the anniversary and Christmas hours; quote `contato@emporiodamusica.com.br` and WhatsApp (67) 3341-4444; installments always via `calc_installments`; after the defect window, mention the legal warranty and offer a person; accessories are politely declined with a partner-store hint.
  - The static part comes first.

- [ ] **Step 1: failing tests:**
  - `test_prompt_has_no_human_agent_name` (no "Duda");
  - `test_dynamic_suffix_last`;
  - `test_prompt_files_free_of_ai_tells`: run `ai_tells` over the example replies in `voice.md`;
  - `test_prompt_mentions_cover_email_and_whatsapp`.
- [ ] **Step 2:** red commit, then `feat(support): add pt-BR agent and guard prompts`.

### Task 7: the graph

**Files:**
- Create: `support/infrastructure/agent/graph.py`, `…/agent/guard.py`
- Test: `backend/tests/unit/support/test_graph.py`, `backend/tests/fakes/fake_chat_model.py`

**Interfaces:**
- `AgentState(MessagesState)` plus `scope: Scope | None`.
- `make_classifier(model: BaseChatModel) -> Callable[[Sequence[BaseMessage]], Scope]`: `with_structured_output` over `{label}`, fed the last user message and the previous assistant message.
- `build_graph(model: BaseChatModel, tools: Sequence[BaseTool], classify: Callable[..., Scope], checkpointer: BaseCheckpointSaver, *, max_history_tokens: int = 3000) -> CompiledStateGraph`. Nodes and routing:
  - `guard` sets the scope.
  - `loja` → `agent` with tools bound.
  - `acessorio` / `fora_de_escopo` → `agent` without tools, plus a one-line scope instruction.
  - `abuso` → `abuse_reply`, a fixed text: `"Vamos manter a conversa respeitosa. Posso te ajudar com instrumentos, pedidos ou dúvidas da loja."`
  - `agent` ⇄ `ToolNode(tools)` via `tools_condition`.
  - Trimming uses `trim_messages(strategy="last", start_on="human", end_on=("human", "tool"))` on a copy.
- Test fake: `FakeToolCallingModel(GenericFakeChatModel)` with `bind_tools` returning self.

- [ ] **Step 1: failing tests** (with `InMemorySaver` and a lambda classifier):
  - `test_store_question_calls_tool_then_answers`;
  - `test_accessory_skips_tools`;
  - `test_abuse_returns_fixed_reply_without_model_call`;
  - `test_context_customer_reaches_tool`;
  - `test_tool_error_does_not_abort_turn`;
  - `test_history_trimmed_without_orphan_tool_messages`.
- [ ] **Step 2:** red commit, then `feat(support): add guard and agent graph`.

### Task 8: handle_message, checkpointer, metrics store

**Files:**
- Create:
  - `support/application/ports.py`, `support/application/handle_message.py`;
  - `support/infrastructure/metrics_store.py`, `support/infrastructure/checkpointer.py`;
  - `support/infrastructure/agent/runner.py`;
  - `backend/migrations/004_turn_metrics.sql`.
- Modify: `emporio/migrate.py` (`PostgresSaver.setup()` after the SQL files, on its own autocommit `dict_row` connection)
- Test: `backend/tests/unit/support/test_handle_message.py`, `backend/tests/integration/test_metrics_store.py` (`postgres`), `backend/tests/integration/test_checkpointer.py` (`postgres`)

**Interfaces:**
- `Reply(bubbles: tuple[str, ...], scope: Scope, trace_id: str, tells: tuple[Tell, ...])`.
- `TurnMetrics(thread_id, provider, model, scope, input_tokens, output_tokens, cached_tokens, llm_calls, tools: tuple[str, ...], ms_total, ms_guard, ms_llm, ms_tools, cost_brl: Decimal | None, trace_id)`.
- `AgentRunner` Protocol: `run(identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]`.
- `MetricsStore` Protocol: `save(m: TurnMetrics) -> None`.
- `HandleMessage(runner, metrics)`, with `__call__(identity, text) -> Reply`. Blank text gets the voice guide's chat-error copy without calling the runner. It computes tells, saves the metrics and returns a `Reply`.
- The `turn_metrics` table follows research §9 exactly.
- `GraphRunner(graph, settings, tracer_factory)` implements `AgentRunner`:
  - tokens summed from the turn's new `AIMessage.usage_metadata`;
  - timings from node wrappers and `ToolNode(wrap_tool_call=...)`;
  - cost from `settings.prices`, None for Gemma.
- `make_checkpointer(url) -> PostgresSaver` on its own small pool (`dict_row`, `prepare_threshold=0`).

- [ ] **Step 1: failing tests:**
  - unit `test_handle_message_returns_bubbles_and_saves_metrics` (fake runner and store);
  - `test_blank_message_short_circuits`;
  - `test_new_customer_gets_fresh_thread` (graph with `InMemorySaver`: customer 14 then customer 3, same session; the second turn's state holds no message from the first);
  - `postgres` tests `test_metrics_row_roundtrip` and `test_checkpointer_persists_thread`.
- [ ] **Step 2:** red commit, then `feat(support): add handle_message, turn metrics and Postgres checkpointer`.

### Task 9: mandatory Langfuse

**Files:**
- Create: `support/infrastructure/tracing.py`, `backend/tests/fakes/recording_tracer.py`, `docker-compose.yml` profile `observability`, Makefile `langfuse-keys`/`langfuse-up`
- Modify: `emporio/config.py`
- Test: `backend/tests/unit/test_config.py` (extend), `backend/tests/unit/support/test_tracing.py`

**Interfaces:**
- Settings validation per Global Constraints. It raises `ConfigError`, and the message names the missing or rejecting variables plus `make langfuse-up`.
- `TracerFactory` Protocol: `for_turn(identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]` (the callbacks and the `trace_id`).
- `LangfuseTracerFactory(client: Langfuse, salt: str)` implements it:
  - `trace_id = Langfuse.create_trace_id(seed=uuid4().hex)`;
  - `CallbackHandler(trace_context={"trace_id": ...})`;
  - `propagate_attributes(session_id=thread_id, user_id=pseudonym)`.
- `make_langfuse(settings) -> Langfuse` registers `mask_otel_spans`, which redacts e-mail, phone and CPF regexes, and calls `auth_check()`; failure raises `ConfigError`.
- `shutdown_tracing()`.
- **Compose profile `observability`:**
  - `langfuse-web` and `langfuse-worker` on tag `4`, ClickHouse, Redis and MinIO, following the upstream compose;
  - Postgres is our `db` service with a separate `langfuse` database created idempotently;
  - ports are bound to `127.0.0.1`.
- `make langfuse-keys` writes `SALT`, `ENCRYPTION_KEY` (64 hex), `NEXTAUTH_SECRET`, `LANGFUSE_INIT_*`, `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY`/`BASE_URL=http://localhost:3000` and `LANGFUSE_SALT` into `.env`, **only if absent**, with `openssl rand`. It never prints the values.
- `make langfuse-up` runs `langfuse-keys` plus `docker compose --profile observability up -d --wait`.

- [ ] **Step 1: failing tests:**
  - `test_missing_langfuse_vars_fail_startup`;
  - `test_disabling_vars_are_rejected` (parametrized over the three variables);
  - `test_pseudonym_is_stable_and_not_the_id`;
  - `test_mask_redacts_email_phone_cpf`;
  - `test_fake_tracer_records_one_trace_per_turn` (the graph from Task 7 plus `GraphRunner` with the recording fake).
- [ ] **Step 2:** red commit, then implement. Run `make langfuse-up` locally once and confirm `auth_check()` passes against it; note the RAM used (`docker stats --no-stream`) in the report. Commit `feat(support): make Langfuse tracing mandatory`.

### Task 10: composition root and CLI

**Files:**
- Create: `backend/src/emporio/bootstrap.py`, `backend/src/emporio/cli.py`; `[project.scripts] emporio = "emporio.cli:main"`; Makefile `chat`
- Test: `backend/tests/unit/test_cli.py`

**Interfaces:**
- `build_agent(settings: Settings) -> HandleMessage`. It is the only place that builds, in this order:
  - the pool;
  - `E5Embedder`;
  - the repos and use cases;
  - `Toolbox` and the tools;
  - the model and classifier;
  - the checkpointer;
  - the Langfuse client and tracer factory;
  - `GraphRunner` and `PgMetricsStore`.

  `FixedClock(settings.store_today)` goes to orders and `SystemClock()` to `StoreNow`.
- `emporio chat [--as-customer ID] [--provider P]`: a REPL that prints each bubble on its own line with a short pause (`delay_ms` per bubble ≈ 400 + 15 ms/char, capped at 1500), shows the scope and the trace id in dim text, and calls `shutdown_tracing()` on exit. Startup errors print the `ConfigError` message and exit 2.
- `make chat` runs `make db langfuse-up` and then `emporio chat`.

- [ ] **Step 1: failing tests:**
  - `test_cli_prints_config_error_and_exits_2` (no env);
  - `test_cli_prints_bubbles_in_order`, with `build_agent` monkeypatched to a fake `HandleMessage`.
- [ ] **Step 2:** red commit, then `feat(support): add composition root and chat CLI`.
- [ ] **Step 3: manual smoke** (needs the owner's `.env` with `VLLM_*`, or `--provider gemini` with a key — ask the owner; never copy keys). Run `make chat` and three turns: a price question, "tá aberto?", and an order as customer 14. Paste the transcript and the Langfuse trace ids into the report.

### Task 11: MCP server

**Files:**
- Create: `support/infrastructure/mcp/server.py`; Makefile `mcp`
- Test: `backend/tests/contract/test_mcp_contract.py`

**Interfaces:**
- `build_mcp(box: Toolbox, *, customer_id: int | None) -> FastMCP`. It registers the same ten functions from `tools.py`; the shared implementation lives in plain functions that both layers call. Identity comes from a `Depends()` provider that is excluded from the schema: on stdio, the `EMPORIO_MCP_CUSTOMER_ID` env var read at launch; on HTTP, a token claim (documented, not exercised).
- `FastMCP(mask_error_details=True)`. Domain errors use the same texts as Task 4, raised as `ToolError`.
- `make mcp` runs `emporio mcp` over stdio.

- [ ] **Step 1: failing tests:**
  - `test_mcp_schemas_equal_agent_schemas`, with an in-memory `fastmcp.Client(server)` and `list_tools()` compared against Task 4's model-visible schemas;
  - `test_mcp_call_returns_same_json` (`store_now` and `search_products`);
  - `test_mcp_schema_has_no_customer_id`.
- [ ] **Step 2:** red commit, then `feat(support): expose the agent tools over MCP`.

### Task 12: agent evals

**Files:**
- Create: `backend/evals/agent_cases.toml`, `backend/tests/eval/test_agent_evals.py`, `backend/evals/verify.py`, `backend/evals/reports/.gitkeep`
- Modify: Makefile `evals` (`PROVIDER ?= gemma`; runs `-m eval` with `LLM_PROVIDER=$(PROVIDER)`), `.gitignore` (reports are committed only for the README run)

**Interfaces:**
- Each case has `name, message, customer_id?, expect_tools (list), all_of, any_of, none_of, ask (bool)`.
- 16 cases, per research §7: the spike's 14, plus ambiguous "Takamine" (expects a question and no price), plus order 5 out of window (expects `defect_window_closed` handling with the legal warranty mention), plus `recommend_products` ("algo pra tocar MPB em casa").
- `verify.py`: paraphrase-tolerant matching. Normalize accents, case, `R$`, dots and `,00`; ship synonym groups (`9x|9 parcelas|nove vezes`, `descontinu|saiu de linha|não está mais disponível|não faz mais parte`). Expected facts are computed from the use cases at test time, never hard-coded prices.
- The eval runs every case through `build_agent(settings)` (real model and Langfuse), on the `emporio_test` DB after ingest. It writes `backend/evals/reports/<provider>.md` with per-case pass/fail, tools, tells, latency p50/p95, tokens, R$ per conversation, the trace id, and full transcripts of failures. Gate: ≥ 0.90 pass and 0 tells.

- [ ] **Step 1:** commit `test(evals): agent golden cases (red)`. It is red because `build_agent` exists, but the cases have not yet been run against a real model.
- [ ] **Step 2:** run `make evals PROVIDER=<what the owner's .env supports>` (ask the owner which provider keys are available; never copy keys). If the gate fails, report the failing transcripts and **do not** edit cases to pass. Prompt fixes are allowed only for real behavior gaps, as separate `fix(support): …` commits, and each one is listed.
- [ ] **Step 3:** commit the report for the provider that was run. `docs(evals): first agent eval report`.

### Task 13: spec sync, PR and review
- [ ] **Step 1:** `docs(spec): record phase 4 decisions`. Update:
  - §5: the factory, model defaults, mandatory Langfuse;
  - §7.3: ten tools incl. `list_my_orders`, the thread_id rule, the guard routes, the abuse reply;
  - §7.7: the tree (`config.py`, `bootstrap.py`, `cli.py`, `support/**`, `mcp/`, `migrations/004`);
  - §7.12: MCP in-process plus FastMCP.

  Update AGENTS.md commands (`make chat`, `make langfuse-up`, `make mcp`, `make evals PROVIDER=`) and gotchas (Langfuse mandatory, about 2–4 GB RAM for the observability profile).
- [ ] **Step 2:** `git push -u origin feat/agent`, `gh pr create` with an English body ending in `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** run the `reviewing-changes` skill on the PR and apply the FIX-NOW items.
- [ ] **Step 4:** checkpoint with the owner before merging, with the eval table, a CLI transcript and one Langfuse trace screenshot path.
