import pandas as pd
import streamlit as st
from core.database import duck_query
from business_logic.estoque.base_sets import ensure_bases_estoque

def calcular_gmroi_baseado_vendas_duck(data_atual, periodo_vendas=90):
    """
    Versão otimizada priorizando bases cache_ (quando existentes).
    Mantém MESMAS colunas e semântica.
    
    Estratégia:
    1. Usa fact_vendas_final (filtra período) para receita, cmv, margem.
    2. Para estoque médio tenta usar cache_estoque_diario (esperado: um registro por dia por (filial,embalagemid)
       com as colunas: filial_codigo, embalagemid, data_dia, estoque, customedio, valor_estoque_dia (customedio*estoque)).
       Se não existir, faz fallback para derivar a visão diária a partir de fact_estoque_final (último registro do dia).
    3. Estoque médio por item = AVG(valor_estoque_dia) nos dias em que apareceu.
    4. Agrega por filial e gera linha 'Geral'.
    """
    try:
        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        data_limite_periodo = (pd.Timestamp(data_limite_ontem) - pd.Timedelta(days=periodo_vendas)).strftime('%Y-%m-%d')

        # Verifica existência da tabela cache_estoque_diario (opcional)
        try:
            exists_df = duck_query("SELECT 1 FROM information_schema.tables WHERE table_name = 'cache_estoque_diario' LIMIT 1;")
            has_cache_diario = not (exists_df is None or exists_df.empty)
        except:
            has_cache_diario = False

        if has_cache_diario:
            estoque_diario_cte = f"""
            -- Usa cache pré-calculada (assume 1 linha por dia/item/filial representando o snapshot válido)
            estoque_diario AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    data_dia,
                    valor_estoque_dia AS valor_dia
                FROM cache_estoque_diario
                WHERE data_dia BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
                  AND valor_estoque_dia >= 0
            ),
            """
        else:
            estoque_diario_cte = f"""
            -- Fallback: deriva último registro do dia a partir de fact_estoque_final
            estoque_diario_raw AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    DATE(datahora) AS data_dia,
                    customedio,
                    estoque,
                    ROW_NUMBER() OVER (
                        PARTITION BY filial_codigo, embalagemid, DATE(datahora)
                        ORDER BY datahora DESC
                    ) AS rn_dia
                FROM fact_estoque_final
                WHERE DATE(datahora) BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
                  AND estoque >= 0
                  AND customedio > 0
            ),
            estoque_diario AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    data_dia,
                    customedio * estoque AS valor_dia
                FROM estoque_diario_raw
                WHERE rn_dia = 1
            ),
            """

        sql = f"""
        -- Vendas agregadas por filial (receita real, cmv, margem)
        WITH vendas_filial AS (
            SELECT
                filial_codigo,
                SUM( (item_valorunitario - COALESCE(item_desconto,0)) * ABS(item_quantidade) ) AS receita_real_vendas,
                SUM( customedio * ABS(item_quantidade) ) AS cmv_vendas,
                SUM( ((item_valorunitario - COALESCE(item_desconto,0)) - customedio) * ABS(item_quantidade) ) AS margem_bruta_vendas,
                COUNT(*) AS total_transacoes,
                SUM(ABS(item_quantidade)) AS total_quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
              AND customedio > 0
              AND item_valorunitario > 0
            GROUP BY filial_codigo
        ),
        vendas_geral AS (
            SELECT
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_filial
        ),
        {estoque_diario_cte}
        estoque_medio_item AS (
            SELECT
                filial_codigo,
                embalagemid,
                AVG(valor_dia) AS valor_estoque_medio
            FROM estoque_diario
            GROUP BY filial_codigo, embalagemid
        ),
        estoque_medio_filial AS (
            SELECT
                filial_codigo,
                SUM(valor_estoque_medio) AS valor_medio_estoque,
                COUNT(*) AS total_produtos_estoque
            FROM estoque_medio_item
            GROUP BY filial_codigo
        ),
        estoque_medio_geral AS (
            SELECT
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_medio_filial
        )
        -- Linha Geral
        SELECT
            'Geral' AS filial_codigo,
            'Baseado_Vendas_Real' AS tipo,
            {periodo_vendas} AS periodo_dias,
            vg.receita_real_vendas,
            vg.cmv_vendas,
            vg.margem_bruta_vendas,
            eg.valor_medio_estoque,
            vg.total_transacoes,
            vg.total_quantidade_vendida,
            eg.total_produtos_estoque,
            CASE WHEN eg.valor_medio_estoque > 0
                 THEN (vg.margem_bruta_vendas / eg.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN eg.valor_medio_estoque > 0
                 THEN vg.margem_bruta_vendas / eg.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_geral vg
        CROSS JOIN estoque_medio_geral eg
        UNION ALL
        -- Por Filial
        SELECT
            vf.filial_codigo,
            'Baseado_Vendas_Real' AS tipo,
            {periodo_vendas} AS periodo_dias,
            vf.receita_real_vendas,
            vf.cmv_vendas,
            vf.margem_bruta_vendas,
            emf.valor_medio_estoque,
            vf.total_transacoes,
            vf.total_quantidade_vendida,
            emf.total_produtos_estoque,
            CASE WHEN emf.valor_medio_estoque > 0
                 THEN (vf.margem_bruta_vendas / emf.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN emf.valor_medio_estoque > 0
                 THEN vf.margem_bruta_vendas / emf.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial vf
        INNER JOIN estoque_medio_filial emf USING (filial_codigo)
        ORDER BY filial_codigo;
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame(columns=[
                'filial_codigo','tipo','periodo_dias','receita_real_vendas','cmv_vendas',
                'margem_bruta_vendas','valor_medio_estoque','total_transacoes',
                'total_quantidade_vendida','total_produtos_estoque','gmroi_percentual','gmroi_ratio'
            ])

        df['periodo_dias'] = df['periodo_dias'].astype(int)
        for col in ['receita_real_vendas','cmv_vendas','margem_bruta_vendas','valor_medio_estoque',
                    'gmroi_percentual','gmroi_ratio','total_quantidade_vendida']:
            if col in df:
                df[col] = df[col].round(4 if col in ('gmroi_percentual','gmroi_ratio') else 2)
        for col in ['total_transacoes','total_produtos_estoque']:
            if col in df:
                df[col] = df[col].fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Erro ao calcular GMROI baseado em vendas reais (cache/refatorado): {e}")
        return pd.DataFrame()
    
def calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=90):
    try:
        ensure_bases_estoque(str(data_atual))
        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        data_limite_periodo = (pd.Timestamp(data_limite_ontem) - pd.Timedelta(days=periodo_vendas)).strftime('%Y-%m-%d')

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
        vendas_periodo AS (
            SELECT
                v.filial_codigo,
                v.item_embalagemid AS embalagemid,
                v.data_date,
                v.classificacao_n1,
                COALESCE(ca.curvaABC, 'D') AS curvaABC,
                ABS(v.item_quantidade) AS quantidade_vendida,
                v.item_valorunitario,
                COALESCE(v.item_desconto, 0) AS item_desconto,
                (v.item_valorunitario - COALESCE(v.item_desconto, 0)) AS item_precoaposdesconto,
                v.customedio,
                (v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade) AS receita_real,
                v.customedio * ABS(v.item_quantidade) AS cmv_real,
                ((v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade)) - (v.customedio * ABS(v.item_quantidade)) AS margem_bruta_real
            FROM fact_vendas_final v
            LEFT JOIN curva_abc ca
              ON v.filial_codigo = ca.filial_codigo
             AND v.item_embalagemid = ca.embalagemid
            WHERE v.data_date BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
              AND v.customedio > 0
              AND v.item_valorunitario > 0
        ),
        estoque_diario AS (
            SELECT
                e.filial_codigo,
                e.embalagemid,
                DATE(e.datahora) AS data_estoque,
                e.estoque,
                e.customedio,
                ROW_NUMBER() OVER (
                    PARTITION BY e.filial_codigo, e.embalagemid, DATE(e.datahora)
                    ORDER BY e.datahora DESC
                ) AS rn_dia
            FROM fact_estoque_final e
            WHERE DATE(e.datahora) BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
              AND e.estoque >= 0
              AND e.customedio > 0
        ),
        estoque_medio_base AS (
            SELECT
                filial_codigo,
                embalagemid,
                AVG(customedio * estoque) AS valor_estoque_medio
            FROM estoque_diario
            WHERE rn_dia = 1
            GROUP BY filial_codigo, embalagemid
        ),
        classificacao_atual AS (
            SELECT
                filial_codigo,
                embalagemid,
                classificacao_n1,
                ROW_NUMBER() OVER (
                    PARTITION BY filial_codigo, embalagemid
                    ORDER BY datahora DESC
                ) AS rn_class
            FROM fact_estoque_final
            WHERE DATE(datahora) BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
        ),
        estoque_medio AS (
            SELECT
                emb.filial_codigo,
                emb.embalagemid,
                COALESCE(cls.classificacao_n1, 'N/A') AS classificacao_n1,
                COALESCE(ca.curvaABC, 'D') AS curvaABC,
                emb.valor_estoque_medio
            FROM estoque_medio_base emb
            LEFT JOIN classificacao_atual cls
              ON emb.filial_codigo = cls.filial_codigo
             AND emb.embalagemid = cls.embalagemid
             AND cls.rn_class = 1
            LEFT JOIN curva_abc ca
              ON emb.filial_codigo = ca.filial_codigo
             AND emb.embalagemid = ca.embalagemid
        ),
        vendas_agregadas AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n1,
                SUM(receita_real) AS receita_real_vendas,
                SUM(cmv_real) AS cmv_vendas,
                SUM(margem_bruta_real) AS margem_bruta_vendas,
                SUM(quantidade_vendida) AS total_quantidade_vendida,
                COUNT(*) AS total_transacoes
            FROM vendas_periodo
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        ),
        estoque_agregado AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n1,
                SUM(valor_estoque_medio) AS valor_medio_estoque,
                COUNT(*) AS total_produtos_estoque
            FROM estoque_medio
            GROUP BY filial_codigo, curvaABC, classificacao_n1
        ),
        vendas_curva AS (
            SELECT
                curvaABC,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY curvaABC
        ),
        estoque_curva AS (
            SELECT
                curvaABC,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY curvaABC
        ),
        vendas_filial_curva AS (
            SELECT
                filial_codigo,
                curvaABC,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY filial_codigo, curvaABC
        ),
        estoque_filial_curva AS (
            SELECT
                filial_codigo,
                curvaABC,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY filial_codigo, curvaABC
        ),
        vendas_filial_classificacao AS (
            SELECT
                filial_codigo,
                classificacao_n1,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY filial_codigo, classificacao_n1
        ),
        estoque_filial_classificacao AS (
            SELECT
                filial_codigo,
                classificacao_n1,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY filial_codigo, classificacao_n1
        ),
        vendas_classificacao AS (
            SELECT
                classificacao_n1,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY classificacao_n1
        ),
        estoque_classificacao AS (
            SELECT
                classificacao_n1,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY classificacao_n1
        ),
        vendas_curva_classificacao AS (
            SELECT
                curvaABC,
                classificacao_n1,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY curvaABC, classificacao_n1
        ),
        estoque_curva_classificacao AS (
            SELECT
                curvaABC,
                classificacao_n1,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY curvaABC, classificacao_n1
        )
        SELECT
            'Geral' AS filial_codigo,
            vc.curvaABC,
            'Geral' AS classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            vc.receita_real_vendas,
            vc.cmv_vendas,
            vc.margem_bruta_vendas,
            COALESCE(ec.valor_medio_estoque, 0) AS valor_medio_estoque,
            vc.total_transacoes,
            vc.total_quantidade_vendida,
            COALESCE(ec.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN (vc.margem_bruta_vendas / ec.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN vc.margem_bruta_vendas / ec.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_curva vc
        LEFT JOIN estoque_curva ec ON vc.curvaABC = ec.curvaABC

        UNION ALL

        SELECT
            vfc.filial_codigo,
            vfc.curvaABC,
            'Geral' AS classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            vfc.receita_real_vendas,
            vfc.cmv_vendas,
            vfc.margem_bruta_vendas,
            COALESCE(efc.valor_medio_estoque, 0) AS valor_medio_estoque,
            vfc.total_transacoes,
            vfc.total_quantidade_vendida,
            COALESCE(efc.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(efc.valor_medio_estoque, 0) > 0 THEN (vfc.margem_bruta_vendas / efc.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(efc.valor_medio_estoque, 0) > 0 THEN vfc.margem_bruta_vendas / efc.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial_curva vfc
        LEFT JOIN estoque_filial_curva efc
          ON vfc.filial_codigo = efc.filial_codigo
         AND vfc.curvaABC = efc.curvaABC

        UNION ALL

        SELECT
            vfc_cls.filial_codigo,
            'Geral' AS curvaABC,
            vfc_cls.classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            vfc_cls.receita_real_vendas,
            vfc_cls.cmv_vendas,
            vfc_cls.margem_bruta_vendas,
            COALESCE(efc_cls.valor_medio_estoque, 0) AS valor_medio_estoque,
            vfc_cls.total_transacoes,
            vfc_cls.total_quantidade_vendida,
            COALESCE(efc_cls.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN (vfc_cls.margem_bruta_vendas / efc_cls.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN vfc_cls.margem_bruta_vendas / efc_cls.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial_classificacao vfc_cls
        LEFT JOIN estoque_filial_classificacao efc_cls
          ON vfc_cls.filial_codigo = efc_cls.filial_codigo
         AND vfc_cls.classificacao_n1 = efc_cls.classificacao_n1
        WHERE vfc_cls.classificacao_n1 IS NOT NULL

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            vc.classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            vc.receita_real_vendas,
            vc.cmv_vendas,
            vc.margem_bruta_vendas,
            COALESCE(ec.valor_medio_estoque, 0) AS valor_medio_estoque,
            vc.total_transacoes,
            vc.total_quantidade_vendida,
            COALESCE(ec.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN (vc.margem_bruta_vendas / ec.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN vc.margem_bruta_vendas / ec.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_classificacao vc
        LEFT JOIN estoque_classificacao ec
          ON vc.classificacao_n1 = ec.classificacao_n1
        WHERE vc.classificacao_n1 IS NOT NULL

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            vcc.curvaABC,
            vcc.classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            vcc.receita_real_vendas,
            vcc.cmv_vendas,
            vcc.margem_bruta_vendas,
            COALESCE(ecc.valor_medio_estoque, 0) AS valor_medio_estoque,
            vcc.total_transacoes,
            vcc.total_quantidade_vendida,
            COALESCE(ecc.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ecc.valor_medio_estoque, 0) > 0 THEN (vcc.margem_bruta_vendas / ecc.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ecc.valor_medio_estoque, 0) > 0 THEN vcc.margem_bruta_vendas / ecc.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_curva_classificacao vcc
        LEFT JOIN estoque_curva_classificacao ecc
          ON vcc.curvaABC = ecc.curvaABC
         AND vcc.classificacao_n1 = ecc.classificacao_n1
        WHERE vcc.curvaABC IS NOT NULL AND vcc.classificacao_n1 IS NOT NULL

        UNION ALL

        SELECT
            va.filial_codigo,
            va.curvaABC,
            va.classificacao_n1,
            {periodo_vendas} AS periodo_dias,
            va.receita_real_vendas,
            va.cmv_vendas,
            va.margem_bruta_vendas,
            COALESCE(ea.valor_medio_estoque, 0) AS valor_medio_estoque,
            va.total_transacoes,
            va.total_quantidade_vendida,
            COALESCE(ea.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ea.valor_medio_estoque, 0) > 0 THEN (va.margem_bruta_vendas / ea.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ea.valor_medio_estoque, 0) > 0 THEN va.margem_bruta_vendas / ea.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_agregadas va
        LEFT JOIN estoque_agregado ea
          ON va.filial_codigo = ea.filial_codigo
         AND va.curvaABC = ea.curvaABC
         AND va.classificacao_n1 = ea.classificacao_n1
        WHERE va.curvaABC IS NOT NULL AND va.classificacao_n1 IS NOT NULL

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame()

        for col in ['periodo_dias', 'total_transacoes', 'total_produtos_estoque']:
            if col in df:
                df[col] = df[col].fillna(0).astype(int)
        for col in ['receita_real_vendas', 'cmv_vendas', 'margem_bruta_vendas',
                    'valor_medio_estoque', 'total_quantidade_vendida']:
            if col in df:
                df[col] = df[col].round(2)
        for col in ['gmroi_percentual', 'gmroi_ratio']:
            if col in df:
                df[col] = df[col].round(4)
        return df
    except Exception as e:
        st.error(f"Erro ao calcular GMROI por Curva ABC: {e}")
        return pd.DataFrame()


def calcular_gmroi_por_curva_abc_n2_duck(data_atual, periodo_vendas=90):
    try:
        ensure_bases_estoque(str(data_atual))

        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        data_limite_periodo = (pd.Timestamp(data_limite_ontem) - pd.Timedelta(days=periodo_vendas)).strftime('%Y-%m-%d')

        sql = f"""
        WITH vendas_periodo AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n2,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes
            FROM vw_vendas_n2_agregado
            WHERE data_venda BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        estoque_diario_raw AS (
            SELECT
                e.filial_codigo,
                e.embalagemid,
                DATE(e.datahora) AS data_dia,
                ABS(e.estoque) AS estoque,
                e.customedio,
                ROW_NUMBER() OVER (
                    PARTITION BY e.filial_codigo, e.embalagemid, DATE(e.datahora)
                    ORDER BY e.datahora DESC
                ) AS rn_dia
            FROM fact_estoque_final e
            WHERE DATE(e.datahora) BETWEEN DATE '{data_limite_periodo}' AND DATE '{data_limite_ontem}'
              AND e.estoque >= 0
              AND e.customedio > 0
        ),
        estoque_diario AS (
            SELECT
                filial_codigo,
                embalagemid,
                data_dia,
                estoque,
                customedio
            FROM estoque_diario_raw
            WHERE rn_dia = 1
        ),
        classificacao_ref AS (
            SELECT
                filial_codigo,
                embalagemid,
                classificacao_n2,
                curvaABC
            FROM vw_estoque_snapshot_n2
        ),
        estoque_medio_base AS (
            SELECT
                ed.filial_codigo,
                ed.embalagemid,
                AVG(ed.customedio * ed.estoque) AS valor_estoque_medio
            FROM estoque_diario ed
            GROUP BY ed.filial_codigo, ed.embalagemid
        ),
        estoque_medio AS (
            SELECT
                emb.filial_codigo,
                emb.embalagemid,
                COALESCE(cls.classificacao_n2, 'N/A') AS classificacao_n2,
                COALESCE(cls.curvaABC, 'D') AS curvaABC,
                emb.valor_estoque_medio
            FROM estoque_medio_base emb
            LEFT JOIN classificacao_ref cls
              ON emb.filial_codigo = cls.filial_codigo
             AND emb.embalagemid = cls.embalagemid
        ),
        vendas_agregadas AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n2,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida,
                SUM(total_transacoes) AS total_transacoes
            FROM vendas_periodo
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        estoque_agregado AS (
            SELECT
                filial_codigo,
                curvaABC,
                classificacao_n2,
                SUM(valor_estoque_medio) AS valor_medio_estoque,
                COUNT(*) AS total_produtos_estoque
            FROM estoque_medio
            GROUP BY filial_codigo, curvaABC, classificacao_n2
        ),
        vendas_curva AS (
            SELECT
                curvaABC,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY curvaABC
        ),
        estoque_curva AS (
            SELECT
                curvaABC,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY curvaABC
        ),
        vendas_filial_curva AS (
            SELECT
                filial_codigo,
                curvaABC,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY filial_codigo, curvaABC
        ),
        estoque_filial_curva AS (
            SELECT
                filial_codigo,
                curvaABC,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY filial_codigo, curvaABC
        ),
        vendas_filial_classificacao AS (
            SELECT
                filial_codigo,
                classificacao_n2,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY filial_codigo, classificacao_n2
        ),
        estoque_filial_classificacao AS (
            SELECT
                filial_codigo,
                classificacao_n2,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY filial_codigo, classificacao_n2
        ),
        vendas_classificacao AS (
            SELECT
                classificacao_n2,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY classificacao_n2
        ),
        estoque_classificacao AS (
            SELECT
                classificacao_n2,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY classificacao_n2
        ),
        vendas_curva_classificacao AS (
            SELECT
                curvaABC,
                classificacao_n2,
                SUM(receita_real_vendas) AS receita_real_vendas,
                SUM(cmv_vendas) AS cmv_vendas,
                SUM(margem_bruta_vendas) AS margem_bruta_vendas,
                SUM(total_transacoes) AS total_transacoes,
                SUM(total_quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_agregadas
            GROUP BY curvaABC, classificacao_n2
        ),
        estoque_curva_classificacao AS (
            SELECT
                curvaABC,
                classificacao_n2,
                SUM(valor_medio_estoque) AS valor_medio_estoque,
                SUM(total_produtos_estoque) AS total_produtos_estoque
            FROM estoque_agregado
            GROUP BY curvaABC, classificacao_n2
        )
        SELECT
            'Geral' AS filial_codigo,
            vc.curvaABC,
            'Geral' AS classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            vc.receita_real_vendas,
            vc.cmv_vendas,
            vc.margem_bruta_vendas,
            COALESCE(ec.valor_medio_estoque, 0) AS valor_medio_estoque,
            vc.total_transacoes,
            vc.total_quantidade_vendida,
            COALESCE(ec.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN (vc.margem_bruta_vendas / ec.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN vc.margem_bruta_vendas / ec.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_curva vc
        LEFT JOIN estoque_curva ec ON vc.curvaABC = ec.curvaABC

        UNION ALL

        SELECT
            vfc.filial_codigo,
            vfc.curvaABC,
            'Geral' AS classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            vfc.receita_real_vendas,
            vfc.cmv_vendas,
            vfc.margem_bruta_vendas,
            COALESCE(efc.valor_medio_estoque, 0) AS valor_medio_estoque,
            vfc.total_transacoes,
            vfc.total_quantidade_vendida,
            COALESCE(efc.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(efc.valor_medio_estoque, 0) > 0 THEN (vfc.margem_bruta_vendas / efc.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(efc.valor_medio_estoque, 0) > 0 THEN vfc.margem_bruta_vendas / efc.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial_curva vfc
        LEFT JOIN estoque_filial_curva efc
          ON vfc.filial_codigo = efc.filial_codigo
         AND vfc.curvaABC = efc.curvaABC

        UNION ALL

        SELECT
            vfc_cls.filial_codigo,
            'Geral' AS curvaABC,
            vfc_cls.classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            vfc_cls.receita_real_vendas,
            vfc_cls.cmv_vendas,
            vfc_cls.margem_bruta_vendas,
            COALESCE(efc_cls.valor_medio_estoque, 0) AS valor_medio_estoque,
            vfc_cls.total_transacoes,
            vfc_cls.total_quantidade_vendida,
            COALESCE(efc_cls.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN (vfc_cls.margem_bruta_vendas / efc_cls.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN vfc_cls.margem_bruta_vendas / efc_cls.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial_classificacao vfc_cls
        LEFT JOIN estoque_filial_classificacao efc_cls
          ON vfc_cls.filial_codigo = efc_cls.filial_codigo
         AND vfc_cls.classificacao_n2 = efc_cls.classificacao_n2
        WHERE vfc_cls.classificacao_n2 IS NOT NULL

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            'Geral' AS curvaABC,
            vc.classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            vc.receita_real_vendas,
            vc.cmv_vendas,
            vc.margem_bruta_vendas,
            COALESCE(ec.valor_medio_estoque, 0) AS valor_medio_estoque,
            vc.total_transacoes,
            vc.total_quantidade_vendida,
            COALESCE(ec.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN (vc.margem_bruta_vendas / ec.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ec.valor_medio_estoque, 0) > 0 THEN vc.margem_bruta_vendas / ec.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_classificacao vc
        LEFT JOIN estoque_classificacao ec
          ON vc.classificacao_n2 = ec.classificacao_n2
        WHERE vc.classificacao_n2 IS NOT NULL

        UNION ALL

        SELECT
            'Geral' AS filial_codigo,
            vcc.curvaABC,
            vcc.classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            vcc.receita_real_vendas,
            vcc.cmv_vendas,
            vcc.margem_bruta_vendas,
            COALESCE(ecc.valor_medio_estoque, 0) AS valor_medio_estoque,
            vcc.total_transacoes,
            vcc.total_quantidade_vendida,
            COALESCE(ecc.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ecc.valor_medio_estoque, 0) > 0 THEN (vcc.margem_bruta_vendas / ecc.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ecc.valor_medio_estoque, 0) > 0 THEN vcc.margem_bruta_vendas / ecc.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_curva_classificacao vcc
        LEFT JOIN estoque_curva_classificacao ecc
          ON vcc.curvaABC = ecc.curvaABC
         AND vcc.classificacao_n2 = ecc.classificacao_n2
        WHERE vcc.curvaABC IS NOT NULL AND vcc.classificacao_n2 IS NOT NULL

        UNION ALL

        SELECT
            va.filial_codigo,
            'Geral' AS curvaABC,
            va.classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            va.receita_real_vendas,
            va.cmv_vendas,
            va.margem_bruta_vendas,
            COALESCE(efc_cls.valor_medio_estoque, 0) AS valor_medio_estoque,
            va.total_transacoes,
            va.total_quantidade_vendida,
            COALESCE(efc_cls.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN (va.margem_bruta_vendas / efc_cls.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(efc_cls.valor_medio_estoque, 0) > 0 THEN va.margem_bruta_vendas / efc_cls.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_filial_classificacao va
        LEFT JOIN estoque_filial_classificacao efc_cls
          ON va.filial_codigo = efc_cls.filial_codigo
         AND va.classificacao_n2 = efc_cls.classificacao_n2
        WHERE va.classificacao_n2 IS NOT NULL

        UNION ALL

        SELECT
            va.filial_codigo,
            va.curvaABC,
            va.classificacao_n2,
            {periodo_vendas} AS periodo_dias,
            va.receita_real_vendas,
            va.cmv_vendas,
            va.margem_bruta_vendas,
            COALESCE(ea.valor_medio_estoque, 0) AS valor_medio_estoque,
            va.total_transacoes,
            va.total_quantidade_vendida,
            COALESCE(ea.total_produtos_estoque, 0) AS total_produtos_estoque,
            CASE WHEN COALESCE(ea.valor_medio_estoque, 0) > 0 THEN (va.margem_bruta_vendas / ea.valor_medio_estoque) * 100 ELSE 0 END AS gmroi_percentual,
            CASE WHEN COALESCE(ea.valor_medio_estoque, 0) > 0 THEN va.margem_bruta_vendas / ea.valor_medio_estoque ELSE 0 END AS gmroi_ratio
        FROM vendas_agregadas va
        LEFT JOIN estoque_agregado ea
          ON va.filial_codigo = ea.filial_codigo
         AND va.curvaABC = ea.curvaABC
         AND va.classificacao_n2 = ea.classificacao_n2
        WHERE va.curvaABC IS NOT NULL AND va.classificacao_n2 IS NOT NULL

        ORDER BY filial_codigo, curvaABC, classificacao_n2
        """

        df = duck_query(sql)
        if df is None or df.empty:
            return pd.DataFrame()

        for col in ['periodo_dias', 'total_transacoes', 'total_produtos_estoque']:
            if col in df:
                df[col] = df[col].fillna(0).astype(int)
        for col in ['receita_real_vendas', 'cmv_vendas', 'margem_bruta_vendas',
                    'valor_medio_estoque', 'gmroi_percentual', 'gmroi_ratio',
                    'total_quantidade_vendida']:
            if col in df:
                df[col] = df[col].round(4)
        return df
    except Exception as e:
        st.error(f"Erro ao calcular GMROI por Curva ABC (classificação N2): {e}")
        return pd.DataFrame()