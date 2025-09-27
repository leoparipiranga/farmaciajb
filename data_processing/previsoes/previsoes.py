"""
Cálculos de previsões e projeções de vendas
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from core.database import duck_query

def calcular_previsao_mes_hibrido_sql(filial_codigo: str | None = None, ref_date: date | None = None) -> dict:
    """
    Previsão híbrida (quantidade+valor) para o mês corrente via SQL (DuckDB).
    - Projeção por Valor: média diária de valor × dias do mês
    - Projeção por Quantidade: média diária de quantidade × dias do mês × ticket médio atual
    - Peso do valor aumenta conforme avança o mês (35% -> 85%)
    Retorna: {'previsto': float|None, 'low': float|None, 'high': float|None, 'dia': int|None}
    Padrão usa D-1 como data de referência.
    """
    ref = ref_date or (date.today() - timedelta(days=1))
    ref_iso = ref.isoformat()

    cond_loja = ""
    if filial_codigo and filial_codigo != "Todas as Filiais":
        cond_loja = f"AND f.filial_codigo = '{filial_codigo}'"

    sql = f"""
    WITH params AS (
        SELECT 
            DATE '{ref_iso}' AS ref_date,
            DATE_TRUNC('month', DATE '{ref_iso}') AS month_start,
            DATE_TRUNC('month', DATE '{ref_iso}') + INTERVAL 1 MONTH AS next_month_start
    ),
    dims AS (
        SELECT 
            ref_date,
            month_start,
            next_month_start,
            DATE_DIFF('day', month_start, next_month_start) AS days_in_month,
            EXTRACT(day FROM ref_date)::INTEGER AS d_hoje
        FROM params
    ),
    base AS (
        SELECT f.data_date::DATE AS data_date,
               SUM(f.item_valortotal) AS valor,
               SUM(f.item_quantidade) AS qtd
        FROM fact_vendas_final f, dims d
        WHERE f.data_date BETWEEN d.month_start AND (d.next_month_start - INTERVAL 1 DAY)
          {cond_loja}
        GROUP BY 1
    ),
    per_day AS (
        SELECT EXTRACT(day FROM data_date)::INTEGER AS dia,
               SUM(valor) AS valor,
               SUM(qtd) AS qtd
        FROM base
        GROUP BY 1
    ),
    d_calc AS (
        SELECT d_hoje,
               COALESCE((SELECT MAX(dia) FROM per_day), 0) AS d_max,
               days_in_month
        FROM dims
    ),
    acc AS (
        SELECT 
            LEAST(d_hoje, d_max) AS d,
            days_in_month,
            COALESCE((SELECT SUM(valor) FROM per_day WHERE dia <= LEAST(d_hoje, d_max)), 0) AS valor_acum,
            COALESCE((SELECT SUM(qtd)   FROM per_day WHERE dia <= LEAST(d_hoje, d_max)), 0) AS qtd_acum
        FROM d_calc
    ),
    proj AS (
        SELECT
            d,
            days_in_month,
            valor_acum,
            qtd_acum,
            CASE WHEN d <= 0 OR valor_acum <= 0 THEN NULL
                 ELSE (valor_acum::DOUBLE / d) * days_in_month END AS proj_valor,
            CASE 
                WHEN d <= 0 THEN NULL
                WHEN qtd_acum > 0 THEN (qtd_acum::DOUBLE / d) * days_in_month * (valor_acum::DOUBLE / NULLIF(qtd_acum::DOUBLE,0))
                ELSE (valor_acum::DOUBLE / d) * days_in_month
            END AS proj_qtd
        FROM acc
    ),
    peso AS (
        SELECT
            d,
            days_in_month,
            valor_acum,
            qtd_acum,
            proj_valor,
            proj_qtd,
            LEAST(0.85, 0.35 + 0.65 * (d::DOUBLE / NULLIF(days_in_month::DOUBLE,0))) AS w_val
        FROM proj
    ),
    final AS (
        SELECT
            d,
            CASE 
              WHEN proj_valor IS NULL OR proj_qtd IS NULL THEN NULL
              ELSE w_val * proj_valor + (1.0 - w_val) * proj_qtd
            END AS previsto
        FROM peso
    )
    SELECT 
        d,
        previsto,
        CASE WHEN previsto IS NULL THEN NULL ELSE previsto * 0.97 END AS low,
        CASE WHEN previsto IS NULL THEN NULL ELSE previsto * 1.03 END AS high
    FROM final
    """
    try:
        df = duck_query(sql)  # <-- usa a conexão do warehouse
    except Exception as e:
        st.error(f"Falha ao consultar DuckDB: {e}")
        return {'previsto': None, 'low': None, 'high': None, 'dia': None}

    if df is None or df.empty:
        return {'previsto': None, 'low': None, 'high': None, 'dia': None}

    row = df.iloc[0].to_dict()
    d = int(row['d']) if pd.notna(row.get('d')) else None
    previsto = float(row['previsto']) if pd.notna(row.get('previsto')) else None
    low = float(row['low']) if pd.notna(row.get('low')) else None
    high = float(row['high']) if pd.notna(row.get('high')) else None
    return {'previsto': previsto, 'low': low, 'high': high, 'dia': d}