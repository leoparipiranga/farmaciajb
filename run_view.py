import os
import pandas as pd
import sys
import datetime
import duckdb
from core.database import duck_query, DUCK_DB_PATH

def _assemble_statements(data_atual: str) -> list[str]:
    dt_ref = datetime.date.fromisoformat(data_atual)
    dt_ontem = dt_ref - datetime.timedelta(days=1)
    dt_30 = dt_ontem - datetime.timedelta(days=30)
    dt_90 = dt_ontem - datetime.timedelta(days=90)
    dt_121 = dt_ontem - datetime.timedelta(days=121)

    s_ontem = dt_ontem.isoformat()
    s_30 = dt_30.isoformat()
    s_90 = dt_90.isoformat()
    s_121 = s_121 = dt_121.isoformat()

    stmts = [
f"""CREATE OR REPLACE VIEW vw_vendas_90d AS
SELECT filial_codigo,
       item_embalagemid AS embalagemid,
       classificacao_n1,
       classificacao_n2,
       classificacao_n3,
       SUM(ABS(item_quantidade)) AS qtd_vendida_90d,
       SUM(ABS(item_quantidade) * COALESCE(customedio,0)) AS cmv_90d
FROM fact_vendas_final
WHERE data_date BETWEEN DATE '{s_90}' AND DATE '{s_ontem}'
GROUP BY 1,2,3,4,5""",
"CREATE OR REPLACE VIEW temp_vendas_90d AS SELECT * FROM vw_vendas_90d",
"CREATE OR REPLACE VIEW temp_vendas_curr_90d AS SELECT * FROM vw_vendas_90d"]
    
def _conn_info():
    p = str(DUCK_DB_PATH)
    exists = os.path.exists(p)
    size = os.path.getsize(p) if exists else -1
    return p, exists, size

def exec_statements(statements: list[str], limit: int | None = None, fallback: bool = False):
    if not fallback:
        try:
            p, exists, size = _conn_info()
            print(f"[DEBUG] Abrindo conexão DuckDB (modo batch): {p}", flush=True)
            conn = duckdb.connect(p)
            conn.execute("SELECT 1")  # pode crashar aqui
            print("[DEBUG] Conexao OK", flush=True)
            # (se chegou aqui, segue normal)
            conn.commit()
            conn.close()
            return
        except Exception as e:
            print(f"[WARN] Falhou batch: {e}. Indo para fallback.", flush=True)
        except SystemExit:
            raise
        except:
            print("[WARN] Crash nativo suspeito. Forçando fallback.", flush=True)

def build_views(data_atual: str, limit: int | None = None, fallback: bool = False):
    stmts = _assemble_statements(data_atual)
    exec_statements(stmts, limit=limit, fallback=fallback)
    print("Views regeneradas para", data_atual, flush=True)

def main():
    # Uso: python run_views.py [data_iso] [--limit=N] [--fallback]
    args = sys.argv[1:]
    data_atual = None
    limit = None
    fallback = False
    for a in args:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
        elif a == "--fallback":
            fallback = True
        elif data_atual is None:
            data_atual = a
    if data_atual is None:
        data_atual = datetime.date.today().isoformat()
    print(f"Iniciando build_views data={data_atual} limit={limit} fallback={fallback}", flush=True)
    build_views(data_atual, limit=limit, fallback=fallback)

if __name__ == "__main__":
    main()