"""
Consultas de dados para análise de promoções usando DuckDB
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core.database import duck_query

def get_promocoes_periodo_duck(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """
    Busca promoções ativas em um período específico via SQL.
    """
    sql = f"""
        SELECT id, nome, datahorainicial, datahorafinal, status
        FROM cadernooferta
        WHERE status = 'A'
          AND datahorainicial IS NOT NULL
          AND datahorafinal IS NOT NULL
          AND datahorafinal >= DATE '{data_inicio}'
          AND datahorainicial <= DATE '{data_fim}'
        ORDER BY datahorainicial DESC
    """
    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar promoções: {e}")
        return pd.DataFrame()

def get_vendas_promocao_duck(promocao_ids: list) -> pd.DataFrame:
    """
    Busca vendas durante a promoção para obter produtos únicos.
    """
    if not promocao_ids:
        return pd.DataFrame()
    
    ids_str = "', '".join(str(id) for id in promocao_ids)
    sql = f"""
        SELECT DISTINCT 
            item_cadernoofertaid,
            item_embalagemid,
            filial_codigo,
            embalagem_descricao,
            classificacao_n1
        FROM fact_vendas_final
        WHERE item_cadernoofertaid IN ('{ids_str}')
          AND item_cadernoofertaid IS NOT NULL
    """
    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar vendas da promoção: {e}")
        return pd.DataFrame()

def get_vendas_periodo_produtos_duck(item_embalagemids: list, data_inicio: str, data_fim: str, filial_codigo: str = None) -> pd.DataFrame:
    """
    Busca vendas de produtos específicos em um período, com filtro opcional de filial.
    """
    if not item_embalagemids:
        return pd.DataFrame()
    
    ids_str = "', '".join(str(id) for id in item_embalagemids)
    cond_filial = f"AND filial_codigo = '{filial_codigo}'" if filial_codigo and filial_codigo != "Todas as Filiais" else ""
    
    sql = f"""
        SELECT 
            data_date,
            item_embalagemid,
            embalagem_descricao,
            classificacao_n1,
            item_quantidade,
            item_valortotal,
            customediototal,
            filial_codigo
        FROM fact_vendas_final
        WHERE item_embalagemid IN ('{ids_str}')
          AND data_date BETWEEN DATE '{data_inicio}' AND DATE '{data_fim}'
          {cond_filial}
    """
    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar vendas por período: {e}")
        return pd.DataFrame()

def calcular_vendas_por_periodo_duck(item_embalagemids: list, promocao_ids: list, 
                                   data_inicio_promo: str, data_fim_promo: str, 
                                   dias_promocao: int, filial_codigo: str = None) -> dict:
    """
    Calcula vendas agrupadas por períodos (antes, durante, depois da promoção) via SQL.
    """
    if not item_embalagemids:
        return {}
    
    ids_str = "', '".join(str(id) for id in item_embalagemids)
    cond_filial = f"AND filial_codigo = '{filial_codigo}'" if filial_codigo and filial_codigo != "Todas as Filiais" else ""
    
    # Calcular datas dos períodos
    data_inicio_dt = datetime.strptime(data_inicio_promo, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim_promo, '%Y-%m-%d')
    
    # Períodos antes (4 períodos)
    periodos_sql_parts = []
    periodos_nomes = []
    
    for i in range(4, 0, -1):
        inicio_antes = (data_inicio_dt - timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        fim_antes = (data_inicio_dt - timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        periodos_sql_parts.append(f"WHEN data_date BETWEEN DATE '{inicio_antes}' AND DATE '{fim_antes}' THEN 'Antes {i}'")
        periodos_nomes.append(f'Antes {i}')
    
    # Período da promoção
    periodos_sql_parts.append(f"WHEN data_date BETWEEN DATE '{data_inicio_promo}' AND DATE '{data_fim_promo}' THEN 'Promoção'")
    periodos_nomes.append('Promoção')
    
    # Períodos após (4 períodos)
    for i in range(1, 5):
        inicio_apos = (data_fim_dt + timedelta(days=(i-1) * dias_promocao + 1)).strftime('%Y-%m-%d')
        fim_apos = (data_fim_dt + timedelta(days=i * dias_promocao)).strftime('%Y-%m-%d')
        periodos_sql_parts.append(f"WHEN data_date BETWEEN DATE '{inicio_apos}' AND DATE '{fim_apos}' THEN 'Após {i}'")
        periodos_nomes.append(f'Após {i}')
    
    # Montar SQL com CASE para classificar períodos
    case_sql = "CASE " + " ".join(periodos_sql_parts) + " ELSE 'Fora dos períodos' END"
    
    sql = f"""
        WITH vendas_periodos AS (
            SELECT 
                {case_sql} AS periodo,
                SUM(item_quantidade) AS total_quantidade,
                SUM(item_valortotal) AS total_valor,
                SUM(item_valortotal - customediototal) AS total_resultado
            FROM fact_vendas_final
            WHERE item_embalagemid IN ('{ids_str}')
              {cond_filial}
            GROUP BY periodo
            HAVING periodo != 'Fora dos períodos'
        )
        SELECT * FROM vendas_periodos
        ORDER BY 
            CASE periodo
                WHEN 'Antes 4' THEN 1
                WHEN 'Antes 3' THEN 2
                WHEN 'Antes 2' THEN 3
                WHEN 'Antes 1' THEN 4
                WHEN 'Promoção' THEN 5
                WHEN 'Após 1' THEN 6
                WHEN 'Após 2' THEN 7
                WHEN 'Após 3' THEN 8
                WHEN 'Após 4' THEN 9
                ELSE 10
            END
    """
    
    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return {}
        
        resultado = {}
        for _, row in df.iterrows():
            periodo = row['periodo']
            resultado[periodo] = {
                'quantidade': float(row['total_quantidade'] or 0),
                'valor': float(row['total_valor'] or 0),
                'resultado': float(row['total_resultado'] or 0)
            }
        
        return resultado
    except Exception as e:
        st.error(f"Erro ao calcular vendas por período: {e}")
        return {}

def get_top_produtos_promocao_duck(promocao_ids: list, classificacao: str = None, top_n: int = 10) -> pd.DataFrame:
    """
    Busca top produtos vendidos durante a promoção via SQL.
    """
    if not promocao_ids:
        return pd.DataFrame()
    
    ids_str = "', '".join(str(id) for id in promocao_ids)
    cond_classificacao = f"AND classificacao_n1 = '{classificacao}'" if classificacao and classificacao != "Todas" else ""
    
    sql = f"""
        SELECT 
            embalagem_descricao AS produto,
            SUM(item_quantidade) AS quantidade_total,
            SUM(item_valortotal) AS valor_total
        FROM fact_vendas_final
        WHERE item_cadernoofertaid IN ('{ids_str}')
          AND item_cadernoofertaid IS NOT NULL
          {cond_classificacao}
        GROUP BY embalagem_descricao
        ORDER BY quantidade_total DESC, valor_total DESC
        LIMIT {top_n}
    """
    
    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar top produtos: {e}")
        return pd.DataFrame()

def get_filiais_promocao_duck(promocao_ids: list) -> list:
    """
    Busca filiais que tiveram vendas na promoção.
    """
    if not promocao_ids:
        return []
    
    ids_str = "', '".join(str(id) for id in promocao_ids)
    sql = f"""
        SELECT DISTINCT filial_codigo
        FROM fact_vendas_final
        WHERE item_cadernoofertaid IN ('{ids_str}')
          AND item_cadernoofertaid IS NOT NULL
          AND filial_codigo IS NOT NULL
        ORDER BY filial_codigo
    """
    
    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return []
        return df['filial_codigo'].tolist()
    except Exception as e:
        st.error(f"Erro ao carregar filiais: {e}")
        return []

def get_classificacoes_promocao_duck(promocao_ids: list) -> list:
    """
    Busca classificações N1 dos produtos da promoção.
    """
    if not promocao_ids:
        return []
    
    ids_str = "', '".join(str(id) for id in promocao_ids)
    sql = f"""
        SELECT DISTINCT classificacao_n1
        FROM fact_vendas_final
        WHERE item_cadernoofertaid IN ('{ids_str}')
          AND item_cadernoofertaid IS NOT NULL
          AND classificacao_n1 IS NOT NULL
        ORDER BY classificacao_n1
    """
    
    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return []
        return df['classificacao_n1'].tolist()
    except Exception as e:
        st.error(f"Erro ao carregar classificações: {e}")
        return []

