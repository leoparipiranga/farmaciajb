import pandas as pd
import streamlit as st
from business_logic.estoque.base_sets import ensure_bases_estoque
from core.database import duck_query

def calcular_disponibilidade_duck(data_atual):
    """
    Versão otimizada: usa as TEMP TABLES preparadas em base_sets.py.
    Fórmula (ajuste se sua lógica original diferir):
      Denominador = itens em temp_denominador_disp (comprados 90d ∩ vendidos 30d)
      Numerador   = desses, os que possuem estoque > 0 no snapshot mais recente dentro de 90 dias.
    Retorna:
      filial_codigo | total_itens | itens_disponiveis | disponibilidade_percent
      + linha 'Geral'
    """
    # Garante que as bases existem (idempotente / rápido se já criadas)
    ensure_bases_estoque(str(data_atual))

    # Tenta primeiro usar cache_ (persistente). Se quiser manter temp_, basta trocar nomes.
    sql = """
    WITH base AS (
        SELECT
            d.filial_codigo,
            d.embalagemid,
            COALESCE(es.estoque, 0) AS estoque,
            CASE WHEN COALESCE(es.estoque,0) > 0 THEN 1 ELSE 0 END AS disponivel
        FROM cache_denominador_disp d
        LEFT JOIN cache_estoque_snapshot_90d es
          ON d.filial_codigo = es.filial_codigo
         AND d.embalagemid = es.embalagemid
    ),
    agreg_filial AS (
        SELECT
            filial_codigo,
            COUNT(*) AS total_itens,
            SUM(disponivel) AS itens_disponiveis,
            CASE WHEN COUNT(*) > 0 THEN (SUM(disponivel)*100.0/COUNT(*)) ELSE 0 END AS disponibilidade_percent
        FROM base
        GROUP BY filial_codigo
    ),
    agreg_geral AS (
        SELECT
            'Geral' AS filial_codigo,
            COUNT(*) AS total_itens,
            SUM(disponivel) AS itens_disponiveis,
            CASE WHEN COUNT(*) > 0 THEN (SUM(disponivel)*100.0/COUNT(*)) ELSE 0 END AS disponibilidade_percent
        FROM base
    )
    SELECT * FROM agreg_geral
    UNION ALL
    SELECT * FROM agreg_filial
    ORDER BY filial_codigo;
    """
    df = duck_query(sql)
    if df is None or df.empty:
        return pd.DataFrame(columns=["filial_codigo","total_itens","itens_disponiveis","disponibilidade_percent"])
    df["disponibilidade_percent"] = df["disponibilidade_percent"].round(2)
    return df

def calcular_disponibilidade_por_curva_abc_duck(data_atual):
    """
    Calcula índice de disponibilidade/ruptura por curva ABC e suas combinações.
    Agora reutiliza cache_curva_abc_90d (pré-calculada em ensure_bases_estoque)
    em vez de recalcular ABC a partir de fact_vendas_final.
    
    Saída:
      (1) Curva ABC (geral rede)
      (2) Curva ABC + filial
      (2b) Filial + classificacao_n1 (curvaABC='Geral')
      (2c) classificacao_n1 (rede, curvaABC='Geral')
      (3) Curva ABC + classificacao_n1 (rede)
      (4) Curva ABC + filial + classificacao_n1
    """
    try:
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        ensure_bases_estoque(str(data_atual))  # garante cache_curva_abc_90d e demais caches
        data_limite_ontem = ontem.strftime('%Y-%m-%d')

        sql = f"""
        -- Curva ABC já materializada (quantidade 90d) em cache_curva_abc_90d
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM cache_curva_abc_90d
            WHERE data_ref = DATE '{data_limite_ontem}'
        ),
        -- Denominador (compra 90d ∩ venda 30d) já pré-calculado
        denominador AS (
            SELECT filial_codigo, embalagemid
            FROM cache_denominador_disp
        ),
        -- Snapshot (estoque + classificacao_n1)
        estoque AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                COALESCE(s.estoque,0) AS estoque,
                s.classificacao_n1
            FROM cache_estoque_snapshot_90d s
        ),
        base AS (
            SELECT
                d.filial_codigo,
                d.embalagemid,
                e.estoque,
                e.classificacao_n1,
                COALESCE(c.curvaABC,'D') AS curvaABC
            FROM denominador d
            LEFT JOIN estoque e
              ON d.filial_codigo = e.filial_codigo
             AND d.embalagemid = e.embalagemid
            LEFT JOIN curva_abc c
              ON d.filial_codigo = c.filial_codigo
             AND d.embalagemid = c.embalagemid
        ),
        -- 1) Curva ABC (geral)
        agg_curva_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                'Geral' AS classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY curvaABC
        ),
        -- 2) Curva ABC + filial
        agg_curva_filial AS (
            SELECT
                filial_codigo,
                curvaABC,
                'Geral' AS classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY filial_codigo, curvaABC
        ),
        -- 2b) Filial + classificacao_n1
        agg_filial_classif AS (
            SELECT
                filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, classificacao_n1
        ),
        -- 2c) classificacao_n1 (rede)
        agg_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY classificacao_n1
        ),
        -- 3) Curva ABC + classificacao_n1 (rede)
        agg_curva_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
            GROUP BY curvaABC, classificacao_n1
        ),
        -- 4) Curva ABC + filial + classificacao_n1
        agg_curva_filial_classif AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        ),
        uniao AS (
            SELECT * FROM agg_curva_geral
            UNION ALL SELECT * FROM agg_curva_filial
            UNION ALL SELECT * FROM agg_filial_classif
            UNION ALL SELECT * FROM agg_classif_geral
            UNION ALL SELECT * FROM agg_curva_classif_geral
            UNION ALL SELECT * FROM agg_curva_filial_classif
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            total_produtos,
            produtos_zerados,
            CASE WHEN total_produtos > 0
                 THEN (produtos_zerados * 100.0 / total_produtos)
                 ELSE 0 END AS indice_ruptura,
            CASE WHEN total_produtos > 0
                 THEN (100.0 - (produtos_zerados * 100.0 / total_produtos))
                 ELSE 0 END AS disponibilidade
        FROM uniao
        ORDER BY filial_codigo, curvaABC, classificacao_n1;
        """

        df_resultado = duck_query(sql)
        if df_resultado is None or df_resultado.empty:
            return pd.DataFrame()

        df_resultado['total_produtos'] = df_resultado['total_produtos'].astype(int)
        df_resultado['produtos_zerados'] = df_resultado['produtos_zerados'].astype(int)
        df_resultado['indice_ruptura'] = df_resultado['indice_ruptura'].round(4)
        df_resultado['disponibilidade'] = df_resultado['disponibilidade'].round(4)
        return df_resultado

    except Exception as e:
        st.error(f"Erro ao calcular disponibilidade por curva ABC: {e}")
        return pd.DataFrame()

def calcular_giro_geral_e_combinacoes_duck(data_atual):
    """
    Versão otimizada: utiliza as tabelas cache_ criadas em ensure_bases_estoque.
    Mantém exatamente os mesmos nomes de colunas e chaves de kpis_giro.
    Saída df: filial_codigo, classificacao_n1, classificacao_n2, classificacao_n3,
              total_produtos, total_valor_estoque, valor_estoque_com_giro,
              valor_estoque_sem_giro, giro_medio_anual
    """
    ensure_bases_estoque(str(data_atual))

    sql = """
    -- Universo 90d (estoque dentro da janela + teve 'Recebimento Físico' nos 90d)
    WITH dados_90d AS (
        SELECT
            s.filial_codigo,
            s.embalagemid,
            s.valor_estoque,
            s.classificacao_n1,
            s.classificacao_n2,
            s.classificacao_n3,
            CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS teve_giro,
            CASE WHEN v.embalagemid IS NOT NULL THEN s.valor_estoque ELSE 0 END AS valor_estoque_com_giro
        FROM cache_estoque_snapshot_90d s
        INNER JOIN cache_comprados_90d c   -- garante compra nos 90d
          ON s.filial_codigo = c.filial_codigo AND s.embalagemid = c.embalagemid
        LEFT JOIN cache_vendidos_30d_ids v -- identifica giro (venda 30d)
          ON s.filial_codigo = v.filial_codigo AND s.embalagemid = v.embalagemid
    ),
    agreg_geral_90d AS (
        SELECT
            SUM(valor_estoque) AS total_valor_estoque_90d,
            SUM(valor_estoque_com_giro) AS valor_estoque_com_giro_90d,
            SUM(CASE WHEN valor_estoque_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro_90d
        FROM dados_90d
    ),
    -- Estoque total (snapshot completo até ontem) para linha 'Geral'
    total_snapshot AS (
        SELECT
            t.filial_codigo,
            t.embalagemid,
            t.valor_estoque,
            t.classificacao_n1,
            t.classificacao_n2,
            t.classificacao_n3,
            CASE WHEN v.embalagemid IS NOT NULL THEN t.valor_estoque ELSE 0 END AS valor_estoque_com_giro
        FROM cache_estoque_snapshot t
        LEFT JOIN cache_vendidos_30d_ids v
          ON t.filial_codigo = v.filial_codigo AND t.embalagemid = v.embalagemid
    )
    -- 1) Linha Geral_90d
    SELECT
        'Geral_90d' AS filial_codigo,
        'Geral' AS classificacao_n1,
        'Geral' AS classificacao_n2,
        'Geral' AS classificacao_n3,
        0 AS total_produtos,
        g.total_valor_estoque_90d AS total_valor_estoque,
        g.valor_estoque_com_giro_90d AS valor_estoque_com_giro,
        g.valor_estoque_sem_giro_90d AS valor_estoque_sem_giro,
        CASE WHEN g.total_valor_estoque_90d > 0
             THEN (g.valor_estoque_com_giro_90d / g.total_valor_estoque_90d) * 100
             ELSE 0 END AS giro_medio_anual
    FROM agreg_geral_90d g

    UNION ALL

    -- 2) Linha Geral (todo o estoque)
    SELECT
        'Geral' AS filial_codigo,
        'Geral' AS classificacao_n1,
        'Geral' AS classificacao_n2,
        'Geral' AS classificacao_n3,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(valor_estoque_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN valor_estoque_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0
             THEN (SUM(valor_estoque_com_giro) / SUM(valor_estoque)) * 100
             ELSE 0 END AS giro_medio_anual
    FROM total_snapshot

    UNION ALL

    -- 3) Por filial (universo 90d)
    SELECT
        filial_codigo,
        'Geral' AS classificacao_n1,
        'Geral' AS classificacao_n2,
        'Geral' AS classificacao_n3,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(valor_estoque_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN valor_estoque_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0
             THEN (SUM(valor_estoque_com_giro) / SUM(valor_estoque)) * 100
             ELSE 0 END AS giro_medio_anual
    FROM dados_90d
    GROUP BY filial_codigo

    UNION ALL

    -- 4) Por classificacao_n1 (Geral rede, universo 90d)
    SELECT
        'Geral' AS filial_codigo,
        classificacao_n1,
        'Geral' AS classificacao_n2,
        'Geral' AS classificacao_n3,
        COUNT(*) AS total_produtos,
        SUM(valor_estoque) AS total_valor_estoque,
        SUM(valor_estoque_com_giro) AS valor_estoque_com_giro,
        SUM(CASE WHEN valor_estoque_com_giro = 0 THEN valor_estoque ELSE 0 END) AS valor_estoque_sem_giro,
        CASE WHEN SUM(valor_estoque) > 0
             THEN (SUM(valor_estoque_com_giro) / SUM(valor_estoque)) * 100
             ELSE 0 END AS giro_medio_anual
    FROM dados_90d
    WHERE classificacao_n1 IS NOT NULL
    GROUP BY classificacao_n1

    ORDER BY filial_codigo, classificacao_n1;
    """

    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(), {
                'total_cmv': 0.0, 'total_cmv_giro': 0.0, 'total_cmv_sem_giro': 0.0,
                'perc_giro': 0.0, 'perc_sem_giro': 100.0, 'giro_medio': 0.0,
                'total_cmv_90d': 0.0, 'total_cmv_90d_giro': 0.0, 'total_cmv_90d_sem_giro': 0.0,
                'perc_giro_90d': 0.0, 'perc_sem_giro_90d': 100.0
            }

        def _get_row(df_, filial_val):
            q = df_[df_['filial_codigo'] == filial_val]
            return q.iloc[0] if not q.empty else None

        row_total = _get_row(df, 'Geral')
        row_90d = _get_row(df, 'Geral_90d')

        kpis_giro = {
            'total_cmv': 0.0,
            'total_cmv_giro': 0.0,
            'total_cmv_sem_giro': 0.0,
            'perc_giro': 0.0,
            'perc_sem_giro': 100.0,
            'giro_medio': 0.0,
            'total_cmv_90d': 0.0,
            'total_cmv_90d_giro': 0.0,
            'total_cmv_90d_sem_giro': 0.0,
            'perc_giro_90d': 0.0,
            'perc_sem_giro_90d': 100.0
        }

        if row_total is not None:
            tv = float(row_total.total_valor_estoque or 0)
            vg = float(row_total.valor_estoque_com_giro or 0)
            vsg = float(row_total.valor_estoque_sem_giro or 0)
            perc = (vg / tv * 100) if tv > 0 else 0.0
            kpis_giro.update({
                'total_cmv': tv,
                'total_cmv_giro': vg,
                'total_cmv_sem_giro': vsg,
                'perc_giro': perc,
                'perc_sem_giro': 100.0 - perc,
                'giro_medio': float(row_total.giro_medio_anual or 0)
            })

        if row_90d is not None:
            tv90 = float(row_90d.total_valor_estoque or 0)
            vg90 = float(row_90d.valor_estoque_com_giro or 0)
            vsg90 = float(row_90d.valor_estoque_sem_giro or 0)
            perc90 = (vg90 / tv90 * 100) if tv90 > 0 else 0.0
            kpis_giro.update({
                'total_cmv_90d': tv90,
                'total_cmv_90d_giro': vg90,
                'total_cmv_90d_sem_giro': vsg90,
                'perc_giro_90d': perc90,
                'perc_sem_giro_90d': 100.0 - perc90
            })

        # Formatação
        for col in ['total_valor_estoque','valor_estoque_com_giro','valor_estoque_sem_giro','giro_medio_anual']:
            if col in df:
                df[col] = df[col].round(2 if col != 'giro_medio_anual' else 4)
        if 'total_produtos' in df:
            df['total_produtos'] = df['total_produtos'].astype(int)

        return df, kpis_giro
    except Exception as e:
        st.error(f"Erro ao calcular giro: {e}")
        return pd.DataFrame(), {
            'total_cmv': 0.0, 'total_cmv_giro': 0.0, 'total_cmv_sem_giro': 0.0,
            'perc_giro': 0.0, 'perc_sem_giro': 100.0, 'giro_medio': 0.0,
            'total_cmv_90d': 0.0, 'total_cmv_90d_giro': 0.0, 'total_cmv_90d_sem_giro': 0.0,
            'perc_giro_90d': 0.0, 'perc_sem_giro_90d': 100.0
        }

def calcular_giro_por_curva_abc_duck(data_atual):
    """
    Calcula giro de estoque por curva ABC e suas combinações usando cache_curva_abc_90d.
    Reaproveita caches:
      - cache_curva_abc_90d (ou cache_curva_abc_curr_90d fallback)
      - cache_estoque_snapshot_90d
      - cache_comprados_90d
      - cache_vendidos_30d_ids
    Saída: filial_codigo, curvaABC, classificacao_n1, total_produtos,
           total_valor_estoque, valor_estoque_com_giro, valor_estoque_sem_giro, giro_medio_anual
    """
    try:
        ensure_bases_estoque(str(data_atual))
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_limite_ontem = ontem.strftime('%Y-%m-%d')

        # Detecta nome correto da tabela ABC
        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            try:
                duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
            except Exception as e:
                st.error(f"Tabela de Curva ABC não encontrada: {e}")
                return pd.DataFrame()

        sql = f"""
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_limite_ontem}'
        ),
        base AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                s.valor_estoque,
                s.classificacao_n1,
                s.classificacao_n2,
                s.classificacao_n3,
                COALESCE(ca.curvaABC,'D') AS curvaABC,
                CASE WHEN v30.embalagemid IS NOT NULL THEN s.valor_estoque ELSE 0 END AS valor_estoque_com_giro
            FROM cache_estoque_snapshot_90d s
            INNER JOIN cache_comprados_90d cmp
              ON s.filial_codigo = cmp.filial_codigo AND s.embalagemid = cmp.embalagemid
            LEFT JOIN cache_vendidos_30d_ids v30
              ON s.filial_codigo = v30.filial_codigo AND s.embalagemid = v30.embalagemid
            LEFT JOIN curva_abc ca
              ON s.filial_codigo = ca.filial_codigo AND s.embalagemid = ca.embalagemid
        ),
        agg_curva_rede AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                'Geral' AS classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY curvaABC
        ),
        agg_curva_filial AS (
            SELECT
                filial_codigo,
                curvaABC,
                'Geral' AS classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY filial_codigo, curvaABC
        ),
        agg_filial_classif AS (
            SELECT
                filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, classificacao_n1
        ),
        agg_classif_rede AS (
            SELECT
                'Geral' AS filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY classificacao_n1
        ),
        agg_curva_classif_rede AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
            GROUP BY curvaABC, classificacao_n1
        ),
        agg_curva_filial_classif AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n1,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        ),
        uniao AS (
            SELECT * FROM agg_curva_rede
            UNION ALL SELECT * FROM agg_curva_filial
            UNION ALL SELECT * FROM agg_filial_classif
            UNION ALL SELECT * FROM agg_classif_rede
            UNION ALL SELECT * FROM agg_curva_classif_rede
            UNION ALL SELECT * FROM agg_curva_filial_classif
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            total_produtos,
            total_valor_estoque,
            valor_estoque_com_giro,
            (total_valor_estoque - valor_estoque_com_giro) AS valor_estoque_sem_giro,
            CASE WHEN total_valor_estoque > 0
                 THEN (valor_estoque_com_giro / total_valor_estoque) * 100
                 ELSE 0 END AS giro_medio_anual
        FROM uniao
        ORDER BY filial_codigo, curvaABC, classificacao_n1;
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame()

        df['total_produtos'] = df['total_produtos'].astype(int)
        for c in ['total_valor_estoque','valor_estoque_com_giro','valor_estoque_sem_giro']:
            df[c] = df[c].round(2)
        df['giro_medio_anual'] = df['giro_medio_anual'].round(4)
        return df

    except Exception as e:
        st.error(f"Erro ao calcular giro por curva ABC: {e}")
        return pd.DataFrame()


def calcular_fator_cobertura_duck(data_atual):
    """
    Versão otimizada.
    Usa:
      - cache_estoque_snapshot (snapshot completo até ontem) -> valor_estoque
      - cache_vendas_30d       (cmv_30d por filial+embalagem)
    Saída: stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    ensure_bases_estoque(str(data_atual))
    sql = """
    WITH vendas AS (
        SELECT SUM(cmv_30d) AS cmv_vendido_30d
        FROM cache_vendas_30d
    ),
    estoque AS (
        SELECT SUM(COALESCE(valor_estoque,0)) AS stock_cmv
        FROM cache_estoque_snapshot
    )
    SELECT
        e.stock_cmv,
        v.cmv_vendido_30d,
        CASE WHEN v.cmv_vendido_30d > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque e CROSS JOIN vendas v;
    """
    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(columns=["stock_cmv","cmv_vendido_30d","cobertura_ratio"])
        df["stock_cmv"] = df["stock_cmv"].round(2)
        df["cmv_vendido_30d"] = df["cmv_vendido_30d"].round(2)
        df["cobertura_ratio"] = df["cobertura_ratio"].round(4)
        return df
    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura: {e}")
        return pd.DataFrame(columns=["stock_cmv","cmv_vendido_30d","cobertura_ratio"])

def calcular_fator_cobertura_por_filial_duck(data_atual):
    """
    Versão otimizada por filial.
    Usa cache_estoque_snapshot e cache_vendas_30d.
    Colunas: filial_codigo, stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    ensure_bases_estoque(str(data_atual))
    sql = """
    WITH vendas AS (
        SELECT filial_codigo, SUM(cmv_30d) AS cmv_vendido_30d
        FROM cache_vendas_30d
        GROUP BY filial_codigo
    ),
    estoque AS (
        SELECT filial_codigo, SUM(COALESCE(valor_estoque,0)) AS stock_cmv
        FROM cache_estoque_snapshot
        GROUP BY filial_codigo
    )
    SELECT
        e.filial_codigo,
        e.stock_cmv,
        COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
        CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
    FROM estoque e
    LEFT JOIN vendas v USING (filial_codigo)
    ORDER BY filial_codigo;
    """
    try:
        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(columns=["filial_codigo","stock_cmv","cmv_vendido_30d","cobertura_ratio"])
        df["stock_cmv"] = df["stock_cmv"].round(2)
        df["cmv_vendido_30d"] = df["cmv_vendido_30d"].round(2)
        df["cobertura_ratio"] = df["cobertura_ratio"].round(4)
        return df
    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura por filial: {e}")
        return pd.DataFrame(columns=["filial_codigo","stock_cmv","cmv_vendido_30d","cobertura_ratio"])
    
def calcular_fator_cobertura_por_curva_abc_duck(data_atual):
    """
    Calcula fator de cobertura (stock CMV / CMV vendido 30d) por Curva ABC e combinações.
    Agora reutiliza caches:
      - cache_curva_abc_90d (ou cache_curva_abc_curr_90d como fallback)
      - cache_estoque_snapshot_90d (valor_estoque e classificacao_n1)
      - cache_vendas_30d (cmv_30d por filial+embalagem)
    Combinações retornadas:
      (1) Curva ABC (rede)
      (2) Curva ABC + filial
      (2b) Filial + classificacao_n1 (curvaABC='Geral')
      (2c) classificacao_n1 (rede, curvaABC='Geral')
      (3) Curva ABC + classificacao_n1 (rede)
      (4) Curva ABC + filial + classificacao_n1
    Colunas: filial_codigo, curvaABC, classificacao_n1, stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    try:
        ensure_bases_estoque(str(data_atual))
        ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_ref = ontem.strftime('%Y-%m-%d')

        # Detecta a tabela de curva ABC já materializada
        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            try:
                duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
            except Exception as e:
                st.error(f"Tabela de Curva ABC não encontrada: {e}")
                return pd.DataFrame()

        sql = f"""
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        -- Estoque (valor_estoque) + classificacao + curva
        estoque AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                s.valor_estoque,
                s.classificacao_n1,
                COALESCE(c.curvaABC,'D') AS curvaABC
            FROM cache_estoque_snapshot_90d s
            LEFT JOIN curva_abc c
              ON s.filial_codigo = c.filial_codigo
             AND s.embalagemid = c.embalagemid
        ),
        -- Vendas 30d (cmv) enriquecidas com curva e classificacao_n1 via estoque
        vendas_30d AS (
            SELECT
                v.filial_codigo,
                v.embalagemid,
                COALESCE(e.curvaABC,'D') AS curvaABC,
                e.classificacao_n1,
                COALESCE(v.cmv_30d,0) AS cmv_vendido_30d
            FROM cache_vendas_30d v
            LEFT JOIN estoque e
              ON v.filial_codigo = e.filial_codigo
             AND v.embalagemid = e.embalagemid
        ),
        -- Agregações de estoque
        estoque_curva_rede AS (
            SELECT
                curvaABC,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            GROUP BY curvaABC
        ),
        estoque_curva_filial AS (
            SELECT
                filial_codigo,
                curvaABC,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            GROUP BY filial_codigo, curvaABC
        ),
        estoque_filial_classif AS (
            SELECT
                filial_codigo,
                classificacao_n1,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, classificacao_n1
        ),
        estoque_classif_rede AS (
            SELECT
                classificacao_n1,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY classificacao_n1
        ),
        estoque_curva_classif_rede AS (
            SELECT
                curvaABC,
                classificacao_n1,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY curvaABC, classificacao_n1
        ),
        estoque_curva_filial_classif AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n1,
                SUM(valor_estoque) AS stock_cmv
            FROM estoque
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        ),
        -- Agregações de vendas
        vendas_curva_rede AS (
            SELECT curvaABC, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            GROUP BY curvaABC
        ),
        vendas_curva_filial AS (
            SELECT filial_codigo, curvaABC, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            GROUP BY filial_codigo, curvaABC
        ),
        vendas_filial_classif AS (
            SELECT filial_codigo, classificacao_n1, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, classificacao_n1
        ),
        vendas_classif_rede AS (
            SELECT classificacao_n1, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY classificacao_n1
        ),
        vendas_curva_classif_rede AS (
            SELECT curvaABC, classificacao_n1, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY curvaABC, classificacao_n1
        ),
        vendas_curva_filial_classif AS (
            SELECT filial_codigo, curvaABC, classificacao_n1, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_30d
            WHERE classificacao_n1 IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        )

        -- 1) Curva ABC (rede)
        SELECT
            'Geral' AS filial_codigo,
            e.curvaABC,
            'Geral' AS classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_rede e
        LEFT JOIN vendas_curva_rede v
          ON e.curvaABC = v.curvaABC
        WHERE e.curvaABC IS NOT NULL

        UNION ALL
        -- 2) Curva ABC + filial
        SELECT
            e.filial_codigo,
            e.curvaABC,
            'Geral' AS classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_filial e
        LEFT JOIN vendas_curva_filial v
          ON e.filial_codigo = v.filial_codigo AND e.curvaABC = v.curvaABC
        WHERE e.curvaABC IS NOT NULL

        UNION ALL
        -- 2b) Filial + classificacao_n1 (curvaABC='Geral')
        SELECT
            e.filial_codigo,
            'Geral' AS curvaABC,
            e.classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_filial_classif e
        LEFT JOIN vendas_filial_classif v
          ON e.filial_codigo = v.filial_codigo AND e.classificacao_n1 = v.classificacao_n1
        WHERE e.classificacao_n1 IS NOT NULL

        UNION ALL
        -- 2c) classificacao_n1 (rede, curvaABC='Geral')
        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            e.classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_classif_rede e
        LEFT JOIN vendas_classif_rede v
          ON e.classificacao_n1 = v.classificacao_n1
        WHERE e.classificacao_n1 IS NOT NULL

        UNION ALL
        -- 3) Curva ABC + classificacao_n1 (rede)
        SELECT
            'Geral' AS filial_codigo,
            e.curvaABC,
            e.classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_classif_rede e
        LEFT JOIN vendas_curva_classif_rede v
          ON e.curvaABC = v.curvaABC AND e.classificacao_n1 = v.classificacao_n1
        WHERE e.curvaABC IS NOT NULL AND e.classificacao_n1 IS NOT NULL

        UNION ALL
        -- 4) Curva ABC + filial + classificacao_n1
        SELECT
            e.filial_codigo,
            e.curvaABC,
            e.classificacao_n1,
            e.stock_cmv,
            COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d,0) > 0 THEN e.stock_cmv / v.cmv_vendido_30d ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_filial_classif e
        LEFT JOIN vendas_curva_filial_classif v
          ON e.filial_codigo = v.filial_codigo
         AND e.curvaABC = v.curvaABC
         AND e.classificacao_n1 = v.classificacao_n1
        WHERE e.curvaABC IS NOT NULL AND e.classificacao_n1 IS NOT NULL

        ORDER BY filial_codigo, curvaABC, classificacao_n1;
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(columns=[
                "filial_codigo","curvaABC","classificacao_n1",
                "stock_cmv","cmv_vendido_30d","cobertura_ratio"
            ])

        df["stock_cmv"] = df["stock_cmv"].round(2)
        df["cmv_vendido_30d"] = df["cmv_vendido_30d"].round(2)
        df["cobertura_ratio"] = df["cobertura_ratio"].round(4)
        return df

    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura por curva ABC: {e}")
        return pd.DataFrame(columns=[
            "filial_codigo","curvaABC","classificacao_n1",
            "stock_cmv","cmv_vendido_30d","cobertura_ratio"
        ])

def calcular_disponibilidade_por_classificacao_n2_duck(data_atual):
    """
    Calcula índice de disponibilidade/ruptura por classificacao_n2 (subgrupo) e suas combinações.
    Filtro: produtos com compras nos últimos 90 dias E vendas nos últimos 30 dias.
    
    Calcula por classificacao_n2 e suas combinações:
    - Por classificacao_n2 (geral da rede)
    - Por classificacao_n2 + filial
    - Por curva ABC + classificacao_n2 (geral da rede)
    - Por curva ABC + filial + classificacao_n2
    
    Retorna DataFrame com colunas:
    filial_codigo, curvaABC, classificacao_n2, total_produtos, produtos_zerados, 
    indice_ruptura, disponibilidade
    """
    try:
        ensure_bases_estoque(str(data_atual))

        data_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).date()
        data_limite_ontem = data_ontem.strftime('%Y-%m-%d')

        abc_table = 'cache_curva_abc_90d'
        try:
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")
        except Exception:
            abc_table = 'cache_curva_abc_curr_90d'
            duck_query(f"SELECT 1 FROM {abc_table} LIMIT 1")

        sql = f"""
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_limite_ontem}'
        ),
        denominador AS (
            SELECT filial_codigo, embalagemid
            FROM cache_denominador_disp
        ),
        estoque AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                COALESCE(s.estoque, 0) AS estoque,
                s.classificacao_n2
            FROM cache_estoque_snapshot_90d s
        ),
        base AS (
            SELECT
                d.filial_codigo,
                d.embalagemid,
                e.estoque,
                e.classificacao_n2,
                COALESCE(c.curvaABC, 'D') AS curvaABC
            FROM denominador d
            JOIN estoque e
              ON d.filial_codigo = e.filial_codigo
             AND d.embalagemid = e.embalagemid
            LEFT JOIN curva_abc c
              ON d.filial_codigo = c.filial_codigo
             AND d.embalagemid = c.embalagemid
            WHERE e.classificacao_n2 IS NOT NULL
        ),
        agg_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            GROUP BY classificacao_n2
        ),
        agg_classif_filial AS (
            SELECT
                filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            GROUP BY filial_codigo, classificacao_n2
        ),
        agg_curva_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY curvaABC, classificacao_n2
        ),
        agg_curva_filial_classif AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(CASE WHEN estoque = 0 THEN 1 ELSE 0 END) AS produtos_zerados
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        uniao AS (
            SELECT * FROM agg_classif_geral
            UNION ALL SELECT * FROM agg_classif_filial
            UNION ALL SELECT * FROM agg_curva_classif_geral
            UNION ALL SELECT * FROM agg_curva_filial_classif
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n2,
            total_produtos,
            produtos_zerados,
            CASE WHEN total_produtos > 0
                 THEN (produtos_zerados * 100.0 / total_produtos)
                 ELSE 0 END AS indice_ruptura,
            CASE WHEN total_produtos > 0
                 THEN (100.0 - (produtos_zerados * 100.0 / total_produtos))
                 ELSE 0 END AS disponibilidade
        FROM uniao
        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df_resultado = duck_query(sql)

        if df_resultado is None or df_resultado.empty:
            return pd.DataFrame()

        df_resultado['total_produtos'] = df_resultado['total_produtos'].astype(int)
        df_resultado['produtos_zerados'] = df_resultado['produtos_zerados'].astype(int)
        df_resultado['indice_ruptura'] = df_resultado['indice_ruptura'].round(4)
        df_resultado['disponibilidade'] = df_resultado['disponibilidade'].round(4)

        return df_resultado

    except Exception as e:
        st.error(f"Erro ao calcular disponibilidade por classificacao_n2: {e}")
        return pd.DataFrame()
    
def calcular_giro_por_classificacao_n2_duck(data_atual):
    """
    Calcula giro de estoque por classificacao_n2 (subgrupo) e suas combinações usando caches pré-processados.

    Combinações retornadas:
    - classificacao_n2 (rede, curvaABC='Geral')
    - classificacao_n2 + filial (curvaABC='Geral')
    - curvaABC + classificacao_n2 (rede)
    - curvaABC + filial + classificacao_n2

    Colunas: filial_codigo, curvaABC, classificacao_n2, total_produtos,
             total_valor_estoque, valor_estoque_com_giro, valor_estoque_sem_giro, giro_medio_anual
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

        sql = f"""
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        base AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                s.valor_estoque,
                s.classificacao_n2,
                COALESCE(ca.curvaABC, 'D') AS curvaABC,
                CASE WHEN v30.embalagemid IS NOT NULL THEN s.valor_estoque ELSE 0 END AS valor_estoque_com_giro
            FROM cache_estoque_snapshot_90d s
            INNER JOIN cache_comprados_90d cmp
              ON s.filial_codigo = cmp.filial_codigo AND s.embalagemid = cmp.embalagemid
            LEFT JOIN cache_vendidos_30d_ids v30
              ON s.filial_codigo = v30.filial_codigo AND s.embalagemid = v30.embalagemid
            LEFT JOIN curva_abc ca
              ON s.filial_codigo = ca.filial_codigo AND s.embalagemid = ca.embalagemid
            WHERE s.classificacao_n2 IS NOT NULL
        ),
        agg_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            GROUP BY classificacao_n2
        ),
        agg_classif_filial AS (
            SELECT
                filial_codigo,
                'Geral' AS curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            GROUP BY filial_codigo, classificacao_n2
        ),
        agg_curva_classif_geral AS (
            SELECT
                'Geral' AS filial_codigo,
                curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY curvaABC, classificacao_n2
        ),
        agg_curva_filial_classif AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n2,
                COUNT(*) AS total_produtos,
                SUM(valor_estoque) AS total_valor_estoque,
                SUM(valor_estoque_com_giro) AS valor_estoque_com_giro
            FROM base
            WHERE curvaABC IS NOT NULL
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        uniao AS (
            SELECT * FROM agg_classif_geral
            UNION ALL SELECT * FROM agg_classif_filial
            UNION ALL SELECT * FROM agg_curva_classif_geral
            UNION ALL SELECT * FROM agg_curva_filial_classif
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n2,
            total_produtos,
            total_valor_estoque,
            valor_estoque_com_giro,
            (total_valor_estoque - valor_estoque_com_giro) AS valor_estoque_sem_giro,
            CASE WHEN total_valor_estoque > 0
                 THEN (valor_estoque_com_giro / total_valor_estoque) * 100
                 ELSE 0 END AS giro_medio_anual
        FROM uniao
        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame()

        df['total_produtos'] = df['total_produtos'].astype(int)
        for col in ['total_valor_estoque', 'valor_estoque_com_giro', 'valor_estoque_sem_giro']:
            df[col] = df[col].round(2)
        df['giro_medio_anual'] = df['giro_medio_anual'].round(4)

        return df

    except Exception as e:
        st.error(f"Erro ao calcular giro por classificacao_n2: {e}")
        return pd.DataFrame()

def calcular_fator_cobertura_por_classificacao_n2_duck(data_atual):
    """
    Calcula fator de cobertura (stock CMV / CMV vendido 30d) por classificacao_n2 (subgrupo) e suas combinações.
    
    Combinações calculadas:
    - classificacao_n2 (rede, curvaABC='Geral')
    - classificacao_n2 + filial (curvaABC='Geral')
    - curvaABC + classificacao_n2 (rede)
    - curvaABC + filial + classificacao_n2

    Retorna DataFrame com colunas:
    filial_codigo, curvaABC, classificacao_n2, stock_cmv, cmv_vendido_30d, cobertura_ratio
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

        sql = f"""
        WITH curva_abc AS (
            SELECT filial_codigo, embalagemid, curvaABC
            FROM {abc_table}
            WHERE data_ref = DATE '{data_ref}'
        ),
        estoque_base AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                s.classificacao_n2,
                COALESCE(c.curvaABC, 'D') AS curvaABC,
                COALESCE(s.valor_estoque, 0) AS valor_estoque
            FROM cache_estoque_snapshot_90d s
            LEFT JOIN curva_abc c
              ON s.filial_codigo = c.filial_codigo
             AND s.embalagemid = c.embalagemid
            WHERE s.classificacao_n2 IS NOT NULL
        ),
        vendas_enriquecidas AS (
            SELECT
                v.filial_codigo,
                COALESCE(e.curvaABC, 'D') AS curvaABC,
                e.classificacao_n2,
                SUM(COALESCE(v.cmv_30d, 0)) AS cmv_vendido_30d
            FROM cache_vendas_30d v
            LEFT JOIN estoque_base e
              ON v.filial_codigo = e.filial_codigo
             AND v.embalagemid = e.embalagemid
            WHERE e.classificacao_n2 IS NOT NULL
            GROUP BY v.filial_codigo, COALESCE(e.curvaABC, 'D'), e.classificacao_n2
        ),
        estoque_classif_geral AS (
            SELECT classificacao_n2, SUM(valor_estoque) AS stock_cmv
            FROM estoque_base
            GROUP BY classificacao_n2
        ),
        estoque_por_filial_classif AS (
            SELECT filial_codigo, classificacao_n2, SUM(valor_estoque) AS stock_cmv
            FROM estoque_base
            GROUP BY filial_codigo, classificacao_n2
        ),
        estoque_curva_classif_geral AS (
            SELECT curvaABC, classificacao_n2, SUM(valor_estoque) AS stock_cmv
            FROM estoque_base
            GROUP BY curvaABC, classificacao_n2
        ),
        estoque_curva_filial_classif AS (
            SELECT filial_codigo, curvaABC, classificacao_n2, SUM(valor_estoque) AS stock_cmv
            FROM estoque_base
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        vendas_classif_geral AS (
            SELECT classificacao_n2, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_enriquecidas
            GROUP BY classificacao_n2
        ),
        vendas_por_filial_classif AS (
            SELECT filial_codigo, classificacao_n2, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_enriquecidas
            GROUP BY filial_codigo, classificacao_n2
        ),
        vendas_curva_classif_geral AS (
            SELECT curvaABC, classificacao_n2, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_enriquecidas
            GROUP BY curvaABC, classificacao_n2
        ),
        vendas_curva_filial_classif AS (
            SELECT filial_codigo, curvaABC, classificacao_n2, SUM(cmv_vendido_30d) AS cmv_vendido_30d
            FROM vendas_enriquecidas
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        )
        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            ec.classificacao_n2,
            ec.stock_cmv,
            COALESCE(vc.cmv_vendido_30d, 0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(vc.cmv_vendido_30d, 0) > 0
                 THEN ec.stock_cmv / vc.cmv_vendido_30d
                 ELSE NULL END AS cobertura_ratio
        FROM estoque_classif_geral ec
        LEFT JOIN vendas_classif_geral vc
          ON ec.classificacao_n2 = vc.classificacao_n2

        UNION ALL

        SELECT
            epf.filial_codigo,
            'Geral' AS curvaABC,
            epf.classificacao_n2,
            epf.stock_cmv,
            COALESCE(vpf.cmv_vendido_30d, 0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(vpf.cmv_vendido_30d, 0) > 0
                 THEN epf.stock_cmv / vpf.cmv_vendido_30d
                 ELSE NULL END AS cobertura_ratio
        FROM estoque_por_filial_classif epf
        LEFT JOIN vendas_por_filial_classif vpf
          ON epf.filial_codigo = vpf.filial_codigo
         AND epf.classificacao_n2 = vpf.classificacao_n2

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            eg.curvaABC,
            eg.classificacao_n2,
            eg.stock_cmv,
            COALESCE(vg.cmv_vendido_30d, 0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(vg.cmv_vendido_30d, 0) > 0
                 THEN eg.stock_cmv / vg.cmv_vendido_30d
                 ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_classif_geral eg
        LEFT JOIN vendas_curva_classif_geral vg
          ON eg.curvaABC = vg.curvaABC
         AND eg.classificacao_n2 = vg.classificacao_n2

        UNION ALL

        SELECT
            ef.filial_codigo,
            ef.curvaABC,
            ef.classificacao_n2,
            ef.stock_cmv,
            COALESCE(v.cmv_vendido_30d, 0) AS cmv_vendido_30d,
            CASE WHEN COALESCE(v.cmv_vendido_30d, 0) > 0
                 THEN ef.stock_cmv / v.cmv_vendido_30d
                 ELSE NULL END AS cobertura_ratio
        FROM estoque_curva_filial_classif ef
        LEFT JOIN vendas_curva_filial_classif v
          ON ef.filial_codigo = v.filial_codigo
         AND ef.curvaABC = v.curvaABC
         AND ef.classificacao_n2 = v.classificacao_n2

        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df = duck_query(sql)

        if df is None or df.empty:
            return pd.DataFrame()

        df['stock_cmv'] = df['stock_cmv'].round(2)
        df['cmv_vendido_30d'] = df['cmv_vendido_30d'].round(2)
        df['cobertura_ratio'] = df['cobertura_ratio'].round(4)

        return df

    except Exception as e:
        st.error(f"Erro ao calcular fator de cobertura por classificacao_n2: {e}")
        return pd.DataFrame()