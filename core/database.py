import os
from pathlib import Path
from datetime import datetime
import duckdb
import pandas as pd
import psycopg2
from data_processing.etl import queries

# -------------------------
# Configurações e caminhos
# -------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # .../sprintdfarma
DATA_DIR = PROJECT_ROOT / "duck_cache"
DATA_DIR.mkdir(exist_ok=True)
DUCK_DB_PATH = DATA_DIR / "warehouse.duckdb"  # arquivo do DuckDB

# Use variáveis de ambiente quando possível; mantém compatibilidade com seu atual config
db_config = {
    'dbname': os.getenv('PG_DB', 'drogariajb_esc'),
    'user': os.getenv('PG_USER', 'leiturabd_24072024'),
    'password': os.getenv('PG_PASSWORD', 'bbtSBIE5sr66qe9'),
    'host': os.getenv('PG_HOST', '192.168.60.2'),
    'port': os.getenv('PG_PORT', '5432'),
}

# -------------------------
# Warehouse DuckDB
# -------------------------
class DuckWarehouse:
    def __init__(self, duckdb_path: Path, pg_config: dict):
        self.duckdb_path = str(duckdb_path)
        self.pg_config = pg_config
        self.conn = duckdb.connect(self.duckdb_path)  # persistente

    def close(self):
        if self.conn:
            self.conn.close()

    # PostgreSQL -> DataFrame
    def fetch_pg(self, sql: str) -> pd.DataFrame:
        try:
            with psycopg2.connect(**self.pg_config) as cn:
                df = pd.read_sql_query(sql, cn)
            return df
        except Exception as e:
            print(f"❌ Erro PG: {e}")
            return pd.DataFrame()

    # DataFrame -> DuckDB (CREATE OR REPLACE)
    def create_or_replace_table(self, table_name: str, df: pd.DataFrame):
        # Registra DF e cria/atualiza tabela
        self.conn.register("df_tmp", df)
        self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_tmp")
        self.conn.unregister("df_tmp")

    def ensure_basic_indexes(self):
        # Índices simples (DuckDB cria zone maps; indexes úteis em alguns casos)
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_venda_data ON venda(venda_datahorafechamento)")
        except Exception:
            pass

    def bulk_load_from_postgres(self, tables: list[str] | None = None):
        target = tables or list(queries.query.keys())
        loaded = {}
        print("🔄 Carregando do PostgreSQL para DuckDB...")
        for name in target:
            sql = queries.query[name]
            print(f"  ▶ {name} ...", end="")
            df = self.fetch_pg(sql)
            if df.empty:
                print(" vazio")
                loaded[name] = 0
                continue
            self.create_or_replace_table(name, df)
            count = self.conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f" {count:,} linhas")
            loaded[name] = count
        self.ensure_basic_indexes()
        print("✅ Concluído.")
        return loaded

    def query_df(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).fetchdf()

    def table_counts(self) -> pd.DataFrame:
        sql = """
        SELECT table_name, row_count
        FROM (
            SELECT table_name, 
                   (SELECT COUNT(*) FROM duckdb_columns WHERE table_name = t.table_name LIMIT 1) AS cols,
                   (SELECT COUNT(*) FROM (EXECUTE ('SELECT * FROM ' || quote_ident(t.table_name))) ) AS row_count
            FROM information_schema.tables t
            WHERE table_schema = 'main'
        )
        ORDER BY row_count DESC NULLS LAST;
        """
        # Fallback simples (mais barato)
        tables = self.conn.execute("PRAGMA show_tables").fetchdf()
        out = []
        for t in tables['name'].tolist():
            cnt = self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            out.append((t, cnt))
        return pd.DataFrame(out, columns=['table_name', 'row_count'])

# -------------------------
# APIs externas (para usar no app_duck)
# -------------------------
def init_duck_warehouse(load_from_pg: bool = True, tables: list[str] | None = None) -> DuckWarehouse:
    wh = DuckWarehouse(DUCK_DB_PATH, db_config)
    if load_from_pg:
        wh.bulk_load_from_postgres(tables=tables)
    return wh

def duck_query(sql: str) -> pd.DataFrame:
    wh = DuckWarehouse(DUCK_DB_PATH, db_config)
    try:
        return wh.query_df(sql)
    finally:
        wh.close()

def load_minimal():
    """Carrega apenas tabelas essenciais para primeiro teste."""
    return init_duck_warehouse(load_from_pg=True, tables=['venda', 'item', 'filial'])

if __name__ == "__main__":
    wh = init_duck_warehouse(load_from_pg=True, tables=['venda', 'item'])
    print(wh.table_counts())
    wh.close()