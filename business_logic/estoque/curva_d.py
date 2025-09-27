import pandas as pd
import streamlit as st
import numpy as np
from core.database import duck_query
from business_logic.estoque.base_sets import ensure_bases_estoque

def calcular_indice_curva_d_geral(data_atual):
    """
    Versão usando temp_recebimentos_121d e temp_vendas_121d (criadas em base_sets).
    """
    try:
        ref_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()

        pairs = []
        for offset in range(30):
            day = ref_ontem - pd.Timedelta(days=1 + offset)   # dia de referência
            purchase_date = day - pd.Timedelta(days=91)       # purchase_date = day - 91
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join(f"(DATE '{d}', DATE '{p}')" for d, p in pairs)

        # Menor purchase_date (para qualquer eventual filtro se fosse preciso)
        min_purchase_date = min(p[1] for p in pairs)
        max_day = max(p[0] for p in pairs)

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                r.filial_codigo,
                r.embalagemid,
                SUM(r.quantidade) AS total_qtde,
                CASE WHEN SUM(r.quantidade)=0 THEN 0
                     ELSE SUM(r.quantidade * r.customedio)/SUM(r.quantidade) END AS customedio_med,
                SUM(r.quantidade * r.customedio) AS total_valor
            FROM days d
            JOIN temp_recebimentos_121d r
              ON r.data_compra = d.purchase_date
            GROUP BY d.day, d.purchase_date, r.filial_codigo, r.embalagemid
        ),
        vendas_periodo AS (
            SELECT filial_codigo,
                   embalagemid,
                   data_date,
                   qtde_vendida
            FROM temp_vendas_121d
            WHERE data_date BETWEEN DATE '{min_purchase_date}' AND DATE '{max_day}'
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.total_qtde,
                c.customedio_med,
                c.total_valor,
                COUNT(*) FILTER (
                   WHERE v.data_date BETWEEN c.purchase_date AND c.day
                ) AS vendas_cnt,
                COALESCE(SUM(
                   CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day
                        THEN v.qtde_vendida ELSE 0 END),0) AS vendas_qtde
            FROM compras c
            LEFT JOIN vendas_periodo v
              ON v.filial_codigo = c.filial_codigo
             AND v.embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid,
                     c.total_qtde, c.customedio_med, c.total_valor
        )
        SELECT
            day,
            purchase_date,
            filial_codigo,
            embalagemid,
            total_qtde,
            customedio_med,
            total_valor,
            vendas_cnt,
            vendas_qtde,
            CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END AS produto_curva_d,
            CASE WHEN SUM(total_qtde) OVER () = 0 THEN 0
                 ELSE (total_qtde * 100.0 / SUM(total_qtde) OVER ()) END AS pct_quantity,
            CASE WHEN SUM(total_valor) OVER () = 0 THEN 0
                 ELSE (total_valor * 100.0 / SUM(total_valor) OVER ()) END AS pct_value
        FROM vendas_por_compra
        ORDER BY purchase_date, filial_codigo, total_valor DESC
        """

        df_itemizado = duck_query(sql)

        # (restante igual à versão refatorada anterior)
        if df_itemizado is None or df_itemizado.empty:
            kpi_general = {
                'total_denom': 0,'total_numer': 0,
                'total_qtde_all': 0,'total_qtde_curva_d': 0,
                'total_val_all': 0.0,'total_val_curva_d': 0.0,
                'pct_unique': 0.0,'pct_quantity': 0.0,'pct_value': 0.0
            }
            df_filial = pd.DataFrame(columns=[
                'filial_codigo','total_denom','total_numer',
                'total_qtde_all','total_qtde_curva_d',
                'total_val_all','total_val_curva_d',
                'pct_unique','pct_quantity','pct_value'
            ])
            return kpi_general, df_filial, pd.DataFrame()

        for col in ['total_qtde','total_valor','vendas_cnt','vendas_qtde','produto_curva_d','pct_quantity','pct_value']:
            if col in df_itemizado.columns:
                df_itemizado[col] = pd.to_numeric(df_itemizado[col], errors='coerce').fillna(0)

        df_itemizado['day'] = pd.to_datetime(df_itemizado['day']).dt.date
        df_itemizado['purchase_date'] = pd.to_datetime(df_itemizado['purchase_date']).dt.date
        df_itemizado['qtde_curva_masked'] = df_itemizado['total_qtde'] * df_itemizado['produto_curva_d']
        df_itemizado['val_curva_masked'] = df_itemizado['total_valor'] * df_itemizado['produto_curva_d']

        total_denom = int(df_itemizado.shape[0])
        total_numer = int(df_itemizado['produto_curva_d'].sum())
        total_qtde_all = float(df_itemizado['total_qtde'].sum())
        total_qtde_curva = float(df_itemizado['qtde_curva_masked'].sum())
        total_val_all = float(df_itemizado['total_valor'].sum())
        total_val_curva = float(df_itemizado['val_curva_masked'].sum())

        kpi_general = {
            'total_denom': total_denom,
            'total_numer': total_numer,
            'total_qtde_all': int(total_qtde_all),
            'total_qtde_curva_d': int(total_qtde_curva),
            'total_val_all': round(total_val_all,2),
            'total_val_curva_d': round(total_val_curva,2),
            'pct_unique': round((total_numer*100/total_denom) if total_denom else 0,4),
            'pct_quantity': round((total_qtde_curva*100/total_qtde_all) if total_qtde_all else 0,4),
            'pct_value': round((total_val_curva*100/total_val_all) if total_val_all else 0,4),
        }

        df_filial = (
            df_itemizado
            .groupby('filial_codigo', dropna=False)
            .agg(
                total_denom=('embalagemid','count'),
                total_numer=('produto_curva_d','sum'),
                total_qtde_all=('total_qtde','sum'),
                total_qtde_curva_d=('qtde_curva_masked','sum'),
                total_val_all=('total_valor','sum'),
                total_val_curva_d=('val_curva_masked','sum')
            ).reset_index()
        )
        df_filial['pct_unique'] = df_filial.apply(lambda r: (r.total_numer*100/r.total_denom) if r.total_denom else 0, axis=1)
        df_filial['pct_quantity'] = df_filial.apply(lambda r: (r.total_qtde_curva_d*100/r.total_qtde_all) if r.total_qtde_all else 0, axis=1)
        df_filial['pct_value'] = df_filial.apply(lambda r: (r.total_val_curva_d*100/r.total_val_all) if r.total_val_all else 0, axis=1)

        for c in ['total_denom','total_numer','total_qtde_all','total_qtde_curva_d']:
            df_filial[c] = df_filial[c].astype(int)
        df_filial['total_val_all'] = df_filial['total_val_all'].round(2)
        df_filial['total_val_curva_d'] = df_filial['total_val_curva_d'].round(2)
        for c in ['pct_unique','pct_quantity','pct_value']:
            df_filial[c] = df_filial[c].round(4)

        return kpi_general, df_filial, df_itemizado

    except Exception as e:
        st.error(f"Erro Curva D (bases materializadas): {e}")
        zero = {
            'total_denom':0,'total_numer':0,'total_qtde_all':0,'total_qtde_curva_d':0,
            'total_val_all':0.0,'total_val_curva_d':0.0,'pct_unique':0.0,'pct_quantity':0.0,'pct_value':0.0
        }
        return zero, pd.DataFrame(), pd.DataFrame()

def calcular_indice_curva_d_por_curva_abc(data_atual):
    """
    Calcula indicador "Curva D" por curva ABC e suas combinações.
    Agora inclui agregações por produto único, quantidade total e valor:
      - total_unicos_denom (COUNT DISTINCT embalagemid)
      - produtos_unicos_curva_d (COUNT DISTINCT embalagemid com vendas_cnt = 0)
      - total_qtde_all / total_qtde_curva_d
      - total_val_all / total_val_curva_d
      - indice_curva_d (produtos_unicos_curva_d * 100 / total_unicos_denom)
    Retorna DataFrame com colunas apropriadas para cada combinação:
      filial_codigo, curvaABC, classificacao_n1,
      total_unicos_denom, produtos_unicos_curva_d,
      total_qtde_all, total_qtde_curva_d,
      total_val_all, total_val_curva_d,
      indice_curva_d
    """
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        # normalizar data
        if isinstance(data_limite_ontem, (str,)):
            data = pd.to_datetime(data_limite_ontem).date()
        elif isinstance(data_limite_ontem, pd.Timestamp):
            data = data_limite_ontem.date()
        else:
            data = data_limite_ontem

        # construir lista de (day, purchase_date) para os últimos 30 dias
        pairs = []
        for offset in range(30):
            day = data - pd.Timedelta(days=1 + offset)
            purchase_date = day - pd.Timedelta(days=91)
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{d}', DATE '{p}')" for d, p in pairs])

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        -- Agregar compras por day/purchase_date/filial/embalagemid com qtde e valor
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                SUM(ABS(f.quantidade)) AS total_qtde,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) AS total_valor,
                -- opcional: customedio médio ponderado
                CASE WHEN SUM(ABS(f.quantidade)) = 0 THEN 0
                     ELSE SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) / SUM(ABS(f.quantidade))
                END AS customedio_med,
                f.classificacao_n1,
                f.classificacao_n2,
                f.classificacao_n3
            FROM days d
            JOIN fact_estoque_final f
                ON DATE(f.datahora) = d.purchase_date
                AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY d.day, d.purchase_date, f.filial_codigo, f.embalagemid, f.classificacao_n1, f.classificacao_n2, f.classificacao_n3
        ),
        -- Curva ABC baseada nos últimos 90 dias de vendas
        vendas_90d_abc AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                item_embalagemid AS embalagemid,
                SUM(ABS(item_quantidade)) AS quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date >= DATE '{(pd.to_datetime(data) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')}'
              AND data_date <= DATE '{data.strftime('%Y-%m-%d')}'
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
            FROM vendas_90d_abc
        ),
        produtos_com_curva AS (
            SELECT 
                filial_codigo,
                embalagemid,
                CASE 
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
                    WHEN total_vendas_grupo > 0 THEN 'C'
                    ELSE 'D'
                END AS curvaABC
            FROM vendas_com_acumulado
        ),
        compras_com_curva AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.total_qtde,
                c.total_valor,
                c.customedio_med,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                COALESCE(pc.curvaABC, 'D') AS curvaABC
            FROM compras c
            LEFT JOIN produtos_com_curva pc
                ON c.filial_codigo = pc.filial_codigo AND c.embalagemid = pc.embalagemid
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.total_qtde,
                c.total_valor,
                c.customedio_med,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                c.curvaABC,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) AS vendas_cnt,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN ABS(v.item_quantidade) ELSE 0 END) AS vendas_qtde
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
                ON v.filial_codigo = c.filial_codigo AND v.item_embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid,
                     c.total_qtde, c.total_valor, c.customedio_med,
                     c.classificacao_n1, c.classificacao_n2, c.classificacao_n3, c.curvaABC
        )

        -- 1) Por curva ABC (geral da rede) - agregações por produto único, qtde e valor
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC

        UNION ALL

        -- 2) Por curva ABC + filial
        SELECT
            filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC

        UNION ALL

        -- 3) Por curva ABC + classificacao_n1 (geral da rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY curvaABC, classificacao_n1

        UNION ALL

        -- 4) Por curva ABC + filial + classificacao_n1
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """

        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()

    except Exception as e:
        st.error(f"Erro ao calcular índice de Curva D por curva ABC: {e}")
        return pd.DataFrame()

def calcular_indice_curva_d_por_classificacao_n1(data_atual):
    """
    Calcula indicador "Curva D" por classificacao_n1 e suas combinações:
    - Por classificacao_n1 (geral da rede)
    - Por classificacao_n1 + filial
    - Por classificacao_n1 + curva ABC (geral da rede)
    - Por classificacao_n1 + filial + curva ABC
    """
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        ensure_bases_estoque(str(data_atual))

        if isinstance(data_limite_ontem, (str,)):
            data = pd.to_datetime(data_limite_ontem).date()
        elif isinstance(data_limite_ontem, pd.Timestamp):
            data = data_limite_ontem.date()
        else:
            data = data_limite_ontem

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        pairs = []
        for offset in range(30):
            day = data - pd.Timedelta(days=1 + offset)
            purchase_date = day - pd.Timedelta(days=91)
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{d}', DATE '{p}')" for d, p in pairs])
        data_ref = data.strftime('%Y-%m-%d')

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                f.classificacao_n1,
                f.classificacao_n2,
                f.classificacao_n3
            FROM days d
            JOIN fact_estoque_final f
                ON DATE(f.datahora) = d.purchase_date
                AND f.descricao_movimentacao = 'Recebimento Físico'
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        compras_com_curva AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                COALESCE(ca.curvaABC, 'D') AS curvaABC
            FROM compras c
            LEFT JOIN curva_abc ca
                ON c.filial_codigo = ca.filial_codigo
               AND c.embalagemid = ca.embalagemid
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                c.curvaABC,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) AS vendas_cnt
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
                ON v.filial_codigo = c.filial_codigo AND v.item_embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid, c.classificacao_n1, c.classificacao_n2, c.classificacao_n3, c.curvaABC
        )
        SELECT 
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE 
                WHEN COUNT(*) > 0 
                THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE classificacao_n1 IS NOT NULL
        GROUP BY classificacao_n1
        
        UNION ALL
        
        SELECT 
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE 
                WHEN COUNT(*) > 0 
                THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, classificacao_n1
        
        UNION ALL
        
        SELECT 
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE 
                WHEN COUNT(*) > 0 
                THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE classificacao_n1 IS NOT NULL AND curvaABC IS NOT NULL
        GROUP BY curvaABC, classificacao_n1
        
        UNION ALL
        
        SELECT 
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE 
                WHEN COUNT(*) > 0 
                THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE classificacao_n1 IS NOT NULL AND curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1
        
        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """

        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()

    except Exception as e:
        st.error(f"Erro ao calcular índice de Curva D por classificacao_n1: {e}")
        return pd.DataFrame()

def calcular_indice_curva_d_por_classificacao_n2_geral(data_atual):
    """
    Calcula indicador "Curva D" por classificacao_n2 (subgrupo) e suas combinações.
    Versão empilhada por day+purchase_date+filial+produto, similar à função geral.
    
    Calcula por classificacao_n2 e suas combinações:
    - Por classificacao_n2 (geral da rede)
    - Por classificacao_n2 + filial
    - Por classificacao_n2 + curva ABC (geral da rede)
    - Por classificacao_n2 + filial + curva ABC
    
    Retorna (kpi_general, df_combinacoes):
      - kpi_general: {'pct_unique','pct_quantity','pct_value', totals...} - KPIs globais
      - df_combinacoes: DataFrame com colunas:
          filial_codigo, curvaABC, classificacao_n2,
          total_denom, total_numer, total_qtde_all, total_qtde_curva_d,
          total_val_all, total_val_curva_d, pct_unique, pct_quantity, pct_value
    """
    try:
        ensure_bases_estoque(str(data_atual))
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_ref = ontem.strftime('%Y-%m-%d')

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        pairs = []
        for offset in range(30):
            day = ontem - pd.Timedelta(days=1 + offset)
            purchase_date = day - pd.Timedelta(days=91)
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{d}', DATE '{p}')" for d, p in pairs])

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                f.classificacao_n1,
                f.classificacao_n2,
                f.classificacao_n3,
                SUM(ABS(f.quantidade)) AS total_qtde,
                CASE WHEN SUM(ABS(f.quantidade)) = 0 THEN 0
                     ELSE SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) / SUM(ABS(f.quantidade))
                END AS customedio_med,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) AS total_valor
            FROM days d
            JOIN fact_estoque_final f
              ON DATE(f.datahora) = d.purchase_date
             AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY d.day, d.purchase_date, f.filial_codigo, f.embalagemid,
                     f.classificacao_n1, f.classificacao_n2, f.classificacao_n3
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        compras_com_curva AS (
            SELECT
                c.*,
                COALESCE(ca.curvaABC, 'D') AS curvaABC
            FROM compras c
            LEFT JOIN curva_abc ca
              ON c.filial_codigo = ca.filial_codigo
             AND c.embalagemid = ca.embalagemid
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                c.curvaABC,
                c.total_qtde,
                c.customedio_med,
                c.total_valor,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) AS vendas_cnt,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN ABS(v.item_quantidade) ELSE 0 END) AS vendas_qtde,
                CASE WHEN SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) = 0 OR
                          SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) IS NULL THEN 1 ELSE 0 END AS produto_curva_d
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
              ON v.filial_codigo = c.filial_codigo
             AND v.item_embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid,
                     c.classificacao_n1, c.classificacao_n2, c.classificacao_n3, c.curvaABC,
                     c.total_qtde, c.customedio_med, c.total_valor
        ),
        dados_com_mascaras AS (
            SELECT
                *,
                total_qtde * produto_curva_d AS qtde_curva_masked,
                total_valor * produto_curva_d AS val_curva_masked
            FROM vendas_por_compra
            WHERE classificacao_n2 IS NOT NULL
        )
        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_curva_d) AS total_numer,
            SUM(total_qtde) AS total_qtde_all,
            SUM(qtde_curva_masked) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(val_curva_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_curva_d) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(total_qtde) > 0
                 THEN (SUM(qtde_curva_masked) * 100.0 / SUM(total_qtde))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(total_valor) > 0
                 THEN (SUM(val_curva_masked) * 100.0 / SUM(total_valor))
                 ELSE 0 END AS pct_value
        FROM dados_com_mascaras
        GROUP BY classificacao_n2

        UNION ALL

        SELECT
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_curva_d) AS total_numer,
            SUM(total_qtde) AS total_qtde_all,
            SUM(qtde_curva_masked) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(val_curva_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_curva_d) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(total_qtde) > 0
                 THEN (SUM(qtde_curva_masked) * 100.0 / SUM(total_qtde))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(total_valor) > 0
                 THEN (SUM(val_curva_masked) * 100.0 / SUM(total_valor))
                 ELSE 0 END AS pct_value
        FROM dados_com_mascaras
        GROUP BY filial_codigo, classificacao_n2

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_curva_d) AS total_numer,
            SUM(total_qtde) AS total_qtde_all,
            SUM(qtde_curva_masked) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(val_curva_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_curva_d) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(total_qtde) > 0
                 THEN (SUM(qtde_curva_masked) * 100.0 / SUM(total_qtde))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(total_valor) > 0
                 THEN (SUM(val_curva_masked) * 100.0 / SUM(total_valor))
                 ELSE 0 END AS pct_value
        FROM dados_com_mascaras
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC, classificacao_n2

        UNION ALL

        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_curva_d) AS total_numer,
            SUM(total_qtde) AS total_qtde_all,
            SUM(qtde_curva_masked) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(val_curva_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_curva_d) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(total_qtde) > 0
                 THEN (SUM(qtde_curva_masked) * 100.0 / SUM(total_qtde))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(total_valor) > 0
                 THEN (SUM(val_curva_masked) * 100.0 / SUM(total_valor))
                 ELSE 0 END AS pct_value
        FROM dados_com_mascaras
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n2

        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df_combinacoes = duck_query(sql)

        if df_combinacoes is None or df_combinacoes.empty:
            kpi_general = {
                'total_denom': 0,
                'total_numer': 0,
                'total_qtde_all': 0,
                'total_qtde_curva_d': 0,
                'total_val_all': 0.0,
                'total_val_curva_d': 0.0,
                'pct_unique': 0.0,
                'pct_quantity': 0.0,
                'pct_value': 0.0,
            }
            return kpi_general, pd.DataFrame()

        numeric_cols = ['total_denom', 'total_numer', 'total_qtde_all', 'total_qtde_curva_d',
                        'total_val_all', 'total_val_curva_d', 'pct_unique', 'pct_quantity', 'pct_value']
        for col in numeric_cols:
            if col in df_combinacoes.columns:
                df_combinacoes[col] = pd.to_numeric(df_combinacoes[col], errors='coerce').fillna(0)

        total_denom = int(df_combinacoes['total_denom'].sum())
        total_numer = int(df_combinacoes['total_numer'].sum())
        total_qtde_all = float(df_combinacoes['total_qtde_all'].sum())
        total_qtde_curva = float(df_combinacoes['total_qtde_curva_d'].sum())
        total_val_all = float(df_combinacoes['total_val_all'].sum())
        total_val_curva = float(df_combinacoes['total_val_curva_d'].sum())

        pct_unique = (total_numer * 100.0 / total_denom) if total_denom > 0 else 0.0
        pct_quantity = (total_qtde_curva * 100.0 / total_qtde_all) if total_qtde_all > 0 else 0.0
        pct_value = (total_val_curva * 100.0 / total_val_all) if total_val_all > 0 else 0.0

        kpi_general = {
            'total_denom': total_denom,
            'total_numer': total_numer,
            'total_qtde_all': int(total_qtde_all),
            'total_qtde_curva_d': int(total_qtde_curva),
            'total_val_all': round(total_val_all, 2),
            'total_val_curva_d': round(total_val_curva, 2),
            'pct_unique': round(pct_unique, 4),
            'pct_quantity': round(pct_quantity, 4),
            'pct_value': round(pct_value, 4),
        }

        int_cols = ['total_denom', 'total_numer', 'total_qtde_all', 'total_qtde_curva_d']
        for c in int_cols:
            if c in df_combinacoes.columns:
                df_combinacoes[c] = df_combinacoes[c].astype(int)

        df_combinacoes['total_val_all'] = df_combinacoes['total_val_all'].round(2)
        df_combinacoes['total_val_curva_d'] = df_combinacoes['total_val_curva_d'].round(2)
        df_combinacoes['pct_unique'] = df_combinacoes['pct_unique'].round(4)
        df_combinacoes['pct_quantity'] = df_combinacoes['pct_quantity'].round(4)
        df_combinacoes['pct_value'] = df_combinacoes['pct_value'].round(4)

        return kpi_general, df_combinacoes.reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao calcular índice Curva D por classificacao_n2: {e}")
        kpi_zero = {
            'total_denom': 0,
            'total_numer': 0,
            'total_qtde_all': 0,
            'total_qtde_curva_d': 0,
            'total_val_all': 0.0,
            'total_val_curva_d': 0.0,
            'pct_unique': 0.0,
            'pct_quantity': 0.0,
            'pct_value': 0.0,
        }
        return kpi_zero, pd.DataFrame()

def calcular_indice_curva_d_por_laboratorio(data_atual, lab_col='fabricante_nome'):
    """
    Calcula indicador "Curva D" por laboratório (fabricante) e combinações:
      1) Agregado geral por fabricante ('Geral' AS filial_codigo, fabricante_nome)
      2) Por fabricante + filial (filial_codigo, fabricante_nome)
      3) Por fabricante + curva ABC (geral da rede)
      4) Por fabricante + filial + curva ABC
    Segue o mesmo padrão das funções por classificacao_n*.
    """
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        # normalizar data
        if isinstance(data_limite_ontem, (str,)):
            data = pd.to_datetime(data_limite_ontem).date()
        elif isinstance(data_limite_ontem, pd.Timestamp):
            data = data_limite_ontem.date()
        else:
            data = data_limite_ontem

        # construir lista (day, purchase_date) últimos 30 dias
        pairs = []
        for offset in range(30):
            day = data - pd.Timedelta(days=1 + offset)
            purchase_date = day - pd.Timedelta(days=91)
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join([f"(DATE '{d}', DATE '{p}')" for d, p in pairs])

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                COALESCE(f.{lab_col}, 'Sem fabricante') AS fabricante_nome,
                f.classificacao_n1,
                f.classificacao_n2,
                f.classificacao_n3
            FROM days d
            JOIN fact_estoque_final f
                ON DATE(f.datahora) = d.purchase_date
                AND f.descricao_movimentacao = 'Recebimento Físico'
        ),
        -- Curva ABC baseada nos últimos 90 dias de vendas (por filial + classificacao_n3)
        vendas_90d_abc AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                item_embalagemid AS embalagemid,
                SUM(ABS(item_quantidade)) AS quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date >= DATE '{(pd.to_datetime(data) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')}'
              AND data_date <= DATE '{data.strftime('%Y-%m-%d')}'
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
            FROM vendas_90d_abc
        ),
        produtos_com_curva AS (
            SELECT
                filial_codigo,
                embalagemid,
                CASE
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
                    WHEN total_vendas_grupo > 0 THEN 'C'
                    ELSE 'D'
                END AS curvaABC
            FROM vendas_com_acumulado
        ),
        compras_com_curva AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.fabricante_nome,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                COALESCE(pc.curvaABC, 'D') AS curvaABC
            FROM compras c
            LEFT JOIN produtos_com_curva pc
                ON c.filial_codigo = pc.filial_codigo AND c.embalagemid = pc.embalagemid
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.fabricante_nome,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                c.curvaABC,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) AS vendas_cnt
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
                ON v.filial_codigo = c.filial_codigo AND v.item_embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid, c.fabricante_nome,
                     c.classificacao_n1, c.classificacao_n2, c.classificacao_n3, c.curvaABC
        )
        -- 1) Por fabricante (geral da rede)
        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            fabricante_nome,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE fabricante_nome IS NOT NULL
        GROUP BY fabricante_nome

        UNION ALL

        -- 2) Por fabricante + filial
        SELECT
            filial_codigo,
            'Geral' AS curvaABC,
            fabricante_nome,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE fabricante_nome IS NOT NULL
        GROUP BY filial_codigo, fabricante_nome

        UNION ALL

        -- 3) Por fabricante + curva ABC (geral da rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            fabricante_nome,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE fabricante_nome IS NOT NULL AND curvaABC IS NOT NULL
        GROUP BY curvaABC, fabricante_nome

        UNION ALL

        -- 4) Por fabricante + filial + curva ABC
        SELECT
            filial_codigo,
            curvaABC,
            fabricante_nome,
            COUNT(*) AS total_produtos_denom,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) AS produtos_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                 ELSE 0
            END AS indice_curva_d
        FROM vendas_por_compra
        WHERE fabricante_nome IS NOT NULL AND curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC, fabricante_nome

        ORDER BY filial_codigo, curvaABC, fabricante_nome
        """

        df = duck_query(sql)
        return df if df is not None else pd.DataFrame()

    except Exception as e:
        st.error(f"Erro ao calcular índice de Curva D por laboratório: {e}")
        return pd.DataFrame()

def calcular_indice_desfazimento_curva_d(data_atual):
    """
    Indicador de 'desfazimento' Curva D (geral) – versão otimizada.
    Correção: compras_90d agora considera até MAX(venda_end) (ontem), como na lógica original,
    evitando inflar o denominador (antes parava em MAX(window_end) = ontem-2).
    """
    try:
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        s_ontem = ontem.strftime('%Y-%m-%d')

        sql = f"""
        WITH days AS (
            SELECT
              (DATE '{s_ontem}' - (i+1)::INT)       AS day,
              (DATE '{s_ontem}' - (i+1 + 90)::INT)  AS window_start,
              (DATE '{s_ontem}' - (i+1 + 1)::INT)   AS window_end,
              (DATE '{s_ontem}' - (i+1 + 120)::INT) AS produtos_start,
              (DATE '{s_ontem}' - (i+1 + 91)::INT)  AS produtos_end,
              DATE '{s_ontem}'                      AS venda_end
            FROM range(30) t(i)
        ),
        candidatos_base AS (
            SELECT
                d.day,
                d.window_start,
                d.window_end,
                d.produtos_start,
                d.produtos_end,
                d.venda_end,
                u.filial_codigo,
                u.embalagemid,
                ABS(u.ultima_qtde) AS qtde_estoque,
                u.ultimo_customedio AS customedio_estoque,
                ABS(u.ultima_qtde) * u.ultimo_customedio AS valor_estoque,
                u.data_ultima_aquisicao
            FROM days d
            JOIN vw_ultima_aquisicao u
              ON u.data_ultima_aquisicao BETWEEN d.produtos_start AND d.produtos_end
        ),
        compras_90d AS (
            -- CORREÇÃO: usar MAX(venda_end) (ontem) como limite superior
            SELECT filial_codigo, embalagemid, DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
              AND DATE(datahora) <= (SELECT MAX(venda_end) FROM days)
        ),
        vendas_full AS (
            SELECT filial_codigo,
                   item_embalagemid AS embalagemid,
                   data_date AS data_venda,
                   ABS(item_quantidade) AS qtde_vendida
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
              AND data_date <= (SELECT MAX(venda_end) FROM days)
        ),
        candidatos_filtrados AS (
            SELECT c.*
            FROM candidatos_base c
            WHERE NOT EXISTS (
                SELECT 1 FROM compras_90d x
                WHERE x.filial_codigo = c.filial_codigo
                  AND x.embalagemid = c.embalagemid
                  AND x.data_compra BETWEEN c.window_start AND c.window_end
            )
            AND NOT EXISTS (
                SELECT 1 FROM vendas_full v
                WHERE v.filial_codigo = c.filial_codigo
                  AND v.embalagemid = c.embalagemid
                  AND v.data_venda BETWEEN c.window_start AND c.window_end
            )
        ),
        candidatos_com_venda AS (
            SELECT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_estoque,
                c.customedio_estoque,
                c.valor_estoque,
                c.data_ultima_aquisicao,
                COALESCE(SUM(v.qtde_vendida),0) AS qtde_vendida_periodo,
                CASE WHEN SUM(v.qtde_vendida)>0 THEN 1 ELSE 0 END AS produto_vendido
            FROM candidatos_filtrados c
            LEFT JOIN vendas_full v
              ON v.filial_codigo = c.filial_codigo
             AND v.embalagemid = c.embalagemid
             AND v.data_venda BETWEEN c.day AND c.venda_end
            GROUP BY c.day, c.filial_codigo, c.embalagemid, c.qtde_estoque,
                     c.customedio_estoque, c.valor_estoque, c.data_ultima_aquisicao
        ),
        dados AS (
            SELECT
              *,
              qtde_estoque * produto_vendido AS qtde_vendida_masked,
              valor_estoque * produto_vendido AS valor_vendido_masked
            FROM candidatos_com_venda
            WHERE qtde_estoque > 0
        )
        SELECT * FROM dados
        ORDER BY day, filial_codigo, valor_estoque DESC;
        """

        df_itemizado = duck_query(sql)
        if df_itemizado is None or df_itemizado.empty:
            zero = {
                'total_denom':0,'total_numer':0,
                'total_qtde_all':0,'total_qtde_curva_d':0,
                'total_val_all':0.0,'total_val_curva_d':0.0,
                'pct_unique':0.0,'pct_quantity':0.0,'pct_value':0.0
            }
            return zero, pd.DataFrame(), pd.DataFrame()

        for c in ['qtde_estoque','valor_estoque','qtde_vendida_periodo',
                  'produto_vendido','qtde_vendida_masked','valor_vendido_masked']:
            if c in df_itemizado.columns:
                df_itemizado[c] = pd.to_numeric(df_itemizado[c], errors='coerce').fillna(0)

        total_denom = int(len(df_itemizado))
        total_numer = int(df_itemizado['produto_vendido'].sum())
        total_qtde_all = float(df_itemizado['qtde_estoque'].sum())
        total_qtde_curva = float(df_itemizado['qtde_vendida_masked'].sum())
        total_val_all = float(df_itemizado['valor_estoque'].sum())
        total_val_curva = float(df_itemizado['valor_vendido_masked'].sum())

        kpi_general = {
            'total_denom': total_denom,
            'total_numer': total_numer,
            'total_qtde_all': int(total_qtde_all),
            'total_qtde_curva_d': int(total_qtde_curva),
            'total_val_all': round(total_val_all,2),
            'total_val_curva_d': round(total_val_curva,2),
            'pct_unique': round((total_numer*100/total_denom) if total_denom else 0,4),
            'pct_quantity': round((total_qtde_curva*100/total_qtde_all) if total_qtde_all else 0,4),
            'pct_value': round((total_val_curva*100/total_val_all) if total_val_all else 0,4),
        }

        df_filial = (
            df_itemizado.groupby('filial_codigo', dropna=False)
              .agg(
                  total_denom=('embalagemid','count'),
                  total_numer=('produto_vendido','sum'),
                  total_qtde_all=('qtde_estoque','sum'),
                  total_qtde_curva_d=('qtde_vendida_masked','sum'),
                  total_val_all=('valor_estoque','sum'),
                  total_val_curva_d=('valor_vendido_masked','sum')
              ).reset_index()
        )
        df_filial['pct_unique'] = df_filial.apply(lambda r: (r.total_numer*100/r.total_denom) if r.total_denom else 0, axis=1)
        df_filial['pct_quantity'] = df_filial.apply(lambda r: (r.total_qtde_curva_d*100/r.total_qtde_all) if r.total_qtde_all else 0, axis=1)
        df_filial['pct_value'] = df_filial.apply(lambda r: (r.total_val_curva_d*100/r.total_val_all) if r.total_val_all else 0, axis=1)

        for c in ['total_denom','total_numer','total_qtde_all','total_qtde_curva_d']:
            df_filial[c] = df_filial[c].astype(int)
        df_filial['total_val_all'] = df_filial['total_val_all'].round(2)
        df_filial['total_val_curva_d'] = df_filial['total_val_curva_d'].round(2)
        for c in ['pct_unique','pct_quantity','pct_value']:
            df_filial[c] = df_filial[c].round(4)

        return kpi_general, df_filial, df_itemizado

    except Exception as e:
        st.error(f"Erro (desfazimento Curva D): {e}")
        zero = {
            'total_denom':0,'total_numer':0,
            'total_qtde_all':0,'total_qtde_curva_d':0,
            'total_val_all':0.0,'total_val_curva_d':0.0,
            'pct_unique':0.0,'pct_quantity':0.0,'pct_value':0.0
        }
        return zero, pd.DataFrame(), pd.DataFrame()

def calcular_indice_desfazimento_curva_d_por_filial(data_atual):
    """
    Desfazimento Curva D por filial – lógica alinhada à função geral:
      Para cada dia d (últimos 30 dias retro a ontem):
        - candidatos: produtos cuja última aquisição (vw_ultima_aquisicao) está entre d-120 e d-91
                      e sem compra/venda no intervalo (d-90, d-1)
        - numerador: desses candidatos, os vendidos entre d e ontem
      Multi-contagem por produto (cada dia elegível gera uma linha, como na função geral).

    Retorna DataFrame com:
      filial_codigo, total_denom, total_numer,
      total_qtde_all, total_qtde_curva_d,
      total_val_all, total_val_curva_d,
      pct_unique, pct_quantity, pct_value
    """
    try:
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        s_ontem = ontem.strftime('%Y-%m-%d')

        sql = f"""
        WITH days AS (
            SELECT
              (DATE '{s_ontem}' - (i+1)::INT)       AS day,
              (DATE '{s_ontem}' - (i+1 + 90)::INT)  AS window_start,
              (DATE '{s_ontem}' - (i+1 + 1)::INT)   AS window_end,
              (DATE '{s_ontem}' - (i+1 + 120)::INT) AS produtos_start,
              (DATE '{s_ontem}' - (i+1 + 91)::INT)  AS produtos_end,
              DATE '{s_ontem}'                      AS venda_end
            FROM range(30) t(i)
        ),
        candidatos_base AS (
            SELECT
                d.day,
                d.window_start,
                d.window_end,
                d.produtos_start,
                d.produtos_end,
                d.venda_end,
                u.filial_codigo,
                u.embalagemid,
                ABS(u.ultima_qtde) AS qtde_estoque,
                u.ultimo_customedio AS customedio_estoque,
                ABS(u.ultima_qtde) * u.ultimo_customedio AS valor_estoque,
                u.data_ultima_aquisicao
            FROM days d
            JOIN vw_ultima_aquisicao u
              ON u.data_ultima_aquisicao BETWEEN d.produtos_start AND d.produtos_end
        ),
        compras_90d AS (
            SELECT filial_codigo, embalagemid, DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
              AND DATE(datahora) <= (SELECT MAX(venda_end) FROM days)
        ),
        vendas_full AS (
            SELECT filial_codigo,
                   item_embalagemid AS embalagemid,
                   data_date AS data_venda,
                   ABS(item_quantidade) AS qtde_vendida
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
              AND data_date <= (SELECT MAX(venda_end) FROM days)
        ),
        candidatos_filtrados AS (
            SELECT c.*
            FROM candidatos_base c
            WHERE NOT EXISTS (
                SELECT 1 FROM compras_90d x
                WHERE x.filial_codigo = c.filial_codigo
                  AND x.embalagemid = c.embalagemid
                  AND x.data_compra BETWEEN c.window_start AND c.window_end
            )
            AND NOT EXISTS (
                SELECT 1 FROM vendas_full v
                WHERE v.filial_codigo = c.filial_codigo
                  AND v.embalagemid = c.embalagemid
                  AND v.data_venda BETWEEN c.window_start AND c.window_end
            )
        ),
        candidatos_com_venda AS (
            SELECT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.qtde_estoque,
                c.customedio_estoque,
                c.valor_estoque,
                c.data_ultima_aquisicao,
                COALESCE(SUM(v.qtde_vendida),0) AS qtde_vendida_periodo,
                CASE WHEN SUM(v.qtde_vendida)>0 THEN 1 ELSE 0 END AS produto_vendido
            FROM candidatos_filtrados c
            LEFT JOIN vendas_full v
              ON v.filial_codigo = c.filial_codigo
             AND v.embalagemid = c.embalagemid
             AND v.data_venda BETWEEN c.day AND c.venda_end
            GROUP BY c.day, c.filial_codigo, c.embalagemid,
                     c.qtde_estoque, c.customedio_estoque,
                     c.valor_estoque, c.data_ultima_aquisicao
        ),
        dados AS (
            SELECT
              *,
              qtde_estoque * produto_vendido AS qtde_vendida_masked,
              valor_estoque * produto_vendido AS valor_vendido_masked
            FROM candidatos_com_venda
            WHERE qtde_estoque > 0
        )
        SELECT * FROM dados;
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(columns=[
                'filial_codigo','total_denom','total_numer',
                'total_qtde_all','total_qtde_curva_d',
                'total_val_all','total_val_curva_d',
                'pct_unique','pct_quantity','pct_value'
            ])

        # Garantir tipos
        for c in ['qtde_estoque','valor_estoque','produto_vendido',
                  'qtde_vendida_masked','valor_vendido_masked']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Agregar por filial
        agg = (
            df.groupby('filial_codigo', dropna=False)
              .agg(
                  total_denom=('embalagemid','count'),
                  total_numer=('produto_vendido','sum'),
                  total_qtde_all=('qtde_estoque','sum'),
                  total_qtde_curva_d=('qtde_vendida_masked','sum'),
                  total_val_all=('valor_estoque','sum'),
                  total_val_curva_d=('valor_vendido_masked','sum')
              ).reset_index()
        )

        # Percentuais
        agg['pct_unique'] = agg.apply(lambda r: (r.total_numer*100/r.total_denom) if r.total_denom else 0, axis=1)
        agg['pct_quantity'] = agg.apply(lambda r: (r.total_qtde_curva_d*100/r.total_qtde_all) if r.total_qtde_all else 0, axis=1)
        agg['pct_value'] = agg.apply(lambda r: (r.total_val_curva_d*100/r.total_val_all) if r.total_val_all else 0, axis=1)

        # Tipos / arredondamentos
        for c in ['total_denom','total_numer','total_qtde_all','total_qtde_curva_d']:
            agg[c] = agg[c].astype(int)
        agg['total_val_all'] = agg['total_val_all'].round(2)
        agg['total_val_curva_d'] = agg['total_val_curva_d'].round(2)
        agg['pct_unique'] = agg['pct_unique'].round(4)
        agg['pct_quantity'] = agg['pct_quantity'].round(4)
        agg['pct_value'] = agg['pct_value'].round(4)

        return agg

    except Exception as e:
        st.error(f"Erro ao calcular índice desfazimento Curva D por filial: {e}")
        return pd.DataFrame()
    
def calcular_indice_desfazimento_curva_d_por_curva_abc(data_atual):
    """
    Versão otimizada que calcula indicador de 'desfazimento' da Curva D por curva ABC.
    Elimina CROSS JOIN e reduz transferência de dados entre database e Python.
    
    Calcula por curva ABC e suas combinações:
    - Por curva ABC (geral da rede)
    - Por curva ABC + filial
    - Por curva ABC + classificacao_n1 (geral da rede)
    - Por curva ABC + filial + classificacao_n1
    
    Retorna DataFrame com colunas:
    filial_codigo, curvaABC, classificacao_n1, total_denom, total_numer, indice_30d_pct
    """
    try:
        # normalizar data para trabalhar com "ontem"
        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        if isinstance(data_limite_ontem, (str,)):
            data = pd.to_datetime(data_limite_ontem).date()
        elif isinstance(data_limite_ontem, pd.Timestamp):
            data = data_limite_ontem.date()
        else:
            data = data_limite_ontem

        # construir pares (day, window_start, window_end) para os últimos 30 dias
        values = []
        for offset in range(30):
            day = pd.to_datetime(data) - pd.Timedelta(days=1 + offset)
            window_start = (day - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
            window_end = (day - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            values.append((day.strftime('%Y-%m-%d'), window_start, window_end))

        values_sql = ",\n            ".join([f"(DATE '{d}', DATE '{s}', DATE '{e}')" for d, s, e in values])

        sql = f"""
        WITH days(day, window_start, window_end) AS (
            VALUES
            {values_sql}
        ),
        -- Pre-filtrar produtos existentes no estoque com suas filiais
        produtos_existentes AS (
            SELECT DISTINCT filial_codigo, embalagemid
            FROM fact_estoque_final 
            WHERE filial_codigo IS NOT NULL
        ),
        -- Curva ABC baseada nos últimos 90 dias de vendas
        vendas_90d_abc AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                item_embalagemid AS embalagemid,
                SUM(ABS(item_quantidade)) AS quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date >= DATE '{(pd.to_datetime(data) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')}'
            AND data_date <= DATE '{data.strftime('%Y-%m-%d')}'
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
            FROM vendas_90d_abc
        ),
        produtos_com_curva AS (
            SELECT 
                filial_codigo,
                embalagemid,
                CASE 
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
                    WHEN total_vendas_grupo > 0 THEN 'C'
                    ELSE 'D'
                END AS curvaABC
            FROM vendas_com_acumulado
        ),
        -- Pre-filtrar todas as compras para os períodos relevantes
        todas_compras AS (
            SELECT 
                filial_codigo, 
                embalagemid,
                DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
            AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
            AND DATE(datahora) <= (SELECT MAX(day) FROM days)
        ),
        -- Pre-filtrar todas as vendas para os períodos relevantes
        todas_vendas AS (
            SELECT 
                filial_codigo,
                item_embalagemid AS embalagemid,
                data_date AS data_venda
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
            AND data_date <= (SELECT MAX(day) FROM days)
        ),
        -- Para cada dia e cada produto, verificar se é candidato Curva D
        candidatos_por_dia AS (
            SELECT DISTINCT
                d.day,
                p.filial_codigo,
                p.embalagemid,
                COALESCE(pc.curvaABC, 'D') AS curvaABC
            FROM days d
            CROSS JOIN produtos_existentes p
            LEFT JOIN produtos_com_curva pc
                ON p.filial_codigo = pc.filial_codigo AND p.embalagemid = pc.embalagemid
            WHERE NOT EXISTS (
                -- Verificar se não teve compra na janela DA MESMA FILIAL
                SELECT 1
                FROM todas_compras c
                WHERE c.filial_codigo = p.filial_codigo
                AND c.embalagemid = p.embalagemid
                AND c.data_compra BETWEEN d.window_start AND d.window_end
            )
            AND NOT EXISTS (
                -- Verificar se não teve venda na janela DA MESMA FILIAL
                SELECT 1
                FROM todas_vendas v
                WHERE v.filial_codigo = p.filial_codigo
                AND v.embalagemid = p.embalagemid
                AND v.data_venda BETWEEN d.window_start AND d.window_end
            )
        ),
        -- Adicionar classificacao_n1 aos candidatos
        candidatos_com_classificacao AS (
            SELECT DISTINCT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.curvaABC,
                e.classificacao_n1
            FROM candidatos_por_dia c
            LEFT JOIN (
                SELECT 
                    filial_codigo,
                    embalagemid,
                    classificacao_n1,
                    ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
                FROM fact_estoque_final
                WHERE datahora <= DATE '{data.strftime('%Y-%m-%d')}'
            ) e ON c.filial_codigo = e.filial_codigo AND c.embalagemid = e.embalagemid AND e.rn = 1
        ),
        -- Verificar se cada candidato foi vendido em seu dia específico NA MESMA FILIAL
        candidatos_vendidos AS (
            SELECT DISTINCT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.curvaABC,
                c.classificacao_n1,
                CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS sold_flag
            FROM candidatos_com_classificacao c
            LEFT JOIN todas_vendas v
                ON v.filial_codigo = c.filial_codigo
                AND v.embalagemid = c.embalagemid
                AND v.data_venda = c.day
        )
        -- 1) Por curva ABC (geral da rede)
        SELECT 
            'Geral' AS filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) AS total_numer,
            CASE 
                WHEN COUNT(DISTINCT embalagemid) > 0 
                THEN (COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid)) 
                ELSE 0 
            END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC

        UNION ALL

        -- 2) Por curva ABC + filial
        SELECT 
            filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) AS total_numer,
            CASE 
                WHEN COUNT(DISTINCT embalagemid) > 0 
                THEN (COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid)) 
                ELSE 0 
            END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC

        UNION ALL

        -- 3) Por curva ABC + classificacao_n1 (geral da rede)
        SELECT 
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) AS total_numer,
            CASE 
                WHEN COUNT(DISTINCT embalagemid) > 0 
                THEN (COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid)) 
                ELSE 0 
            END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY curvaABC, classificacao_n1

        UNION ALL

        -- 4) Por curva ABC + filial + classificacao_n1
        SELECT 
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) AS total_numer,
            CASE 
                WHEN COUNT(DISTINCT embalagemid) > 0 
                THEN (COUNT(DISTINCT CASE WHEN sold_flag = 1 THEN embalagemid END) * 100.0 / COUNT(DISTINCT embalagemid)) 
                ELSE 0 
            END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """
        
        df_resultado = duck_query(sql)
        
        if df_resultado is None or df_resultado.empty:
            return pd.DataFrame()
        
        # Formatar resultado final
        df_resultado['total_denom'] = df_resultado['total_denom'].astype(int)
        df_resultado['total_numer'] = df_resultado['total_numer'].astype(int)
        df_resultado['indice_30d_pct'] = df_resultado['indice_30d_pct'].round(4)
        
        return df_resultado

    except Exception as e:
        st.error(f"Erro ao calcular índice desfazimento Curva D por curva ABC: {e}")
        return pd.DataFrame()

def calcular_indice_desfazimento_curva_d_por_classificacao_n1(data_atual):
    """
    Versão atualizada que calcula indicador de 'desfazimento' da Curva D por classificacao_n1
    com lógica aprimorada e janela de produtos parados (mesma lógica da função geral).
    """
    try:
        ensure_bases_estoque(str(data_atual))

        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        if isinstance(data_limite_ontem, (str,)):
            data_ontem = pd.to_datetime(data_limite_ontem).date()
        elif isinstance(data_limite_ontem, pd.Timestamp):
            data_ontem = data_limite_ontem.date()
        else:
            data_ontem = data_limite_ontem

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        values = []
        for offset in range(30):
            day = pd.to_datetime(data_ontem) - pd.Timedelta(days=1 + offset)
            window_start = (day - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
            window_end = (day - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            produtos_start = (day - pd.Timedelta(days=120)).strftime('%Y-%m-%d')
            produtos_end = (day - pd.Timedelta(days=91)).strftime('%Y-%m-%d')
            venda_end = data_ontem.strftime('%Y-%m-%d')
            values.append((day.strftime('%Y-%m-%d'), window_start, window_end,
                           produtos_start, produtos_end, venda_end))

        values_sql = ",\n        ".join([f"(DATE '{d}', DATE '{ws}', DATE '{we}', DATE '{ps}', DATE '{pe}', DATE '{ve}')"
                                        for d, ws, we, ps, pe, ve in values])
        data_ref = data_ontem.strftime('%Y-%m-%d')

        sql = f"""
        WITH days(day, window_start, window_end, produtos_start, produtos_end, venda_end) AS (
            VALUES
            {values_sql}
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        ultima_aquisicao AS (
            SELECT 
                filial_codigo,
                embalagemid,
                DATE(datahora) AS data_ultima_aquisicao,
                ABS(quantidade) AS ultima_qtde,
                COALESCE(customedio, 0) AS ultimo_customedio,
                classificacao_n1,
                ROW_NUMBER() OVER (
                    PARTITION BY filial_codigo, embalagemid
                    ORDER BY datahora DESC
                ) AS rn
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND filial_codigo IS NOT NULL
              AND DATE(datahora) <= DATE '{data_ref}'
        ),
        produtos_ultima_aquisicao AS (
            SELECT
                filial_codigo,
                embalagemid,
                data_ultima_aquisicao,
                ultima_qtde,
                ultimo_customedio,
                classificacao_n1
            FROM ultima_aquisicao
            WHERE rn = 1
        ),
        todas_compras AS (
            SELECT 
                filial_codigo, 
                embalagemid,
                DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
              AND DATE(datahora) <= (SELECT MAX(venda_end) FROM days)
        ),
        todas_vendas AS (
            SELECT 
                filial_codigo,
                item_embalagemid AS embalagemid,
                data_date AS data_venda
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
              AND data_date <= (SELECT MAX(venda_end) FROM days)
        ),
        candidatos_por_dia AS (
            SELECT 
                d.day,
                d.venda_end,
                p.filial_codigo,
                p.embalagemid,
                p.classificacao_n1,
                COALESCE(ca.curvaABC, 'D') AS curvaABC,
                p.ultima_qtde AS qtde_estoque,
                p.ultimo_customedio AS customedio_estoque,
                p.ultima_qtde * p.ultimo_customedio AS valor_estoque,
                p.data_ultima_aquisicao
            FROM produtos_ultima_aquisicao p
            JOIN days d
              ON p.data_ultima_aquisicao BETWEEN d.produtos_start AND d.produtos_end
            LEFT JOIN curva_abc ca
              ON p.filial_codigo = ca.filial_codigo AND p.embalagemid = ca.embalagemid
            WHERE NOT EXISTS (
                SELECT 1
                FROM todas_compras c
                WHERE c.filial_codigo = p.filial_codigo
                  AND c.embalagemid = p.embalagemid
                  AND c.data_compra BETWEEN d.window_start AND d.window_end
            )
              AND NOT EXISTS (
                SELECT 1
                FROM todas_vendas v
                WHERE v.filial_codigo = p.filial_codigo
                  AND v.embalagemid = p.embalagemid
                  AND v.data_venda BETWEEN d.window_start AND d.window_end
            )
        ),
        candidatos_com_vendas AS (
            SELECT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.classificacao_n1,
                c.curvaABC,
                c.qtde_estoque,
                c.customedio_estoque,
                c.valor_estoque,
                c.data_ultima_aquisicao,
                CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS produto_vendido
            FROM candidatos_por_dia c
            LEFT JOIN todas_vendas v
              ON v.filial_codigo = c.filial_codigo
             AND v.embalagemid = c.embalagemid
             AND v.data_venda BETWEEN c.day AND c.venda_end
        ),
        dados_finais AS (
            SELECT
                day,
                filial_codigo,
                embalagemid,
                classificacao_n1,
                curvaABC,
                qtde_estoque,
                customedio_estoque,
                valor_estoque,
                data_ultima_aquisicao,
                produto_vendido,
                qtde_estoque * produto_vendido AS qtde_vendida_masked,
                valor_estoque * produto_vendido AS valor_vendido_masked
            FROM candidatos_com_vendas
            WHERE qtde_estoque > 0
              AND classificacao_n1 IS NOT NULL
        )
        SELECT 
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY classificacao_n1

        UNION ALL

        SELECT 
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n1,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY filial_codigo, classificacao_n1

        UNION ALL

        SELECT 
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY curvaABC, classificacao_n1

        UNION ALL

        SELECT 
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """
        
        df_resultado = duck_query(sql)
        
        if df_resultado is None or df_resultado.empty:
            return pd.DataFrame()
        
        df_resultado['total_denom'] = df_resultado['total_denom'].astype(int)
        df_resultado['total_numer'] = df_resultado['total_numer'].astype(int)
        df_resultado['total_qtde_all'] = df_resultado['total_qtde_all'].astype(int)
        df_resultado['total_qtde_curva_d'] = df_resultado['total_qtde_curva_d'].astype(int)
        df_resultado['total_val_all'] = df_resultado['total_val_all'].round(2)
        df_resultado['total_val_curva_d'] = df_resultado['total_val_curva_d'].round(2)
        df_resultado['pct_unique'] = df_resultado['pct_unique'].round(4)
        df_resultado['pct_quantity'] = df_resultado['pct_quantity'].round(4)
        df_resultado['pct_value'] = df_resultado['pct_value'].round(4)
        
        return df_resultado

    except Exception as e:
        st.error(f"Erro ao calcular índice desfazimento Curva D por classificacao_n1: {e}")
        return pd.DataFrame() 

def calcular_indice_desfazimento_curva_d_por_classificacao_n2(data_atual):
    """
    Versão atualizada que calcula indicador de 'desfazimento' da Curva D por classificacao_n2
    com lógica aprimorada e janela de produtos parados (mesma lógica da função geral).
    """
    try:
        ensure_bases_estoque(str(data_atual))

        data_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_ref = data_ontem.strftime('%Y-%m-%d')

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        values = []
        for offset in range(30):
            day = data_ontem - pd.Timedelta(days=1 + offset)
            window_start = (day - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
            window_end = (day - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            produtos_start = (day - pd.Timedelta(days=120)).strftime('%Y-%m-%d')
            produtos_end = (day - pd.Timedelta(days=91)).strftime('%Y-%m-%d')
            venda_end = data_ontem.strftime('%Y-%m-%d')
            values.append((day.strftime('%Y-%m-%d'), window_start, window_end,
                           produtos_start, produtos_end, venda_end))

        values_sql = ",\n        ".join(
            f"(DATE '{d}', DATE '{ws}', DATE '{we}', DATE '{ps}', DATE '{pe}', DATE '{ve}')"
            for d, ws, we, ps, pe, ve in values
        )

        sql = f"""
        WITH days(day, window_start, window_end, produtos_start, produtos_end, venda_end) AS (
            VALUES
            {values_sql}
        ),
        ultima_aquisicao AS (
            SELECT
                filial_codigo,
                embalagemid,
                DATE(datahora) AS data_ultima_aquisicao,
                ABS(quantidade) AS qtde_estoque,
                COALESCE(customedio, 0) AS customedio_estoque,
                classificacao_n2,
                ROW_NUMBER() OVER (
                    PARTITION BY filial_codigo, embalagemid
                    ORDER BY datahora DESC
                ) AS rn
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND filial_codigo IS NOT NULL
              AND DATE(datahora) <= DATE '{data_ref}'
        ),
        produtos_ultima_aquisicao AS (
            SELECT
                filial_codigo,
                embalagemid,
                data_ultima_aquisicao,
                qtde_estoque,
                customedio_estoque,
                classificacao_n2
            FROM ultima_aquisicao
            WHERE rn = 1
        ),
        curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        todas_compras AS (
            SELECT
                filial_codigo,
                embalagemid,
                DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
              AND DATE(datahora) <= (SELECT MAX(venda_end) FROM days)
        ),
        todas_vendas AS (
            SELECT
                filial_codigo,
                item_embalagemid AS embalagemid,
                data_date AS data_venda
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
              AND data_date <= (SELECT MAX(venda_end) FROM days)
        ),
        candidatos_por_dia AS (
            SELECT
                d.day,
                d.venda_end,
                p.filial_codigo,
                p.embalagemid,
                p.classificacao_n2,
                COALESCE(ca.curvaABC, 'D') AS curvaABC,
                p.qtde_estoque,
                p.customedio_estoque,
                p.qtde_estoque * p.customedio_estoque AS valor_estoque,
                p.data_ultima_aquisicao
            FROM days d
            JOIN produtos_ultima_aquisicao p
              ON p.data_ultima_aquisicao BETWEEN d.produtos_start AND d.produtos_end
            LEFT JOIN curva_abc ca
              ON p.filial_codigo = ca.filial_codigo
             AND p.embalagemid = ca.embalagemid
            WHERE NOT EXISTS (
                SELECT 1
                FROM todas_compras c
                WHERE c.filial_codigo = p.filial_codigo
                  AND c.embalagemid = p.embalagemid
                  AND c.data_compra BETWEEN d.window_start AND d.window_end
            )
              AND NOT EXISTS (
                SELECT 1
                FROM todas_vendas v
                WHERE v.filial_codigo = p.filial_codigo
                  AND v.embalagemid = p.embalagemid
                  AND v.data_venda BETWEEN d.window_start AND d.window_end
            )
        ),
        candidatos_com_vendas AS (
            SELECT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.classificacao_n2,
                c.curvaABC,
                c.qtde_estoque,
                c.customedio_estoque,
                c.valor_estoque,
                c.data_ultima_aquisicao,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM todas_vendas v
                    WHERE v.filial_codigo = c.filial_codigo
                      AND v.embalagemid = c.embalagemid
                      AND v.data_venda BETWEEN c.day AND c.venda_end
                ) THEN 1 ELSE 0 END AS produto_vendido
            FROM candidatos_por_dia c
        ),
        dados_finais AS (
            SELECT
                day,
                filial_codigo,
                embalagemid,
                classificacao_n2,
                curvaABC,
                qtde_estoque,
                customedio_estoque,
                valor_estoque,
                data_ultima_aquisicao,
                produto_vendido,
                qtde_estoque * produto_vendido AS qtde_vendida_masked,
                valor_estoque * produto_vendido AS valor_vendido_masked
            FROM candidatos_com_vendas
            WHERE qtde_estoque > 0
              AND classificacao_n2 IS NOT NULL
        )
        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY classificacao_n2

        UNION ALL

        SELECT
            filial_codigo,
            'Geral' AS curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY filial_codigo, classificacao_n2

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY curvaABC, classificacao_n2

        UNION ALL

        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n2,
            COUNT(*) AS total_denom,
            SUM(produto_vendido) AS total_numer,
            SUM(qtde_estoque) AS total_qtde_all,
            SUM(qtde_vendida_masked) AS total_qtde_curva_d,
            SUM(valor_estoque) AS total_val_all,
            SUM(valor_vendido_masked) AS total_val_curva_d,
            CASE WHEN COUNT(*) > 0
                 THEN (SUM(produto_vendido) * 100.0 / COUNT(*))
                 ELSE 0 END AS pct_unique,
            CASE WHEN SUM(qtde_estoque) > 0
                 THEN (SUM(qtde_vendida_masked) * 100.0 / SUM(qtde_estoque))
                 ELSE 0 END AS pct_quantity,
            CASE WHEN SUM(valor_estoque) > 0
                 THEN (SUM(valor_vendido_masked) * 100.0 / SUM(valor_estoque))
                 ELSE 0 END AS pct_value
        FROM dados_finais
        GROUP BY filial_codigo, curvaABC, classificacao_n2

        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df_resultado = duck_query(sql)

        if df_resultado is None or df_resultado.empty:
            return pd.DataFrame()

        for col in ['total_denom', 'total_numer', 'total_qtde_all', 'total_qtde_curva_d']:
            if col in df_resultado.columns:
                df_resultado[col] = pd.to_numeric(df_resultado[col], errors='coerce').fillna(0).astype(int)

        for col in ['total_val_all', 'total_val_curva_d', 'pct_unique', 'pct_quantity', 'pct_value']:
            if col in df_resultado.columns:
                df_resultado[col] = pd.to_numeric(df_resultado[col], errors='coerce').fillna(0.0)

        df_resultado['total_val_all'] = df_resultado['total_val_all'].round(2)
        df_resultado['total_val_curva_d'] = df_resultado['total_val_curva_d'].round(2)
        df_resultado['pct_unique'] = df_resultado['pct_unique'].round(4)
        df_resultado['pct_quantity'] = df_resultado['pct_quantity'].round(4)
        df_resultado['pct_value'] = df_resultado['pct_value'].round(4)

        return df_resultado

    except Exception as e:
        st.error(f"Erro ao calcular índice desfazimento Curva D por classificacao_n2: {e}")
        return pd.DataFrame()