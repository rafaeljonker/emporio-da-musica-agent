# Phase 4 research: agent, tools, providers, MCP, voice, evals

Date: 2026-11-05. PyPI versions fetched 2026-11-05 from `https://pypi.org/pypi/<name>/json`. Library internals were checked against source on GitHub `main`/`master` that day. Anything not verified is marked "unconfirmed". Local facts cite repo paths. The spike lives in the session scratchpad (`spike/bench.py`, `relatorio.md`, `relatorio_v2.md`, `modal/gemma_emporio.py`); it was still present and was read in full.

| Package | Version | Note |
|---|---|---|
| langgraph | 1.2.20 | `StateGraph`, `ToolNode`, `tools_condition` |
| langgraph-prebuilt | 1.1.1 | `create_react_agent` deprecated (`LangGraphDeprecatedSinceV10`), moved to `langchain.agents.create_agent` |
| langgraph-checkpoint-postgres | 3.2.0 | `PostgresSaver` |
| langchain / langchain-core | 1.4.9 / 1.7.6 | `init_chat_model`, `langchain.mcp` (beta) |
| langchain-openai / -google-genai / -anthropic | 1.7.4 / 4.4.3 / 1.7.10 | provider adapters |
| langchain-mcp-adapters | 0.3.2 (2026-08-06) | GitHub repo says archived; replaced by `langchain[mcp]>=1.4.0` |
| fastmcp / mcp | 4.1.6 / 2.3.0 | MCP server |
| langfuse | 5.2.0 | SDK v5, needs Langfuse server v4 (latest v4.76.0); mandatory tracing |
| vllm | 0.33.0 | Modal image uses `vllm/vllm-openai:latest` (version not pinned) |
| pydantic / pydantic-settings | 2.14.3 / 2.16.2 | tool schemas, config |

## 1. LangGraph: graph, memory, sync tools, layering
- `create_react_agent` is deprecated: "create_react_agent has been moved to `langchain.agents`. Please update your import to `from langchain.agents import create_agent`" (`libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py`). `create_agent` takes `model, tools, system_prompt, response_format, middleware, checkpointer, context_schema` (https://docs.langchain.com/oss/python/langchain/agents).
- For our shape (spec §7.3: `guard → agent ⇄ tools`), an explicit `StateGraph(MessagesState + scope, context_schema=TurnContext)` with three nodes is about 40 lines and reads exactly like the README diagram. `ToolNode` and `tools_condition` are still the supported building blocks. `create_agent` would hide the guard inside a middleware (`before_agent` with a jump), which is harder to show and test.
- **Sync tool execution:** `ToolNode._func` runs the calls of one AI message through `get_executor_for_config(config)` and `executor.map(...)` (`tool_node.py` line 829). That is a thread pool sized by `config["max_concurrency"]`. So two tool calls in one turn hit our Postgres adapters from two threads at once. A single shared `psycopg.Connection` with `with conn.transaction()` (current `PgPolicyIndex`, `PgProductIndex`) is not safe for that. This is why R6 asks for a pool.
- **Tool errors:** the default `_default_handle_tool_errors` turns only `ToolInvocationError` (bad arguments) into a message and re-raises anything else (`tool_node.py` line 391). A `DomainError` escaping a tool would abort the turn, so tools must map errors themselves (section 4).
- **Memory:** `PostgresSaver` from `langgraph.checkpoint.postgres`, `checkpointer.setup()` once, `config={"configurable": {"thread_id": ...}}` (https://docs.langchain.com/oss/python/langgraph/add-memory). Connections need `autocommit=True, prepare_threshold=0, row_factory=dict_row` (phase 3 research §5). `dict_row` breaks our adapters, which index rows by position (`r[0]`), so the checkpointer gets **its own** small pool. `setup()` goes into `make migrate` (phase 3 ruling).
- **Trimming:** `trim_messages(messages, strategy="last", token_counter=count_tokens_approximately, max_tokens=N, start_on="human", end_on=("human","tool"))` on a copy inside the agent node; state keeps the full history (same docs page). `start_on="human"` prevents orphan `ToolMessage`s.
- **thread_id is a security boundary:** it must be derived server-side from the channel identity (`web:customer:14`, `cli:anon:<uuid>`). If the web "conversar como…" selector switches customer without a new thread, the old customer's order data stays in the history the model reads.
- **Sync vs async:** the whole stack is sync (psycopg adapters, use cases). FastAPI's `StreamingResponse` iterates a sync generator in a threadpool, so `graph.stream(..., stream_mode="messages")` works in phase 5 without `AsyncPostgresSaver`.
- **Layering:** LangGraph, LangChain and pydantic stay in `support/infrastructure/agent/`. `support/application/handle_message.py` depends on a small `AgentRunner` Protocol (`reply(identity, text) -> Reply`), already allowed by the "Application stays framework-free" contract (`backend/pyproject.toml`).
- **Contract blocker:** "Support infrastructure never imports another context's domain or application" (`backend/pyproject.toml`) forbids `support/infrastructure/agent/tools.py` from calling `catalog.application` etc. The tool layer is an anti-corruption layer by design (spec §7.2), so it needs an exemption: either `ignore_imports` for `emporio.support.infrastructure.agent.tools` (wildcard syntax per import-linter docs, unconfirmed for this version) or move the wiring into a composition-root module like `emporio.ingest`.

**Recommendation:** explicit 3-node `StateGraph` + `ToolNode`, sync everywhere, `PostgresSaver` on its own pool, `thread_id` from channel identity, and a narrow contract exemption for the tools module.

## 2. LLM providers via `init_chat_model`
- One call covers all four: `init_chat_model(model, model_provider=..., **kwargs)`; OpenAI-compatible servers use `model_provider="openai", base_url=..., api_key=...` (https://docs.langchain.com/oss/python/langchain/models).
- **Gemma 4 31B on vLLM:** `init_chat_model("google/gemma-4-31B-it", model_provider="openai", base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, temperature=0.3)`. The Modal app serves `--enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4` with `tool_chat_template_gemma4.jinja` (`spike/modal/gemma_emporio.py`).
  - Parser name `gemma4` confirmed (https://docs.vllm.ai/en/latest/api/vllm/tool_parsers/gemma4_tool_parser/). Gemma's call format is not JSON (unquoted keys, a special quote token), and multiple calls are concatenated without separators. The parser handles several calls in one message, but end-to-end parallel-call behaviour is **unconfirmed**. vLLM issue #39468 (0.19.0) reported raw tool tokens left in `content` with both gemma4 parsers on (https://github.com/vllm-project/vllm/issues/39468); the spike on Modal saw 14/14, so it is fixed or not hit.
  - Thinking is **off by default** for Gemma 4 unless `chat_template_kwargs={"enable_thinking": True}` (https://docs.vllm.ai/en/latest/features/reasoning_outputs/). Good for latency; keep it off.
  - `tool_choice="required"`/named and JSON-schema output use guided decoding ("guaranteed to parse, not a high-quality one"; first named call compiles a grammar, several seconds) (https://docs.vllm.ai/en/latest/features/tool_calling.html).
  - For token usage while streaming, set `stream_usage=True` on `ChatOpenAI` (vLLM honours `stream_options.include_usage`; unconfirmed on our image).
- **Gemini:** `langchain-google-genai` 4.4.3, `model_provider="google_genai"`. It reads `GOOGLE_API_KEY` first, then `GEMINI_API_KEY` (https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai), which matches spec §5. Use `thinking_level="minimal"` on Gemini 3+. Model ids (https://aistudio.google.com/docs/models): `gemini-3.8-flash` (newest Flash, badged "New", spike winner 14/14), `gemini-3.6-flash` (newest "Stable"), alias `gemini-flash-latest`.
- **OpenAI:** `langchain-openai` 1.7.4. The current lineup has no "mini" model (https://developers.openai.com/api/docs/models): `gpt-6-luna` ($0.10/$0.50 per MTok, cheapest), `gpt-6.1-terra` ($1/$5, supports reasoning `none`), flagship `gpt-6-astra`. Neither was in the spike.
- **Anthropic:** `langchain-anthropic` 1.7.10. `claude-haiku-5-5` (fastest, "from $0.10 / $0.50" per MTok, adaptive thinking, default effort `medium`) and `claude-sonnet-5-5` ($2/$10) (https://platform.claude.com/docs/en/about-claude/models/overview). Pass `effort="low"` or disable thinking if `capabilities.thinking.types.disabled` allows; the `langchain-anthropic` kwarg name is unconfirmed.
- **Usage metadata** (all four): `AIMessage.usage_metadata = {input_tokens, output_tokens, total_tokens, input_token_details: {cache_read, cache_creation}, output_token_details: {reasoning}}` (models page). This is the only source we need for cost (section 9).
- **Structured output:** `model.with_structured_output(Schema, method="json_schema" | "function_calling" | "json_mode", include_raw=...)`. Gemini defaults to `json_schema` (native). vLLM accepts `response_format` json_schema with the gemma4 reasoning parser (reasoning docs above).
- **The port:** `BaseChatModel` already is the provider port. Four adapter classes would each be one `init_chat_model` call. One `make_chat_model(settings) -> BaseChatModel` with a defaults table, plus the flag+key check (spec §5: no flag → Gemma; flag without key → clear startup error; no silent switch), is the honest size.

**Recommendation:** a single factory over `init_chat_model` with per-provider default ids in settings: Gemma 4 31B (vLLM), `gemini-3.8-flash`, `gpt-6-luna`, `claude-haiku-5-5`, all overridable by env.

## 3. MCP: FastMCP, adapters, identity
- **FastMCP 4.1.6** (https://gofastmcp.com/servers/tools): sync tools "automatically run in a threadpool"; dicts, dataclasses and pydantic returns become `structuredContent`; `raise ToolError("...")` is always shown to clients, and `FastMCP(mask_error_details=True)` hides other exceptions. Transports: stdio for Claude Desktop, streamable HTTP for remote.
- **Hidden parameters:** "Parameters using `Depends()` are automatically excluded from the tool schema" (FastMCP ≥ 2.14). Identity can come from `get_http_headers()` / `CurrentAccessToken()` / `TokenClaim("sub")` on HTTP (https://gofastmcp.com/servers/dependency-injection). On stdio, identity is a launch-time setting (an env var for the server process), which fits a single-user Claude Desktop demo. `Client.call_tool(..., meta={...})` exists since 2.13.1 (https://gofastmcp.com/clients/tools); reading it server-side is unconfirmed.
- **Client side changed:** `langchain-mcp-adapters` is superseded. Its README says the repo is archived and MCP support moved to `langchain[mcp]`. The new API is `from langchain.mcp import MCPAdapter` (beta, emits `LangChainBetaWarning`), which accepts a URL, a script `Path` (stdio), or an **in-process `FastMCP` instance**. `tool_interceptors` are replaced by `@wrap_tool_call` middleware. The API is async-only (`async with MCPAdapter(...)`, `await adapter.list_tools()`), and by default opens one client session per tool call (https://docs.langchain.com/oss/python/langchain/mcp, `/mcp/connections`, `/migrate/langchain-mcp-adapters`). Per-call headers or `_meta` from runtime context are not documented.
- **Latency:** in-process is memory streams; stdio adds JSON-RPC over pipes plus a child process; both are milliseconds against ~2.2 s of LLM (not measured here). The real cost of routing the agent through MCP is complexity: an async boundary in a sync stack, a beta API, a session handshake per call, and no documented per-turn identity channel.
- **Honest take:** routing the agent's own calls through MCP buys nothing for this agent and makes the customer_id rule harder. The simplest design that still meets §7.12 is **one tool contract, two transports**: `tools.py` defines the tool functions once (pydantic input, lean dict output, identity from context). The LangGraph agent calls them directly, and `mcp/server.py` registers the **same functions** in FastMCP, taking identity from `Depends()` (token claim on HTTP, env on stdio). A contract test asserts the agent's tool schemas equal the MCP `list_tools()` schemas and calls one tool through the in-memory `fastmcp.Client(server)`. The README then says truthfully: "the same tools serve any MCP client".

**Recommendation:** agent calls tools in-process; FastMCP exposes the identical functions for external clients; schema-equality contract test; skip the deprecated `langchain-mcp-adapters`.

## 4. Tool design
- **Ten tools:** `search_products(query, max_price?)`, `recommend_products(need)`, `get_product(product_id)`, `list_active_promotions()`, `calc_installments(total, count?)`, `list_my_orders()`, `get_order_status(order_id, email_or_phone?)`, `check_return_eligibility(order_id, email_or_phone?)`, `store_now()`, `search_policies(question)`. `list_my_orders` is not in the spec §7.3 list but the identity flow and the spike prompt v2 need it.
- **Identity (R17):** `customer_id` never appears in a schema. Tools take `runtime: ToolRuntime[TurnContext]` (`from langchain.tools import ToolRuntime`); "the parameter is not included in the tool schema sent to the model" (https://docs.langchain.com/oss/python/langchain/tools). Context is passed per turn: `graph.invoke(state, config, context=TurnContext(customer_id=...))`.
  - Identified customer: order tools check ownership by `customer_id`; `CheckReturnEligibility` already makes a foreign order look unknown.
  - Anonymous: `email_or_phone` is required; `GetOrderStatus` verifies, then the order's own `customer_id` feeds `CheckReturnEligibility`.
  - A contract test asserts no tool's model-visible schema contains `customer_id`.
- **Schemas:** pydantic arguments via `@tool(args_schema=...)` or annotated signatures. Use `Decimal` for money in, `int` ids. Descriptions in pt-BR, short, because they are prompt text.
- **Outputs (lean JSON, R6/R17):**
  - Product: `{id, name, category, available, status, stock, price: {table, promo_percent, final, pix}}`, money as voice-ready strings ("R$ 2.199", "R$ 2.089,05"), from `quote_price`. Every product leaves the tool paired with its `PriceQuote`, so the model never does arithmetic.
  - Search: `{match: "exact"|"candidates"|"none", products: [...≤8]}`. If the visible search is `NoMatch`, retry with `include_unavailable=True` so "Ainda tem o SN-7C?" gets `status: discontinued` instead of silence.
  - Order allowlist: `{id, order_date, status, total, payment_method, tracking_code, estimated_delivery, items: [{product_id, quantity}]}`. Never `notes` (R17). Item names need the catalog: resolve them in the tool layer, not in `orders`.
  - Eligibility: `ReturnEligibility` fields plus `reason` code; dates `isoformat()`. When `reason == defect_window_closed`, add `legal_warranty_note` so the prompt can say the legal 90-day warranty for durable goods may still apply (CDC art. 26, II, https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm) and hand off, instead of "não dá mais".
  - Policies: flatten `PolicyHit` to `{section, title, text}`, five hits, drop `score` (R6).
  - `store_now`: `{open, now, next_opening}` in isoformat plus the weekday in pt-BR.
- **Errors:** each tool catches `DomainError` and returns one short pt-BR line. `IdentityMismatch` and `OrderNotFound` return the same text ("dados não conferem; não revele nada do pedido"), `InvalidInstallments` returns the max plan, `IndexUnavailable` (R6) returns "busca indisponível agora". Anything else propagates to `handle_message`, which answers with the voice guide's chat error copy.
- **Pooling (R6, PR #4 row 11):** one `psycopg_pool.ConnectionPool(url, min_size=1, max_size=4, kwargs={"autocommit": True}, configure=register_vector_if_available, check=ConnectionPool.check_connection)` shared by both indexes (https://www.psycopg.org/psycopg3/docs/api/pool.html). Indexes take the pool, use `with pool.connection() as conn`, drop the `BEGIN/COMMIT` around single SELECTs, and wrap `psycopg.OperationalError` as `IndexUnavailable`. Build one `E5Embedder` per process. onnxruntime sessions are documented thread-safe for `run`; fastembed's wrapper is unconfirmed, so serialise it with a lock if a test shows otherwise.
- `STORE_TODAY` from env into `FixedClock` for return windows; `SystemClock` for `store_now` (phase 3 ruling).

**Recommendation:** ten thin tools with `ToolRuntime` identity, voice-ready lean JSON, products always paired with their quote, order allowlist without `notes`, errors mapped in the tool, one autocommit pool.

## 5. Voice in code
- **Bubbles:** keep the spike's delimiter: "1 a 3 mensagens curtas separadas por uma linha em branco" (prompt v2). Gemma followed it at 4.7–4.8 human score. Structured output (a JSON list of bubbles) would stop token streaming and tends to stiffen the prose; it is not worth it. `split_bubbles(text) -> tuple[str, ...]` is a pure function in `support/domain/bubbles.py`: split on blank lines, drop empties, merge any overflow into bubble 3. Phase 5 streams a bubble when `\n\n` arrives.
- **AI-tell detector:** a pure function `ai_tells(text) -> tuple[Tell, ...]` in `support/domain/ai_tells.py` with these checks:
  - em dash `—` and en dash used as punctuation;
  - markdown: `**`, `__`, leading `-`/`•`/`1.`, `#`;
  - banned phrases from the voice guide (fico feliz em ajudar, ótima pergunta, espero ter ajudado, não hesite, estou aqui para ajudar, sinta-se à vontade, à disposição, prezado);
  - "vc|pq|blz"; emoji; more than one `!`;
  - more than one `?`, or a question that is not in the last bubble;
  - more than 3 bubbles, or a bubble over about 2 sentences / 280 characters.
  The spike's regex list (`bench.py` `AI_TELLS`) is the seed. Evals gate on it (spec §10: 0 failures). At runtime, only log the tells; do not rewrite text.
- **Prompt layout (pt-BR, in `support/infrastructure/agent/prompts/`):** `persona.md` + `voice.md` (attributes, style rules, a few of the guide's 9 examples) + `tools.md` (prompt v2 rules), all static, then one dynamic suffix (customer name or "não identificado", today's date). Keep a **single** system message, static part first, so vLLM prefix caching hits and Anthropic/Gemini accept it.
- **Fix from the spike:** prompt v1 named the agent "Duda". The owner-approved voice guide says "assistente da Empório", with no invented human name.
- **Rules to add to v2 (carried items):**
  - hours "podem ser estendidos" on Black Friday, anniversary and Christmas, so hedge special dates (PR #4 row 10);
  - quote the cover e-mail `contato@emporiodamusica.com.br` and WhatsApp (67) 3341-4444 (spec §7.2.2);
  - installments follow 3.1, i.e. trust `calc_installments` (row 10);
  - after the defect window, mention the legal warranty and offer a person;
  - when asked, say it is the store's virtual assistant.
- The PT-vs-EN instruction A/B (spec §7.4) is two prompt files and one eval flag; PT stays the default.

**Recommendation:** blank-line bubbles split by a pure function, a pure `ai_tells` detector reused by evals, one static-first system prompt in pt-BR.

## 6. Guard node
- Same model, `with_structured_output(Scope, method="json_schema")`, with `Scope = {label: Literal["loja","acessorio","fora_de_escopo","abuso"]}`. Input is a short classifier prompt plus the last user message and the previous assistant turn, `max_tokens≈20`, thinking off. On vLLM this is guided decoding; the cost is one extra round trip per turn, since the static prefix is cached. Expect roughly a few hundred ms on a warm H200 (unconfirmed; measure in evals).
- Routing:
  - `loja` → agent with tools;
  - `acessorio` / `fora_de_escopo` → agent without tools plus a one-line scope instruction (voice guide examples 4 and 5);
  - `abuso` → one fixed short reply, no second LLM call.
- The spike handled accessory and off-topic correctly with **no** guard (14/14 on Gemma v2, `relatorio_v2.md`). So the guard's real value is abuse/prompt-injection screening and a cheaper path for off-topic, not accuracy.
- A rule-based pre-check (keyword lists) is not worth it: pt-BR paraphrase breaks it, and a false "abuso" on a real customer is worse than one LLM call. Spec §7.5 "deterministic answers for hours/address" is a later optimisation; skip it now.
- For testability, the guard node takes a `classify: Callable[[list[BaseMessage]], Scope]`; tests pass a lambda, and production passes the structured-output model.

**Recommendation:** keep the guard as specified (same model, json_schema, tiny prompt), inject the classifier for tests, no keyword pre-check.

## 7. Evals
- About 16 cases in `backend/evals/agent_cases.toml`:
  - the spike's 14 (catalog ≤ R$1000, address, Takamine GD20 price, PIX, regret anonymous, regret identified (customer 14), accessory, off-topic, 12x on R$900, order 5 ok, order 5 wrong identity, promotions, open now, discontinued);
  - ambiguous "Takamine" (expects a question, no price);
  - regret out of window (order 5, defect window closed);
  - `recommend_products` ("algo pra tocar MPB em casa").
- Each case has `message`, optional `customer_id`, `expect_tools` (set), facts `all_of` / `any_of` / `none_of`, and `ask` (must end with a question). Every case runs the voice detector.
- **Spike lessons:**
  - The verifier must be paraphrase-tolerant: "9x | 9 parcelas | nove vezes"; "não está mais disponível | saiu de linha | descontinu"; numbers compared after normalising "R$", dots and ",00".
  - Derive expected facts from the use cases at test time (the spike computed `viol_ok` from data), not from hard-coded strings.
  - The two v2 "failures" were verifier false negatives, so keep a failure transcript in the report.
- Run: `make evals PROVIDER=gemma|gemini|openai|anthropic` → pytest marker `eval`, same `emporio_test` DB as the retrieval eval. It writes `backend/evals/reports/<provider>.md` with hit rate, tells, p50/p95 latency, tokens and R$ per conversation, all read from the turn metrics (section 9).
- **LLM-as-judge:** report-only "human score 1–5", opt-in (`JUDGE=1`), never gating. The spike judge (Gemini) was useful for the model choice but adds cost and its own variance. Gating stays deterministic (tool + fact + tells). Target per spec §10: ≥ 90% and 0 tells.
- Temperature 0.3 as in the spike; run each case once by default, `REPEAT=3` for the README table.

**Recommendation:** ~16 TOML cases, deterministic paraphrase-tolerant gating plus the tell detector, optional non-gating judge, per-provider markdown report with cost and latency.

## 8. Observability: mandatory Langfuse tracing (owner decision, binding)
Every agent turn is traced. This overrides spec §7.12 ("optional by variable") and the §7.9 cut list. It moves from phase 6 into phase 4.

**SDK.**
- `langfuse` 5.2.0 is SDK major v5. It is OpenTelemetry-based and **requires a Langfuse v4 server**; v3 servers need SDK v4 (https://langfuse.com/docs/observability/sdk/overview). The current server release is v4.76.0 (GitHub releases, 2026-11-05). The "v3 stack" no longer applies: v4 is current.
- LangChain/LangGraph: `from langfuse.langchain import CallbackHandler`, passed in `config["callbacks"]`. It traces graph nodes, model calls (with usage) and tools.
- Useful API, checked in `langfuse/_client/client.py` and `langfuse/langchain/CallbackHandler.py`:
  - `CallbackHandler(trace_context={"trace_id": ...})`;
  - static `Langfuse.create_trace_id(seed=...)`;
  - `get_current_trace_id()`;
  - `auth_check()`;
  - `propagate_attributes(user_id=..., session_id=...)`.

**Mandatory, but `make check` stays offline.**
- **Fail fast:** the SDK never fails on its own. Without keys it logs "Client will be disabled". `LANGFUSE_TRACING_ENABLED=false`, `OTEL_SDK_DISABLED=true` or `LANGFUSE_SAMPLE_RATE<1` also turn tracing off silently (`client.py`). So enforcement is ours, in `config.py`, in the same style as the provider flag+key rule:
  - `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` are required;
  - any of the three disabling variables above is rejected.
  Missing or rejected values raise one clear startup error naming the variables, the local self-host command and where the deployed keys live. At API/CLI start, `auth_check()` runs once, so a wrong key or a down server fails at boot, not silently per turn.
- **Tests:** the graph factory takes `callbacks: Sequence[BaseCallbackHandler]` as a required argument with no default. The composition root (`build_agent(settings)`) always passes the real `CallbackHandler`; there is no runtime fallback branch. Unit tests pass a recording fake (`tests/fakes/recording_tracer.py`), so they can assert one trace per turn. One test asserts that settings without Langfuse variables raise. `make check` never builds the composition root, so it needs no server.
- **Evals:** `make evals` goes through the composition root, so agent evals are traced too. This is useful: every failed case links to its trace.

**Ids, PII and the metrics link.**
- Per turn, the server computes `trace_id = Langfuse.create_trace_id(seed=turn_uuid)` and builds a fresh `CallbackHandler(trace_context={"trace_id": trace_id})`. A fresh handler per turn avoids the `last_trace_id` race under concurrency. The same id goes to `turn_metrics.trace_id` (section 9), so the phase 5 panel can deep-link to the trace.
- Set `session_id = thread_id`, which is already server-derived. `user_id` must be a pseudonym, not the CSV id with name/e-mail; for example `cust-<hmac(customer_id)[:10]>`, or `anon`.
- Traces contain what customers type and what the tools return (e-mails, phones, tracking codes). The order allowlist (section 4) already keeps `notes` out. Also register `Langfuse(mask_otel_spans=...)` to redact e-mail/phone/CPF patterns at export time; it runs on raw OTel spans, including third-party instrumentation (https://langfuse.com/docs/observability/features/masking). That it covers the Python CallbackHandler spans is inferred from "raw OpenTelemetry span attributes"; confirm with a test trace.
- This matters most if traces leave our infrastructure (Langfuse Cloud = third-party processor under LGPD).

**Flush and serverless.**
- The SDK exports from a background OTel batch processor and registers `atexit(shutdown)` (`langfuse/_client/resource_manager.py` line 283).
- FastAPI: call `get_client().shutdown()` in the lifespan exit. On Modal, also call it from an `@modal.exit()` hook, because a scaled-down container must not drop the last batch.
- CLI/evals: `flush()` at the end of the run.
- Per-turn `flush()` is not needed in a long-lived container and would add latency.

**Hosting options.**
| | (a) Langfuse Cloud Hobby | (b) Self-host, docker compose | (c) Self-host on Railway |
|---|---|---|---|
| Cost | Free, no card; 50k units/month (traces + observations + scores), 30-day access, 2 users; Core $29/month (https://langfuse.com/pricing) | Free; laptop resources | Six services (web, worker, ClickHouse, Redis, MinIO, Postgres); at $10/GB-month RAM, roughly $30–40/month (estimate, unconfirmed), far above the $5 Hobby credit |
| Region | US, EU or Japan; no Brazil | local | owner's Railway project |
| Stack | none | `langfuse-web` + `langfuse-worker` (tag `4`), `clickhouse-server:26.3.62.3`, `redis:7`, MinIO, `postgres:17`; `ai-gateway` is optional and skipped (https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) | community template, Langfuse 4.69.0, ClickHouse 26.4, Redis 8.2.1 (https://railway.com/deploy/langfuse-v4690-production-ready-ai-observability--langfuse-v410-production-ready-ai-observ); not official |
| Keys | `.env` locally, Modal secret `emporio-langfuse` | **generated** by `make` into `.env` (`openssl rand`), seeded by headless init `LANGFUSE_INIT_PROJECT_PUBLIC_KEY/SECRET_KEY`, `LANGFUSE_INIT_USER_*`: zero signup | Railway variables + Modal secret |
| Fit | deployed demo | `make up` and evaluator clones | deployed demo |
- **Volume:** with the LangGraph handler, a turn is about 8–15 observations (guard, agent steps, tools, node spans; estimate). So the 50k Hobby units cover roughly 3–6k turns a month. That covers the demo and the real-LLM load test (dozens of conversations). The simulated-LLM load test (hundreds of conversations) could exhaust it, and sampling is forbidden. Run that load test against a self-hosted Langfuse, or budget one month of Core. Overage behaviour on Hobby is unconfirmed.
- **Reusing our Postgres (b):** possible. Langfuse v4 needs Postgres ≥ 15 (16 recommended), uses the `public` schema of the database it is given, and expects UTC (https://langfuse.com/self-hosting/deployment/infrastructure/postgres). Our `pgvector/pgvector:0.8.7-pg17` qualifies, so `DATABASE_URL=.../langfuse` on a **separate database** in the same container saves one service. Sharing our `emporio` database is not an option: both apps use `public`.
- **Footprint (b):** Langfuse recommends 4 cores and 16 GiB for a VM. Local Docker use is lighter, but ClickHouse plus two Node services is likely 2–4 GB RAM and a slower first boot for ClickHouse migrations (estimate, unconfirmed: measure on the owner's Mac). The upstream compose notes "lacks high-availability, scaling capabilities, and backup functionality", which is fine for local use (https://langfuse.com/self-hosting/deployment/docker-compose).
- **`make up` wiring:**
  - add a compose profile `observability` with the five Langfuse services;
  - add `make langfuse-keys`, which writes `SALT`, `ENCRYPTION_KEY`, `NEXTAUTH_SECRET` and the init project keys into `.env` if they are absent;
  - `make up` runs both and waits for `langfuse-web` health.
  `.env.example` lists the names only.

**Recommendation:** enforce Langfuse in `config.py` (required vars, reject disabling vars, `auth_check()` at boot); inject handlers only through the composition root and fakes in tests; a per-turn deterministic `trace_id` stored in `turn_metrics`; pseudonymous `user_id` plus span masking. Host it self-hosted locally (compose profile, own database on our Postgres, generated keys) and on Langfuse Cloud Hobby (EU) for the Modal demo.

## 9. Cost and latency per turn (§7.5)
- **Tokens:** sum `usage_metadata` of the turn's new `AIMessage`s (guard + agent steps). Everything is already in state, so no callback is needed.
- **Timings:** `perf_counter` around the guard node and each model call. For tools, use `ToolNode(wrap_tool_call=...)`, which times each tool. Vector search time is inside `search_policies` / `recommend_products`.
- **Cost:** `settings.prices[model] = (usd_in, usd_out, usd_cached_in)` × `USD_BRL` from env. Gemma self-hosted has no per-token price: store tokens and latency now, and phase 6 derives cost from GPU $/h ÷ measured throughput (pricing unconfirmed for Gemini; OpenAI/Anthropic from the pages in section 2).
- Table (new migration):
  ```sql
  CREATE TABLE turn_metrics (
    id bigserial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),
    thread_id text NOT NULL, provider text NOT NULL, model text NOT NULL, scope text NOT NULL,
    input_tokens int NOT NULL, output_tokens int NOT NULL, cached_tokens int NOT NULL DEFAULT 0,
    llm_calls smallint NOT NULL, tools text[] NOT NULL DEFAULT '{}',
    ms_total int NOT NULL, ms_guard int NOT NULL, ms_llm int NOT NULL, ms_tools int NOT NULL,
    cost_brl numeric(10,6), trace_id text);
  CREATE INDEX turn_metrics_thread_idx ON turn_metrics (thread_id, created_at);
  ```
  Phase 5's panel reads the last row per thread plus a per-conversation sum. Write it after the reply, with no customer data in the row.

**Recommendation:** derive tokens from state and timings from node/tool wrappers; one flat `turn_metrics` table; Gemma cost deferred to phase 6.

## 10. Testing strategy
- **Pure (support/domain):** `split_bubbles`, `ai_tells`, `thread_id` derivation, scope routing.
- **Graph (offline):** `GenericFakeChatModel` scripted with `AIMessage(tool_calls=[...])` then a final text. It "does not implement `bind_tools`", so subclass it with `bind_tools` returning `self` (https://docs.langchain.com/oss/python/langchain/test/unit-testing). Use `InMemorySaver` as the checkpointer, the guard as a lambda, and tools over in-memory repos and `tests/fakes/hash_embedder.py`. Assert routing, that identity reaches tools via context, trimming, and that a `DomainError` becomes a tool message. Keep fake models at function scope (they consume their iterator).
- **Contract (`tests/contract/`):** a snapshot of each tool's model-visible JSON schema; no `customer_id` anywhere; outputs lean (key allowlist, no `notes`, isoformat dates); MCP `list_tools()` schemas equal the agent's (in-memory `fastmcp.Client(server)`).
- **Provider factory:** flag/key matrix with monkeypatched env, constructing models without network. `init_chat_model` does not call the API at construction; confirm per provider in the test.
- `make check` stays offline: no keys, no DB (`env -u DATABASE_URL`), no Langfuse server. Tests inject a recording fake tracer and never build the composition root; one test asserts missing Langfuse variables fail startup. Postgres checkpointer and pool tests use the `postgres` marker; real-model evals use `eval`.

**Recommendation:** fake tool-calling model + InMemorySaver for the graph, schema-snapshot contract tests, everything networked behind existing markers.

## Proposed task breakdown for the plan
1. `config.py` (pydantic-settings: provider, model ids, keys, `VLLM_BASE_URL`, `STORE_TODAY`, prices, `USD_BRL`) + `make_chat_model` with the flag+key rule; tests.
2. Import-contract exemption for the tools module; pooled autocommit read adapters, shared embedder, `IndexUnavailable` (R6, PR #4 row 11).
3. Pure serializers: product+quote, order allowlist, eligibility (+ legal warranty note), policy hits, store status; tests.
4. Ten tools with `ToolRuntime` identity and `DomainError` mapping; contract tests (schemas snapshot, no `customer_id`).
5. `support/domain`: `split_bubbles`, `ai_tells`, `thread_id` derivation (TDD).
6. pt-BR prompts (persona without a human name, voice, tool rules v2 + carried rules) and single-system-message assembly.
7. Graph: guard (injected classifier) → agent ⇄ `ToolNode`, trimming; fake-model tests.
8. `PostgresSaver` on its own pool + `setup()` in `make migrate`; `handle_message` + `AgentRunner` port; `emporio chat --as-customer --provider` CLI.
9. `turn_metrics` migration + capture (tokens from state, timings via node/`wrap_tool_call`).
10. Mandatory Langfuse: settings validation + `auth_check()` at boot, per-turn handler with seeded `trace_id`, pseudonymous ids, span masking, shutdown hooks; compose profile `observability` + `make langfuse-keys`.
11. FastMCP server over the same tool functions (identity via `Depends`) + in-memory schema-equality contract test.
12. Agent evals: ~16 TOML cases, paraphrase-tolerant verifier, detector gate, per-provider report; `make evals PROVIDER=...`.

## Decisions to confirm with the owner
(Question 5 was added by the owner's Langfuse ruling, so this list goes one past the usual 4.)
1. **MCP path:** should the agent call the tools in-process, with FastMCP exposing the same functions to outside clients (recommended), or route the agent's own calls through `langchain.mcp.MCPAdapter` (beta, async-only, no documented per-turn identity)?
2. **Provider port:** one `make_chat_model` factory over `init_chat_model` (recommended), or the four adapter classes spec §5 describes?
3. **Default cloud models:** OpenAI has no "mini" now. Pick `gpt-6-luna` (cheapest) or `gpt-6.1-terra`? For Gemini, pick `gemini-3.8-flash` (spike winner, badged "New") or `gemini-3.6-flash` (stable)?
4. **Guard cost:** keep a separate guard LLM call every turn as specified (+1 round trip; the spike needed no guard for scope), or keep it but skip it on follow-up turns already labelled `loja`?
5. **Langfuse hosting** (local and deployed): recommended is self-hosted via a compose profile for `make up` and evaluator clones (own `langfuse` database on our Postgres, generated keys, zero signup) **plus** Langfuse Cloud Hobby (EU) for the Modal demo (free; 50k units/month, 30-day access). The alternatives are Cloud for both (every evaluator needs their own account and keys before `make up` works) or self-host on Railway for the demo (about $30–40/month estimate, community template).

## Risks
- Gemma 4 parallel tool calls through the `gemma4` parser are unverified; the image tag `vllm/vllm-openai:latest` is unpinned, so a parser regression can land silently. Pin the vLLM version in phase 6 and keep one two-tool eval case.
- `thread_id` not tied to channel identity would leak one customer's orders to another through history. Needs a test.
- The tools module needs an import-contract exemption; doing it broadly would erode the layering the README sells.
- `langchain.mcp` is beta and `langchain-mcp-adapters` is archived, so the API may churn before Monday. Keep MCP at the edge.
- The guard adds latency against the ≤ 3 s median target. Measure it in evals before the GPU sizing in phase 6.
- Anthropic and OpenAI defaults have adaptive or reasoning modes that may add latency. Set effort/thinking explicitly per provider (kwarg names unconfirmed).
- Eval flakiness at temperature 0.3, and verifier false negatives (seen twice in the spike). Keep transcripts in reports and use `REPEAT` for the README numbers.
- Gemini pricing and Gemma per-turn cost are unconfirmed here, so cost columns stay null until phase 6.
- Mandatory tracing adds a hard dependency at boot. If Langfuse Cloud or the local stack is down, the agent refuses to start (by design). The README must say so, and `make up` must bring Langfuse up first.
- Langfuse Cloud Hobby quota (50k units) can run out during the simulated-LLM load test; sampling is not allowed, so point that test at the self-hosted stack.
- Traces carry customer-typed PII. Masking coverage of CallbackHandler spans is inferred, not verified, so add a test trace check before the demo goes public.
- The local Langfuse stack (ClickHouse + 2 Node services) adds an unmeasured 2–4 GB RAM to `make up` on the evaluator's machine.

## Owner decisions (2026-11-05)
- Langfuse is mandatory: every agent turn is traced; startup fails clearly when it is not configured. Hosting: self-hosted via a compose profile locally (own `langfuse` database on our Postgres, generated keys, zero signup) and Langfuse Cloud Hobby (EU) for the Modal demo.
- MCP: the agent calls the tool functions in-process; FastMCP exposes the same functions to external clients with identity injected server-side; a contract test asserts the schemas match.
- Guard: a separate guard call on every turn, as specified.
- Controller calls (owner may veto): one `make_chat_model` factory over `init_chat_model` instead of four adapter classes; default cloud models `gemini-3.8-flash` (spike winner), `gpt-6-luna`, `claude-haiku-5-5`, all overridable by env.
