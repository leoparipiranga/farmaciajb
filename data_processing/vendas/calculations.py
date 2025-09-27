import streamlit as st
import pandas as pd
from datetime import date, timedelta
from core.database import duck_query
from utils.helpers import _escape, _bounds_mes_atual, _cond_filial

def venda_acumulada_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Soma de item_valortotal no mês corrente (MTD). data_ref padrão = D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS venda_acumulada
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["venda_acumulada"] if len(df) else 0.0)

def venda_dezena1_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Soma de item_valortotal de 1 a 10 no mês da data_ref (padrão D-1).
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    d1_ini = data_ini
    d1_fim = min((pd.Timestamp(data_ini).replace(day=10)).date(), data_fim)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS venda
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{d1_ini}' AND DATE '{d1_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["venda"] if len(df) else 0.0)

def venda_dezena2_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Soma de item_valortotal de 11 a 20 no mês da data_ref (padrão D-1).
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    d2_ini = (pd.Timestamp(data_ini).replace(day=11)).date()
    d2_fim = min((pd.Timestamp(data_ini).replace(day=20)).date(), data_fim)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS venda
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{d2_ini}' AND DATE '{d2_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["venda"] if len(df) else 0.0)

def venda_dezena3_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Soma de item_valortotal de 21 ao D-1 (ou fim do mês, se D-1 passou).
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    d3_ini = (pd.Timestamp(data_ini).replace(day=21)).date()
    d3_fim = data_fim
    if d3_ini > d3_fim:
        return 0.0
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS venda
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{d3_ini}' AND DATE '{d3_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["venda"] if len(df) else 0.0)

def cmv_percent_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    CMV (%) = 100 * SUM(customediototal) / NULLIF(SUM(item_valortotal), 0)
    Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT 
            100.0 * COALESCE(SUM(customediototal), 0) 
            / NULLIF(COALESCE(SUM(item_valortotal), 0), 0) AS cmv_perc
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["cmv_perc"] if len(df) else 0.0)

def desconto_percent_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Desconto Médio (%) = 100 * SUM(item_valordesconto) / NULLIF(SUM(item_valortotal + item_valordesconto), 0)
    Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT 
            100.0 * COALESCE(SUM(item_valordesconto), 0)
            / NULLIF(COALESCE(SUM(item_valortotal + COALESCE(item_valordesconto,0)), 0), 0) AS desconto_perc
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["desconto_perc"] if len(df) else 0.0)


def conversao_vitaminas_percent_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Conversão Vitaminas (razão) = total de vendas / vendas com vitaminas (DISTINCT venda_id).
    Vitaminas detectadas por classificacao_n2 = 'VITAMINAS'. Padrão D-1.
    Retorna número (não é %). Se não houver vendas com vitaminas, retorna 0.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    cond_vit = "AND UPPER(COALESCE(classificacao_n2, '')) = 'VITAMINAS'"

    sql = f"""
        WITH tot AS (
            SELECT COUNT(DISTINCT venda_id) AS n_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
            {cond_loja}
        ),
        vit AS (
            SELECT COUNT(DISTINCT venda_id) AS n_vit
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
            {cond_loja}
            {cond_vit}
        )
        SELECT 
            CASE WHEN vit.n_vit = 0 THEN 0.0
                 ELSE CAST(tot.n_total AS DOUBLE) / vit.n_vit
            END AS conv_ratio
        FROM tot CROSS JOIN vit
    """
    df = duck_query(sql)
    return float(df.iloc[0]["conv_ratio"] if len(df) else 0.0)

def vendas_identificadas_percent_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Vendas Identificadas (%) = 100 * vendas_com_pessoa / vendas_totais (DISTINCT venda_id).
    Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        WITH tot AS (
            SELECT COUNT(DISTINCT venda_id) AS n_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
            {cond_loja}
        ),
        ident AS (
            SELECT COUNT(DISTINCT venda_id) AS n_ident
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
            {cond_loja}
              AND venda_pessoaid IS NOT NULL
        )
        SELECT 
            CASE WHEN tot.n_total = 0 THEN 0.0
                 ELSE 100.0 * ident.n_ident / tot.n_total
            END AS ident_perc
        FROM tot CROSS JOIN ident
    """
    df = duck_query(sql)
    return float(df.iloc[0]["ident_perc"] if len(df) else 0.0)

def num_vendas_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> int:
    """
    Número de Vendas (DISTINCT venda_id) no mês corrente. Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COUNT(DISTINCT venda_id) AS num_vendas
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return int(df.iloc[0]["num_vendas"] if len(df) else 0)

def itens_por_nota_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Itens por Nota = SUM(item_quantidade) / COUNT(DISTINCT venda_id). Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT 
            CASE WHEN COUNT(DISTINCT venda_id)=0 THEN 0.0
                 ELSE CAST(COALESCE(SUM(item_quantidade),0) AS DOUBLE) / COUNT(DISTINCT venda_id)
            END AS itens_por_nota
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_loja}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["itens_por_nota"] if len(df) else 0.0)

def vitaminas_vendidas_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> float:
    """
    Vitaminas Vendidas = SUM(item_quantidade) onde classificacao_n2 = 'VITAMINAS'. Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        SELECT COALESCE(SUM(item_quantidade), 0) AS qtd_vitaminas
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
          {cond_loja}
          AND UPPER(COALESCE(classificacao_n2, '')) = 'VITAMINAS'
    """
    df = duck_query(sql)
    return float(df.iloc[0]["qtd_vitaminas"] if len(df) else 0.0)

def vendas_por_classificacao_n1_mes_atual(filial_codigo: str | None = None, data_ref: date | None = None) -> pd.DataFrame:
    """
    Retorna o acumulado do mês (MTD) por classificacao_n1, com percentual sobre o total.
    Colunas: classificacao_n1, venda_total, perc_total.
    Padrão D-1.
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_loja = _cond_filial(filial_codigo)
    sql = f"""
        WITH base AS (
            SELECT 
                UPPER(COALESCE(classificacao_n1, 'OUTROS')) AS classificacao_n1,
                SUM(item_valortotal) AS venda_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
            {cond_loja}
            GROUP BY 1
        ),
        tot AS (
            SELECT COALESCE(SUM(venda_total), 0) AS venda_total_acumulada
            FROM base
        )
        SELECT 
            b.classificacao_n1,
            b.venda_total,
            CASE WHEN t.venda_total_acumulada = 0 THEN 0.0
                 ELSE b.venda_total / t.venda_total_acumulada
            END AS perc_total
        FROM base b
        CROSS JOIN tot t
        ORDER BY b.classificacao_n1
    """
    return duck_query(sql)