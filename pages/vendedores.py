import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import sys
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import calendar
from dateutil.relativedelta import relativedelta
from components.db_vendedores import calcular_metas_vendedores, ticket_por_hora, vendas_vendedores_por_hora, calcular_escada_100
from components.db_df import df, metas, DATA_ATUAL_SIMULADA  # Importa o DataFrame df do módulo db_df

df_metas = calcular_metas_vendedores(df, ticket_por_hora)

if not pd.api.types.is_datetime64_any_dtype(df['data_venda_apenas']):
    df['data_venda_apenas'] = pd.to_datetime(df['data_venda_apenas'], format='%Y-%m-%d %H:%M:%S')

def main():

    col101, col102, col103 = st.columns(3)
    with col101:
        filial_selecionada = st.selectbox("Filial", ["Todas"] + sorted(df["filial_nome"].dropna().unique().tolist()))
    with col102:
        classificacao_selecionada = st.selectbox("Classificação", ["Todas"] + sorted(df["class_painome"].dropna().unique().tolist()))
    with col103:
        filtro_periodo = st.radio("Período", ["Acumulado Mês", "Ontem"], index=0, key="filtro_periodo_vendedores")


    col1, col2 = st.columns(2)

    with col1:

        # Primeiro, filtre os dados apenas pela filial (ignora o filtro de classificação do produto)
        df_filtrado_vend = df.copy()
        if filial_selecionada != "Todas":
            df_filtrado_vend = df_filtrado_vend[df_filtrado_vend["filial_nome"] == filial_selecionada]
        if filtro_periodo == "Acumulado Mês":
            df_periodo_vend = df_filtrado_vend[
                (df_filtrado_vend['data_venda_apenas'].dt.month == DATA_ATUAL_SIMULADA.month) &
                (df_filtrado_vend['data_venda_apenas'].dt.year == DATA_ATUAL_SIMULADA.year) &
                (df_filtrado_vend['data_venda_apenas'].apply(lambda x: x.day) <= DATA_ATUAL_SIMULADA.day)
            ].copy()
        else:
            data_ontem = DATA_ATUAL_SIMULADA - timedelta(days=1)
            df_periodo_vend = df_filtrado_vend[
                (df_filtrado_vend['data_venda_apenas'].dt.year == data_ontem.year) &
                (df_filtrado_vend['data_venda_apenas'].dt.month == data_ontem.month) &
                (df_filtrado_vend['data_venda_apenas'].dt.day == data_ontem.day)
            ].copy()
        df_escada = calcular_escada_100(df_periodo_vend, df_metas, metas)
        # Primeiro menu: grupo de visão
        grupo_menu = option_menu(
            menu_title="",
            options=["VISÃO GERAL", "COMISSIONAMENTO"],
            icons=["info-circle", "currency-exchange"],
            menu_icon="",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {
                    "display": "flex",
                    "justify-content": "flex-start",
                    "padding": "0!important",
                    "background-color": "transparent",
                    "width": "fit-content"
                },
                "nav-link": {
                    "font-size": "14px",
                    "color": "white",
                    "padding": "4px",
                    "margin": "2px 6px 2px 0",
                    "width": "180px",
                    "height": "75px",
                    "display": "flex",                    # Exibe o conteúdo como flex container
                    "flex-direction": "column",           # Coloca ícone e texto em colunas
                    "align-items": "center",              # Centraliza horizontalmente
                    "justify-content": "center",          # Centraliza verticalmente
                    "white-space": "normal",              # Permite a quebra de linha
                    "text-align": "center",
                    "border": "2px solid #7FDBFF",
                    "border-radius": "5px",
                    "background-color": "LightSteelBlue"
                },
                "nav-link-selected": {"background-color": "SlateBlue"}
            }
        )

        # Menu aninhado conforme grupo selecionado
        if grupo_menu == "VISÃO GERAL":
            sub_menu = option_menu(
                menu_title="",
                options=["Indicadores Gerais", "Vendas Geral", "Vendas Indicação", "Vendas SBB", "Vendas Vitamina"],
                icons=["table", "bar-chart", "info-circle", "chat-left-text", "plus-circle"],
                menu_icon="",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {
                        "display": "flex",
                        "justify-content": "flex-start",
                        "padding": "0!important",
                        "background-color": "transparent",
                        "width": "fit-content"
                    },
                    "nav-link": {
                        "font-size": "14px",
                        "color": "white",
                        "padding": "4px",
                        "margin": "2px 6px 2px 0",
                        "width": "130px",
                        "height": "75px",
                        "display": "flex",                    # Exibe o conteúdo como flex container
                        "flex-direction": "column",           # Coloca ícone e texto em colunas
                        "align-items": "center",              # Centraliza horizontalmente
                        "justify-content": "center",          # Centraliza verticalmente
                        "white-space": "normal",              # Permite a quebra de linha
                        "text-align": "center",
                        "border": "2px solid #7FDBFF",
                        "border-radius": "5px",
                        "background-color": "DarkGray"
                    },
                    "nav-link-selected": {"background-color": "DimGray"}
                }
            )
        else:
            sub_menu = option_menu(
                menu_title="",
                options=["Resumo Escada", "Desempenho Indicação", "Desempenho SBB", "Desempenho Vitamina", "Comissão"],
                icons=["list-task", "speedometer", "speedometer", "speedometer", "wallet"],
                menu_icon="",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {
                        "display": "flex",
                        "justify-content": "flex-start",
                        "padding": "0!important",
                        "background-color": "transparent",
                        "width": "fit-content"
                    },
                    "nav-link": {
                        "font-size": "14px",
                        "color": "white",
                        "padding": "4px",
                        "margin": "2px 6px 2px 0",
                        "width": "130px",
                        "height": "75px",
                        "display": "flex",                    # Exibe o conteúdo como flex container
                        "flex-direction": "column",           # Coloca ícone e texto em colunas
                        "align-items": "center",              # Centraliza horizontalmente
                        "justify-content": "center",          # Centraliza verticalmente
                        "white-space": "normal",              # Permite a quebra de linha
                        "text-align": "center",
                        "border": "2px solid #7FDBFF",
                        "border-radius": "5px",
                        "background-color": "DarkGray"
                    },
                    "nav-link-selected": {"background-color": "DimGray"}
                }
            )

        # Agora use a variável sub_menu para determinar qual conteúdo exibir
        st.write("Opção selecionada:", sub_menu)
        
        df_escada = df_escada.rename(columns={
            'nome_vendedor': 'Vendedor',
            'meta_vend_geral': 'Meta Geral (R$)',
            'total_geral': 'Venda Geral (R$)',
            'degrau_geral': 'Degrau Geral',
            'meta_vend_indicacao': 'Meta Indicação (R$)',
            'total_indicacao': 'Venda Indicação (R$)',
            'degrau_indicacao': 'Degrau Indicação',
            'meta_vend_sbb': 'Meta SBB (R$)',
            'total_sbb': 'Venda SBB (R$)',
            'degrau_sbb': 'Degrau SBB',
            'meta_vend_vitamina': 'Meta Vitamina (R$)',
            'total_vitamina': 'Venda Vitamina (R$)',
            'degrau_vitamina': 'Degrau Vitamina',
            'perf_indicacao':'Desempenho Indicação', 
            'comm_indicacao':'Comissão Indicação',
            'perf_vitamina':'Desempenho Vitamina',
            'comm_vitamina':'Comissão Vitamina',
            'perf_sbb':'Desempenho SBB',
            'comm_sbb':'Comissão SBB' ,
            'degrau_total': 'Degrau Total',
            'comissao_indicacao': 'Comissão Indicação (R$)',
            'comissao_sbb': 'Comissão SBB (R$)',
            'comissao_vitamina': 'Comissão Vitamina (R$)',
            'comissao_total': 'Comissão Total (R$)'

        })
        df_escada = df_escada.sort_values(by='Venda Geral (R$)', ascending=False)

        # Crie o DataFrame de exibição conforme a categoria selecionada
        if sub_menu == "Indicadores Gerais":
            # Aplicar os filtros ao DataFrame
            df_filtrado = df.copy()
            if filial_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado["filial_nome"] == filial_selecionada]
            if classificacao_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado["class_painome"] == classificacao_selecionada]
            if filtro_periodo == "Acumulado Mês":
                df_periodo = df_filtrado[
                    (df_filtrado['data_venda_apenas'].dt.month == DATA_ATUAL_SIMULADA.month) &
                    (df_filtrado['data_venda_apenas'].dt.year == DATA_ATUAL_SIMULADA.year) &
                    (df_filtrado['data_venda_apenas'].apply(lambda x: x.day) <= DATA_ATUAL_SIMULADA.day)
                ].copy()
            else:
                data_ontem = DATA_ATUAL_SIMULADA - timedelta(days=1)
                df_periodo = df_filtrado[
                    (df_filtrado['data_venda_apenas'].dt.year == data_ontem.year) &
                    (df_filtrado['data_venda_apenas'].dt.month == data_ontem.month) &
                    (df_filtrado['data_venda_apenas'].dt.day == data_ontem.day)
                ].copy()

            # Agrupar por vendedor e calcular indicadores mensais
            df_vendedores = df_periodo.groupby('nome_vendedor').agg(
                total_vendido = ('item_valortotal', 'sum'),
                num_vendas = ('venda_coo', 'nunique'),
                itens_vendidos = ('item_quantidade', 'sum')
            ).reset_index()

            # Cálculo do Ticket Médio e Itens por Nota
            df_vendedores['ticket_medio'] = df_vendedores.apply(
                lambda row: row['total_vendido'] / row['num_vendas'] if row['num_vendas'] > 0 else 0, axis=1
            )
            df_vendedores['itens_por_nota'] = df_vendedores.apply(
                lambda row: row['itens_vendidos'] / row['num_vendas'] if row['num_vendas'] > 0 else 0, axis=1
            )

            df_vendedores.rename(columns={
                'nome_vendedor': 'Vendedor',
                'total_vendido': 'Venda Total (R$)',
                'num_vendas': 'Nº Vendas',
                'itens_vendidos': 'Itens Vendidos',
                'ticket_medio': 'Ticket Médio (R$)',
                'itens_por_nota': 'Itens / NF'
            }, inplace=True)

            # Formatação da tabela usando Styler - separador de milhar para totais e 2 casas decimais para médias
            df_vendedores_formatado = (
                df_vendedores.sort_values(by='Venda Total (R$)', ascending=False)
                .style.format({
                    'Venda Total (R$)': "{:,.0f}",
                    'Nº Vendas': "{:,.0f}",
                    "Itens Vendidos": "{:,.0f}",
                    "Ticket Médio (R$)": "{:,.2f}",
                    "Itens / NF": "{:,.2f}"
                })
            )
            st.subheader("Indicadores por Vendedor (Acumulado Mês)")
            st.dataframe(df_vendedores_formatado, hide_index=True, use_container_width=False)
        
        elif sub_menu == "Vendas Geral":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Meta Geral (R$)', 'Venda Geral (R$)', 'Degrau Geral']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:,.0f}",
                df_display.columns[2]: "{:,.0f}",
                df_display.columns[3]: "{:.0f}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Vendas Indicação":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Meta Indicação (R$)', 'Venda Indicação (R$)', 'Degrau Indicação']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:,.0f}",
                df_display.columns[2]: "{:,.0f}",
                df_display.columns[3]: "{:.0f}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Vendas SBB":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Meta SBB (R$)', 'Venda SBB (R$)', 'Degrau SBB']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:,.0f}",
                df_display.columns[2]: "{:,.0f}",
                df_display.columns[3]: "{:.0f}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Vendas Vitamina":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Meta Vitamina (R$)', 'Venda Vitamina (R$)', 'Degrau Vitamina']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:,.0f}",
                df_display.columns[2]: "{:,.0f}",
                df_display.columns[3]: "{:.0f}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Resumo Escada":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Degrau Geral', 'Degrau Indicação', 'Degrau SBB', 'Degrau Vitamina','Degrau Total']]
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Desempenho Indicação":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Degrau Indicação', 'Desempenho Indicação', 'Comissão Indicação']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:.0f}",
                df_display.columns[3]: "{:.1%}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Desempenho SBB":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Degrau SBB', 'Desempenho SBB', 'Comissão SBB']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:.0f}",
                df_display.columns[3]: "{:.1%}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Desempenho Vitamina":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 'Degrau Vitamina', 'Desempenho Vitamina', 'Comissão Vitamina']]
            df_display = df_display.style.format({
                df_display.columns[1]: "{:.0f}",
                df_display.columns[3]: "{:.1%}"
            })
            st.dataframe(df_display, 
                    hide_index=True)
        elif sub_menu == "Comissão":
            df_display = df_escada.copy()
            df_display = df_display[['Vendedor', 
                                    'Comissão Indicação (R$)', 
                                    'Comissão SBB (R$)', 
                                    'Comissão Vitamina (R$)', 
                                    'Comissão Total (R$)']].sort_values(by='Comissão Total (R$)', ascending=False)
            df_display = df_display.style.format({
                df_display.columns[1]: "{:,.2f}",
                df_display.columns[2]: "{:,.2f}",
                df_display.columns[3]: "{:,.2f}",
                df_display.columns[4]: "{:,.2f}"
            })
            st.dataframe(df_display,
                    hide_index=True,
                    use_container_width=False)


        
