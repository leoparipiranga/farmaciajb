# Quick orientation for AI coding agents working on this repo

This file contains focused, actionable information to help an AI agent be productive in this codebase.

High level
- Entrypoint: `app.py` is a Streamlit app that renders UI modules (Lojas, Estoque, Promoções, Vendedores).
- Local warehouse: DuckDB file at `duck_cache/warehouse.duckdb`. Core accessors are in `core/database.py`.
- ETL orchestration and view rebuilds:
  - Full update (Postgres -> DuckDB -> facts -> views -> historical caches): `run_update_duck.py`.
  - Regenerate SQL views only: `run_views.py` (accepts date and flags: `--mode=batch5|batch10|fallback|auto`, `--limit=N`, `--verbose`).

Important directories and responsibilities
- `core/` — db connection, DuckWarehouse class, convenience `duck_query()` and `init_duck_warehouse()`.
- `modules_duck/` — feature pages implemented against DuckDB (e.g. `lojas_duck.py`, `estoque_duck.py`). Prefer changing these when modifying UI/feature logic.
- `data_processing/` — ETL and business calculations (subfolders: `etl/`, `vendas/`, `estoque/`, `previsoes/`, `legacy/`). SQL used to bulk-load from Postgres is under `data_processing/etl/queries.py`.
- `visualizations/` — styling, re-usable chart and card components. CSS and popover styling live here and are applied by modules.
- `interfaces/` — cross-module UI interfaces (for alert pages, etc.).

Project-specific patterns and gotchas
- DuckDB connection patterns:
  - For bulk loads or multi-statement ETL use `init_duck_warehouse(load_from_pg=True)` to keep a persistent connection (`DuckWarehouse` instance) and avoid repeatedly opening/closing.
  - For ad-hoc single-query reads use `core.database.duck_query(sql)` which opens a short-lived DuckWarehouse.
  - Race condition: multiple processes writing the same `warehouse.duckdb` concurrently can conflict — coordinate long-running ETL (`run_update_duck.py`) with UI sessions.
- Streamlit session/state:
  - Session state keys used widely: `pagina_atual`, `view`, `filial_sel`, `ultima_atualizacao`, `autenticado`, `usuario`.
  - Login secrets come from `st.secrets['usuarios']`; code falls back to an embedded test account `admin/123456` in `app.py`.
- Naming conventions:
  - SQL views: `vw_*`; temporary copies: `temp_*`; cache tables: `cache_*`; materialized fact tables created during ETL are named `fact_*_final`.
  - UI modules that use DuckDB use the `_duck` suffix (e.g., `lojas_duck.py`).
- View rebuild behavior: `run_views.py` assembles many CREATE OR REPLACE VIEW statements and executes them in batches. Use `--mode=fallback` to run each statement via `duck_query()` if a batch execution fails.

Developer workflows (use these commands locally)
- Install dependencies (create a venv first):

```powershell
python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt
```

- Run the Streamlit app locally:

```powershell
streamlit run app.py
```

- Full warehouse update (Postgres -> DuckDB -> facts -> views -> historical caches):

```powershell
python run_update_duck.py
```

- Regenerate views only (example for 2025-09-28, 5-statement batches):

```powershell
python run_views.py 2025-09-28 --mode=batch5 --verbose
```

Useful code pointers / examples
- To run many SQL queries efficiently: inspect `data_processing/etl/transformations.py` and `run_views.py` — `exec_statements()` supports `batchN` modes.
- To add a new Streamlit page: add a module in `modules_duck/` and import it from `app.py`'s module routing (see `render_lojas_module()` as example).
- To run ad-hoc queries in Python: use `from core.database import duck_query; duck_query("SELECT ...")`.
- To see which Postgres source SQL is used during bulk loads: open `data_processing/etl/queries.py` (keys used by `core.database.DuckWarehouse.bulk_load_from_postgres`).

Testing / debugging tips
- For fast iteration while developing SQL or view logic, prefer `run_views.py --limit=N` to only run the first N statements.
- When investigating performance or missing rows: open the DuckDB with any DuckDB client or programmatically via `DuckWarehouse.query_df(sql)` and inspect `PRAGMA show_tables` or `SELECT COUNT(*) FROM table`.
- If ETL is failing with connection/credential errors, check `core/config.py` for Postgres defaults; production credentials should be provided via environment variables or `st.secrets` and not committed.

When to ask maintainers
- Secrets and Postgres host/credentials — these are environment-dependent. If you need remote access or sample dumps, request sanitized credentials or a small sample dataset.
- Long-running refactors that change data shapes (rename fact tables or columns) — coordinate with the team as views and many modules depend on stable column names.

If anything in these notes is unclear or you'd like more examples (typical queries, a small unit test, or an automated smoke test), tell me which area to expand and I'll update this file.
