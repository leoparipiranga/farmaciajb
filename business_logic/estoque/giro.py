import pandas as pd
import streamlit as st
import numpy as np
from core.database import duck_query
from business_logic.estoque.base_sets import ensure_bases_estoque


def calcular_primeira_venda_geral(data_atual):
    """
    Calcula o tempo médio (em dias) até a PRIMEIRA venda após a compra.
    
    Para cada dia dos últimos 30 dias:
    1. Considera compras realizadas 90 dias antes desse dia
    2. Identifica quando a PRIMEIRA unidade de cada produto foi vendida
    3. Calcula tempo médio ponderado por quantidade comprada até primeira venda
    
    Lógica simplificada focada na primeira venda para melhor relevância gerencial.
    
    Retorna:
    - kpi_general: dict com tempo_primeira_venda_geral, tempo_primeira_venda_apos_30d e taxa_conversao_30d
    - df_filial: DataFrame com tempo médio por filial
    - df_distribuicao: DataFrame para gráfico (dia_primeira_venda, total_compras) agregado
    """
    try:
        # referência (ontem)
        ref_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()

        # construir lista de (reference_day, purchase_date) para os últimos 30 dias
        pairs = []
        for offset in range(30):
            reference_day = ref_ontem - pd.Timedelta(days=offset)
            purchase_date = reference_day - pd.Timedelta(days=90)
            pairs.append((reference_day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{r}', DATE '{p}')" for r, p in pairs])

        # Query otimizada: foco na primeira venda
        sql = f"""
        WITH reference_days(reference_day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        -- Compras realizadas em cada purchase_date
        compras_base AS (
            SELECT
                r.reference_day,
                r.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                SUM(ABS(f.quantidade)) AS qtde_comprada,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio, 0)) AS valor_comprado
            FROM reference_days r
            JOIN fact_estoque_final f
                ON DATE(f.datahora) = r.purchase_date
                AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid
        ),
        -- Primeira venda de cada produto comprado
        primeira_venda AS (
            SELECT
                c.reference_day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_comprada,
                c.valor_comprado,
                MIN(v.data_date) AS data_primeira_venda,
                MIN(v.data_date - c.purchase_date) AS dias_primeira_venda
            FROM compras_base c
            LEFT JOIN fact_vendas_final v
                ON v.filial_codigo = c.filial_codigo
                AND v.item_embalagemid = c.embalagemid
                AND v.data_date BETWEEN c.purchase_date + INTERVAL '1 day' 
                AND c.purchase_date + INTERVAL '90 days'
            GROUP BY c.reference_day, c.purchase_date, c.filial_codigo, c.embalagemid, c.qtde_comprada, c.valor_comprado
        ),
        -- Classificar vendas e preparar dados finais
        vendas_classificadas AS (
            SELECT
                reference_day,
                purchase_date,
                filial_codigo,
                embalagemid,
                qtde_comprada,
                valor_comprado,
                data_primeira_venda,
                dias_primeira_venda,
                -- Classificações
                CASE WHEN data_primeira_venda IS NOT NULL THEN 1 ELSE 0 END AS teve_venda,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda <= 30 THEN 1 ELSE 0 END AS vendeu_ate_30d,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda > 30 THEN 1 ELSE 0 END AS vendeu_apos_30d,
                -- Para produtos que venderam, usar dias reais; para não vendidos, considerar 90 dias
                CASE 
                    WHEN dias_primeira_venda IS NOT NULL THEN dias_primeira_venda
                    ELSE 90
                END AS dias_para_calculo
            FROM primeira_venda
        ),
        -- KPIs gerais
        kpis_gerais AS (
            SELECT
                -- Tempo médio até primeira venda (apenas produtos que venderam)
                CASE 
                    WHEN SUM(CASE WHEN teve_venda = 1 THEN qtde_comprada ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN teve_venda = 1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) / 
                        SUM(CASE WHEN teve_venda = 1 THEN qtde_comprada ELSE 0 END), 
                        1
                    )
                    ELSE 0.0
                END AS tempo_primeira_venda_geral,
                -- Tempo médio para produtos que venderam após 30 dias
                CASE 
                    WHEN SUM(CASE WHEN vendeu_apos_30d = 1 THEN qtde_comprada ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN vendeu_apos_30d = 1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) / 
                        SUM(CASE WHEN vendeu_apos_30d = 1 THEN qtde_comprada ELSE 0 END), 
                        1
                    )
                    ELSE 0.0
                END AS tempo_primeira_venda_apos_30d,
                -- Taxa de conversão em 30 dias (% de compras que venderam pelo menos 1 unidade em 30 dias)
                CASE 
                    WHEN COUNT(*) > 0
                    THEN ROUND(
                        SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 
                        1
                    )
                    ELSE 0.0
                END AS taxa_conversao_30d
            FROM vendas_classificadas
        ),
        -- KPIs por filial
        kpis_por_filial AS (
            SELECT
                filial_codigo,
                CASE 
                    WHEN SUM(CASE WHEN teve_venda = 1 THEN qtde_comprada ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN teve_venda = 1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) / 
                        SUM(CASE WHEN teve_venda = 1 THEN qtde_comprada ELSE 0 END), 
                        1
                    )
                    ELSE 0.0
                END AS tempo_primeira_venda_geral,
                CASE 
                    WHEN SUM(CASE WHEN vendeu_apos_30d = 1 THEN qtde_comprada ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN vendeu_apos_30d = 1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) / 
                        SUM(CASE WHEN vendeu_apos_30d = 1 THEN qtde_comprada ELSE 0 END), 
                        1
                    )
                    ELSE 0.0
                END AS tempo_primeira_venda_apos_30d,
                CASE 
                    WHEN COUNT(*) > 0
                    THEN ROUND(
                        SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 
                        1
                    )
                    ELSE 0.0
                END AS taxa_conversao_30d
            FROM vendas_classificadas
            GROUP BY filial_codigo
        ),
        -- Distribuição para gráfico (apenas produtos que venderam)
        distribuicao AS (
            SELECT
                dias_primeira_venda AS dia_primeira_venda,
                COUNT(*) AS total_compras
            FROM vendas_classificadas
            WHERE teve_venda = 1
            GROUP BY dias_primeira_venda
            ORDER BY dias_primeira_venda
        )
        -- Retornar os três conjuntos de resultados
        SELECT 'kpi_geral' AS tipo, 
               NULL AS filial_codigo,
               NULL AS dia_primeira_venda,
               tempo_primeira_venda_geral AS valor1,
               tempo_primeira_venda_apos_30d AS valor2,
               taxa_conversao_30d AS valor3
        FROM kpis_gerais
        
        UNION ALL
        
        SELECT 'kpi_filial' AS tipo,
               filial_codigo,
               NULL AS dia_primeira_venda,
               tempo_primeira_venda_geral AS valor1,
               tempo_primeira_venda_apos_30d AS valor2,
               taxa_conversao_30d AS valor3
        FROM kpis_por_filial
        
        UNION ALL
        
        SELECT 'distribuicao' AS tipo,
               NULL AS filial_codigo,
               dia_primeira_venda,
               NULL AS valor1,
               NULL AS valor2,
               total_compras AS valor3
        FROM distribuicao
        
        ORDER BY tipo, filial_codigo, dia_primeira_venda
        """

        df_resultado = duck_query(sql)
        
        if df_resultado is None or df_resultado.empty:
            kpi_general = {
                'tempo_primeira_venda_geral': 0.0,
                'tempo_primeira_venda_apos_30d': 0.0,
                'taxa_conversao_30d': 0.0
            }
            df_filial = pd.DataFrame(columns=[
                'filial_codigo', 'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d'
            ])
            df_distribuicao = pd.DataFrame(columns=[
                'dia_primeira_venda', 'total_compras'
            ])
            return kpi_general, df_filial, df_distribuicao

        # Separar os resultados por tipo
        df_kpi_geral = df_resultado[df_resultado['tipo'] == 'kpi_geral']
        df_kpi_filial = df_resultado[df_resultado['tipo'] == 'kpi_filial']
        df_dist = df_resultado[df_resultado['tipo'] == 'distribuicao']

        # Processar KPI geral
        if not df_kpi_geral.empty:
            row = df_kpi_geral.iloc[0]
            kpi_general = {
                'tempo_primeira_venda_geral': float(row['valor1']) if row['valor1'] is not None else 0.0,
                'tempo_primeira_venda_apos_30d': float(row['valor2']) if row['valor2'] is not None else 0.0,
                'taxa_conversao_30d': float(row['valor3']) if row['valor3'] is not None else 0.0
            }
        else:
            kpi_general = {
                'tempo_primeira_venda_geral': 0.0,
                'tempo_primeira_venda_apos_30d': 0.0,
                'taxa_conversao_30d': 0.0
            }

        # Processar KPIs por filial
        if not df_kpi_filial.empty:
            df_filial = df_kpi_filial[['filial_codigo', 'valor1', 'valor2', 'valor3']].copy()
            df_filial.columns = ['filial_codigo', 'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d']
            df_filial['tempo_primeira_venda_geral'] = df_filial['tempo_primeira_venda_geral'].fillna(0.0).astype(float)
            df_filial['tempo_primeira_venda_apos_30d'] = df_filial['tempo_primeira_venda_apos_30d'].fillna(0.0).astype(float)
            df_filial['taxa_conversao_30d'] = df_filial['taxa_conversao_30d'].fillna(0.0).astype(float)
        else:
            df_filial = pd.DataFrame(columns=[
                'filial_codigo', 'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d'
            ])

        # Processar distribuição
        if not df_dist.empty:
            df_distribuicao = df_dist[['dia_primeira_venda', 'valor3']].copy()
            df_distribuicao.columns = ['dia_primeira_venda', 'total_compras']
            df_distribuicao['dia_primeira_venda'] = df_distribuicao['dia_primeira_venda'].astype(int)
            df_distribuicao['total_compras'] = df_distribuicao['total_compras'].fillna(0.0).astype(float)
            df_distribuicao = df_distribuicao.sort_values('dia_primeira_venda')
        else:
            df_distribuicao = pd.DataFrame(columns=['dia_primeira_venda', 'total_compras'])

        return kpi_general, df_filial, df_distribuicao

    except Exception as e:
        st.error(f"Erro ao calcular tempo primeira venda: {e}")
        return {
            'tempo_primeira_venda_geral': 0.0,
            'tempo_primeira_venda_apos_30d': 0.0,
            'taxa_conversao_30d': 0.0
        }, pd.DataFrame(), pd.DataFrame()


def calcular_primeira_venda_geral_por_curva_abc(data_atual):
    """
    Calcula tempo médio (dias) até a PRIMEIRA venda após compra, por combinações de Curva ABC:
      - Por curva ABC (geral da rede)
      - Por curva ABC + filial
      - Por curva ABC + classificacao_n1 (geral da rede)
      - Por curva ABC + filial + classificacao_n1
    """
    try:
        ensure_bases_estoque(str(data_atual))
        ref_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_ref = ref_ontem.strftime('%Y-%m-%d')

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            try:
                duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
            except Exception as e:
                st.error(f"Tabela de Curva ABC não encontrada: {e}")
                return {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}, pd.DataFrame(), pd.DataFrame()

        pairs = []
        for offset in range(30):
            reference_day = ref_ontem - pd.Timedelta(days=offset)
            purchase_date = reference_day - pd.Timedelta(days=90)
            pairs.append((reference_day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{r}', DATE '{p}')" for r, p in pairs])

        sql = f"""
        WITH reference_days(reference_day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras_base AS (
            SELECT
                r.reference_day,
                r.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                SUM(ABS(f.quantidade)) AS qtde_comprada,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) AS valor_comprado,
                f.classificacao_n1
            FROM reference_days r
            JOIN fact_estoque_final f
              ON DATE(f.datahora) = r.purchase_date
             AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid, f.classificacao_n1
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        compras_com_curva AS (
            SELECT
                c.reference_day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_comprada,
                c.valor_comprado,
                c.classificacao_n1,
                COALESCE(ca.curvaABC,'D') AS curvaABC
            FROM compras_base c
            LEFT JOIN curva_abc ca
              ON c.filial_codigo = ca.filial_codigo
             AND c.embalagemid = ca.embalagemid
        ),
        primeira_venda AS (
            SELECT
                c.reference_day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_comprada,
                c.valor_comprado,
                c.classificacao_n1,
                c.curvaABC,
                MIN(v.data_date) AS data_primeira_venda,
                MIN(v.data_date - c.purchase_date) AS dias_primeira_venda
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
              ON v.filial_codigo = c.filial_codigo
             AND v.item_embalagemid = c.embalagemid
             AND v.data_date BETWEEN c.purchase_date + INTERVAL '1 day' AND c.purchase_date + INTERVAL '90 days'
            GROUP BY c.reference_day, c.purchase_date, c.filial_codigo, c.embalagemid, c.qtde_comprada, c.valor_comprado, c.classificacao_n1, c.curvaABC
        ),
        vendas_classificadas AS (
            SELECT
                reference_day,
                purchase_date,
                filial_codigo,
                embalagemid,
                qtde_comprada,
                valor_comprado,
                curvaABC,
                classificacao_n1,
                data_primeira_venda,
                dias_primeira_venda,
                CASE WHEN data_primeira_venda IS NOT NULL THEN 1 ELSE 0 END AS teve_venda,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda <= 30 THEN 1 ELSE 0 END AS vendeu_ate_30d,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda > 30 THEN 1 ELSE 0 END AS vendeu_apos_30d
            FROM primeira_venda
        )
        SELECT
            'combo' AS tipo,
            'Geral' AS filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END AS tempo_primeira_venda_geral,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END AS tempo_primeira_venda_apos_30d,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END AS taxa_conversao_30d
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC

        UNION ALL

        SELECT
            'combo' AS tipo,
            filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC

        UNION ALL

        SELECT
            'combo' AS tipo,
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, classificacao_n1

        UNION ALL

        SELECT
            'combo' AS tipo,
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE classificacao_n1 IS NOT NULL
        GROUP BY classificacao_n1

        UNION ALL

        SELECT
            'combo' AS tipo,
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY curvaABC, classificacao_n1

        UNION ALL

        SELECT
            'combo' AS tipo,
            filial_codigo,
            curvaABC,
            classificacao_n1,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        UNION ALL

        SELECT
            'dist' AS tipo,
            NULL AS filial_codigo,
            NULL AS curvaABC,
            NULL AS classificacao_n1,
            NULL AS tempo_primeira_venda_geral,
            NULL AS tempo_primeira_venda_apos_30d,
            dias_primeira_venda AS taxa_conversao_30d
        FROM (
            SELECT dias_primeira_venda, COUNT(*) AS total
            FROM vendas_classificadas
            WHERE teve_venda = 1 AND dias_primeira_venda IS NOT NULL
            GROUP BY dias_primeira_venda
            ORDER BY dias_primeira_venda
        )
        """

        df = duck_query(sql)
        if df is None or df.empty:
            # retornar estruturas vazias padronizadas
            kpi_general = {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}
            return kpi_general, pd.DataFrame(), pd.DataFrame()

        # separar métricas e distribuição
        df_combo = df[df['tipo'] == 'combo'].copy()
        df_dist = df[df['tipo'] == 'dist'].copy()

        # renomear colunas do resultado combo
        if not df_combo.empty:
            df_combo = df_combo[['filial_codigo', 'curvaABC', 'classificacao_n1',
                                 df_combo.columns[4], df_combo.columns[5], df_combo.columns[6]]].copy()
            df_combo.columns = ['filial_codigo', 'curvaABC', 'classificacao_n1',
                                'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d']
        else:
            df_combo = pd.DataFrame(columns=['filial_codigo', 'curvaABC', 'classificacao_n1',
                                             'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d'])

        # distribuição: coluna 'taxa_conversao_30d' veio com dias (como usamos campo temporário)
        if not df_dist.empty:
            df_distribuicao = df_dist[['taxa_conversao_30d']].copy()
            df_distribuicao.columns = ['dia_primeira_venda']
            # contar total por dia precisa ser recalculado via query separada para obter contagens
            # executar pequena query para contagem real da distribuição
            sql_dist = f"""
            WITH reference_days(reference_day, purchase_date) AS (VALUES {values_sql}),
            compras_base AS (
                SELECT r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid, SUM(ABS(f.quantidade)) AS qtde_comprada
                FROM reference_days r
                JOIN fact_estoque_final f
                  ON DATE(f.datahora) = r.purchase_date
                  AND f.descricao_movimentacao = 'Recebimento Físico'
                GROUP BY r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid
            ),
            primeira_por_compra AS (
                SELECT
                    c.reference_day,
                    c.purchase_date,
                    c.filial_codigo,
                    c.embalagemid,
                    MIN(v.data_date) AS data_primeira_venda,
                    MIN(v.data_date - c.purchase_date) AS dias_primeira_venda
                FROM compras_base c
                LEFT JOIN fact_vendas_final v
                  ON v.filial_codigo = c.filial_codigo
                  AND v.item_embalagemid = c.embalagemid
                  AND v.data_date BETWEEN c.purchase_date + INTERVAL '1 day' AND c.purchase_date + INTERVAL '90 days'
                GROUP BY c.reference_day, c.purchase_date, c.filial_codigo, c.embalagemid
            )
            SELECT
                dias_primeira_venda::INTEGER AS dia_primeira_venda,
                COUNT(*) AS total_compras
            FROM primeira_por_compra
            WHERE dias_primeira_venda IS NOT NULL
            GROUP BY dias_primeira_venda
            ORDER BY dias_primeira_venda
            """
            df_dist_real = duck_query(sql_dist)
            if df_dist_real is None or df_dist_real.empty:
                df_distribuicao = pd.DataFrame(columns=['dia_primeira_venda', 'total_compras'])
            else:
                df_distribuicao = df_dist_real.copy()
                df_distribuicao['dia_primeira_venda'] = df_distribuicao['dia_primeira_venda'].astype(int)
                df_distribuicao['total_compras'] = df_distribuicao['total_compras'].astype(int)
        else:
            df_distribuicao = pd.DataFrame(columns=['dia_primeira_venda', 'total_compras'])

        # KPI geral: linha onde filial='Geral' e curvaABC='Geral' e classificacao_n1='Geral' não existe diretamente
        # construímos kpi geral agregando todos os registros (equivalente à visão global)
        if not df_combo.empty:
            # prefer row where filial='Geral' and classificacao='Geral' and curvaABC='Geral' if present
            mask_general = (df_combo['filial_codigo'] == 'Geral') & (df_combo['curvaABC'] == 'Geral') & (df_combo['classificacao_n1'] == 'Geral')
            if mask_general.any():
                row = df_combo[mask_general].iloc[0]
                kpi_general = {
                    'tempo_primeira_venda_geral': float(row['tempo_primeira_venda_geral']),
                    'tempo_primeira_venda_apos_30d': float(row['tempo_primeira_venda_apos_30d']),
                    'taxa_conversao_30d': float(row['taxa_conversao_30d'])
                }
            else:
                kpi_general = {
                    'tempo_primeira_venda_geral': float(df_combo['tempo_primeira_venda_geral'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0,
                    'tempo_primeira_venda_apos_30d': float(df_combo['tempo_primeira_venda_apos_30d'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0,
                    'taxa_conversao_30d': float(df_combo['taxa_conversao_30d'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0
                }
        else:
            kpi_general = {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}

        # garantir tipos/ordenação mínimos
        if 'taxa_conversao_30d' in df_combo.columns:
            df_combo['taxa_conversao_30d'] = df_combo['taxa_conversao_30d'].astype(float)
        return kpi_general, df_combo.reset_index(drop=True), df_distribuicao.reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao calcular tempo até primeira venda por Curva ABC: {e}")
        return {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}, pd.DataFrame(), pd.DataFrame()


def calcular_primeira_venda_por_classificacao_n2(data_atual):
    """
    Calcula tempo médio (dias) até a PRIMEIRA venda após compra, por classificacao_n2 (subgrupo) e suas combinações.
    
    Calcula por classificacao_n2 e suas combinações:
    - Por classificacao_n2 (geral da rede)
    - Por classificacao_n2 + filial
    - Por curva ABC + classificacao_n2 (geral da rede)
    - Por curva ABC + filial + classificacao_n2

    Retorna: kpi_general (dict), df_combinacoes (DataFrame com linhas por combinação),
             df_distribuicao (DataFrame com distribuição de dias até primeira venda)
    """
    try:
        ensure_bases_estoque(str(data_atual))
        ref_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_ref = ref_ontem.strftime('%Y-%m-%d')

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        pairs = []
        for offset in range(30):
            reference_day = ref_ontem - pd.Timedelta(days=offset)
            purchase_date = reference_day - pd.Timedelta(days=90)
            pairs.append((reference_day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{r}', DATE '{p}')" for r, p in pairs])

        sql = f"""
        WITH reference_days(reference_day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras_base AS (
            SELECT
                r.reference_day,
                r.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                SUM(ABS(f.quantidade)) AS qtde_comprada,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) AS valor_comprado,
                f.classificacao_n2
            FROM reference_days r
            JOIN fact_estoque_final f
              ON DATE(f.datahora) = r.purchase_date
             AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid, f.classificacao_n2
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        compras_com_curva AS (
            SELECT
                c.reference_day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_comprada,
                c.valor_comprado,
                c.classificacao_n2,
                COALESCE(ca.curvaABC, 'D') AS curvaABC
            FROM compras_base c
            LEFT JOIN curva_abc ca
              ON c.filial_codigo = ca.filial_codigo
             AND c.embalagemid = ca.embalagemid
        ),
        primeira_venda AS (
            SELECT
                c.reference_day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_comprada,
                c.valor_comprado,
                c.classificacao_n2,
                c.curvaABC,
                MIN(v.data_date) AS data_primeira_venda,
                MIN(v.data_date - c.purchase_date) AS dias_primeira_venda
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
              ON v.filial_codigo = c.filial_codigo
             AND v.item_embalagemid = c.embalagemid
             AND v.data_date BETWEEN c.purchase_date + INTERVAL '1 day' AND c.purchase_date + INTERVAL '90 days'
            GROUP BY c.reference_day, c.purchase_date, c.filial_codigo, c.embalagemid, c.qtde_comprada, c.valor_comprado, c.classificacao_n2, c.curvaABC
        ),
        vendas_classificadas AS (
            SELECT
                reference_day,
                purchase_date,
                filial_codigo,
                embalagemid,
                qtde_comprada,
                valor_comprado,
                curvaABC,
                classificacao_n2,
                data_primeira_venda,
                dias_primeira_venda,
                CASE WHEN data_primeira_venda IS NOT NULL THEN 1 ELSE 0 END AS teve_venda,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda <= 30 THEN 1 ELSE 0 END AS vendeu_ate_30d,
                CASE WHEN dias_primeira_venda IS NOT NULL AND dias_primeira_venda > 30 THEN 1 ELSE 0 END AS vendeu_apos_30d
            FROM primeira_venda
        )
        SELECT
            'combo' AS tipo,
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END AS tempo_primeira_venda_geral,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END AS tempo_primeira_venda_apos_30d,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END AS taxa_conversao_30d
        FROM vendas_classificadas
        WHERE classificacao_n2 IS NOT NULL
        GROUP BY classificacao_n2

        UNION ALL

        SELECT
            'combo' AS tipo,
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE classificacao_n2 IS NOT NULL
        GROUP BY filial_codigo, classificacao_n2

        UNION ALL

        SELECT
            'combo' AS tipo,
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n2,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL AND classificacao_n2 IS NOT NULL
        GROUP BY curvaABC, classificacao_n2

        UNION ALL

        SELECT
            'combo' AS tipo,
            filial_codigo,
            curvaABC,
            classificacao_n2,
            CASE WHEN SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN teve_venda=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN teve_venda=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END) > 0
                 THEN ROUND(SUM(CASE WHEN vendeu_apos_30d=1 THEN dias_primeira_venda * qtde_comprada ELSE 0 END) /
                            SUM(CASE WHEN vendeu_apos_30d=1 THEN qtde_comprada ELSE 0 END), 1)
                 ELSE 0.0 END,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND(SUM(vendeu_ate_30d) * 100.0 / COUNT(*), 1)
                 ELSE 0.0 END
        FROM vendas_classificadas
        WHERE curvaABC IS NOT NULL AND classificacao_n2 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n2

        UNION ALL

        SELECT
            'dist' AS tipo,
            NULL AS filial_codigo,
            NULL AS curvaABC,
            NULL AS classificacao_n2,
            NULL AS tempo_primeira_venda_geral,
            NULL AS tempo_primeira_venda_apos_30d,
            dias_primeira_venda AS taxa_conversao_30d
        FROM (
            SELECT dias_primeira_venda, COUNT(*) AS total
            FROM vendas_classificadas
            WHERE teve_venda = 1 AND dias_primeira_venda IS NOT NULL
            GROUP BY dias_primeira_venda
            ORDER BY dias_primeira_venda
        )
        """

        df = duck_query(sql)
        if df is None or df.empty:
            kpi_general = {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}
            return kpi_general, pd.DataFrame(), pd.DataFrame()

        df_combo = df[df['tipo'] == 'combo'].copy()
        df_dist = df[df['tipo'] == 'dist'].copy()

        if not df_combo.empty:
            df_combo = df_combo[['filial_codigo', 'curvaABC', 'classificacao_n2',
                                 df_combo.columns[4], df_combo.columns[5], df_combo.columns[6]]].copy()
            df_combo.columns = ['filial_codigo', 'curvaABC', 'classificacao_n2',
                                'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d']
        else:
            df_combo = pd.DataFrame(columns=['filial_codigo', 'curvaABC', 'classificacao_n2',
                                             'tempo_primeira_venda_geral', 'tempo_primeira_venda_apos_30d', 'taxa_conversao_30d'])

        if not df_dist.empty:
            df_distribuicao = df_dist[['taxa_conversao_30d']].copy()
            df_distribuicao.columns = ['dia_primeira_venda']
            sql_dist = f"""
            WITH reference_days(reference_day, purchase_date) AS (VALUES {values_sql}),
            compras_base AS (
                SELECT r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid, SUM(ABS(f.quantidade)) AS qtde_comprada
                FROM reference_days r
                JOIN fact_estoque_final f
                  ON DATE(f.datahora) = r.purchase_date
                 AND f.descricao_movimentacao = 'Recebimento Físico'
                GROUP BY r.reference_day, r.purchase_date, f.filial_codigo, f.embalagemid
            ),
            primeira_por_compra AS (
                SELECT
                    c.reference_day,
                    c.purchase_date,
                    c.filial_codigo,
                    c.embalagemid,
                    MIN(v.data_date) AS data_primeira_venda,
                    MIN(v.data_date - c.purchase_date) AS dias_primeira_venda
                FROM compras_base c
                LEFT JOIN fact_vendas_final v
                  ON v.filial_codigo = c.filial_codigo
                 AND v.item_embalagemid = c.embalagemid
                 AND v.data_date BETWEEN c.purchase_date + INTERVAL '1 day' AND c.purchase_date + INTERVAL '90 days'
                GROUP BY c.reference_day, c.purchase_date, c.filial_codigo, c.embalagemid
            )
            SELECT
                dias_primeira_venda::INTEGER AS dia_primeira_venda,
                COUNT(*) AS total_compras
            FROM primeira_por_compra
            WHERE dias_primeira_venda IS NOT NULL
            GROUP BY dias_primeira_venda
            ORDER BY dias_primeira_venda
            """
            df_dist_real = duck_query(sql_dist)
            if df_dist_real is None or df_dist_real.empty:
                df_distribuicao = pd.DataFrame(columns=['dia_primeira_venda', 'total_compras'])
            else:
                df_distribuicao = df_dist_real.copy()
                df_distribuicao['dia_primeira_venda'] = df_distribuicao['dia_primeira_venda'].astype(int)
                df_distribuicao['total_compras'] = df_distribuicao['total_compras'].astype(int)
        else:
            df_distribuicao = pd.DataFrame(columns=['dia_primeira_venda', 'total_compras'])

        if not df_combo.empty:
            mask_general = (df_combo['filial_codigo'] == 'Geral') & (df_combo['curvaABC'] == 'Geral') & (df_combo['classificacao_n2'] == 'Geral')
            if mask_general.any():
                row = df_combo[mask_general].iloc[0]
                kpi_general = {
                    'tempo_primeira_venda_geral': float(row['tempo_primeira_venda_geral']),
                    'tempo_primeira_venda_apos_30d': float(row['tempo_primeira_venda_apos_30d']),
                    'taxa_conversao_30d': float(row['taxa_conversao_30d'])
                }
            else:
                kpi_general = {
                    'tempo_primeira_venda_geral': float(df_combo['tempo_primeira_venda_geral'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0,
                    'tempo_primeira_venda_apos_30d': float(df_combo['tempo_primeira_venda_apos_30d'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0,
                    'taxa_conversao_30d': float(df_combo['taxa_conversao_30d'].replace('', 0).astype(float).mean()) if not df_combo.empty else 0.0
                }
        else:
            kpi_general = {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}

        if 'taxa_conversao_30d' in df_combo.columns:
            df_combo['taxa_conversao_30d'] = df_combo['taxa_conversao_30d'].astype(float)
        
        return kpi_general, df_combo.reset_index(drop=True), df_distribuicao.reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao calcular tempo até primeira venda por classificacao_n2: {e}")
        return {'tempo_primeira_venda_geral': 0.0, 'tempo_primeira_venda_apos_30d': 0.0, 'taxa_conversao_30d': 0.0}, pd.DataFrame(), pd.DataFrame()