import pandas as pd
import streamlit as st
from core.database import duck_query

def calcular_curva_abc_duck(data_atual):
    """
    Calcula curva ABC baseada em vendas dos últimos 90 dias via SQL.
    Retorna DataFrame com colunas: filial_codigo, classificacao_n3, embalagemid, curvaABC
    """
    data_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    data_limite_90 = (pd.Timestamp(data_ontem) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    
    sql = f"""
    WITH vendas_90d AS (
        SELECT 
            filial_codigo,
            classificacao_n3,
            item_embalagemid AS embalagemid,
            SUM(ABS(item_quantidade)) AS quantidade_vendida
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_90}' AND data_date <= DATE '{data_ontem}'
        GROUP BY filial_codigo, classificacao_n3, item_embalagemid
    ),
    vendas_com_acumulado AS (
        SELECT 
            filial_codigo,
            classificacao_n3,
            embalagemid,
            quantidade_vendida,
            SUM(quantidade_vendida) OVER (
                PARTITION BY filial_codigo, classificacao_n3 
                ORDER BY quantidade_vendida DESC
                ROWS UNBOUNDED PRECEDING
            ) AS quantidade_acum,
            SUM(quantidade_vendida) OVER (PARTITION BY filial_codigo, classificacao_n3) AS total_vendas_grupo
        FROM vendas_90d
        ORDER BY filial_codigo, classificacao_n3, quantidade_vendida DESC
    ),
    vendas_com_percentual AS (
        SELECT 
            filial_codigo,
            classificacao_n3,
            embalagemid,
            quantidade_vendida,
            CASE 
                WHEN total_vendas_grupo > 0 
                THEN (quantidade_acum * 100.0 / total_vendas_grupo)
                ELSE 0
            END AS perc_acum
        FROM vendas_com_acumulado
    ),
    produtos_com_curva AS (
        SELECT 
            filial_codigo,
            classificacao_n3,
            embalagemid,
            CASE 
                WHEN perc_acum <= 50 THEN 'A'
                WHEN perc_acum <= 80 THEN 'B'
                ELSE 'C'
            END AS curvaABC
        FROM vendas_com_percentual
    ),
    todos_produtos AS (
        SELECT DISTINCT 
            filial_codigo,
            classificacao_n3,
            item_embalagemid AS embalagemid
        FROM fact_vendas_final
        WHERE filial_codigo IS NOT NULL 
        AND classificacao_n3 IS NOT NULL 
        AND item_embalagemid IS NOT NULL
    )
    SELECT 
        tp.filial_codigo,
        tp.classificacao_n3,
        tp.embalagemid,
        COALESCE(pc.curvaABC, 'D') AS curvaABC
    FROM todos_produtos tp
    LEFT JOIN produtos_com_curva pc 
        ON tp.filial_codigo = pc.filial_codigo 
        AND tp.classificacao_n3 = pc.classificacao_n3 
        AND tp.embalagemid = pc.embalagemid
    """
    
    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular curva ABC: {e}")
        return pd.DataFrame()

def calcular_indice_ruptura_por_classificacao_n2_duck(data_atual):
    """
    Calcula índice de ruptura/disponibilidade apenas para classificacao_n2.
    Retorna:
      - Agregado geral por classificacao_n2 ('Geral' AS filial_codigo, classificacao_n2)
      - Por filial + classificacao_n2 (filial_codigo, classificacao_n2)
    Observação: não repete as linhas 'Geral' e 'por filial' já geradas por calcular_disponibilidade_duck.
    """
    data_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    data_limite_90 = (pd.Timestamp(data_ontem) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    data_limite_30 = (pd.Timestamp(data_ontem) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')

    sql = f"""
    WITH produtos_comprados_90d AS (
        SELECT DISTINCT filial_codigo, embalagemid
        FROM fact_estoque_final
        WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_ontem}'
          AND descricao_movimentacao = 'Recebimento Físico'
    ),
    produtos_vendidos_30d AS (
        SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_ontem}'
    ),
    produtos_denominador AS (
        SELECT pc.filial_codigo, pc.embalagemid
        FROM produtos_comprados_90d pc
        INNER JOIN produtos_vendidos_30d pv
            ON pc.filial_codigo = pv.filial_codigo
           AND pc.embalagemid = pv.embalagemid
    ),
    estoque_atual AS (
        SELECT
            e.filial_codigo,
            e.embalagemid,
            e.estoque,
            e.classificacao_n2
        FROM (
            SELECT
                filial_codigo,
                embalagemid,
                estoque,
                classificacao_n2,
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_ontem}'
        ) e
        WHERE e.rn = 1
    ),
    estoque_filtrado AS (
        SELECT ea.*
        FROM estoque_atual ea
        INNER JOIN produtos_denominador pd
            ON ea.filial_codigo = pd.filial_codigo AND ea.embalagemid = pd.embalagemid
    )
    -- 1) Agregado geral por classificacao_n2
    SELECT
        'Geral' AS filial_codigo,
        classificacao_n2,
        COUNT(*) AS total_produtos,
        SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados,
        CASE WHEN COUNT(*) > 0 THEN (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) ELSE 0 END AS indice_ruptura,
        CASE WHEN COUNT(*) > 0 THEN (100.0 - (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))) ELSE 0 END AS disponibilidade
    FROM estoque_filtrado
    WHERE classificacao_n2 IS NOT NULL
    GROUP BY classificacao_n2

    UNION ALL

    -- 2) Por filial + classificacao_n2
    SELECT
        filial_codigo,
        classificacao_n2,
        COUNT(*) AS total_produtos,
        SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados,
        CASE WHEN COUNT(*) > 0 THEN (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) ELSE 0 END AS indice_ruptura,
        CASE WHEN COUNT(*) > 0 THEN (100.0 - (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))) ELSE 0 END AS disponibilidade
    FROM estoque_filtrado
    WHERE classificacao_n2 IS NOT NULL
    GROUP BY filial_codigo, classificacao_n2
    ORDER BY filial_codigo, classificacao_n2
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular índice de ruptura por classificação N2: {e}")
        return pd.DataFrame()

def calcular_indice_ruptura_por_laboratorio_duck(data_atual, lab_col='fabricante_nome'):
    """
    Calcula índice de ruptura/disponibilidade apenas por laboratório (fabricante).
    Retorna duas agregações:
      - Agregado geral por laboratório ('Geral' AS filial_codigo, fabricante_nome)
      - Por filial + laboratório (filial_codigo, fabricante_nome)
    Observação: não repete as linhas 'Geral' e 'por filial' já geradas por calcular_disponibilidade_duck.
    """
    data_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    data_limite_90 = (pd.Timestamp(data_ontem) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    data_limite_30 = (pd.Timestamp(data_ontem) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')

    sql = f"""
    WITH produtos_comprados_90d AS (
        SELECT DISTINCT filial_codigo, embalagemid
        FROM fact_estoque_final
        WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_ontem}'
          AND descricao_movimentacao = 'Recebimento Físico'
    ),
    produtos_vendidos_30d AS (
        SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_ontem}'
    ),
    produtos_denominador AS (
        SELECT pc.filial_codigo, pc.embalagemid
        FROM produtos_comprados_90d pc
        INNER JOIN produtos_vendidos_30d pv
            ON pc.filial_codigo = pv.filial_codigo
           AND pc.embalagemid = pv.embalagemid
    ),
    estoque_atual AS (
        SELECT
            e.filial_codigo,
            e.embalagemid,
            e.estoque,
            COALESCE(e.{lab_col}, 'Sem fabricante') AS fabricante_nome
        FROM (
            SELECT
                filial_codigo,
                embalagemid,
                estoque,
                {lab_col},
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_ontem}'
        ) e
        WHERE e.rn = 1
    ),
    estoque_filtrado AS (
        SELECT ea.*
        FROM estoque_atual ea
        INNER JOIN produtos_denominador pd
            ON ea.filial_codigo = pd.filial_codigo AND ea.embalagemid = pd.embalagemid
    )
    -- 1) Agregado geral por laboratório
    SELECT
        'Geral' AS filial_codigo,
        fabricante_nome,
        COUNT(*) AS total_produtos,
        SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados,
        CASE WHEN COUNT(*) > 0 THEN (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) ELSE 0 END AS indice_ruptura,
        CASE WHEN COUNT(*) > 0 THEN (100.0 - (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))) ELSE 0 END AS disponibilidade
    FROM estoque_filtrado
    WHERE fabricante_nome IS NOT NULL
    GROUP BY fabricante_nome

    UNION ALL

    -- 2) Por filial + laboratório
    SELECT
        filial_codigo,
        fabricante_nome,
        COUNT(*) AS total_produtos,
        SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados,
        CASE WHEN COUNT(*) > 0 THEN (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) ELSE 0 END AS indice_ruptura,
        CASE WHEN COUNT(*) > 0 THEN (100.0 - (SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))) ELSE 0 END AS disponibilidade
    FROM estoque_filtrado
    WHERE fabricante_nome IS NOT NULL
    GROUP BY filial_codigo, fabricante_nome
    ORDER BY filial_codigo, fabricante_nome
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular índice de ruptura por laboratório: {e}")
        return pd.DataFrame()



def calcular_giro_por_classificacao_n2_duck(data_atual):
    """
    Calcula giro apenas por classificacao_n2.
    Retorna duas agregações:
      - Agregado geral por classificacao_n2 ('Geral' AS filial_codigo, classificacao_n2)
      - Por filial + classificacao_n2 (filial_codigo, classificacao_n2)
    Colunas retornadas: filial_codigo, classificacao_n2, total_produtos, total_valor_estoque,
                        valor_estoque_com_giro, valor_estoque_sem_giro, giro_medio_anual
    """
    data_limite_90 = (pd.Timestamp(data_atual) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    data_limite_30 = (pd.Timestamp(data_atual) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    sql = f"""
    WITH vendas_30d_produtos AS (
        SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_limite_ontem}'
    ),
    estoque_ultimo AS (
        SELECT
            filial_codigo,
            embalagemid,
            estoque,
            customedio AS custo_medio,
            customedio * estoque AS valor_estoque,
            classificacao_n1,
            classificacao_n2,
            classificacao_n3
        FROM (
            SELECT
                filial_codigo,
                embalagemid,
                estoque,
                customedio,
                classificacao_n1,
                classificacao_n2,
                classificacao_n3,
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_limite_ontem}'
        ) sub
        WHERE rn = 1
    ),
    dados_combinados AS (
        SELECT
            ef.filial_codigo,
            ef.embalagemid,
            ef.estoque,
            ef.custo_medio,
            ef.valor_estoque,
            ef.classificacao_n1,
            ef.classificacao_n2,
            ef.classificacao_n3,
            CASE WHEN v30.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS teve_giro,
            CASE WHEN v30.embalagemid IS NOT NULL THEN ef.valor_estoque ELSE 0 END AS cmv_com_giro
        FROM estoque_ultimo ef
        LEFT JOIN vendas_30d_produtos v30
            ON ef.filial_codigo = v30.filial_codigo AND ef.embalagemid = v30.embalagemid
    )
    -- 1) Agregado geral por classificacao_n2
    SELECT
        'Geral' AS filial_codigo,
        classificacao_n2,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(cmv_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN cmv_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0 THEN (SUM(cmv_com_giro) / SUM(valor_estoque)) * 100 ELSE 0 END AS giro_medio_anual
    FROM dados_combinados
    WHERE classificacao_n2 IS NOT NULL
    GROUP BY classificacao_n2

    UNION ALL

    -- 2) Por filial + classificacao_n2
    SELECT
        filial_codigo,
        classificacao_n2,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(cmv_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN cmv_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0 THEN (SUM(cmv_com_giro) / SUM(valor_estoque)) * 100 ELSE 0 END AS giro_medio_anual
    FROM dados_combinados
    WHERE classificacao_n2 IS NOT NULL
    GROUP BY filial_codigo, classificacao_n2
    ORDER BY filial_codigo, classificacao_n2
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular giro por classificacao_n2: {e}")
        return pd.DataFrame()
    
def calcular_giro_por_laboratorio_duck(data_atual, lab_col='fabricante_nome'):
    """
    Calcula giro apenas por laboratório (fabricante).
    Retorna duas agregações:
      - Agregado geral por fabricante ('Geral' AS filial_codigo, fabricante_nome)
      - Por filial + fabricante (filial_codigo, fabricante_nome)
    Colunas retornadas: filial_codigo, fabricante_nome, total_produtos, total_valor_estoque,
                        valor_estoque_com_giro, valor_estoque_sem_giro, giro_medio_anual
    Observação: não recalcula as linhas 'Geral' e 'por filial' já geradas pela função principal.
    """
    data_limite_90 = (pd.Timestamp(data_atual) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    data_limite_30 = (pd.Timestamp(data_atual) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    sql = f"""
    WITH vendas_30d_produtos AS (
        SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_limite_ontem}'
    ),
    estoque_ultimo AS (
        SELECT
            filial_codigo,
            embalagemid,
            estoque,
            customedio AS custo_medio,
            customedio * estoque AS valor_estoque,
            classificacao_n1,
            classificacao_n2,
            classificacao_n3,
            {lab_col}
        FROM (
            SELECT
                filial_codigo,
                embalagemid,
                estoque,
                customedio,
                classificacao_n1,
                classificacao_n2,
                classificacao_n3,
                {lab_col},
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora >= DATE '{data_limite_90}' AND datahora <= DATE '{data_limite_ontem}'
        ) sub
        WHERE rn = 1
    ),
    dados_combinados AS (
        SELECT
            ef.filial_codigo,
            ef.embalagemid,
            ef.estoque,
            ef.custo_medio,
            ef.valor_estoque,
            COALESCE(ef.{lab_col}, 'Sem fabricante') AS fabricante_nome,
            ef.classificacao_n1,
            ef.classificacao_n2,
            ef.classificacao_n3,
            CASE WHEN v30.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS teve_giro,
            CASE WHEN v30.embalagemid IS NOT NULL THEN ef.valor_estoque ELSE 0 END AS cmv_com_giro
        FROM estoque_ultimo ef
        LEFT JOIN vendas_30d_produtos v30
            ON ef.filial_codigo = v30.filial_codigo AND ef.embalagemid = v30.embalagemid
    )
    -- 1) Agregado geral por fabricante
    SELECT
        'Geral' AS filial_codigo,
        fabricante_nome,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(cmv_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN cmv_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0 THEN (SUM(cmv_com_giro) / SUM(valor_estoque)) * 100 ELSE 0 END AS giro_medio_anual
    FROM dados_combinados
    WHERE fabricante_nome IS NOT NULL
    GROUP BY fabricante_nome

    UNION ALL

    -- 2) Por filial + fabricante
    SELECT
        filial_codigo,
        fabricante_nome,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(cmv_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN cmv_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0 THEN (SUM(cmv_com_giro) / SUM(valor_estoque)) * 100 ELSE 0 END AS giro_medio_anual
    FROM dados_combinados
    WHERE fabricante_nome IS NOT NULL
    GROUP BY filial_codigo, fabricante_nome
    ORDER BY filial_codigo, fabricante_nome
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular giro por laboratório: {e}")
        return pd.DataFrame()



def calcular_fator_cobertura_por_classificacao_n2_duck(data_atual):
    """
    Calcula fator de cobertura (stock CMV / CMV vendido 30d) por classificacao_n2.
    Retorna duas agregações:
      - Agregado geral por classificacao_n2  ('Geral' AS filial_codigo, classificacao_n2)
      - Por filial + classificacao_n2        (filial_codigo, classificacao_n2)
    Colunas retornadas: filial_codigo, classificacao_n2, stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    data_limite_30 = (pd.Timestamp(data_atual) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    sql = f"""
    WITH vendas_30d AS (
        SELECT 
            filial_codigo,
            classificacao_n2,
            SUM(ABS(item_quantidade) * COALESCE(customedio,0)) AS cmv_vendido_30d
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_limite_ontem}'
        GROUP BY filial_codigo, classificacao_n2
    ),
    vendas_30d_tot AS (
        SELECT classificacao_n2, SUM(cmv_vendido_30d) AS cmv_vendido_30d
        FROM vendas_30d
        GROUP BY classificacao_n2
    ),
    estoque_ultimo AS (
        SELECT
            filial_codigo,
            embalagemid,
            classificacao_n2,
            COALESCE(customedio,0) AS customedio,
            estoque,
            (COALESCE(customedio,0) * estoque) AS valor_estoque,
            ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
        FROM fact_estoque_final
        WHERE datahora <= DATE '{data_limite_ontem}'
    ),
    estoque_geral_n2 AS (
        SELECT
            classificacao_n2,
            SUM(valor_estoque) AS stock_cmv
        FROM estoque_ultimo
        WHERE rn = 1
        GROUP BY classificacao_n2
    ),
    estoque_filial_n2 AS (
        SELECT
            filial_codigo,
            classificacao_n2,
            SUM(valor_estoque) AS stock_cmv
        FROM estoque_ultimo
        WHERE rn = 1
        GROUP BY filial_codigo, classificacao_n2
    )
    -- 1) Agregado geral por classificacao_n2 (soma de todas as filiais)
    SELECT
        'Geral' AS filial_codigo,
        eg.classificacao_n2,
        eg.stock_cmv,
        COALESCE(vt.cmv_vendido_30d, 0) AS cmv_vendido_30d,
        CASE WHEN COALESCE(vt.cmv_vendido_30d, 0) > 0 THEN eg.stock_cmv / vt.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque_geral_n2 eg
    LEFT JOIN vendas_30d_tot vt
        ON eg.classificacao_n2 = vt.classificacao_n2
    WHERE eg.classificacao_n2 IS NOT NULL

    UNION ALL

    -- 2) Por filial + classificacao_n2
    SELECT
        ef.filial_codigo,
        ef.classificacao_n2,
        ef.stock_cmv,
        COALESCE(v.cmv_vendido_30d, 0) AS cmv_vendido_30d,
        CASE WHEN COALESCE(v.cmv_vendido_30d, 0) > 0 THEN ef.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque_filial_n2 ef
    LEFT JOIN vendas_30d v
        ON ef.filial_codigo = v.filial_codigo AND ef.classificacao_n2 = v.classificacao_n2
    WHERE ef.classificacao_n2 IS NOT NULL
    ORDER BY filial_codigo, classificacao_n2
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura por classificacao_n2: {e}")
        return pd.DataFrame()

def calcular_fator_cobertura_por_laboratorio_duck(data_atual, lab_col='fabricante_nome'):
    """
    Calcula fator de cobertura (stock CMV / CMV vendido 30d) por laboratório (fabricante).
    Retorna duas agregações:
      - Agregado geral por fabricante  ('Geral' AS filial_codigo, fabricante_nome)
      - Por filial + fabricante         (filial_codigo, fabricante_nome)
    Colunas retornadas: filial_codigo, fabricante_nome, stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    data_limite_30 = (pd.Timestamp(data_atual) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    sql = f"""
    WITH vendas_30d AS (
        SELECT 
            filial_codigo,
            COALESCE({lab_col}, 'Sem fabricante') AS fabricante_nome,
            SUM(ABS(item_quantidade) * COALESCE(customedio,0)) AS cmv_vendido_30d
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}' AND data_date <= DATE '{data_limite_ontem}'
        GROUP BY filial_codigo, COALESCE({lab_col}, 'Sem fabricante')
    ),
    vendas_30d_tot AS (
        SELECT fabricante_nome, SUM(cmv_vendido_30d) AS cmv_vendido_30d
        FROM vendas_30d
        GROUP BY fabricante_nome
    ),
    estoque_ultimo AS (
        SELECT
            filial_codigo,
            embalagemid,
            COALESCE({lab_col}, 'Sem fabricante') AS fabricante_nome,
            COALESCE(customedio,0) AS customedio,
            estoque,
            (COALESCE(customedio,0) * estoque) AS valor_estoque,
            ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
        FROM fact_estoque_final
        WHERE datahora <= DATE '{data_limite_ontem}'
    ),
    estoque_geral_lab AS (
        SELECT
            fabricante_nome,
            SUM(valor_estoque) AS stock_cmv
        FROM estoque_ultimo
        WHERE rn = 1
        GROUP BY fabricante_nome
    ),
    estoque_filial_lab AS (
        SELECT
            filial_codigo,
            fabricante_nome,
            SUM(valor_estoque) AS stock_cmv
        FROM estoque_ultimo
        WHERE rn = 1
        GROUP BY filial_codigo, fabricante_nome
    )
    -- 1) Agregado geral por fabricante (soma de todas as filiais)
    SELECT
        'Geral' AS filial_codigo,
        eg.fabricante_nome,
        eg.stock_cmv,
        COALESCE(vt.cmv_vendido_30d, 0) AS cmv_vendido_30d,
        CASE WHEN COALESCE(vt.cmv_vendido_30d, 0) > 0 THEN eg.stock_cmv / vt.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque_geral_lab eg
    LEFT JOIN vendas_30d_tot vt
        ON eg.fabricante_nome = vt.fabricante_nome
    WHERE eg.fabricante_nome IS NOT NULL

    UNION ALL

    -- 2) Por filial + fabricante
    SELECT
        ef.filial_codigo,
        ef.fabricante_nome,
        ef.stock_cmv,
        COALESCE(v.cmv_vendido_30d, 0) AS cmv_vendido_30d,
        CASE WHEN COALESCE(v.cmv_vendido_30d, 0) > 0 THEN ef.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque_filial_lab ef
    LEFT JOIN vendas_30d v
        ON ef.filial_codigo = v.filial_codigo AND ef.fabricante_nome = v.fabricante_nome
    WHERE ef.fabricante_nome IS NOT NULL
    ORDER BY filial_codigo, fabricante_nome
    """

    try:
        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura por laboratório: {e}")
        return pd.DataFrame()