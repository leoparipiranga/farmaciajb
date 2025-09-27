import os
import sys
import datetime
import duckdb
import pandas as pd
from core.database import DUCK_DB_PATH, duck_query

DEBUG_LOG = "exec_multi_debug.log"  # pode remover se não usar mais

def _assemble_statements(data_atual: str) -> list[str]:
    dt_ref = datetime.date.fromisoformat(data_atual)
    dt_ontem = dt_ref - datetime.timedelta(days=1)
    dt_30 = dt_ontem - datetime.timedelta(days=30)
    dt_90 = dt_ontem - datetime.timedelta(days=90)
    dt_121 = dt_ontem - datetime.timedelta(days=121)

    s_ontem = dt_ontem.isoformat()
    s_30 = dt_30.isoformat()
    s_90 = dt_90.isoformat()
    s_121 = dt_121.isoformat()

    return [
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
"CREATE OR REPLACE VIEW temp_vendas_curr_90d AS SELECT * FROM vw_vendas_90d",
f"""CREATE OR REPLACE VIEW vw_vendas_30d AS
SELECT filial_codigo,
       item_embalagemid AS embalagemid,
       SUM(ABS(item_quantidade)) AS qtd_vendida_30d,
       SUM(ABS(item_quantidade) * COALESCE(customedio,0)) AS cmv_30d
FROM fact_vendas_final
WHERE data_date BETWEEN DATE '{s_30}' AND DATE '{s_ontem}'
GROUP BY 1,2""",
"CREATE OR REPLACE VIEW temp_vendas_30d AS SELECT * FROM vw_vendas_30d",
f"""CREATE OR REPLACE VIEW vw_curva_abc_90d AS
WITH ranked AS (
  SELECT *,
         SUM(qtd_vendida_90d) OVER (
           PARTITION BY filial_codigo, classificacao_n3
           ORDER BY qtd_vendida_90d DESC) AS acum,
         SUM(qtd_vendida_90d) OVER (
           PARTITION BY filial_codigo, classificacao_n3) AS total_grp
  FROM vw_vendas_90d
)
SELECT filial_codigo,
       embalagemid,
       classificacao_n1,
       classificacao_n2,
       classificacao_n3,
       CASE
         WHEN total_grp>0 AND (acum*100.0/total_grp)<=50 THEN 'A'
         WHEN total_grp>0 AND (acum*100.0/total_grp)<=80 THEN 'B'
         WHEN total_grp>0 THEN 'C'
         ELSE 'D'
       END AS curvaABC
FROM ranked""",
"CREATE OR REPLACE VIEW temp_curva_abc_90d AS SELECT * FROM vw_curva_abc_90d",
"CREATE OR REPLACE VIEW temp_curva_abc_curr_90d AS SELECT * FROM vw_curva_abc_90d",
f"""CREATE OR REPLACE VIEW vw_estoque_snapshot_90d AS
WITH ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
  FROM fact_estoque_final
  WHERE datahora BETWEEN DATE '{s_90}' AND DATE '{s_ontem}'
)
SELECT filial_codigo, embalagemid, estoque, customedio,
       customedio * estoque AS valor_estoque,
       classificacao_n1, classificacao_n2, classificacao_n3
FROM ranked WHERE rn=1""",
"CREATE OR REPLACE VIEW temp_estoque_snapshot_90d AS SELECT * FROM vw_estoque_snapshot_90d",
f"""CREATE OR REPLACE VIEW vw_estoque_snapshot AS
WITH ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
  FROM fact_estoque_final
  WHERE datahora <= DATE '{s_ontem}'
)
SELECT filial_codigo, embalagemid, estoque, customedio,
       customedio * estoque AS valor_estoque,
       classificacao_n1, classificacao_n2, classificacao_n3
FROM ranked WHERE rn=1""",
"CREATE OR REPLACE VIEW temp_estoque_snapshot AS SELECT * FROM vw_estoque_snapshot",
f"""CREATE OR REPLACE VIEW vw_comprados_90d AS
SELECT DISTINCT filial_codigo, embalagemid
FROM fact_estoque_final
WHERE datahora BETWEEN DATE '{s_90}' AND DATE '{s_ontem}'
  AND descricao_movimentacao = 'Recebimento Físico'""",
"CREATE OR REPLACE VIEW temp_comprados_90d AS SELECT * FROM vw_comprados_90d",
f"""CREATE OR REPLACE VIEW vw_vendidos_30d_ids AS
SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
FROM fact_vendas_final
WHERE data_date BETWEEN DATE '{s_30}' AND DATE '{s_ontem}'""",
"CREATE OR REPLACE VIEW temp_vendidos_30d_ids AS SELECT * FROM vw_vendidos_30d_ids",
"""CREATE OR REPLACE VIEW vw_denominador_disp AS
SELECT c.filial_codigo, c.embalagemid
FROM vw_comprados_90d c
INNER JOIN vw_vendidos_30d_ids v
  ON c.filial_codigo = v.filial_codigo
 AND c.embalagemid = v.embalagemid""",
"CREATE OR REPLACE VIEW temp_denominador_disp AS SELECT * FROM vw_denominador_disp",
"""CREATE OR REPLACE VIEW vw_giro_flag_30d AS
SELECT es.filial_codigo,
       es.embalagemid,
       CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS teve_giro_30d
FROM vw_estoque_snapshot_90d es
LEFT JOIN vw_vendidos_30d_ids v
  ON es.filial_codigo = v.filial_codigo
 AND es.embalagemid = v.embalagemid""",
"CREATE OR REPLACE VIEW temp_giro_flag_30d AS SELECT * FROM vw_giro_flag_30d",
f"""CREATE OR REPLACE VIEW vw_vendas_121d AS
SELECT filial_codigo,
       item_embalagemid AS embalagemid,
       data_date,
       classificacao_n1,
       classificacao_n2,
       classificacao_n3,
       ABS(item_quantidade) AS qtde_vendida
FROM fact_vendas_final
WHERE data_date BETWEEN DATE '{s_121}' AND DATE '{s_ontem}'""",
"CREATE OR REPLACE VIEW temp_vendas_121d AS SELECT * FROM vw_vendas_121d",
f"""CREATE OR REPLACE VIEW vw_recebimentos_121d AS
SELECT filial_codigo,
       embalagemid,
       DATE(datahora) AS data_compra,
       ABS(quantidade) AS quantidade,
       COALESCE(customedio,0) AS customedio,
       classificacao_n1,
       classificacao_n2,
       classificacao_n3
FROM fact_estoque_final
WHERE datahora BETWEEN DATE '{s_121}' AND DATE '{s_ontem}'
  AND descricao_movimentacao = 'Recebimento Físico'""",
"CREATE OR REPLACE VIEW temp_recebimentos_121d AS SELECT * FROM vw_recebimentos_121d",
f"""CREATE OR REPLACE VIEW vw_vendas_n2_detalhe AS
SELECT
    v.filial_codigo,
    v.item_embalagemid AS embalagemid,
    v.data_date,
    v.classificacao_n1,
    v.classificacao_n2,
    v.classificacao_n3,
    ABS(v.item_quantidade) AS quantidade_vendida,
    v.item_valorunitario,
    COALESCE(v.item_desconto, 0) AS item_desconto,
    (v.item_valorunitario - COALESCE(v.item_desconto, 0)) AS preco_liquido,
    v.customedio,
    (v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade) AS receita_real,
    v.customedio * ABS(v.item_quantidade) AS cmv_real,
    ((v.item_valorunitario - COALESCE(v.item_desconto, 0)) - v.customedio) * ABS(v.item_quantidade) AS margem_bruta_real
FROM fact_vendas_final v
WHERE v.data_date BETWEEN DATE '{s_121}' AND DATE '{s_ontem}'
  AND v.customedio > 0
  AND v.item_valorunitario > 0""",
"CREATE OR REPLACE VIEW temp_vendas_n2_detalhe AS SELECT * FROM vw_vendas_n2_detalhe",
"""CREATE OR REPLACE VIEW vw_vendas_n2_curva AS
SELECT d.*,
       COALESCE(c.curvaABC,'D') AS curvaABC
FROM vw_vendas_n2_detalhe d
LEFT JOIN vw_curva_abc_90d c
  ON d.filial_codigo = c.filial_codigo
 AND d.embalagemid = c.embalagemid""",
"CREATE OR REPLACE VIEW temp_vendas_n2_curva AS SELECT * FROM vw_vendas_n2_curva",
"""CREATE OR REPLACE VIEW vw_vendas_n2_agregado AS
SELECT filial_codigo,
       curvaABC,
       classificacao_n2,
       DATE(data_date) AS data_venda,
       SUM(quantidade_vendida) AS total_quantidade_vendida,
       SUM(receita_real) AS receita_real_vendas,
       SUM(cmv_real) AS cmv_vendas,
       SUM(margem_bruta_real) AS margem_bruta_vendas,
       COUNT(*) AS total_transacoes
FROM vw_vendas_n2_curva
GROUP BY filial_codigo, curvaABC, classificacao_n2, DATE(data_date)""",
"CREATE OR REPLACE VIEW temp_vendas_n2_agregado AS SELECT * FROM vw_vendas_n2_agregado",
"""CREATE OR REPLACE VIEW vw_estoque_snapshot_n2 AS
SELECT es.*,
       COALESCE(c.curvaABC,'D') AS curvaABC
FROM vw_estoque_snapshot es
LEFT JOIN vw_curva_abc_90d c
  ON es.filial_codigo = c.filial_codigo
 AND es.embalagemid = c.embalagemid""",
"CREATE OR REPLACE VIEW temp_estoque_snapshot_n2 AS SELECT * FROM vw_estoque_snapshot_n2",
"""CREATE OR REPLACE VIEW vw_estoque_snapshot_90d_n2 AS
SELECT es.*,
       COALESCE(c.curvaABC,'D') AS curvaABC
FROM vw_estoque_snapshot_90d es
LEFT JOIN vw_curva_abc_90d c
  ON es.filial_codigo = c.filial_codigo
 AND es.embalagemid = c.embalagemid""",
"CREATE OR REPLACE VIEW temp_estoque_snapshot_90d_n2 AS SELECT * FROM vw_estoque_snapshot_90d_n2",
"""CREATE OR REPLACE VIEW vw_ultima_aquisicao AS
WITH ranked AS (
    SELECT
        filial_codigo,
        embalagemid,
        DATE(datahora) AS data_ultima_aquisicao,
        quantidade AS ultima_qtde,
        COALESCE(customedio,0) AS ultimo_customedio,
        classificacao_n1,
        classificacao_n2,
        classificacao_n3,
        ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
    FROM fact_estoque_final
    WHERE descricao_movimentacao = 'Recebimento Físico'
)
SELECT *
FROM ranked
WHERE rn = 1"""
    ]

def _build_cache_curva_abc_90d(data_atual: str):
    """
    Materializa/atualiza cache_curva_abc_90d (classificação ABC 90 dias por quantidade).
    Recria somente a partição (data_ref = ontem).
    Cortes: A=50%, B=80%, C=restante, D se sem vendas.
    """
    ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
    data_ref = ontem.strftime('%Y-%m-%d')
    dt_90 = (ontem - pd.Timedelta(days=90)).strftime('%Y-%m-%d')

    create_sql = """
    CREATE TABLE IF NOT EXISTS cache_curva_abc_90d (
        data_ref DATE,
        filial_codigo VARCHAR,
        embalagemid VARCHAR,
        classificacao_n3 VARCHAR,
        quantidade_vendida DOUBLE,
        curvaABC VARCHAR
    );
    """
    duck_query(create_sql)

    duck_query(f"DELETE FROM cache_curva_abc_90d WHERE data_ref = DATE '{data_ref}';")

    insert_sql = f"""
    INSERT INTO cache_curva_abc_90d
    WITH vendas_90d AS (
        SELECT
            v.filial_codigo,
            v.classificacao_n3,
            v.item_embalagemid AS embalagemid,
            SUM(ABS(v.item_quantidade)) AS quantidade_vendida
        FROM fact_vendas_final v
        WHERE v.data_date >= DATE '{dt_90}'
          AND v.data_date <= DATE '{data_ref}'
        GROUP BY v.filial_codigo, v.classificacao_n3, v.item_embalagemid
    ),
    vendas_acum AS (
        SELECT
            filial_codigo,
            classificacao_n3,
            embalagemid,
            quantidade_vendida,
            SUM(quantidade_vendida) OVER (
                PARTITION BY filial_codigo, classificacao_n3
                ORDER BY quantidade_vendida DESC
            ) AS quantidade_acum,
            SUM(quantidade_vendida) OVER (
                PARTITION BY filial_codigo, classificacao_n3
            ) AS total_vendas_grupo
        FROM vendas_90d
    )
    SELECT
        DATE '{data_ref}' AS data_ref,
        filial_codigo,
        embalagemid,
        classificacao_n3,
        quantidade_vendida,
        CASE
            WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
            WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
            WHEN total_vendas_grupo > 0 THEN 'C'
            ELSE 'D'
        END AS curvaABC
    FROM vendas_acum;
    """
    duck_query(insert_sql)

def _exec_batch(statements: list[str], start: int, end: int, verbose: bool):
    subset = statements[start:end]
    if not subset:
        return
    conn = duckdb.connect(str(DUCK_DB_PATH), config={'threads': '1'})
    try:
        conn.execute("SELECT 1")
        for stmt in subset:
            conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()

def exec_statements(statements: list[str],
                    limit: int | None = None,
                    mode: str = "batch5",
                    verbose: bool = False):
    if limit:
        statements = statements[:limit]

    if mode == "fallback":
        for stmt in statements:
            duck_query(stmt)
        return

    if mode.startswith("batch"):
        size = int(mode.replace("batch", "")) if mode != "auto" else 5
        for start in range(0, len(statements), size):
            end = min(start + size, len(statements))
            _exec_batch(statements, start, end, verbose)
        return

    # auto => batch5
    for start in range(0, len(statements), 5):
        end = min(start + 5, len(statements))
        _exec_batch(statements, start, end, verbose)

def build_views(data_atual: str,
                limit: int | None = None,
                mode: str = "batch5",
                verbose: bool = False):
    stmts = _assemble_statements(data_atual)
    exec_statements(stmts, limit=limit, mode=mode, verbose=verbose)
    print(f"Views regeneradas para {data_atual}")

def main():
    # Uso: python run_views.py [data_iso] [--limit=N] [--mode=auto|fallback|batch5|batch10] [--verbose]
    args = sys.argv[1:]
    data_atual = None
    limit = None
    mode = "batch5"
    verbose = False
    for a in args:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
        elif a.startswith("--mode="):
            mode = a.split("=")[1]
        elif a == "--verbose":
            verbose = True
        elif data_atual is None:
            data_atual = a
    if data_atual is None:
        data_atual = datetime.date.today().isoformat()
    build_views(data_atual, limit=limit, mode=mode, verbose=verbose)

if __name__ == "__main__":
    main()