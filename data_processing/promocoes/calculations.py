"""
Consultas de dados para análise de promoções usando DuckDB
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core.database import duck_query
"""
Cálculos e métricas para análise de promoções
"""
import numpy as np


def calcular_metricas_promocao(vendas_por_periodo: dict, promocao_ids: list,
                             data_inicio_promo, data_fim_promo, dias_promocao: int, 
                             selected_filial: str) -> dict:
    """
    Calcula todas as métricas necessárias para análise de promoção
    
    Returns:
        dict: Dicionário com todas as métricas calculadas
    """
    # Preparar dados dos períodos
    periodos_ordenados = ['Antes 4', 'Antes 3', 'Antes 2', 'Antes 1', 'Promoção', 'Após 1', 'Após 2', 'Após 3', 'Após 4']
    periodos_com_dados = [p for p in periodos_ordenados if p in vendas_por_periodo and vendas_por_periodo[p]['quantidade'] > 0]
    
    if not periodos_com_dados:
        return {}
    
    # Calcular médias (excluindo período da promoção)
    periodos_sem_promocao = [p for p in periodos_com_dados if p != 'Promoção']
    media_qtd_sem = np.mean([vendas_por_periodo[p]['quantidade'] for p in periodos_sem_promocao]) if periodos_sem_promocao else 0
    media_valor_sem = np.mean([vendas_por_periodo[p]['valor'] for p in periodos_sem_promocao]) if periodos_sem_promocao else 0
    
    # Médias diárias dos produtos em promoção
    media_qtd_promocao = vendas_por_periodo.get('Promoção', {}).get('quantidade', 0) / dias_promocao
    media_qtd_sem_diaria = media_qtd_sem / dias_promocao if media_qtd_sem > 0 else 0
    media_valor_promocao = vendas_por_periodo.get('Promoção', {}).get('valor', 0) / dias_promocao
    media_valor_sem_diaria = media_valor_sem / dias_promocao if media_valor_sem > 0 else 0
    
    # Calcular totais da loja
    totais_loja = calcular_totais_loja_durante_fora_duck(
        data_inicio_promo.strftime('%Y-%m-%d'),
        data_fim_promo.strftime('%Y-%m-%d'),
        dias_promocao,
        selected_filial
    )
    
    totais_qtd_loja = calcular_totais_loja_qtd_durante_fora_duck(
        data_inicio_promo.strftime('%Y-%m-%d'),
        data_fim_promo.strftime('%Y-%m-%d'),
        dias_promocao,
        selected_filial
    )
    
    # Processar totais da loja
    durante_loja_total = float(totais_loja.get('Promoção', 0))
    fora_periodos = [k for k in totais_loja.keys() if k != 'Promoção']
    fora_loja_total = sum(float(totais_loja.get(k, 0)) for k in fora_periodos)
    fora_period_count = len(fora_periodos)
    
    # Médias da loja total
    media_valor_promocao_total = durante_loja_total / dias_promocao if dias_promocao > 0 else 0
    media_valor_sem_total = (fora_loja_total / fora_period_count) if fora_period_count > 0 else 0
    media_valor_sem_diaria_total = media_valor_sem_total / dias_promocao if dias_promocao > 0 else 0
    
    # Totais quantidade
    durante_qtd_total = float(totais_qtd_loja.get('Promoção', 0))
    fora_qtd_total = sum(float(totais_qtd_loja.get(k, 0)) for k in (k for k in totais_qtd_loja.keys() if k != 'Promoção'))
    fora_qtd_period_count = len([k for k in totais_qtd_loja.keys() if k != 'Promoção'])
    
    media_qtd_promocao_total = durante_qtd_total / dias_promocao if dias_promocao > 0 else 0
    media_qtd_sem_total = (fora_qtd_total / fora_qtd_period_count) if fora_qtd_period_count > 0 else 0
    media_qtd_sem_diaria_total = media_qtd_sem_total / dias_promocao if dias_promocao > 0 else 0
    
    # Calcular variações percentuais
    variacao_valor_parcial = (media_valor_promocao / media_valor_sem_diaria - 1) * 100 if media_valor_promocao > 0 else 0
    variacao_qtd_parcial = (media_qtd_promocao / media_qtd_sem_diaria - 1) * 100 if media_qtd_promocao > 0 else 0
    variacao_valor_total = (media_valor_promocao_total / media_valor_sem_diaria_total - 1) * 100 if media_valor_promocao_total > 0 else 0
    variacao_qtd_total = (media_qtd_promocao_total / media_qtd_sem_diaria_total - 1) * 100 if media_qtd_promocao_total > 0 else 0
    
    return {
        'media_qtd_sem_diaria': media_qtd_sem_diaria,
        'media_valor_sem_diaria': media_valor_sem_diaria,
        'media_qtd_promocao': media_qtd_promocao,
        'media_valor_promocao': media_valor_promocao,
        'media_valor_promocao_total': media_valor_promocao_total,
        'media_valor_sem_diaria_total': media_valor_sem_diaria_total,
        'media_qtd_promocao_total': media_qtd_promocao_total,
        'media_qtd_sem_diaria_total': media_qtd_sem_diaria_total,
        'variacao_valor_parcial': variacao_valor_parcial,
        'variacao_qtd_parcial': variacao_qtd_parcial,
        'variacao_valor_total': variacao_valor_total,
        'variacao_qtd_total': variacao_qtd_total
    }

def preparar_dados_visualizacao(vendas_por_periodo: dict, data_inicio_promo, 
                              data_fim_promo, dias_promocao: int) -> dict:
    """Prepara dados para visualização dos gráficos"""
    periodos_ordenados = ['Antes 4', 'Antes 3', 'Antes 2', 'Antes 1', 'Promoção', 'Após 1', 'Após 2', 'Após 3', 'Após 4']
    periodos_com_dados = [p for p in periodos_ordenados if p in vendas_por_periodo and vendas_por_periodo[p]['quantidade'] > 0]
    
    if not periodos_com_dados:
        return {}
    
    # Extrair dados para gráficos
    quantidades = [vendas_por_periodo[p]['quantidade'] for p in periodos_com_dados]
    valores = [vendas_por_periodo[p]['valor'] for p in periodos_com_dados]
    resultados = [vendas_por_periodo[p]['resultado'] for p in periodos_com_dados]
    
    # Gerar labels das datas
    from datetime import timedelta
    labels = []
    for periodo in periodos_com_dados:
        if periodo == 'Promoção':
            labels.append(f"{data_inicio_promo.strftime('%d/%m')} a {data_fim_promo.strftime('%d/%m')}")
        else:
            if 'Antes' in periodo:
                num = int(periodo.split()[-1])
                inicio = data_inicio_promo - timedelta(days=num * dias_promocao)
                fim = data_inicio_promo - timedelta(days=(num-1) * dias_promocao + 1)
            elif 'Após' in periodo:
                num = int(periodo.split()[-1])
                inicio = data_fim_promo + timedelta(days=(num-1) * dias_promocao + 1)
                fim = data_fim_promo + timedelta(days=num * dias_promocao)
            else:
                inicio = data_inicio_promo
                fim = data_fim_promo
            labels.append(f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')}")
    
    return {
        'periodos_com_dados': periodos_com_dados,
        'quantidades': quantidades,
        'valores': valores,
        'resultados': resultados,
        'labels': labels
    }

def calcular_totais_loja_durante_fora_duck(data_inicio_promo: str, data_fim_promo: str, dias_promocao: int, filial_codigo: str | None = None) -> dict:
    """
    Retorna um dict com totais (somatório item_valortotal) por período:
    - 'Promoção' -> total durante a promoção
    - 'Antes 1'..'Antes 4', 'Após 1'..'Após 4' -> totais para cada período (pode faltar alguns)
    Também aceita filtro por filial (filial_codigo str) ou None para todas as filiais.
    """
    cond_filial = f"AND filial_codigo = '{filial_codigo}'" if filial_codigo and filial_codigo != "Todas as Filiais" else ""

    # construir os períodos iguais aos usados no calcular_vendas_por_periodo_duck
    data_inicio_dt = datetime.strptime(data_inicio_promo, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim_promo, '%Y-%m-%d')

    parts = []
    # Antes 4..1
    for i in range(4, 0, -1):
        inicio_antes = (data_inicio_dt - timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        fim_antes = (data_inicio_dt - timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        parts.append(f"WHEN data_date BETWEEN DATE '{inicio_antes}' AND DATE '{fim_antes}' THEN 'Antes {i}'")

    # Promoção
    parts.append(f"WHEN data_date BETWEEN DATE '{data_inicio_promo}' AND DATE '{data_fim_promo}' THEN 'Promoção'")

    # Após 1..4
    for i in range(1, 5):
        inicio_apos = (data_fim_dt + timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        fim_apos = (data_fim_dt + timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        parts.append(f"WHEN data_date BETWEEN DATE '{inicio_apos}' AND DATE '{fim_apos}' THEN 'Após {i}'")

    case_sql = "CASE " + " ".join(parts) + " ELSE 'Fora dos períodos' END"

    sql = f"""
        SELECT periodo, SUM(item_valortotal) AS total_valor
        FROM (
            SELECT {case_sql} AS periodo, item_valortotal, data_date
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{(data_inicio_dt - timedelta(days=4*dias_promocao)).strftime('%Y-%m-%d')}' AND DATE '{(data_fim_dt + timedelta(days=4*dias_promocao)).strftime('%Y-%m-%d')}'
              {cond_filial}
        ) t
        GROUP BY periodo
        HAVING periodo != 'Fora dos períodos'
    """

    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return {}
        resultado = { row['periodo']: float(row['total_valor'] or 0) for _, row in df.iterrows() }
        return resultado
    except Exception as e:
        st.error(f"Erro ao calcular totais da loja durante/fora promoção: {e}")
        return {}

def calcular_totais_loja_qtd_durante_fora_duck(data_inicio_promo: str, data_fim_promo: str, dias_promocao: int, filial_codigo: str | None = None) -> dict:
    """
    Retorna um dict com totais de quantidade (SUM(item_quantidade)) por período:
    - 'Promoção' -> total durante a promoção
    - 'Antes 1'..'Antes 4', 'Após 1'..'Após 4' -> totais para cada período (pode faltar alguns)
    Aceita filtro por filial (filial_codigo str) ou None para todas as filiais.
    """
    cond_filial = f"AND filial_codigo = '{filial_codigo}'" if filial_codigo and filial_codigo != "Todas as Filiais" else ""

    data_inicio_dt = datetime.strptime(data_inicio_promo, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim_promo, '%Y-%m-%d')

    parts = []
    # Antes 4..1
    for i in range(4, 0, -1):
        inicio_antes = (data_inicio_dt - timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        fim_antes = (data_inicio_dt - timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        parts.append(f"WHEN data_date BETWEEN DATE '{inicio_antes}' AND DATE '{fim_antes}' THEN 'Antes {i}'")

    # Promoção
    parts.append(f"WHEN data_date BETWEEN DATE '{data_inicio_promo}' AND DATE '{data_fim_promo}' THEN 'Promoção'")

    # Após 1..4
    for i in range(1, 5):
        inicio_apos = (data_fim_dt + timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        fim_apos = (data_fim_dt + timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        parts.append(f"WHEN data_date BETWEEN DATE '{inicio_apos}' AND DATE '{fim_apos}' THEN 'Após {i}'")

    case_sql = "CASE " + " ".join(parts) + " ELSE 'Fora dos períodos' END"

    # limitar a janela de datas (promoção +/- 4 períodos)
    window_start = (data_inicio_dt - timedelta(days=4 * dias_promocao)).strftime('%Y-%m-%d')
    window_end = (data_fim_dt + timedelta(days=4 * dias_promocao)).strftime('%Y-%m-%d')

    sql = f"""
        SELECT periodo, SUM(item_quantidade) AS total_qtd
        FROM (
            SELECT {case_sql} AS periodo, item_quantidade, data_date
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{window_start}' AND DATE '{window_end}'
              {cond_filial}
        ) t
        GROUP BY periodo
        HAVING periodo != 'Fora dos períodos'
    """

    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return {}
        resultado = { row['periodo']: float(row['total_qtd'] or 0) for _, row in df.iterrows() }
        return resultado
    except Exception as e:
        st.error(f"Erro ao calcular totais de quantidade da loja durante/fora promoção: {e}")
        return {}
