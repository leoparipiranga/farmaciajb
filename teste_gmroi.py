import streamlit as st
import pandas as pd
from core.database import duck_query

@st.cache_data(show_spinner=False)
def calcular_gmroi_baseado_vendas_duck(data_atual, periodo_vendas=90):
    """
    Calcula GMROI baseado em vendas reais (abordagem mais precisa).
    
    GMROI = (Margem Bruta Real das Vendas) / (Valor Médio do Estoque no Período)
    
    Margem Bruta Real = (item_precoaposdesconto * item_quantidade) - (customedio * item_quantidade)
    Onde item_precoaposdesconto = item_valorunitario - item_desconto
    
    Args:
        data_atual: Data de referência
        periodo_vendas: Período em dias para considerar as vendas (padrão 90 dias)
    
    Retorna DataFrame com colunas:
    - filial_codigo: 'Geral' ou código da filial
    - tipo: 'Baseado_Vendas_Real'
    - periodo_dias: Período considerado
    - receita_real_vendas: Receita real das vendas
    - cmv_vendas: Custo das mercadorias vendidas
    - margem_bruta_vendas: Margem bruta real das vendas do período
    - valor_medio_estoque: Valor médio do estoque no período
    - total_transacoes: Total de transações
    - total_quantidade_vendida: Quantidade total vendida
    - total_produtos_estoque: Produtos únicos no estoque
    - gmroi_percentual: GMROI em percentual
    - gmroi_ratio: GMROI como razão (vezes)
    """
    try:
        data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        data_limite_periodo = (pd.Timestamp(data_limite_ontem) - pd.Timedelta(days=periodo_vendas)).strftime('%Y-%m-%d')
        
        sql = f"""
        WITH vendas_periodo AS (
            SELECT
                v.filial_codigo,
                v.item_embalagemid AS embalagemid,
                v.data_date,
                ABS(v.item_quantidade) AS quantidade_vendida,
                v.item_valorunitario,
                COALESCE(v.item_desconto, 0) AS item_desconto,
                (v.item_valorunitario - COALESCE(v.item_desconto, 0)) AS item_precoaposdesconto,
                v.customedio,
                -- Receita real (preço após desconto)
                (v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade) AS receita_real,
                -- Custo das mercadorias vendidas
                v.customedio * ABS(v.item_quantidade) AS cmv_real,
                -- Margem bruta real
                ((v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade)) - (v.customedio * ABS(v.item_quantidade)) AS margem_bruta_real
            FROM fact_vendas_final v
            WHERE v.data_date >= DATE '{data_limite_periodo}'
            AND v.data_date <= DATE '{data_limite_ontem}'
            AND v.customedio > 0
            AND v.item_valorunitario > 0
        ),
        estoque_diario AS (
            SELECT
                filial_codigo,
                embalagemid,
                DATE(datahora) AS data_estoque,
                estoque,
                customedio,
                ROW_NUMBER() OVER (
                    PARTITION BY filial_codigo, embalagemid, DATE(datahora)
                    ORDER BY datahora DESC
                ) AS rn_dia
            FROM fact_estoque_final
            WHERE DATE(datahora) >= DATE '{data_limite_periodo}'
              AND DATE(datahora) <= DATE '{data_limite_ontem}'
              AND estoque >= 0
              AND customedio > 0
        ),
        estoque_medio AS (
            SELECT
                filial_codigo,
                embalagemid,
                AVG(customedio * estoque) AS valor_estoque_medio
            FROM estoque_diario
            WHERE rn_dia = 1
            GROUP BY filial_codigo, embalagemid
        ),
        -- Resumo geral (toda a rede)
        resumo_vendas_geral AS (
            SELECT
                SUM(receita_real) AS total_receita_real,
                SUM(cmv_real) AS total_cmv_real,
                SUM(margem_bruta_real) AS total_margem_bruta_real,
                COUNT(*) AS total_transacoes,
                SUM(quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_periodo
        ),
        resumo_estoque_geral AS (
            SELECT
                SUM(valor_estoque_medio) AS total_valor_medio_estoque,
                COUNT(*) AS total_produtos_estoque
            FROM estoque_medio
        ),
        -- Resumo por filial
        resumo_vendas_filial AS (
            SELECT
                filial_codigo,
                SUM(receita_real) AS total_receita_real,
                SUM(cmv_real) AS total_cmv_real,
                SUM(margem_bruta_real) AS total_margem_bruta_real,
                COUNT(*) AS total_transacoes,
                SUM(quantidade_vendida) AS total_quantidade_vendida
            FROM vendas_periodo
            GROUP BY filial_codigo
        ),
        resumo_estoque_filial AS (
            SELECT
                filial_codigo,
                SUM(valor_estoque_medio) AS total_valor_medio_estoque,
                COUNT(*) AS total_produtos_estoque
            FROM estoque_medio
            GROUP BY filial_codigo
        )
        -- 1) Resultado Geral
        SELECT
            'Geral' AS filial_codigo,
            'Baseado_Vendas_Real' AS tipo,
            {periodo_vendas} AS periodo_dias,
            rvg.total_receita_real AS receita_real_vendas,
            rvg.total_cmv_real AS cmv_vendas,
            rvg.total_margem_bruta_real AS margem_bruta_vendas,
            reg.total_valor_medio_estoque AS valor_medio_estoque,
            rvg.total_transacoes AS total_transacoes,
            rvg.total_quantidade_vendida AS total_quantidade_vendida,
            reg.total_produtos_estoque AS total_produtos_estoque,
            CASE 
                WHEN reg.total_valor_medio_estoque > 0 
                THEN (rvg.total_margem_bruta_real / reg.total_valor_medio_estoque) * 100
                ELSE 0 
            END AS gmroi_percentual,
            CASE 
                WHEN reg.total_valor_medio_estoque > 0 
                THEN rvg.total_margem_bruta_real / reg.total_valor_medio_estoque
                ELSE 0 
            END AS gmroi_ratio
        FROM resumo_vendas_geral rvg
        CROSS JOIN resumo_estoque_geral reg

        UNION ALL

        -- 2) Resultado por Filial
        SELECT
            rvf.filial_codigo,
            'Baseado_Vendas_Real' AS tipo,
            {periodo_vendas} AS periodo_dias,
            rvf.total_receita_real AS receita_real_vendas,
            rvf.total_cmv_real AS cmv_vendas,
            rvf.total_margem_bruta_real AS margem_bruta_vendas,
            ref.total_valor_medio_estoque AS valor_medio_estoque,
            rvf.total_transacoes AS total_transacoes,
            rvf.total_quantidade_vendida AS total_quantidade_vendida,
            ref.total_produtos_estoque AS total_produtos_estoque,
            CASE 
                WHEN ref.total_valor_medio_estoque > 0 
                THEN (rvf.total_margem_bruta_real / ref.total_valor_medio_estoque) * 100
                ELSE 0 
            END AS gmroi_percentual,
            CASE 
                WHEN ref.total_valor_medio_estoque > 0 
                THEN rvf.total_margem_bruta_real / ref.total_valor_medio_estoque
                ELSE 0 
            END AS gmroi_ratio
        FROM resumo_vendas_filial rvf
        INNER JOIN resumo_estoque_filial ref ON rvf.filial_codigo = ref.filial_codigo

        ORDER BY filial_codigo
        """
        
        df = duck_query(sql)
        
        if df is None or df.empty:
            return pd.DataFrame(columns=['filial_codigo', 'tipo', 'periodo_dias', 'receita_real_vendas', 'cmv_vendas', 
                                       'margem_bruta_vendas', 'valor_medio_estoque', 'total_transacoes',
                                       'total_quantidade_vendida', 'total_produtos_estoque', 
                                       'gmroi_percentual', 'gmroi_ratio'])
        
        # Formatar resultado
        df['periodo_dias'] = df['periodo_dias'].astype(int)
        df['receita_real_vendas'] = df['receita_real_vendas'].round(2)
        df['cmv_vendas'] = df['cmv_vendas'].round(2)
        df['margem_bruta_vendas'] = df['margem_bruta_vendas'].round(2)
        df['valor_medio_estoque'] = df['valor_medio_estoque'].round(2)
        df['total_transacoes'] = df['total_transacoes'].astype(int)
        df['total_quantidade_vendida'] = df['total_quantidade_vendida'].round(2)
        df['total_produtos_estoque'] = df['total_produtos_estoque'].astype(int)
        df['gmroi_percentual'] = df['gmroi_percentual'].round(4)
        df['gmroi_ratio'] = df['gmroi_ratio'].round(4)
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao calcular GMROI baseado em vendas reais: {e}")
        return pd.DataFrame()
    

@st.cache_data(show_spinner=False)
def calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=90):
    data_limite_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    data_limite_periodo = (pd.Timestamp(data_limite_ontem) - pd.Timedelta(days=periodo_vendas)).strftime('%Y-%m-%d')
    
    sql = f"""
    WITH vendas_90d_abc AS (
        SELECT 
            filial_codigo,
            classificacao_n3,
            item_embalagemid AS embalagemid,
            SUM(ABS(item_quantidade)) AS quantidade_vendida
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_periodo}'
          AND data_date <= DATE '{data_limite_ontem}'
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
    vendas_periodo AS (
        SELECT
            v.filial_codigo,
            v.item_embalagemid AS embalagemid,
            v.data_date,
            v.classificacao_n1,
            COALESCE(pc.curvaABC, 'D') AS curvaABC,
            ABS(v.item_quantidade) AS quantidade_vendida,
            v.item_valorunitario,
            COALESCE(v.item_desconto, 0) AS item_desconto,
            (v.item_valorunitario - COALESCE(v.item_desconto, 0)) AS item_precoaposdesconto,
            v.customedio,
            (v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade) AS receita_real,
            v.customedio * ABS(v.item_quantidade) AS cmv_real,
            ((v.item_valorunitario - COALESCE(v.item_desconto, 0)) * ABS(v.item_quantidade)) - (v.customedio * ABS(v.item_quantidade)) AS margem_bruta_real
        FROM fact_vendas_final v
        LEFT JOIN produtos_com_curva pc
            ON v.filial_codigo = pc.filial_codigo AND v.item_embalagemid = pc.embalagemid
        WHERE v.data_date >= DATE '{data_limite_periodo}'
          AND v.data_date <= DATE '{data_limite_ontem}'
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
        WHERE DATE(e.datahora) >= DATE '{data_limite_periodo}'
          AND DATE(e.datahora) <= DATE '{data_limite_ontem}'
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
        WHERE DATE(datahora) >= DATE '{data_limite_periodo}'
          AND DATE(datahora) <= DATE '{data_limite_ontem}'
          
    ),
    estoque_medio AS (
            SELECT
                emb.filial_codigo,
                emb.embalagemid,
                COALESCE(cls.classificacao_n1, 'N/A') AS classificacao_n1,
                COALESCE(pc.curvaABC, 'D') AS curvaABC,
                emb.valor_estoque_medio
            FROM estoque_medio_base emb
            LEFT JOIN classificacao_atual cls
              ON emb.filial_codigo = cls.filial_codigo
             AND emb.embalagemid = cls.embalagemid
             AND cls.rn_class = 1
            LEFT JOIN produtos_com_curva pc
              ON emb.filial_codigo = pc.filial_codigo
             AND emb.embalagemid = pc.embalagemid
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
                'valor_medio_estoque', 'gmroi_percentual', 'gmroi_ratio',
                'total_quantidade_vendida']:
        if col in df:
            df[col] = df[col].round(4)
    return df

st.set_page_config(page_title="Debug GMROI", layout="wide")

col_data, col_periodo = st.columns(2)
data_referencia = col_data.date_input("Data atual", pd.Timestamp.today().date())
periodo = col_periodo.number_input("Período (dias)", min_value=7, max_value=180, value=90, step=1)

if st.button("Executar análises"):
    df_base = calcular_gmroi_baseado_vendas_duck(data_referencia, periodo)
    df_curva = calcular_gmroi_por_curva_abc_duck(data_referencia, periodo)

    st.subheader("Resultado – Função Baseado em Vendas (Geral / Filial)")
    st.dataframe(df_base, use_container_width=True)

    st.subheader("Resultado – Função com Curva ABC")
    st.dataframe(df_curva, use_container_width=True)

    if not df_base.empty and not df_curva.empty:
        st.subheader("Comparativo rápido")
        resumo_base = df_base[['filial_codigo', 'margem_bruta_vendas', 'valor_medio_estoque', 'gmroi_ratio']]
        resumo_curva = df_curva[df_curva['filial_codigo'] == 'Geral'][['curvaABC', 'margem_bruta_vendas', 'valor_medio_estoque', 'gmroi_ratio']]
        st.write("Baseado Vendas – geral e filial:")
        st.dataframe(resumo_base, use_container_width=True)
        st.write("Curva ABC – recorte geral (por curva):")
        st.dataframe(resumo_curva, use_container_width=True)

    with st.expander("SQL bruto – Baseado Vendas"):
        st.code(calcular_gmroi_baseado_vendas_duck.__defaults__[0] if hasattr(calcular_gmroi_baseado_vendas_duck, "__defaults__") else "SQL gerado dentro da função.")

    with st.expander("SQL bruto – Curva ABC"):
        st.code(calcular_gmroi_por_curva_abc_duck.__defaults__[0] if hasattr(calcular_gmroi_por_curva_abc_duck, "__defaults__") else "SQL gerado dentro da função.")
else:
    st.info("Defina os parâmetros e clique em **Executar análises**.")