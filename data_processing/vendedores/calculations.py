"""
Cálculos e métricas para análise de vendedores usando DuckDB
"""
from datetime import date, timedelta
from core.database import duck_query
import pandas as pd

def _escape(v: str) -> str:
    return str(v).replace("'", "''")

def _bounds_mes_atual(data_ref: date | None):
    """Define início e fim do mês atual (D-1 por padrão)"""
    if data_ref is None:
        data_ref = pd.Timestamp("today").date() - pd.Timedelta(days=1)
    data_ref = pd.Timestamp(data_ref).date()
    data_ini = pd.Timestamp(data_ref).replace(day=1).date()
    return data_ini, data_ref

def _cond_filial(filial_codigo: str | None) -> str:
    """Condição SQL para filtrar por filial"""
    if filial_codigo and str(filial_codigo).strip().lower() != "todas as filiais":
        return f"AND CAST(filial_codigo AS VARCHAR) = '{_escape(filial_codigo)}'"
    return ""

def _cond_vendedor(vendedor_nome: str | None) -> str:
    """Condição SQL para filtrar por vendedor"""
    if vendedor_nome and str(vendedor_nome).strip().lower() != "todos os vendedores":
        return f"AND TRIM(vendedor_nome) = '{_escape(vendedor_nome)}'"
    return ""

# ========================================
# FUNÇÕES PARA GAUGES - MÊS ATUAL
# ========================================

def ticket_medio_vendedor_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> float:
    """
    Calcula ticket médio do vendedor no mês atual
    ticket_medio = SUM(item_valortotal) / COUNT(DISTINCT venda_id)
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        SELECT 
            COALESCE(SUM(item_valortotal), 0) / NULLIF(COUNT(DISTINCT venda_id), 0) AS ticket_medio
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["ticket_medio"] if len(df) and df.iloc[0]["ticket_medio"] is not None else 0.0)

def itens_por_nota_vendedor_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> float:
    """
    Calcula itens por nota do vendedor no mês atual
    itens_por_nota = SUM(item_quantidade) / COUNT(DISTINCT venda_id)
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        SELECT 
            COALESCE(SUM(item_quantidade), 0) / NULLIF(COUNT(DISTINCT venda_id), 0) AS itens_por_nota
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["itens_por_nota"] if len(df) and df.iloc[0]["itens_por_nota"] is not None else 0.0)

def venda_total_vendedor_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> float:
    """
    Calcula venda total do vendedor no mês atual
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS venda_total
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
    """
    df = duck_query(sql)
    return float(df.iloc[0]["venda_total"] if len(df) else 0.0)

def percentuais_classificacao_vendedor_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> dict:
    """
    Calcula percentuais por classificação N1 do vendedor no mês atual
    Retorna: {'INDICAÇÃO': 25.5, 'PRESCRIÇÃO': 45.2, 'SBB': 15.0, 'VAREJO': 14.3}
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    # Primeiro obter total geral
    sql_total = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS total_geral
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
    """
    df_total = duck_query(sql_total)
    total_geral = float(df_total.iloc[0]["total_geral"] if len(df_total) else 0.0)
    
    if total_geral == 0:
        return {'INDICAÇÃO': 0.0, 'PRESCRIÇÃO': 0.0, 'SBB': 0.0, 'VAREJO': 0.0}
    
    # Agora obter por classificação
    sql = f"""
        SELECT 
            UPPER(TRIM(COALESCE(classificacao_n1, 'OUTROS'))) AS classificacao,
            SUM(item_valortotal) AS valor_categoria
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
          AND UPPER(TRIM(COALESCE(classificacao_n1, ''))) IN ('INDICAÇÃO', 'PRESCRIÇÃO', 'SBB', 'VAREJO')
        GROUP BY 1
    """
    df = duck_query(sql)
    
    # Converter para dicionário com percentuais
    percentuais = {'INDICAÇÃO': 0.0, 'PRESCRIÇÃO': 0.0, 'SBB': 0.0, 'VAREJO': 0.0}
    
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            classificacao = row['classificacao']
            valor = float(row['valor_categoria'])
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0.0
            
            if classificacao in percentuais:
                percentuais[classificacao] = percentual
    
    return percentuais

def kpis_vendedor_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> dict:
    """
    Retorna todos os KPIs do vendedor para o mês atual em um único dicionário
    """
    ticket_medio = ticket_medio_vendedor_mes_atual(filial_codigo, vendedor_nome, data_ref)
    itens_por_nota = itens_por_nota_vendedor_mes_atual(filial_codigo, vendedor_nome, data_ref)
    venda_total = venda_total_vendedor_mes_atual(filial_codigo, vendedor_nome, data_ref)
    percentuais = percentuais_classificacao_vendedor_mes_atual(filial_codigo, vendedor_nome, data_ref)
    
    return {
        'ticket_medio': ticket_medio,
        'itens_por_nota': itens_por_nota,
        'venda_total': venda_total,
        'percentuais_classificacao': percentuais
    }

# ========================================
# FUNÇÕES PARA KPIs DO DIA ANTERIOR
# ========================================

def kpis_vendedor_dia_anterior(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> dict:
    """
    Calcula KPIs do vendedor para o dia anterior (D-1)
    Retorna: {'num_vendas': int, 'vitaminas_vendidas': int, 'vendas_identificadas_perc': float, 'cmv': float, 'total_venda': float}
    """
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    
    data_ref_iso = data_ref.isoformat()
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        SELECT 
            COUNT(DISTINCT venda_id) AS num_vendas,
            COALESCE(SUM(item_valortotal), 0) AS total_venda,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' 
                              THEN item_quantidade ELSE 0 END), 0) AS vitaminas_vendidas,
            COALESCE(SUM(customediototal), 0) AS total_custo,
            -- Contagem de vendas identificadas vs total
            COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_count,
            COUNT(DISTINCT venda_id) AS total_vendas_count
        FROM fact_vendas_final
        WHERE data_date = DATE '{data_ref_iso}'
        {cond_filial}
        {cond_vendedor}
    """
    df = duck_query(sql)
    
    if df is None or df.empty:
        return {
            'num_vendas': 0,
            'vitaminas_vendidas': 0,
            'vendas_identificadas_perc': 0.0,
            'cmv': 0.0,
            'total_venda': 0.0
        }
    
    row = df.iloc[0]
    total_venda = float(row['total_venda'])
    total_custo = float(row['total_custo'])
    cmv = (total_custo / total_venda * 100) if total_venda > 0 else 0.0
    
    # Calcular percentual de vendas identificadas
    vendas_identificadas_count = int(row['vendas_identificadas_count'])
    total_vendas_count = int(row['total_vendas_count'])
    vendas_identificadas_perc = (vendas_identificadas_count / total_vendas_count * 100) if total_vendas_count > 0 else 0.0
    
    return {
        'num_vendas': int(row['num_vendas']),
        'vitaminas_vendidas': int(row['vitaminas_vendidas']),
        'vendas_identificadas_perc': vendas_identificadas_perc,
        'cmv': cmv,
        'total_venda': total_venda
    }

def calcular_kpis_vendedores_comparativo_duck(filial_codigo: str | None = None, vendedores: list[str] = [], data_ref: date | None = None) -> dict:
    """
    Calcula KPIs agregados para uma lista de vendedores (modo comparativo).
    Adaptado de calcular_kpis_vendedor para DuckDB.
    """
    if not vendedores:
        return {
            'venda_acumulada': 0.0,
            'num_vendas': 0,
            'ticket_medio': 0.0,
            'itens_por_nota': 0.0,
            'num_vitaminas': 0,
            'taxa_conversao_vitaminas': 0.0,
            'desconto_medio': 0.0,
            'vendas_identificadas_perc': 0.0
        }
    
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    vendedores_str = "', '".join(_escape(v) for v in vendedores)
    cond_vendedores = f"AND TRIM(vendedor_nome) IN ('{vendedores_str}')"
    
    sql = f"""
        SELECT 
            SUM(item_valortotal) AS venda_acumulada,
            COUNT(DISTINCT venda_id) AS num_vendas,
            SUM(item_quantidade) AS total_itens,
            SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END) AS num_vitaminas,
            COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas,
            COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas,
            SUM(item_valordesconto) AS desconto_total,
            SUM(customediototal) AS custo_total
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedores}
          AND vendedor_nome IS NOT NULL 
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
    """
    df = duck_query(sql)
    if df is None or df.empty:
        return {
            'venda_acumulada': 0.0,
            'num_vendas': 0,
            'ticket_medio': 0.0,
            'itens_por_nota': 0.0,
            'num_vitaminas': 0,
            'taxa_conversao_vitaminas': 0.0,
            'desconto_medio': 0.0,
            'vendas_identificadas_perc': 0.0
        }
    
    row = df.iloc[0]
    venda_acumulada = row['venda_acumulada'] or 0.0
    num_vendas = row['num_vendas'] or 0
    total_itens = row['total_itens'] or 0
    num_vitaminas = row['num_vitaminas'] or 0
    vendas_com_vitaminas = row['vendas_com_vitaminas'] or 0
    vendas_identificadas = row['vendas_identificadas'] or 0
    desconto_total = row['desconto_total'] or 0.0
    custo_total = row['custo_total'] or 0.0
    
    ticket_medio = (venda_acumulada / num_vendas) if num_vendas > 0 else 0.0
    itens_por_nota = (total_itens / num_vendas) if num_vendas > 0 else 0.0
    taxa_conversao_vitaminas = (vendas_com_vitaminas / num_vendas * 100) if num_vendas > 0 else 0.0
    vendas_identificadas_perc = (vendas_identificadas / num_vendas * 100) if num_vendas > 0 else 0.0
    desconto_medio = (desconto_total / (venda_acumulada + desconto_total) * 100) if (venda_acumulada + desconto_total) > 0 else 0.0
    
    return {
        'venda_acumulada': venda_acumulada,
        'num_vendas': num_vendas,
        'ticket_medio': ticket_medio,
        'itens_por_nota': itens_por_nota,
        'num_vitaminas': num_vitaminas,
        'taxa_conversao_vitaminas': taxa_conversao_vitaminas,
        'desconto_medio': desconto_medio,
        'vendas_identificadas_perc': vendas_identificadas_perc
    }