"""
Consultas de dados para análise de vendedores usando DuckDB
"""
from datetime import date, timedelta
from core.database import duck_query
import pandas as pd
from .calculations import _bounds_mes_atual, _cond_filial, _cond_vendedor
from data_processing.vendedores.calculations import (
    kpis_vendedor_mes_atual,
    kpis_vendedor_dia_anterior,
    
)
from visualizations.components.vendedores_popovers import (
    criar_conteudo_popover_vendas_vendedores_duck,
    criar_conteudo_popover_itens_vendedores_duck,
    criar_conteudo_popover_num_vendas_vendedores_duck,
    criar_conteudo_popover_taxa_conversao_vendedores_duck,
    criar_conteudo_popover_ticket_vendedores_duck,
    criar_conteudo_popover_vendas_identificadas_vendedores_duck,
    criar_conteudo_popover_vitaminas_vendedores_duck,

)

# ========================================
# FUNÇÕES AUXILIARES PARA VENDEDORES
# ========================================

def obter_vendedores_por_filial(filial_codigo: str | None = None, top_n: int = 10, data_ref: date | None = None) -> list:
    """
    Retorna lista dos top N vendedores por valor de vendas no mês atual para uma filial
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    
    sql = f"""
        SELECT 
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_valortotal) AS total_vendas
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL 
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    df = duck_query(sql)
    
    if df is None or df.empty:
        return []
    
    return df['vendedor_nome'].tolist()

def obter_filiais_disponiveis() -> list:
    """
    Retorna lista de filiais disponíveis na base de dados
    """
    sql = """
        SELECT DISTINCT CAST(filial_codigo AS VARCHAR) AS filial_codigo
        FROM fact_vendas_final
        WHERE filial_codigo IS NOT NULL
        ORDER BY filial_codigo
    """
    df = duck_query(sql)
    
    if df is None or df.empty:
        return []
    
    return df['filial_codigo'].tolist()



# ========================================
# FUNÇÕES PARA GRÁFICO DE VENDAS DIÁRIAS
# ========================================

def vendas_por_dia_mes_atual(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> pd.DataFrame:
    """
    Retorna vendas por dia do mês atual para gráfico
    Retorna DataFrame com colunas: dia, item_valortotal
    """
    data_ini, data_fim = _bounds_mes_atual(data_ref)
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        SELECT 
            EXTRACT(day FROM data_date)::INTEGER AS dia,
            SUM(item_valortotal) AS item_valortotal
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{data_ini}' AND DATE '{data_fim}'
        {cond_filial}
        {cond_vendedor}
        GROUP BY 1
        ORDER BY 1
    """
    df = duck_query(sql)
    
    if df is None or df.empty:
        return pd.DataFrame(columns=['dia', 'item_valortotal'])
    
    return df

# ========================================
# FUNÇÕES AUXILIARES ESPECÍFICAS
# ========================================

def verificar_vendas_existe_data(data_ref: date | None = None) -> bool:
    """
    Verifica se existem vendas para uma data específica
    """
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    
    data_ref_iso = data_ref.isoformat()
    
    sql = f"""
        SELECT COUNT(*) AS total
        FROM fact_vendas_final
        WHERE data_date = DATE '{data_ref_iso}'
        LIMIT 1
    """
    df = duck_query(sql)
    
    return df is not None and not df.empty and int(df.iloc[0]['total']) > 0

def obter_ultima_data_vendas() -> date | None:
    """
    Retorna a última data com vendas disponível na base
    """
    sql = """
        SELECT MAX(data_date) AS ultima_data
        FROM fact_vendas_final
        WHERE data_date IS NOT NULL
    """
    df = duck_query(sql)
    
    if df is None or df.empty or pd.isna(df.iloc[0]['ultima_data']):
        return None
    
    return df.iloc[0]['ultima_data'].date() if hasattr(df.iloc[0]['ultima_data'], 'date') else df.iloc[0]['ultima_data']

# ========================================
# FUNÇÕES PARA SÉRIES MENSAL
# ========================================

def gerar_series_mensais_vendedor_duck(filial_codigo: str | None = None, vendedor_nome: str | None = None, meses: int = 9, data_ref: date | None = None) -> pd.DataFrame:
    """
    Gera séries mensais para gráficos do vendedor (últimos N meses)
    Retorna DataFrame com métricas mensais
    """
    if not vendedor_nome or vendedor_nome.strip().lower() == "todos os vendedores":
        return pd.DataFrame()
    
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    
    # Calcular período: últimos N meses incluindo mês atual parcial
    primeiro_mes_atual = data_ref.replace(day=1)
    inicio_periodo = primeiro_mes_atual - pd.DateOffset(months=meses-1)
    inicio_periodo = inicio_periodo.to_pydatetime().date()
    
    cond_filial = _cond_filial(filial_codigo)
    cond_vendedor = _cond_vendedor(vendedor_nome)
    
    sql = f"""
        WITH vendas_mensais AS (
            SELECT 
                DATE_TRUNC('month', data_date) AS ano_mes,
                SUM(item_valortotal) AS venda_acumulada,
                COUNT(DISTINCT venda_id) AS num_vendas,
                SUM(item_quantidade) AS total_itens,
                
                -- Vitaminas
                SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' 
                         THEN item_quantidade ELSE 0 END) AS num_vitaminas,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' 
                                    THEN venda_id END) AS vendas_com_vitaminas,
                
                -- Vendas identificadas
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_count,
                COUNT(DISTINCT venda_id) AS total_vendas_count
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_periodo}' AND DATE '{data_ref}'
            {cond_filial}
            {cond_vendedor}
            GROUP BY 1
            ORDER BY 1
        )
        SELECT 
            ano_mes,
            STRFTIME(ano_mes, '%m/%Y') AS mes_label,
            COALESCE(venda_acumulada, 0) AS venda_acumulada,
            COALESCE(num_vendas, 0) AS num_vendas,
            
            -- Ticket médio
            CASE WHEN num_vendas > 0 THEN venda_acumulada / num_vendas ELSE 0 END AS ticket_medio,
            
            -- Vitaminas
            COALESCE(num_vitaminas, 0) AS num_vitaminas,
            CASE WHEN vendas_com_vitaminas > 0 THEN CAST(num_vendas AS FLOAT) / vendas_com_vitaminas ELSE 0 END AS taxa_conversao_vitaminas,
            
            -- Vendas identificadas (%)
            CASE WHEN total_vendas_count > 0 THEN (vendas_identificadas_count * 100.0) / total_vendas_count ELSE 0 END AS vendas_identificadas_perc
        FROM vendas_mensais
        ORDER BY ano_mes
    """
    
    df = duck_query(sql)
    
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Garantir tipos corretos
    df['ano_mes'] = pd.to_datetime(df['ano_mes'])
    df['mes_label'] = df['mes_label'].astype(str)
    df['venda_acumulada'] = df['venda_acumulada'].astype(float)
    df['num_vendas'] = df['num_vendas'].astype(int)
    df['ticket_medio'] = df['ticket_medio'].astype(float)
    df['num_vitaminas'] = df['num_vitaminas'].astype(int)
    df['taxa_conversao_vitaminas'] = df['taxa_conversao_vitaminas'].astype(float)
    df['vendas_identificadas_perc'] = df['vendas_identificadas_perc'].astype(float)
    
    return df

# ========================================
# FUNÇÃO CONSOLIDADA PARA VISÃO INDIVIDUAL COMPLETA
# ========================================

def dados_completos_vendedor_individual_duck(filial_codigo: str | None = None, vendedor_nome: str | None = None, data_ref: date | None = None) -> dict:
    """
    Retorna TODOS os dados necessários para a visualização individual completa do vendedor
    """
    # KPIs do mês atual
    kpis_mes = kpis_vendedor_mes_atual(filial_codigo, vendedor_nome, data_ref)
    
    # KPIs do dia anterior
    kpis_dia = kpis_vendedor_dia_anterior(filial_codigo, vendedor_nome, data_ref)
    
    # Dados para gráfico diário
    vendas_diarias = vendas_por_dia_mes_atual(filial_codigo, vendedor_nome, data_ref)
    
    # Séries mensais para gráficos históricos
    series_mensais = gerar_series_mensais_vendedor_duck(filial_codigo, vendedor_nome, meses=9, data_ref=data_ref)
    
    # Informações auxiliares
    ultima_data = obter_ultima_data_vendas()
    tem_vendas_dia = verificar_vendas_existe_data(data_ref)
    
    return {
        'kpis_mes_atual': kpis_mes,
        'kpis_dia_anterior': kpis_dia,
        'vendas_por_dia': vendas_diarias,
        'series_mensais': series_mensais,
        'ultima_data_disponivel': ultima_data,
        'tem_vendas_dia_anterior': tem_vendas_dia,
        'data_referencia': data_ref or (date.today() - timedelta(days=1))
    }


# ========================================
# FUNÇÃO PARA DADOS COMPARATIVOS
# ========================================

def dados_completos_vendedores_comparativo_duck(filial_codigo: str | None = None, vendedores: list[str] = [], data_ref: date | None = None) -> dict:
    """
    Retorna dados consolidados para múltiplos vendedores (modo comparativo).
    Inclui DataFrames prontos para gráficos comparativos, reutilizando funções individuais.
    Estrutura retornada:
    - 'dados_individuais': dict com dados de cada vendedor (como dados_completos_vendedor_individual_duck)
    - 'vendas_totais_df': DataFrame com ['vendedor_nome', 'venda_total', 'num_vendas']
    - 'ticket_medio_df': DataFrame com ['vendedor_nome', 'ticket_medio']
    - 'itens_por_nota_df': DataFrame com ['vendedor_nome', 'itens_por_nota']
    - 'vitaminas_df': DataFrame com ['vendedor_nome', 'quantidade_vitaminas']
    - 'taxa_conversao_df': DataFrame com ['vendedor_nome', 'taxa_conversao']
    - 'vendas_identificadas_df': DataFrame com ['vendedor_nome', 'percentual_identificadas']
    - 'series_mensais_df': DataFrame com séries mensais consolidadas (colunas: mes_label, vendedor1, vendedor2, ...)
    """
    if not vendedores:
        return {}
    
    # 1. Obter dados individuais para cada vendedor
    dados_individuais = {}
    for vendedor in vendedores:
        dados_individuais[vendedor] = dados_completos_vendedor_individual_duck(filial_codigo, vendedor, data_ref)
    
    # 2. Consolidar DataFrames para métricas principais (usando as funções migradas)
    vendas_totais_df = criar_conteudo_popover_vendas_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    ticket_medio_df = criar_conteudo_popover_ticket_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    itens_por_nota_df = criar_conteudo_popover_itens_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    vitaminas_df = criar_conteudo_popover_vitaminas_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    taxa_conversao_df = criar_conteudo_popover_taxa_conversao_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    vendas_identificadas_df = criar_conteudo_popover_vendas_identificadas_vendedores_duck(filial_codigo, vendedores, top_n=len(vendedores), data_ref=data_ref)
    
    # 3. Consolidar séries mensais (pivot para colunas por vendedor)
    series_mensais_df = pd.DataFrame()
    if dados_individuais:
        # Pegar séries do primeiro vendedor para base
        primeiro_vendedor = list(dados_individuais.keys())[0]
        base_series = dados_individuais[primeiro_vendedor]['series_mensais']
        if not base_series.empty:
            series_mensais_df = base_series[['ano_mes', 'mes_label']].copy()
            for vendedor in vendedores:
                series_vendedor = dados_individuais[vendedor]['series_mensais']
                if not series_vendedor.empty:
                    # Adicionar coluna para cada métrica (e.g., venda_acumulada_{vendedor})
                    series_mensais_df[f'venda_acumulada_{vendedor}'] = series_vendedor['venda_acumulada']
                    series_mensais_df[f'ticket_medio_{vendedor}'] = series_vendedor['ticket_medio']
                    series_mensais_df[f'num_vendas_{vendedor}'] = series_vendedor['num_vendas']
                    series_mensais_df[f'num_vitaminas_{vendedor}'] = series_vendedor['num_vitaminas']
                    series_mensais_df[f'taxa_conversao_vitaminas_{vendedor}'] = series_vendedor['taxa_conversao_vitaminas']
                    series_mensais_df[f'vendas_identificadas_perc_{vendedor}'] = series_vendedor['vendas_identificadas_perc']
                else:
                    # Preencher com zeros se não houver dados
                    series_mensais_df[f'venda_acumulada_{vendedor}'] = 0.0
                    series_mensais_df[f'ticket_medio_{vendedor}'] = 0.0
                    series_mensais_df[f'num_vendas_{vendedor}'] = 0
                    series_mensais_df[f'num_vitaminas_{vendedor}'] = 0
                    series_mensais_df[f'taxa_conversao_vitaminas_{vendedor}'] = 0.0
                    series_mensais_df[f'vendas_identificadas_perc_{vendedor}'] = 0.0
    
    # 4. Retornar estrutura consolidada
    return {
        'dados_individuais': dados_individuais,
        'vendas_totais_df': vendas_totais_df,
        'ticket_medio_df': ticket_medio_df,
        'itens_por_nota_df': itens_por_nota_df,
        'vitaminas_df': vitaminas_df,
        'taxa_conversao_df': taxa_conversao_df,
        'vendas_identificadas_df': vendas_identificadas_df,
        'series_mensais_df': series_mensais_df,
        'data_referencia': data_ref or (date.today() - timedelta(days=1))
    }
