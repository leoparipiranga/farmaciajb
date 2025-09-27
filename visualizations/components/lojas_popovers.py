import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date, timedelta
from core.database import duck_query
from ai_integration.analysis_ai import render_insight_controls
from utils.helpers import EMPREGADOS_POR_FILIAL, _weekday_labels

def render_popover_vendas_acumuladas(codigo_filial: str | None):
    
    # ⭐ ÂNCORA DE LARGURA - força largura mínima constante
    st.markdown("""
    <div style="
        width: 650px; 
        min-width: 650px; 
        height: 1px; 
        background: transparent; 
        margin: 0; 
        padding: 0;
        overflow: hidden;
        position: absolute;
    "></div>
    """, unsafe_allow_html=True)
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)

    # Filtro por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"

    # Filtro por Classificação N1 (aplica a todas as tabs)
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)

    col1, col2 = st.columns([3,1])
    with col1:
        if df_cls is None or df_cls.empty:
            opcoes_cls = ["Todas as Classificações"]
        else:
            opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

        sel_cls = st.selectbox(
            "🏷️ Classificação N1",
            opcoes_cls,
            index=0,
            key=f"pop_cls_vendas_acc_{(codigo_filial or 'ALL')}"
        )
        cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])

    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        aba_ativa = "dia"  # Definir aba ativa
        
        render_insight_controls(
            popover_type="vendas_acumuladas",
            data=None,  # Não usado mais
            context="Análise de vendas",
            aba_ativa=aba_ativa,
            sel_cls=sel_cls,
            codigo_filial=codigo_filial  # ← PASSAR CÓDIGO DA FILIAL
        )
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")

            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">💰 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].sum():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].max():,.2f}</div></div>""", unsafe_allow_html=True)
      
           
            fig = px.bar(df, x="data_formatada", y="valor", labels={"valor": "Vendas (R$)", "data_formatada": ""}, text_auto='.2s')
            fig.update_traces(marker_color="steelblue", 
                              textangle=0,
                              textposition='inside',
                              textfont=dict(color="white", size=10),
                              hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>")
            fig.update_layout(
                            height=250,
                            width=650,  # Força largura fixa
                            autosize=False,  # Desativa ajuste automático
                            showlegend=False,
                            xaxis_tickangle=-45,
                            template="plotly_white",
                            margin=dict(t=20, b=20, l=30, r=30),
                            xaxis=dict(title="", tickfont=dict(size=10)),
                            yaxis=dict(title="Vendas (R$)", tickfont=dict(size=10)),
                            title=''
                        )
            st.plotly_chart(fig, use_container_width=False)

    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        aba_ativa = "dezena"  # Definir aba ativa
        
        render_insight_controls(
            popover_type="vendas_acumuladas",
            data=None,  # Não usado mais
            context="Análise de vendas",
            aba_ativa=aba_ativa,
            sel_cls=sel_cls,
            codigo_filial=codigo_filial  # ← PASSAR CÓDIGO DA FILIAL
        )
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        sql = f"""
            SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
        """
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["ano_mes_str"] = df["data_date"].dt.strftime("%Y-%m")
            dias = df["data_date"].dt.day
            df["dezena"] = pd.cut(dias, bins=[0,10,20,31], labels=["1ª Dezena", "2ª Dezena", "3ª Dezena"], right=True, include_lowest=True)
            agg = df.groupby(["ano_mes_str","dezena"], as_index=False)["valor"].sum()
            ordem = ["1ª Dezena","2ª Dezena","3ª Dezena"]
            agg["dezena"] = pd.Categorical(agg["dezena"], categories=ordem, ordered=True)
            agg = agg.sort_values(["ano_mes_str","dezena"]).tail(12)
            agg["dezena_formatada"] = pd.to_datetime(agg["ano_mes_str"]).dt.strftime("%b/%y") + " - " + agg["dezena"].astype(str)

            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">💰 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {agg['valor'].sum():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {agg['valor'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {agg['valor'].max():,.2f}</div></div>""", unsafe_allow_html=True)

            fig = px.bar(agg, x="dezena_formatada", y="valor", labels={"valor":"Vendas (R$)","dezena_formatada":""}, text_auto='.2s')
            fig.update_traces(marker_color="darkgreen", 
                              textangle=0,
                              textposition='inside',
                              textfont=dict(color="white", size=10),
                              hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>")
            fig.update_layout(
                            height=250,
                            width=650,  # Força largura fixa
                            autosize=False,  # Desativa ajuste automático
                            showlegend=False,
                            xaxis_tickangle=-45,
                            template="plotly_white",
                            margin=dict(t=20, b=20, l=30, r=30),
                            xaxis=dict(title="", tickfont=dict(size=10)),
                            yaxis=dict(title="Vendas (R$)", tickfont=dict(size=10)),
                            title=''
                        )
            st.plotly_chart(fig, use_container_width=False)

    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        aba_ativa = "mes"  # Definir aba ativa
        
        render_insight_controls(
            popover_type="vendas_acumuladas",
            data=None,  # Não usado mais
            context="Análise de vendas",
            aba_ativa=aba_ativa,
            sel_cls=sel_cls,
            codigo_filial=codigo_filial  # ← PASSAR CÓDIGO DA FILIAL
        )

        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        sql = f"""
            SELECT DATE_TRUNC('month', data_date)::DATE AS mes, SUM(item_valortotal) AS valor
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)

            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">💰 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].sum():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['valor'].max():,.2f}</div></div>""", unsafe_allow_html=True)

            fig = px.bar(df, x="mes_formatado", y="valor", labels={"valor":"Vendas (R$)","mes_formatado":""}, text_auto='.2s')
            fig.update_traces(marker_color="darkslategray", 
                              textangle=0,
                              textposition='inside',
                              textfont=dict(color="white", size=10),
                              hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>")
            fig.update_layout(
                            height=250,
                            width=650,  # Força largura fixa
                            autosize=False,  # Desativa ajuste automático
                            showlegend=False,
                            xaxis_tickangle=-45,
                            template="plotly_white",
                            margin=dict(t=20, b=20, l=30, r=30),
                            xaxis=dict(title="", tickfont=dict(size=10)),
                            yaxis=dict(title="Vendas (R$)", tickfont=dict(size=10)),
                            title=''
                        )
            st.plotly_chart(fig, use_container_width=False)

    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        aba_ativa = "ritmo"  # Definir aba ativa
        
        render_insight_controls(
            popover_type="vendas_acumuladas",
            data=None,  # Não usado mais
            context="Análise de vendas",
            aba_ativa=aba_ativa,
            sel_cls=sel_cls,
            codigo_filial=codigo_filial  # ← PASSAR CÓDIGO DA FILIAL
        )
        
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        sql = f"""
            SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
        """
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["ano_mes"] = df["data_date"].dt.to_period("M")
            df["dia"] = df["data_date"].dt.day
            df_corte = df[df["dia"] <= d].groupby("ano_mes", as_index=False)["valor"].sum()
            df_corte["mes_formatado"] = df_corte["ano_mes"].astype(str)
            df_corte = df_corte.tail(12)

            # Calcular média e variação
            media_valor = df_corte['valor'].mean()
            atual_valor = df_corte['valor'].iloc[-1]
            variacao = ((atual_valor / media_valor) - 1) * 100 if media_valor > 0 else 0

            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {media_valor:,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {atual_valor:,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)

            fig = px.bar(df_corte, x="mes_formatado", y="valor",
                         labels={"valor":"Vendas Acumuladas (R$)","mes_formatado":""}, text_auto='.2s')
            fig.update_traces(marker_color="darkgoldenrod", 
                              textangle=0,
                              textposition='inside',
                              textfont=dict(color="white", size=10),
                              hovertemplate="<b>%{x}</b><br>Vendas: R$ %{y:,.2f}<extra></extra>")
            fig.update_layout(
                            height=250,
                            width=650,  # Força largura fixa
                            autosize=False,  # Desativa ajuste automático
                            showlegend=False,
                            xaxis_tickangle=-45,
                            template="plotly_white",
                            margin=dict(t=20, b=20, l=30, r=30),
                            xaxis=dict(title="", tickfont=dict(size=10)),
                            yaxis=dict(title="Vendas (R$)", tickfont=dict(size=10)),
                            title=''
                        )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_num_vendas(codigo_filial: str | None):
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 🛒 Número de Vendas - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_numvendas_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                COUNT(DISTINCT venda_id) AS num_vendas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🛒 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].sum())}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['num_vendas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].max())}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="num_vendas", text_auto='.2s')
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10)
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Número de Vendas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            )
            SELECT 
                ano_mes_str,
                dezena,
                COUNT(DISTINCT venda_id) AS num_vendas
            FROM base
            GROUP BY ano_mes_str, dezena
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🛒 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].sum())}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['num_vendas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].max())}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="num_vendas", text_auto='.2s')
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10)
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Número de Vendas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                COUNT(DISTINCT venda_id) AS num_vendas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🛒 Total</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].sum())}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['num_vendas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(df['num_vendas'].max())}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="num_vendas", text_auto='.2s')
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10)
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Número de Vendas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH dias_por_mes AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    MAX(EXTRACT(DAY FROM data_date)) AS dias_no_mes
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                GROUP BY 1
            ),
            vendas_ate_dia AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS num_vendas_acumuladas
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
                GROUP BY 1
            )
            SELECT 
                v.mes,
                v.num_vendas_acumuladas,
                LEAST({d}, d.dias_no_mes) AS dias_considerados
            FROM vendas_ate_dia v
            JOIN dias_por_mes d ON v.mes = d.mes
            ORDER BY v.mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_num_vendas = df['num_vendas_acumuladas'].mean()
            atual_num_vendas = df['num_vendas_acumuladas'].iloc[-1]
            variacao = ((atual_num_vendas / media_num_vendas) - 1) * 100 if media_num_vendas > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(media_num_vendas)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{int(atual_num_vendas)}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="num_vendas_acumuladas", text_auto='.2s')
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10)
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vendas Acumuladas (#)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)


def render_popover_ticket_medio(codigo_filial: str | None):
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 🎯 Ticket Médio - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_ticket_medio_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                SUM(item_valortotal) / NULLIF(COUNT(DISTINCT venda_id), 0) AS ticket_medio
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🎯 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].max():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].min():,.2f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="ticket_medio", text_auto='.1f')
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Ticket Médio: R$ %{y:,.2f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Ticket Médio (R$)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_valortotal,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(item_valortotal) AS total_vendas,
                    COUNT(DISTINCT venda_id) AS num_vendas
                FROM base
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                ano_mes_str,
                dezena,
                total_vendas / NULLIF(num_vendas, 0) AS ticket_medio
            FROM agg
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🎯 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].max():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].min():,.2f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="ticket_medio", text_auto='.1f')
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Ticket Médio: R$ %{y:,.2f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Ticket Médio (R$)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                SUM(item_valortotal) / NULLIF(COUNT(DISTINCT venda_id), 0) AS ticket_medio
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🎯 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].mean():,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].max():,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {df['ticket_medio'].min():,.2f}</div></div>""", unsafe_allow_html=True)

            fig = px.bar(df, x="mes_formatado", y="ticket_medio", text_auto='.1f')
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Ticket Médio: R$ %{y:,.2f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Ticket Médio (R$)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_valortotal
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_valortotal) AS total_vendas,
                    COUNT(DISTINCT venda_id) AS num_vendas
                FROM base
                GROUP BY 1
            )
            SELECT 
                mes,
                total_vendas / NULLIF(num_vendas, 0) AS ticket_medio_acumulado
            FROM agg
            ORDER BY mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_ticket = df['ticket_medio_acumulado'].mean()
            atual_ticket = df['ticket_medio_acumulado'].iloc[-1]
            variacao = ((atual_ticket / media_ticket) - 1) * 100 if media_ticket > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {media_ticket:,.2f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">R$ {atual_ticket:,.2f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)

            fig = px.bar(df, x="mes_formatado", y="ticket_medio_acumulado", text_auto='.1f')
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Ticket Médio: R$ %{y:,.2f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Ticket Médio (R$)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_itens_por_nota(codigo_filial: str | None):
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 📦 Itens por Nota - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_itens_por_nota_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                SUM(item_quantidade) / NULLIF(COUNT(DISTINCT venda_id), 0) AS itens_por_nota
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="itens_por_nota", text_auto='.1f')
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Itens por Nota: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Itens por Nota", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_quantidade,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(item_quantidade) AS total_itens,
                    COUNT(DISTINCT venda_id) AS num_vendas
                FROM base
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                ano_mes_str,
                dezena,
                total_itens / NULLIF(num_vendas, 0) AS itens_por_nota
            FROM agg
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="itens_por_nota", text_auto='.1f')
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Itens por Nota: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Itens por Nota", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                SUM(item_quantidade) / NULLIF(COUNT(DISTINCT venda_id), 0) AS itens_por_nota
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['itens_por_nota'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="itens_por_nota", text_auto='.1f')
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Itens por Nota: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Itens por Nota", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_quantidade
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_quantidade) AS total_itens,
                    COUNT(DISTINCT venda_id) AS num_vendas
                FROM base
                GROUP BY 1
            )
            SELECT 
                mes,
                total_itens / NULLIF(num_vendas, 0) AS itens_por_nota_acumulado
            FROM agg
            ORDER BY mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_itens = df['itens_por_nota_acumulado'].mean()
            atual_itens = df['itens_por_nota_acumulado'].iloc[-1]
            variacao = ((atual_itens / media_itens) - 1) * 100 if media_itens > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_itens:.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_itens:.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="itens_por_nota_acumulado", text_auto='.1f')
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Itens por Nota: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Itens por Nota", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_vitaminas_vendidas(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 💊 Vitaminas Vendidas - Filial {codigo_filial}")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                SUM(item_quantidade) AS vitaminas_vendidas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
              {cond_loja}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="vitaminas_vendidas", text_auto='.0f')
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vitaminas Vendidas: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vitaminas Vendidas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    item_quantidade,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                  AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                  {cond_loja}
            ),
            agg AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(item_quantidade) AS vitaminas_vendidas
                FROM base
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                ano_mes_str,
                dezena,
                vitaminas_vendidas
            FROM agg
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="vitaminas_vendidas", text_auto='.0f')
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vitaminas Vendidas: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vitaminas Vendidas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                SUM(item_quantidade) AS vitaminas_vendidas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
              AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
              {cond_loja}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📦 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vitaminas_vendidas'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="vitaminas_vendidas", text_auto='.0f')
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vitaminas Vendidas: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vitaminas Vendidas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    item_quantidade
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                  AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                  {cond_loja}
            ),
            agg AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_quantidade) AS vitaminas_acumuladas
                FROM base
                GROUP BY 1
            )
            SELECT 
                mes,
                vitaminas_acumuladas
            FROM agg
            ORDER BY mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_vitaminas = df['vitaminas_acumuladas'].mean()
            atual_vitaminas = df['vitaminas_acumuladas'].iloc[-1]
            variacao = ((atual_vitaminas / media_vitaminas) - 1) * 100 if media_vitaminas > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_vitaminas:.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_vitaminas:.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="vitaminas_acumuladas", text_auto='.0f')
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vitaminas Vendidas: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vitaminas Vendidas", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_conversao_vitaminas(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 🔄 Taxa de Conversão - Filial {codigo_filial}")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            WITH tot AS (
                SELECT 
                    CAST(data_date AS DATE) AS data_date,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
                {cond_loja}
                GROUP BY 1
            ),
            vit AS (
                SELECT 
                    CAST(data_date AS DATE) AS data_date,
                    SUM(item_quantidade) AS qty_vit  -- Alterado para SUM de quantidades
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
                  AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                {cond_loja}
                GROUP BY 1
            )
            SELECT 
                t.data_date,
                CASE WHEN v.qty_vit = 0 THEN 0.0
                     ELSE CAST(t.n_total AS DOUBLE) / v.qty_vit
                END AS taxa_conversao
            FROM tot t
            LEFT JOIN vit v ON t.data_date = v.data_date
            ORDER BY t.data_date
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔄 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="taxa_conversao", text_auto='.1f')
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Taxa de Conversão: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Taxa de Conversão", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_quantidade,
                    classificacao_n2,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja}
            ),
            tot AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM base
                GROUP BY ano_mes_str, dezena
            ),
            vit AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(item_quantidade) AS qty_vit  -- Alterado para SUM de quantidades
                FROM base
                WHERE UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                t.ano_mes_str,
                t.dezena,
                CASE WHEN v.qty_vit = 0 THEN 0.0
                     ELSE CAST(t.n_total AS DOUBLE) / v.qty_vit
                END AS taxa_conversao
            FROM tot t
            LEFT JOIN vit v ON t.ano_mes_str = v.ano_mes_str AND t.dezena = v.dezena
            ORDER BY t.ano_mes_str, 
                CASE t.dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔄 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="taxa_conversao", text_auto='.1f')
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Taxa de Conversão: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Taxa de Conversão", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH tot AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                {cond_loja}
                GROUP BY 1
            ),
            vit AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_quantidade) AS qty_vit  -- Alterado para SUM de quantidades
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                {cond_loja}
                GROUP BY 1
            )
            SELECT 
                t.mes,
                CASE WHEN v.qty_vit = 0 THEN 0.0
                     ELSE CAST(t.n_total AS DOUBLE) / v.qty_vit
                END AS taxa_conversao
            FROM tot t
            LEFT JOIN vit v ON t.mes = v.mes
            ORDER BY t.mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔄 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].mean():.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].max():.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['taxa_conversao'].min():.1f}</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="taxa_conversao", text_auto='.1f')
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Taxa de Conversão: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Taxa de Conversão", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    item_quantidade,
                    classificacao_n2
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja}
            ),
            tot AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM base
                GROUP BY 1
            ),
            vit AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_quantidade) AS qty_vit  -- Alterado para SUM de quantidades
                FROM base
                WHERE UPPER(TRIM(classificacao_n2)) = 'VITAMINAS'
                GROUP BY 1
            )
            SELECT 
                t.mes,
                CASE WHEN v.qty_vit = 0 THEN 0.0
                     ELSE CAST(t.n_total AS DOUBLE) / v.qty_vit
                END AS taxa_conversao_acumulado
            FROM tot t
            LEFT JOIN vit v ON t.mes = v.mes
            ORDER BY t.mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_taxa = df['taxa_conversao_acumulado'].mean()
            atual_taxa = df['taxa_conversao_acumulado'].iloc[-1]
            variacao = ((atual_taxa / media_taxa) - 1) * 100 if media_taxa > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_taxa:.1f}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_taxa:.1f}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="taxa_conversao_acumulado", text_auto='.1f')
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Taxa de Conversão: %{y:.1f}<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Taxa de Conversão", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_cmv(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 📉 CMV (%) - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_cmv_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                (SUM(customediototal) / NULLIF(SUM(item_valortotal), 0)) * 100 AS cmv_percent
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="cmv_percent", 
                         text=df['cmv_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>CMV: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="CMV (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    customediototal,
                    item_valortotal,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(customediototal) AS total_custo,
                    SUM(item_valortotal) AS total_vendas
                FROM base
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                ano_mes_str,
                dezena,
                (total_custo / NULLIF(total_vendas, 0)) * 100 AS cmv_percent
            FROM agg
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="cmv_percent", 
                         text=df['cmv_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>CMV: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="CMV (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                (SUM(customediototal) / NULLIF(SUM(item_valortotal), 0)) * 100 AS cmv_percent
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['cmv_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="cmv_percent", 
                         text=df['cmv_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>CMV: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="CMV (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    customediototal,
                    item_valortotal
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(customediototal) AS total_custo,
                    SUM(item_valortotal) AS total_vendas
                FROM base
                GROUP BY 1
            )
            SELECT 
                mes,
                (total_custo / NULLIF(total_vendas, 0)) * 100 AS cmv_percent_acumulado
            FROM agg
            ORDER BY mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_cmv = df['cmv_percent_acumulado'].mean()
            atual_cmv = df['cmv_percent_acumulado'].iloc[-1]
            variacao = ((atual_cmv / media_cmv) - 1) * 100 if media_cmv > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_cmv:.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_cmv:.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="cmv_percent_acumulado", 
                         text=df['cmv_percent_acumulado'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>CMV: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="CMV (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_descontos(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 💸 Desconto (%) - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_desconto_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            SELECT 
                CAST(data_date AS DATE) AS data_date, 
                (SUM(item_valordesconto * item_quantidade) / NULLIF(SUM(item_valortotal + (item_valordesconto * item_quantidade)), 0)) * 100 AS desconto_percent
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
              {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="desconto_percent", 
                         text=df['desconto_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Desconto: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Desconto (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    item_valordesconto * item_quantidade AS item_descontototal,
                    item_valortotal,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    SUM(item_descontototal) AS total_desconto,
                    SUM(item_valortotal + item_descontototal) AS total_vendas_com_desconto
                FROM base
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                ano_mes_str,
                dezena,
                (total_desconto / NULLIF(total_vendas_com_desconto, 0)) * 100 AS desconto_percent
            FROM agg
            ORDER BY ano_mes_str, 
                CASE dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="desconto_percent", 
                         text=df['desconto_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Desconto: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Desconto (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            SELECT 
                DATE_TRUNC('month', data_date)::DATE AS mes,
                (SUM(item_valordesconto * item_quantidade) / NULLIF(SUM(item_valortotal + (item_valordesconto * item_quantidade)), 0)) * 100 AS desconto_percent
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY 1
            ORDER BY 1
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['desconto_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="desconto_percent", 
                         text=df['desconto_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Desconto: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Desconto (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    item_valordesconto * item_quantidade AS item_descontototal,
                    item_valortotal
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
            ),
            agg AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    SUM(item_descontototal) AS total_desconto,
                    SUM(item_valortotal + item_descontototal) AS total_vendas_com_desconto
                FROM base
                GROUP BY 1
            )
            SELECT 
                mes,
                (total_desconto / NULLIF(total_vendas_com_desconto, 0)) * 100 AS desconto_percent_acumulado
            FROM agg
            ORDER BY mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_desconto = df['desconto_percent_acumulado'].mean()
            atual_desconto = df['desconto_percent_acumulado'].iloc[-1]
            variacao = ((atual_desconto / media_desconto) - 1) * 100 if media_desconto > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_desconto:.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_desconto:.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="desconto_percent_acumulado", 
                         text=df['desconto_percent_acumulado'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Desconto: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Desconto (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_vendas_identificadas(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 🆔 Vendas Identificadas (%) - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_vendas_ident_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Por Dia", "📈 Por Dezena", "📆 Por Mês", "⚡ Ritmo"])
    
    # --- Por Dia (mês atual, até D-1) ---
    with tab1:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        sql = f"""
            WITH tot AS (
                SELECT 
                    CAST(data_date AS DATE) AS data_date,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
                GROUP BY 1
            ),
            ident AS (
                SELECT 
                    CAST(data_date AS DATE) AS data_date,
                    COUNT(DISTINCT venda_id) AS n_ident
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
                  AND venda_pessoaid IS NOT NULL
                GROUP BY 1
            )
            SELECT 
                t.data_date,
                CASE WHEN t.n_total = 0 THEN 0.0
                     ELSE 100.0 * i.n_ident / t.n_total
                END AS vendas_identificadas_percent
            FROM tot t
            LEFT JOIN ident i ON t.data_date = i.data_date
            ORDER BY t.data_date
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para o período.")
        else:
            df["data_date"] = pd.to_datetime(df["data_date"])
            df["data_formatada"] = df["data_date"].dt.strftime("%d/%m")
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="data_formatada", y="vendas_identificadas_percent", 
                         text=df['vendas_identificadas_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkslateblue',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vendas Identificadas: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vendas Identificadas (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Dezena (últimos ~4 meses = 12 dezenas) ---
    with tab2:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    venda_pessoaid,
                    strftime(data_date, '%Y-%m') AS ano_mes_str,
                    CASE 
                        WHEN EXTRACT(DAY FROM data_date) <= 10 THEN '1ª Dezena'
                        WHEN EXTRACT(DAY FROM data_date) <= 20 THEN '2ª Dezena'
                        ELSE '3ª Dezena'
                    END AS dezena
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
            ),
            tot AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM base
                GROUP BY ano_mes_str, dezena
            ),
            ident AS (
                SELECT 
                    ano_mes_str,
                    dezena,
                    COUNT(DISTINCT venda_id) AS n_ident
                FROM base
                WHERE venda_pessoaid IS NOT NULL
                GROUP BY ano_mes_str, dezena
            )
            SELECT 
                t.ano_mes_str,
                t.dezena,
                CASE WHEN t.n_total = 0 THEN 0.0
                     ELSE 100.0 * i.n_ident / t.n_total
                END AS vendas_identificadas_percent
            FROM tot t
            LEFT JOIN ident i ON t.ano_mes_str = i.ano_mes_str AND t.dezena = i.dezena
            ORDER BY t.ano_mes_str, 
                CASE t.dezena
                    WHEN '1ª Dezena' THEN 1
                    WHEN '2ª Dezena' THEN 2
                    ELSE 3
                END
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para as últimas dezenas.")
        else:
            # Criar dezena formatada para o eixo X
            df["dezena_formatada"] = pd.to_datetime(df["ano_mes_str"]).dt.strftime("%b/%y") + " - " + df["dezena"].astype(str)
            
            # Pegar as últimas 12 dezenas
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="dezena_formatada", y="vendas_identificadas_percent", 
                         text=df['vendas_identificadas_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='indianred',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vendas Identificadas: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vendas Identificadas (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Por Mês (últimos 12 meses) ---
    with tab3:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH tot AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
                GROUP BY 1
            ),
            ident AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_ident
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                {cond_loja} {cond_cls}
                  AND venda_pessoaid IS NOT NULL
                GROUP BY 1
            )
            SELECT 
                t.mes,
                CASE WHEN t.n_total = 0 THEN 0.0
                     ELSE 100.0 * i.n_ident / t.n_total
                END AS vendas_identificadas_percent
            FROM tot t
            LEFT JOIN ident i ON t.mes = i.mes
            ORDER BY t.mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para os últimos meses.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📉 Média Geral</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].mean():.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔝 Maior</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].max():.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">🔻 Menor</div><div style="font-size: 14px; font-weight: bold; color: #333;">{df['vendas_identificadas_percent'].min():.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="vendas_identificadas_percent", 
                         text=df['vendas_identificadas_percent'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='firebrick',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vendas Identificadas: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vendas Identificadas (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)
    
    # --- Ritmo (acumulado até o dia D de cada mês, últimos 12 meses) ---
    with tab4:
        st.markdown('<div style="width:650px; height:1px; min-width:650px;"></div>', unsafe_allow_html=True)
        d = data_ref.day
        ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
        
        sql = f"""
            WITH base AS (
                SELECT 
                    data_date,
                    venda_id,
                    venda_pessoaid
                FROM fact_vendas_final
                WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
                  AND EXTRACT(DAY FROM data_date) <= {d}
                {cond_loja} {cond_cls}
            ),
            tot AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_total
                FROM base
                GROUP BY 1
            ),
            ident AS (
                SELECT 
                    DATE_TRUNC('month', data_date)::DATE AS mes,
                    COUNT(DISTINCT venda_id) AS n_ident
                FROM base
                WHERE venda_pessoaid IS NOT NULL
                GROUP BY 1
            )
            SELECT 
                t.mes,
                CASE WHEN t.n_total = 0 THEN 0.0
                     ELSE 100.0 * i.n_ident / t.n_total
                END AS vendas_identificadas_percent_acumulado
            FROM tot t
            LEFT JOIN ident i ON t.mes = i.mes
            ORDER BY t.mes
        """
        
        df = duck_query(sql)
        if df is None or df.empty:
            st.info("Sem dados para calcular o ritmo.")
        else:
            # Garantir que temos exatamente 12 meses
            df["mes"] = pd.to_datetime(df["mes"])
            df["mes_formatado"] = df["mes"].dt.strftime("%Y-%m")
            df = df.tail(12)
            
            # Calcular média e variação
            media_ident = df['vendas_identificadas_percent_acumulado'].mean()
            atual_ident = df['vendas_identificadas_percent_acumulado'].iloc[-1]
            variacao = ((atual_ident / media_ident) - 1) * 100 if media_ident > 0 else 0
            
            # KPIs compactos
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Média</div><div style="font-size: 14px; font-weight: bold; color: #333;">{media_ident:.1f}%</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📈 Atual</div><div style="font-size: 14px; font-weight: bold; color: #333;">{atual_ident:.1f}%</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div style="text-align: center; font-size: 11px;"><div style="font-weight: bold; color: #666; font-size: 10px;">📊 Variação</div><div style="font-size: 14px; font-weight: bold; color: #333;">{variacao:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            fig = px.bar(df, x="mes_formatado", y="vendas_identificadas_percent_acumulado", 
                         text=df['vendas_identificadas_percent_acumulado'].apply(lambda x: f'{x:.1f}%'), 
                         text_auto=False)
            fig.update_traces(
                marker_color='darkgoldenrod',
                textangle=0,
                textposition="inside",
                textfont=dict(color='white', size=10),
                hovertemplate="<b>%{x}</b><br>Vendas Identificadas: %{y:.1f}%<extra></extra>"
            )
            fig.update_layout(
                height=250,
                width=650,  # Força largura fixa
                autosize=False,  # Desativa ajuste automático
                showlegend=False,
                xaxis_tickangle=-45,
                template="plotly_white",
                margin=dict(t=20, b=20, l=30, r=30),
                xaxis=dict(title="", tickfont=dict(size=10)),
                yaxis=dict(title="Vendas Identificadas (%)", tickfont=dict(size=10)),
                title=''
            )
            st.plotly_chart(fig, use_container_width=False)

def render_popover_top_produtos(codigo_filial: str | None):
    # Inject custom CSS to make dataframe font smaller
    st.markdown("""
    <style>
        .stDataFrame table {
            font-size: 10px;  /* Adjust to 10px or smaller if needed */
        }
        .stDataFrame table th, .stDataFrame table td {
            padding: 2px;  /* Optional: Reduce padding for compactness */
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 🏆 Top Produtos - Filial {codigo_filial}")
    
    # Filtro por Classificação N1
    df_cls = duck_query(f"""
        SELECT DISTINCT UPPER(TRIM(classificacao_n1)) AS n1
        FROM fact_vendas_final
        WHERE classificacao_n1 IS NOT NULL
          {cond_loja}
    """)
    
    if df_cls is None or df_cls.empty:
        opcoes_cls = ["Todas as Classificações"]
    else:
        opcoes_cls = ["Todas as Classificações"] + sorted([c for c in df_cls["n1"].dropna().astype(str).tolist() if c])

    sel_cls = st.selectbox(
        "🏷️ Classificação N1",
        opcoes_cls,
        index=0,
        key=f"pop_cls_top_produtos_{(codigo_filial or 'ALL')}"
    )
    
    # Condição para filtrar por classificação
    cond_cls = "" if sel_cls == "Todas as Classificações" else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls}'"
    
    top1, top2 = st.columns(2)

    with top1:
        # --- Top 10 por Valor ---
        st.markdown("#### 💰 Top 10 por Valor")
        sql_valor = f"""
            SELECT 
                embalagem_descricao AS produto,
                SUM(item_valortotal) AS valor_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY embalagem_descricao
            ORDER BY valor_total DESC
            LIMIT 10
        """
        
        df_valor = duck_query(sql_valor)
        if df_valor is None or df_valor.empty:
            st.info("Sem dados para top produtos por valor.")
        else:
            # Use column_config to set widths and formatting
            st.dataframe(
                df_valor,
                column_config={
                    "produto": st.column_config.TextColumn("Produto", width="medium"),
                    "valor_total": st.column_config.NumberColumn("Valor Total", format="%.2f"),
                },
                use_container_width=True,
                hide_index=True
            )
    
    with top2:
        # --- Top 10 por Quantidade ---
        st.markdown("#### 📦 Top 10 por Quantidade")
        sql_quantidade = f"""
            SELECT 
                embalagem_descricao AS produto,
                SUM(item_quantidade) AS quantidade_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
            {cond_loja} {cond_cls}
            GROUP BY embalagem_descricao
            ORDER BY quantidade_total DESC
            LIMIT 10
        """
        
        df_quantidade = duck_query(sql_quantidade)
        if df_quantidade is None or df_quantidade.empty:
            st.info("Sem dados para top produtos por quantidade.")
        else:
            # Use column_config to set widths and formatting
            st.dataframe(
                df_quantidade,
                column_config={
                    "produto": st.column_config.TextColumn("Produto", width="small"),
                    "quantidade_total": st.column_config.NumberColumn("Quantidade Total", format="%d"),
                },
                use_container_width=True,
                hide_index=True
            )

def render_popover_analise_dia_hora(codigo_filial: str | None):
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_90 = data_ref - timedelta(days=89)
    
    # Condição para filtrar por filial
    cond_loja = "" if (codigo_filial is None or codigo_filial == "Todas as Filiais") else f"AND filial_codigo = '{codigo_filial}'"
    
    # Título compacto
    st.markdown(f"### 📅 Análise Dia e Hora - Filial {codigo_filial}")
    
    # Filiais disponíveis para seletor interno
    sql_filiais = f"""
        SELECT DISTINCT filial_codigo
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
          {cond_loja}
    """
    df_filiais = duck_query(sql_filiais)
    filiais_disp = ["Todas as Filiais"] + sorted(df_filiais["filial_codigo"].dropna().astype(str).unique().tolist()) if df_filiais is not None else ["Todas as Filiais"]
    
    try:
        idx_default = filiais_disp.index(str(codigo_filial)) if codigo_filial else 0
    except ValueError:
        idx_default = 0
    filial_escolhida = st.selectbox("Filial (popover):", filiais_disp, index=idx_default, key=f"sel_filial_analise_{str(codigo_filial or 'ALL')}")
    
    # Atualizar condição de filial baseada na escolha
    cond_loja_final = "" if filial_escolhida == "Todas as Filiais" else f"AND filial_codigo = '{filial_escolhida}'"
    
    # Query para calcular min/max específico das filiais (excluindo "Todas as Filiais")
    sql_filiais_minmax = f"""
        SELECT 
            filial_codigo,
            (EXTRACT(DOW FROM venda_datahorafechamento) + 6) % 7 AS weekday,
            EXTRACT(HOUR FROM venda_datahorafechamento) AS hora,
            COUNT(DISTINCT venda_id) AS qtd_atendimentos
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
          AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
          AND filial_codigo IS NOT NULL
        GROUP BY filial_codigo, weekday, hora
    """
    
    df_filiais_minmax = duck_query(sql_filiais_minmax)
    if df_filiais_minmax is not None and not df_filiais_minmax.empty:
        # Valores min/max considerando apenas as filiais individuais
        filiais_min = float(df_filiais_minmax["qtd_atendimentos"].min())
        filiais_max = float(df_filiais_minmax["qtd_atendimentos"].max())
    else:
        filiais_min = 0.0
        filiais_max = 1.0
    
    # Pills: Apenas "Horas" por enquanto
    opcoes = ["Horas", "Dias", "Dia e Hora (Absoluto)", "Dia e Hora (Relativo)", "Dia e Hora (por Funcionário)"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(opcoes)
    
    with tab1:
        # SQL para contar distinct venda_id por hora
        sql_horas = f"""
            SELECT 
                EXTRACT(HOUR FROM venda_datahorafechamento) AS hora,
                COUNT(DISTINCT venda_id) AS qtd_atendimentos
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
              AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
              {cond_loja_final}
            GROUP BY hora
            ORDER BY hora
        """
        
        df_horas = duck_query(sql_horas)
        if df_horas is None or df_horas.empty:
            st.info("Sem dados para análise de horas.")
            return
        
        # Calcular total de atendimentos e proporção
        total_atendimentos = df_horas["qtd_atendimentos"].sum()
        df_horas["prop"] = (df_horas["qtd_atendimentos"] / total_atendimentos * 100) if total_atendimentos > 0 else 0
        
        # Garantir horas de 7 a 22, preenchendo ausentes com 0
        horas_completas = pd.DataFrame({"hora": list(range(7, 23))})
        df_horas = horas_completas.merge(df_horas, on="hora", how="left").fillna({"qtd_atendimentos": 0, "prop": 0})
        
        # Gráfico de barras
        fig = px.bar(
            df_horas, 
            x="hora", 
            y="prop", 
            title="Proporção por Hora (Últimos 90 Dias)", 
            labels={"hora": "Hora", "prop": "Proporção (%)"}
        )
        fig.update_layout(
            height=250,
            margin=dict(t=20, b=20, l=30, r=30), 
            xaxis=dict(tickmode='linear', dtick=1, title="", tickfont=dict(size=10)),
            yaxis=dict(title="", showticklabels=False),
            title=''
        )
        fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside', cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_tab1_{filial_escolhida}")
    
    with tab2:
        # SQL para contar distinct venda_id por weekday
        sql_dias = f"""
            SELECT 
                (EXTRACT(DOW FROM venda_datahorafechamento) + 6) % 7 AS weekday,  -- Adjust to 0=Monday
                COUNT(DISTINCT venda_id) AS qtd_atendimentos
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
              AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
              {cond_loja_final}
            GROUP BY weekday
            ORDER BY weekday
        """
        
        df_dias = duck_query(sql_dias)
        if df_dias is None or df_dias.empty:
            st.info("Sem dados para análise de dias.")
            return
        
        # Calcular total de atendimentos e proporção
        total_atendimentos = df_dias["qtd_atendimentos"].sum()
        df_dias["prop"] = (df_dias["qtd_atendimentos"] / total_atendimentos * 100) if total_atendimentos > 0 else 0
        
        # Garantir weekdays de 0 a 6, preenchendo ausentes com 0
        dias_completos = pd.DataFrame({"weekday": list(range(7))})
        df_dias = dias_completos.merge(df_dias, on="weekday", how="left").fillna({"qtd_atendimentos": 0, "prop": 0})
        
        # Adicionar labels de dias da semana
        df_dias["weekday_label"] = df_dias["weekday"].apply(lambda x: _weekday_labels([x])[0])
        
        # Gráfico de barras
        fig = px.bar(
            df_dias, 
            x="weekday_label", 
            y="prop", 
            title="Proporção por Dia da Semana (Últimos 90 Dias)", 
            labels={"weekday_label": "Dia", "prop": "Proporção (%)"}
        )
        fig.update_layout(
            height=250,
            margin=dict(t=20, b=20, l=30, r=30), 
            xaxis=dict(title="", tickfont=dict(size=10)),
            yaxis=dict(title="", showticklabels=False),
            title=''
        )
        fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside', cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_tab2_{filial_escolhida}")
    
    with tab3:
        # SQL para contar distinct venda_id por weekday e hora
        sql_matriz = f"""
            SELECT 
                (EXTRACT(DOW FROM venda_datahorafechamento) + 6) % 7 AS weekday,  -- Adjust to 0=Monday
                EXTRACT(HOUR FROM venda_datahorafechamento) AS hora,
                COUNT(DISTINCT venda_id) AS qtd_atendimentos
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
              AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
              {cond_loja_final}
            GROUP BY weekday, hora
            ORDER BY weekday, hora
        """
        
        df_matriz = duck_query(sql_matriz)
        if df_matriz is None or df_matriz.empty:
            st.info("Sem dados para análise de dia e hora absoluto.")
            return
        
        # Pivot para criar matriz (horas como linhas, weekdays como colunas)
        matriz = df_matriz.pivot_table(index='hora', columns='weekday', values='qtd_atendimentos', fill_value=0)
        
        # Garantir horas de 7 a 22 e weekdays de 0 a 6
        horas_range = list(range(7, 23))
        weekdays_range = list(range(7))
        matriz = matriz.reindex(index=horas_range, columns=weekdays_range, fill_value=0)
        
        # Labels para weekdays
        x_labels = _weekday_labels(weekdays_range)
        y_labels = horas_range
        
        # Valores absolutos para determinar min/max
        abs_min = float(matriz.values.min())
        abs_max = float(matriz.values.max())
        
        # Heatmap com px.imshow
        fig = px.imshow(
            matriz.values, 
            x=x_labels, 
            y=y_labels, 
            aspect="auto",
            color_continuous_scale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],  # Blue to red
            labels=dict(color="Vendas"),
            zmin=abs_min, 
            zmax=abs_max
        )
        fig.update_traces(
            text=np.round(matriz.values, 0).astype(int), 
            texttemplate="%{text}", 
            textfont=dict(color="white", size=12), 
            xgap=2, 
            ygap=2
        )
        fig.update_layout(
            height=500,  # Aumentado para melhor visualização
            margin=dict(t=40, b=40, l=50, r=50), 
            coloraxis_colorbar=dict(title="Vendas"),
            title=""
        )
        fig.update_xaxes(side="top")
        st.plotly_chart(fig, use_container_width=True, key=f"chart_tab3_{filial_escolhida}")
    
    with tab4:
        # SQL para contar distinct venda_id por weekday e hora para a filial escolhida (ou agregada)
        sql_filial = f"""
            SELECT 
                (EXTRACT(DOW FROM venda_datahorafechamento) + 6) % 7 AS weekday,  -- Adjust to 0=Monday
                EXTRACT(HOUR FROM venda_datahorafechamento) AS hora,
                COUNT(DISTINCT venda_id) AS qtd_atendimentos
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
              AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
              {cond_loja_final}
            GROUP BY weekday, hora
            ORDER BY weekday, hora
        """
        
        df_matriz = duck_query(sql_filial)
        if df_matriz is None or df_matriz.empty:
            st.info("Sem dados para análise de dia e hora relativo.")
            return
        
        # Pivot para criar matriz (horas como linhas, weekdays como colunas)
        matriz = df_matriz.pivot_table(index='hora', columns='weekday', values='qtd_atendimentos', fill_value=0)
        
        # Garantir horas de 7 a 22 e weekdays de 0 a 6
        horas_range = list(range(7, 23))
        weekdays_range = list(range(7))
        matriz = matriz.reindex(index=horas_range, columns=weekdays_range, fill_value=0)
        
        # Normalização diferente dependendo se é "Todas as Filiais" ou filial individual
        if filial_escolhida == "Todas as Filiais":
            # Para "Todas as Filiais", normaliza com base em min/max das filiais individuais
            denom = (filiais_max - filiais_min) if (filiais_max - filiais_min) != 0 else 1.0
            mat_norm = ((matriz - filiais_min) / denom * 100.0).clip(lower=0, upper=100)
            z_max = 100.0
        else:
            # Para filial individual, normaliza com base em min/max de todas as filiais
            # mas a escala de cor é aplicada apenas ao range da própria filial
            denom = (filiais_max - filiais_min) if (filiais_max - filiais_min) != 0 else 1.0
            mat_norm = ((matriz - filiais_min) / denom * 100.0).clip(lower=0, upper=100)
            z_max = float(mat_norm.values.max())  # Máximo da própria filial para escala de cor
        
        # Labels para weekdays
        x_labels = _weekday_labels(weekdays_range)
        y_labels = horas_range
        
        # Heatmap com px.imshow
        fig = px.imshow(
            mat_norm.values, 
            x=x_labels, 
            y=y_labels, 
            aspect="auto",
            color_continuous_scale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],  # Blue to red
            labels=dict(color="Índice"),
            zmin=0, 
            zmax=z_max
        )
        fig.update_traces(
            text=np.round(mat_norm.values, 0).astype(int), 
            texttemplate="%{text}", 
            textfont=dict(color="white", size=12), 
            xgap=2, 
            ygap=2
        )
        fig.update_layout(
            height=500,  # Aumentado para melhor visualização
            margin=dict(t=40, b=40, l=50, r=50), 
            coloraxis_colorbar=dict(title="Índice 0–100"),
            title=""
        )
        fig.update_xaxes(side="top")
        st.plotly_chart(fig, use_container_width=True, key=f"chart_tab4_{filial_escolhida}")
    
    with tab5:
        # SQL para contar distinct venda_id por weekday e hora para a filial escolhida (ou agregada)
        sql_func = f"""
            SELECT 
                filial_codigo,
                (EXTRACT(DOW FROM venda_datahorafechamento) + 6) % 7 AS weekday,  -- Adjust to 0=Monday
                EXTRACT(HOUR FROM venda_datahorafechamento) AS hora,
                COUNT(DISTINCT venda_id) AS qtd_atendimentos
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_90}' AND DATE '{data_ref}'
              AND EXTRACT(HOUR FROM venda_datahorafechamento) BETWEEN 7 AND 22
              {cond_loja_final}
            GROUP BY filial_codigo, weekday, hora
            ORDER BY filial_codigo, weekday, hora
        """
        
        df_func = duck_query(sql_func)
        if df_func is None or df_func.empty:
            st.info("Sem dados para análise de dia e hora por funcionário.")
            return
        
        # Determinar número de funcionários para a filial escolhida
        if filial_escolhida == "Todas as Filiais":
            # Para todas as filiais, vamos fazer uma média ponderada
            # Primeiro agrupamos por filial para obter o total por filial
            df_by_filial = df_func.groupby('filial_codigo')['qtd_atendimentos'].sum().reset_index()
            
            # Depois calculamos a média ponderada pelo número de funcionários de cada filial
            total_atendimentos = 0
            total_pesos = 0
            
            for _, row in df_by_filial.iterrows():
                filial_cod = row['filial_codigo']
                if filial_cod in EMPREGADOS_POR_FILIAL:
                    num_func = EMPREGADOS_POR_FILIAL[filial_cod]
                    total_atendimentos += row['qtd_atendimentos']
                    total_pesos += num_func
            
            # Agora agrupamos por weekday e hora sem considerar a filial
            df_agregado = df_func.groupby(['weekday', 'hora'])['qtd_atendimentos'].sum().reset_index()
            
            # Calcular uma média de funcionários proporcional às vendas
            num_funcionarios = total_pesos if total_pesos > 0 else sum(EMPREGADOS_POR_FILIAL.values())
            
        else:
            # Para filial específica, usamos o valor do dicionário ou um valor padrão
            num_funcionarios = EMPREGADOS_POR_FILIAL.get(filial_escolhida, 10)  # Valor padrão de 10 funcionários
            df_agregado = df_func.groupby(['weekday', 'hora'])['qtd_atendimentos'].sum().reset_index()
        
        # Pivot para criar matriz (horas como linhas, weekdays como colunas)
        matriz = df_agregado.pivot_table(index='hora', columns='weekday', values='qtd_atendimentos', fill_value=0)
        
        # Garantir horas de 7 a 22 e weekdays de 0 a 6
        horas_range = list(range(7, 23))
        weekdays_range = list(range(7))
        matriz = matriz.reindex(index=horas_range, columns=weekdays_range, fill_value=0)
        
        # Dividir por 90 dias e pelo número de funcionários
        matriz_por_func = matriz.values / 90 / num_funcionarios
        
        # Labels para weekdays
        x_labels = _weekday_labels(weekdays_range)
        y_labels = horas_range
        
        # Valores para determinar min/max
        func_min = float(matriz_por_func.min())
        func_max = float(matriz_por_func.max())
        
        # Heatmap com px.imshow
        fig = px.imshow(
            matriz_por_func, 
            x=x_labels, 
            y=y_labels, 
            aspect="auto",
            color_continuous_scale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],  # Blue to red
            labels=dict(color="Vendas/Func."),
            zmin=func_min, 
            zmax=func_max
        )
        fig.update_traces(
            text=np.round(matriz_por_func, 1),  # 1 casa decimal
            texttemplate="%{text:.1f}", 
            textfont=dict(color="white", size=12), 
            xgap=2, 
            ygap=2
        )
        fig.update_layout(
            height=500,  # Aumentado para melhor visualização
            margin=dict(t=40, b=40, l=50, r=50), 
            coloraxis_colorbar=dict(title="Vendas/Func."),
            title=f"Média de vendas diárias por funcionário (Total: {num_funcionarios} funcionários)"
        )
        fig.update_xaxes(side="top")
        st.plotly_chart(fig, use_container_width=True, key=f"chart_tab5_{filial_escolhida}")