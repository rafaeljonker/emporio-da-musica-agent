# Where backend state lives

Paths are relative to `backend/src/emporio/`.

## Per process (lost on restart, not shared across containers)
- Rate limits, all `SlidingWindow` (`api/guards.py`): login per IP and overall (`api/auth.py`), chat per session and overall (`api/chat.py`), catalog writes per login, per IP and creates per IP (`api/catalog.py`), identity switches (`api/identity.py`), MCP failures per IP and calls per token (`api/mcp_auth.py`).
- One lock per chat thread: `ThreadLocks` (`api/guards.py`), used by `api/chat.py`.
- Warm-up status: `ReadyWarmup` and `ProbeWarmup` with its daemon probe thread (`support/infrastructure/warmup.py`); the fake warm-up clock in `entrypoints/bootstrap.py build_warmup`.
- The MCP caller's identity: a `ContextVar` per request (`api/mcp_auth.py`). `TurnProbe` lives for one turn (`support/infrastructure/agent/turn_probe.py`).

This is why the API runs as one process (`max_containers=1` on Modal). Moving the limits, locks and warm-up to a shared store is the upgrade path.

## Module globals and caches
- The Langfuse client: `_client` in `support/infrastructure/tracing.py`.
- The e5 model registration flag: `_registered` in `platform/embeddings.py`.
- `cached_property` caches: categories in `PgCatalogRepository`, the parsed CSVs in `CsvCatalogRepository` and `CsvOrderRepository`.
- Prompt files read once through `importlib.resources` (`support/infrastructure/agent/prompt.py`).

## Postgres
- Schema from `backend/migrations/*.sql`, applied by `platform/migrate.py` (tracked in `schema_migrations`).
- Tables: `policy_chunks`, `turn_metrics`, `categories`, `products` (demo rows from `products_admin_id_seq`), `promotions`, `catalog_audit`.
- Pools: the read pool built in `entrypoints/bootstrap.py`, the saver pool in `support/infrastructure/checkpointer.py`.

## LangGraph checkpointer
- `PostgresSaver` tables, created by `platform/migrate.py setup_checkpointer`. The key is `ChannelIdentity.thread_id()` (`support/domain/channel_identity.py`).

## Session
- Cookie `emporio_session`, signed and stateless (`api/app.py`); it holds `sid`, `lid` and `customer_id` (`api/auth.py`, `api/identity.py`).

## Files
- Orders and customers are read from the CSVs in `data/` (`platform/paths.py`); the catalog CSVs only seed Postgres (`entrypoints/ingest.py`).
