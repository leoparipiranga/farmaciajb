"""
Módulo de Alertas usando DuckDB
Detecta anomalias em vendas, identificação de clientes e custos
"""
import streamlit as st
import duckdb
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

# =========================
# Helpers de cálculo SQL
# =========================

def calculate_expected_values(conn: duckdb.DuckDBPyConnection, 
                            nivel: str, 
                            eval_date: date,
                            window_days: int,
                            codigo: Optional[str] = None) -> pd.DataFrame:
    """
    Calcula valores esperados baseado em médias históricas
    usando o padrão de dia da semana e posição no mês
    """
    
    # SQL para criar calendário com padrões de dia
    calendar_sql = """
    WITH calendar AS (
        SELECT 
            data_date,
            EXTRACT(YEAR FROM data_date) AS ano,
            EXTRACT(MONTH FROM data_date) AS mes,
            EXTRACT(DOW FROM data_date) AS weekday,
            -- Calcula a n-ésima ocorrência do dia da semana no mês
            (EXTRACT(DAY FROM data_date) - 1) // 7 + 1 AS nth_wd
        FROM (
            SELECT UNNEST(generate_series(
                DATE '2024-01-01',
                CURRENT_DATE,
                INTERVAL '1 day'
            )::DATE[]) AS data_date
        )
    ),
    """
    
    # SQL para agregação diária - AJUSTE: usar filial_codigo
    daily_agg_sql = f"""
    daily_data AS (
        SELECT 
            data_date,
            {nivel} AS categoria,
            SUM(item_quantidade) AS qty
        FROM fact_vendas_final
        WHERE 1=1
        {f"AND filial_codigo = '{codigo}'" if codigo and codigo != 'TODAS' else ""}
        GROUP BY data_date, {nivel}
    ),
    """
    
    # SQL para calcular médias por padrão
    pattern_means_sql = f"""
    pattern_means AS (
        SELECT
            d.categoria,
            c.weekday,
            c.nth_wd,
            AVG(d.qty) AS mean_qty
        FROM daily_data d
        JOIN calendar c ON d.data_date = c.data_date
        WHERE d.data_date >= CURRENT_DATE - INTERVAL '9 months'
          AND d.data_date < DATE '{eval_date}'
        GROUP BY d.categoria, c.weekday, c.nth_wd
    ),
    weekday_means AS (
        SELECT
            d.categoria,
            c.weekday,
            AVG(d.qty) AS mean_qty
        FROM daily_data d
        JOIN calendar c ON d.data_date = c.data_date
        WHERE d.data_date >= CURRENT_DATE - INTERVAL '9 months'
          AND d.data_date < DATE '{eval_date}'
        GROUP BY d.categoria, c.weekday
    ),
    overall_means AS (
        SELECT
            categoria,
            AVG(qty) AS mean_qty
        FROM daily_data
        WHERE data_date >= CURRENT_DATE - INTERVAL '9 months'
          AND data_date < DATE '{eval_date}'
        GROUP BY categoria
    ),
    """
    
    # SQL para calcular esperado e obtido
    expected_sql = f"""
    eval_dates AS (
        SELECT UNNEST(generate_series(
            DATE '{eval_date}' - INTERVAL '{window_days - 1} days',
            DATE '{eval_date}',
            INTERVAL '1 day'
        )::DATE[]) AS eval_date
    ),
    expected_values AS (
        SELECT
            cat.categoria,
            SUM(
                COALESCE(pm.mean_qty, 
                        COALESCE(wm.mean_qty, 
                                COALESCE(om.mean_qty, 0)))
            ) AS expected
        FROM (
            SELECT DISTINCT categoria 
            FROM daily_data
        ) cat
        CROSS JOIN eval_dates ed
        JOIN calendar c ON c.data_date = ed.eval_date
        LEFT JOIN pattern_means pm 
            ON pm.categoria = cat.categoria 
            AND pm.weekday = c.weekday 
            AND pm.nth_wd = c.nth_wd
        LEFT JOIN weekday_means wm 
            ON wm.categoria = cat.categoria 
            AND wm.weekday = c.weekday
        LEFT JOIN overall_means om 
            ON om.categoria = cat.categoria
        GROUP BY cat.categoria
    ),
    observed_values AS (
        SELECT
            categoria,
            SUM(qty) AS observed
        FROM daily_data
        WHERE data_date > DATE '{eval_date}' - INTERVAL '{window_days} days'
          AND data_date <= DATE '{eval_date}'
        GROUP BY categoria
    )
    """
    
    # Query final
    final_sql = f"""
    {calendar_sql}
    {daily_agg_sql}
    {pattern_means_sql}
    {expected_sql}
    SELECT
        COALESCE(e.categoria, o.categoria) AS categoria,
        {window_days} AS janela,
        COALESCE(o.observed, 0) AS obtido,
        COALESCE(e.expected, 0) AS esperado,
        CASE 
            WHEN COALESCE(e.expected, 0) > 0 
            THEN (COALESCE(o.observed, 0) - COALESCE(e.expected, 0)) / e.expected
            ELSE 0
        END AS variacao_pct
    FROM expected_values e
    FULL OUTER JOIN observed_values o ON e.categoria = o.categoria
    WHERE e.expected IS NOT NULL OR o.observed IS NOT NULL
    ORDER BY ABS(CASE 
        WHEN COALESCE(e.expected, 0) > 0 
        THEN (COALESCE(o.observed, 0) - COALESCE(e.expected, 0)) / e.expected
        ELSE 0
    END) DESC
    """
    
    try:
        return conn.execute(final_sql).df()
    except Exception as e:
        st.error(f"Erro no SQL: {e}")
        return pd.DataFrame()

def detect_volume_anomalies_count(conn: duckdb.DuckDBPyConnection, eval_date: date) -> int:
    """
    Conta anomalias de volume para badge
    Usa parâmetros padrão: threshold 50%, janela 1 dia, níveis principais
    """
    try:
        niveis = ["classificacao_n1", "classificacao_n2", "classificacao_n3", "produto_id"]
        total_anomalias = 0
        threshold = 0.5  # 50%
        janela = 1  # 1 dia
        min_expected = 20  # Mínimo esperado
        
        for nivel in niveis:
            # Calcular valores esperados vs obtidos
            df_alerts = calculate_expected_values(conn, nivel, eval_date, janela, None)
            
            if df_alerts.empty:
                continue
            
            # Filtrar por mínimo esperado
            df_alerts = df_alerts[df_alerts['esperado'] >= min_expected].copy()
            
            # Contar anomalias (acima ou abaixo do threshold)
            anomalias = df_alerts[
                (df_alerts['variacao_pct'] >= threshold) | 
                (df_alerts['variacao_pct'] <= -threshold)
            ]
            
            total_anomalias += len(anomalias)
        
        return total_anomalias
    except Exception:
        return 0


def detect_identification_anomalies_count(conn: duckdb.DuckDBPyConnection, eval_date: date) -> int:
    """
    Conta anomalias de identificação para badge
    Conta filiais com identificação < 60% e vendedores < 60%
    """
    try:
        count = 0
        
        # Contar filiais com identificação < 60%
        query_filiais = f"""
        WITH vendas_periodo AS (
            SELECT 
                filial_codigo,
                COUNT(DISTINCT venda_id) as total_vendas,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) as vendas_identificadas
            FROM fact_vendas_final
            WHERE data_date = DATE '{eval_date}'
              AND filial_codigo IS NOT NULL
            GROUP BY filial_codigo
        )
        SELECT COUNT(*) as count
        FROM vendas_periodo
        WHERE total_vendas > 0 
          AND (vendas_identificadas * 100.0 / total_vendas) < 60
        """
        
        result = conn.execute(query_filiais).fetchone()
        if result:
            count += result[0]
        
        # Contar vendedores com identificação < 60% (mín. 20 vendas)
        query_vendedores = f"""
        WITH vendas_vendedor AS (
            SELECT 
                vendedor_nome,
                COUNT(DISTINCT venda_id) as total_vendas,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) as vendas_identificadas
            FROM fact_vendas_final
            WHERE data_date = DATE '{eval_date}'
              AND vendedor_nome IS NOT NULL
            GROUP BY vendedor_nome
            HAVING COUNT(DISTINCT venda_id) >= 20
        )
        SELECT COUNT(*) as count
        FROM vendas_vendedor
        WHERE (vendas_identificadas * 100.0 / total_vendas) < 60
        """
        
        result = conn.execute(query_vendedores).fetchone()
        if result:
            count += result[0]
        
        return count
    except Exception:
        return 0


def detect_cmv_anomalies_count(conn: duckdb.DuckDBPyConnection, eval_date: date) -> int:
    """
    Conta anomalias de CMV para badge
    Conta filiais com CMV > 75%
    """
    try:
        # Contar filiais com CMV > 75%
        query_cmv = f"""
        WITH cmv_periodo AS (
            SELECT 
                filial_codigo,
                SUM(customediototal) as custo_total,
                SUM(item_valortotal) as venda_total
            FROM fact_vendas_final
            WHERE data_date = DATE '{eval_date}'
              AND customediototal IS NOT NULL
              AND item_valortotal IS NOT NULL
              AND item_valortotal > 0
              AND filial_codigo IS NOT NULL
            GROUP BY filial_codigo
        )
        SELECT COUNT(*) as count
        FROM cmv_periodo
        WHERE venda_total > 0 
          AND (custo_total / venda_total) > 0.75
        """
        
        result = conn.execute(query_cmv).fetchone()
        return result[0] if result else 0
    except Exception:
        return 0