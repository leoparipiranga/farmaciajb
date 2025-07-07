# ---
# title: Loja
# icon: 🏬
# ---
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
from components.db_df import df  # Importa o DataFrame df do módulo db_df
from components.db_lojas import grafico_ticket_medio, grafico_desc_medio, grafico_cmv, grafico_resultado_bruto, calcular_projecoes, format_brl, abbreviate_brl


# Adicionar o diretório raiz ao sys.path para importar componentes
# Isso assume que 'pages' está um nível abaixo do diretório raiz do projeto
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from components.db_lojas import calcular_kpi_vendas_loja, DATA_ATUAL_SIMULADA, carregar_dados_metas, calcular_kpis, filtro_mes_corrente

def main():

    # Carregar dados
    df_vendas_completo = df
    df_metas = carregar_dados_metas() # Caminho padrão 'base/metas.csv'

    # Filtros na barra lateral
    filiais = df_vendas_completo['filial_nome'].dropna().unique()
    classes = df_vendas_completo['class_painome'].dropna().unique()

    # Filtros no topo da página
    col_f1, col_f2, col_f3, col_f4 = st.columns([1,1,2,2])

    with col_f1:
        filial_selecionada = st.selectbox("Filial", options=["Todas"] + sorted(filiais.tolist()))
    with col_f2:
        class_selecionada = st.selectbox("Classificação", options=["Todas"] + sorted(classes.tolist()))
    st.markdown("---")  # Linha divisória
    # Aplicar filtros
    df_filtrado = df_vendas_completo.copy()
    if filial_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['filial_nome'] == filial_selecionada]
    if class_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['class_painome'] == class_selecionada]

    # Filtrar metas conforme a filial selecionada
    if filial_selecionada != "Todas":
        meta_total = df_metas[df_metas['filial_nome'] == filial_selecionada]['meta'].sum()
    else:
        meta_total = df_metas['meta'].sum()

    # Supondo que DATA_ATUAL_SIMULADA seja a data de hoje
    dia = DATA_ATUAL_SIMULADA.day
    dias_mes = calendar.monthrange(DATA_ATUAL_SIMULADA.year, DATA_ATUAL_SIMULADA.month)[1]
    meta_proporcional = meta_total * dia / dias_mes
    df_filtrado['data_venda_apenas'] = pd.to_datetime(df_filtrado['data_venda_apenas'])
    vendas_mes = df_filtrado[
        (df_filtrado['data_venda_apenas'].apply(lambda x: x.month) == DATA_ATUAL_SIMULADA.month) &
        (df_filtrado['data_venda_apenas'].apply(lambda x: x.year) == DATA_ATUAL_SIMULADA.year) &
        (df_filtrado['data_venda_apenas'].apply(lambda x: x.day) <= DATA_ATUAL_SIMULADA.day)
    ]
    num_vendas_mes = vendas_mes['venda_coo'].nunique()

    data_dia_anterior = DATA_ATUAL_SIMULADA - timedelta(days=1)
    vendas_dia_ant = df_filtrado[
        pd.to_datetime(df_filtrado['data_venda_apenas']).dt.date == data_dia_anterior
    ]
    num_vendas_dia_ant = vendas_dia_ant['venda_coo'].nunique()

    # 2. Percentual de desconto médio (acumulado mês e dia anterior)
    desconto_mes = vendas_mes['item_desconto'].sum()
    valor_mes = vendas_mes['item_valortotal'].sum()
    perc_desconto_mes = (desconto_mes / valor_mes * 100) if valor_mes > 0 else 0

    desconto_dia_ant = vendas_dia_ant['item_desconto'].sum()
    valor_dia_ant = vendas_dia_ant['item_valortotal'].sum()
    perc_desconto_dia_ant = (desconto_dia_ant / valor_dia_ant * 100) if valor_dia_ant > 0 else 0

    if not df_filtrado.empty:
        # Calcular KPI
        venda_acum_mes, venda_dia_anterior = calcular_kpi_vendas_loja(df_filtrado)
        venda_proj, resultado_proj = calcular_projecoes(df_filtrado, DATA_ATUAL_SIMULADA)

        # Exibir KPI
        col1, col2, col3 = st.columns(3) # Criar colunas para melhor layout, se necessário

        with col1: # Usar a primeira coluna para o KPI
            st.markdown("#### Indicadores de Vendas")
            kpis = calcular_kpis(df_filtrado, DATA_ATUAL_SIMULADA)
            # Exemplo de uso:
            # Exibe Venda Acumulada com fonte maior usando HTML:
            st.metric("Venda Acumulada (Mês)", 
                    f"{venda_acum_mes:,.2f}", 
                    f"{venda_dia_anterior:,.2f}")

            col100, col101 = st.columns(2) # Colunas para os KPIs adicionais
            with col100:
                st.metric(
                    label="Venda Projetada",
                    value=f"{abbreviate_brl(venda_proj)}"
                )
                st.metric("Ticket Médio", f"R$ {kpis['ticket_medio_mes']:,.2f}", f"R$ {kpis['ticket_medio_dia_ant']:,.2f}")
                st.metric("Itens por Nota", f"{kpis['itens_por_nota_mes']:,.1f}", f"{kpis['itens_por_nota_dia_ant']:,.1f}")
            with col101:
                st.metric(
                    label="Resultado Projetado",
                    value=f"{abbreviate_brl(resultado_proj)}"
                )
                st.metric(
                    label="Nº de Vendas (Mês)",
                    value=f"{num_vendas_mes:,}".replace(",", "."),
                    delta=f"{num_vendas_dia_ant:,}".replace(",", "."),
                    delta_color="normal"
                )
                st.metric(
                    label="Desconto Médio (%)",
                    value=f"{perc_desconto_mes:.1f}%",
                    delta=f"{perc_desconto_dia_ant:.1f}%",
                    delta_color="normal"
                )
                
            
        # Exibir outros KPIs, se necessário
        # Você pode adicionar mais KPIs nas colunas col2 e col3
        # Exemplo:
        with col2:
            st.markdown("#### Metas de Vendas")
            col211, col212 = st.columns(2)  # Colunas para os indicadores de vendas
            with col211:
                # Formatar os ticks
                tick_vals = [meta_total * i / 4 for i in range(5)]
                tick_text = [f"{v/1e3:.1f}m" for v in tick_vals[:-1]] + [f"{meta_total/1e3:.1f}m"]

                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=venda_acum_mes,
                    title={'text': "Vendas Totais"},
                    gauge={
                        'axis': {
                            'range': [0, meta_total],
                            'tickvals': tick_vals,
                            'ticktext': tick_text
                        },
                        'bar': {'color': "green"},
                        'steps': [
                            {'range': [0, meta_total*0.5], 'color': "lightgray"},
                            {'range': [meta_total*0.5, meta_total], 'color': "silver"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': meta_proporcional
                        }
                    }
                ))
                
                fig.update_layout(height=150, margin=dict(l=35, r=35, t=50, b=35))

                st.plotly_chart(fig, use_container_width=True)

                df_quero_mes = filtro_mes_corrente(
                    df_filtrado[df_filtrado['class_painome'] == 'QUERODELIVERY'],
                    'data_venda_apenas',
                    DATA_ATUAL_SIMULADA
                )
                venda_quero = df_quero_mes['item_valortotal'].sum()
                if filial_selecionada != "Todas":
                    meta_quero = df_metas[df_metas['filial_nome'] == filial_selecionada]['meta_quero'].sum()
                else:
                    meta_quero = df_metas['meta_quero'].sum()
                meta_proporcional_quero = meta_quero * dia / dias_mes
                fig_quero = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=venda_quero,
                    title={'text': "Vendas: QueroDelivery"},
                    gauge={
                        'axis': {'range': [0, meta_quero]},
                        'bar': {'color': "green"},
                        'steps': [
                            {'range': [0, meta_quero*0.5], 'color': "lightgray"},
                            {'range': [meta_quero*0.5, meta_quero], 'color': "silver"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': meta_proporcional_quero
                        }
                    }
                ))
                fig_quero.update_layout(height=150, margin=dict(l=35, r=35, t=50, b=35))
                st.plotly_chart(fig_quero, use_container_width=True)

            with col212:
                df_indicacao_mes = filtro_mes_corrente(
                df_filtrado[df_filtrado['class_painome'] == 'INDICAÇÃO'],
                'data_venda_apenas',
                DATA_ATUAL_SIMULADA
            )
                venda_indicacao = df_indicacao_mes['item_valortotal'].sum()
                if filial_selecionada != "Todas":
                    meta_indicacao = df_metas[df_metas['filial_nome'] == filial_selecionada]['meta_indicacao'].sum()
                else:
                    meta_indicacao = df_metas['meta_indicacao'].sum()
                meta_proporcional_indicacao = meta_indicacao * dia / dias_mes
                fig_indicacao = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=venda_indicacao,
                    title={'text': "Vendas: Indicação"},
                    gauge={
                        'axis': {'range': [0, meta_indicacao]},
                        'bar': {'color': "green"},
                        'steps': [
                            {'range': [0, meta_indicacao*0.5], 'color': "lightgray"},
                            {'range': [meta_indicacao*0.5, meta_indicacao], 'color': "silver"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': meta_proporcional_indicacao
                        }
                    }
                ))
                fig_indicacao.update_layout(height=150, margin=dict(l=35, r=35, t=50, b=35))
                st.plotly_chart(fig_indicacao, use_container_width=True)

                df_vitamina_mes = filtro_mes_corrente(
                    df_filtrado[df_filtrado['classificacao_nome'].str.contains('VITAMINA', na=False)],
                    'data_venda_apenas',
                    DATA_ATUAL_SIMULADA
                )
                venda_vitamina = df_vitamina_mes['item_valortotal'].sum()
                if filial_selecionada != "Todas":
                    meta_vitamina = df_metas[df_metas['filial_nome'] == filial_selecionada]['meta_vitamina'].sum()
                else:
                    meta_vitamina = df_metas['meta_vitamina'].sum()
                meta_proporcional_vitamina = meta_vitamina * dia / dias_mes
                fig_vitamina = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=venda_vitamina,
                    title={'text': "Vendas: Vitamina"},
                    gauge={
                        'axis': {'range': [0, meta_vitamina]},
                        'bar': {'color': "green"},
                        'steps': [
                            {'range': [0, meta_vitamina*0.5], 'color': "lightgray"},
                            {'range': [meta_vitamina*0.5, meta_vitamina], 'color': "silver"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': meta_proporcional_vitamina
                        }
                    }
                ))
                fig_vitamina.update_layout(height=150, margin=dict(l=35, r=35, t=50, b=35))
                st.plotly_chart(fig_vitamina, use_container_width=True)
        
        with col3:
            st.markdown("#### Ranking de Produtos Mais Vendidos")
            selected_top = option_menu(
                menu_title="",
                options=["Por Valor", "Por Quantidade"],
                icons=["cash-stack", "list-ol"],
                menu_icon="",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {
                        "display": "flex",
                        "justify-content": "flex-start",   # alinha à esquerda
                        "align-items": "center",
                        "padding": "0!important",
                        "background-color": "transparent",
                        "width": "fit-content"            # só o tamanho dos botões
                    },
                    "icon": {
                                "font-size": "14px",
                                "margin-bottom": "0",
                            },
                            "nav-link": {
                                "font-size": "14px",
                                "color": "white",
                                "padding": "4px",
                                "margin": "2px 6px 2px 0",
                                "width": "180px",
                                "height": "60px",
                                "text-align": "center",
                                "display": "flex",
                                "flex-direction": "column",
                                "align-items": "center",
                                "justify-content": "center",
                                "border": "2px solid #7FDBFF",
                                "border-radius": "5px",
                                "background-color": "lightgray"
                            },
                            "nav-link:hover": {
                                "background-color": "gray",
                                "border-color": "#7FDBFF"
                            },
                            "nav-link-selected": {
                                "background-color": "gray",
                            },
                        }
                    )
            
            periodo_ranking = st.radio("Período", ["Dia", "Semana", "Mês"], horizontal=True, key="ranking_periodo")
            
            data_atual_ts = pd.Timestamp(DATA_ATUAL_SIMULADA)

            if periodo_ranking == "Dia":
                data_inicio = data_atual_ts - pd.Timedelta(days=1)
                data_fim    = data_atual_ts - pd.Timedelta(days=1)
            elif periodo_ranking == "Semana":
                data_inicio = data_atual_ts - pd.Timedelta(days=7)
                data_fim    = data_atual_ts - pd.Timedelta(days=1)
            elif periodo_ranking == "Mês":
                data_inicio = data_atual_ts.replace(day=1)
                data_fim    = data_atual_ts - pd.Timedelta(days=1)
            
            # Antes do filtro, converta para datetime64[ns]
            df_filtrado['data_venda_apenas'] = pd.to_datetime(df_filtrado['data_venda_apenas'])

            df_rank = df_filtrado[
                (df_filtrado['data_venda_apenas'] >= data_inicio) &
                (df_filtrado['data_venda_apenas'] <= data_fim)
            ].copy()

            # Agrupamento por produto
            top_valor = (
                df_rank.groupby(['produto_codigo','embalagem_descricao'])['item_valortotal']
                .sum()
                .reset_index()
                .sort_values('item_valortotal', ascending=False)
                .head(5)
            )
            top_quantidade = (
                df_rank.groupby(['produto_codigo','embalagem_descricao'])['item_quantidade']
                .sum()
                .reset_index()
                .sort_values('item_quantidade', ascending=False)
                .head(5)
            )

            if selected_top == "Por Valor":
                st.dataframe(
                    top_valor[['embalagem_descricao', 'item_valortotal']].rename(
                        columns={'embalagem_descricao': 'Produto', 'item_valortotal': 'Valor (R$)'}),
                    hide_index=True,
                    use_container_width=False
                )
            else:
                st.dataframe(
                    top_quantidade[['embalagem_descricao', 'item_quantidade']].rename(
                        columns={'embalagem_descricao': 'Produto', 'item_quantidade': 'Qtde'}),
                    hide_index=True,
                    use_container_width=False
                )
            
        st.markdown("---") # Linha divisória

        col21, col22, col23 = st.columns([3,4,2]) # Colunas para o gráfico
        with col21:
            with st.container():
                st.subheader("Gráficos de Vendas e Mix")
                selected_grafico = option_menu(
                    menu_title="",
                    options=["Vendas", "Mix"],
                    icons=["bar-chart", "layers"],
                    menu_icon="",
                    default_index=0,
                    orientation="horizontal",
                    styles={
                        "container": {
                            "display": "flex",
                            "justify-content": "flex-start",  # Alinha à esquerda
                            "padding": "0!important",
                            "background-color": "transparent",
                            "width": "fit-content"
                        },
                        "icon": {
                            "font-size": "14px",
                            "margin-bottom": "0",
                        },
                        "nav-link": {
                            "font-size": "14px",
                            "color": "white",
                            "padding": "4px",
                            "margin": "2px 6px 2px 0",  # Espaço à direita entre botões
                            "width": "100px",
                            "height": "80px",
                            "text-align": "center",
                            "display": "flex",
                            "flex-direction": "column",
                            "align-items": "center",
                            "justify-content": "center",
                            "border": "2px solid #7FDBFF",
                            "border-radius": "5px",
                            "background-color": "lightgray"
                        },
                        "nav-link:hover": {
                            "background-color": "gray",
                            "border-color": "#7FDBFF"
                        },
                        "nav-link-selected": {
                            "background-color": "gray",
                        },
                    }
                )

            if selected_grafico == "Vendas":
                col211, col212 = st.columns(2)  # Colunas para os filtros do gráfico de vendas
                with col211:
                    tipo_agrupamento = st.radio("Período", ["Diário", "Semanal", "Mensal"], horizontal=True, key="tipo_agrupamento_grafico_vendas")
                with col212:
                    tipo_valor = st.radio("Visualizar por", ["Valor", "Quantidade"], horizontal=True, key="tipo_valor_grafico_vendas")
                # Defina o início e fim do filtro de datas conforme o agrupamento

                data_atual = pd.Timestamp(DATA_ATUAL_SIMULADA)

                if tipo_agrupamento == "Diário":
                    data_inicio = data_atual.replace(day=1)
                elif tipo_agrupamento == "Semanal":
                    data_inicio = data_atual.replace(day=1) - relativedelta(months=2)
                elif tipo_agrupamento == "Mensal":
                    data_inicio = data_atual.replace(day=1) - relativedelta(months=5)
                data_fim = data_atual

                df_grafico = df_filtrado[
                    (df_filtrado['data_venda_apenas'] >= data_inicio) &
                    (df_filtrado['data_venda_apenas'] <= data_fim)
                ].copy()

                # Escolher coluna de valor
                coluna_valor = "item_valortotal" if tipo_valor == "Valor" else "item_quantidade"

                # Agrupamento e tratamento especial para o mensal
                if tipo_agrupamento == "Diário":
                    df_grafico['periodo'] = df_grafico['data_venda_apenas']
                    df_agg = df_grafico.groupby('periodo')[coluna_valor].sum().reset_index()
                    df_agg['label_x'] = df_agg['periodo'].apply(lambda x: f"{x.day}")
                    x_col = 'label_x'
                elif tipo_agrupamento == "Semanal":
                    df_grafico['periodo'] = df_grafico['data_venda_apenas'].apply(lambda x: x.isocalendar()[1])
                    df_agg = df_grafico.groupby('periodo')[coluna_valor].sum().reset_index()
                    x_col = 'periodo'
                elif tipo_agrupamento == "Mensal":
                    dia_ontem = DATA_ATUAL_SIMULADA.day - 1
                    if dia_ontem < 1:
                        dia_ontem = 1
                    opcao_mensal = st.radio(
                        f"Visualização dos meses:",
                        [f"Total", f"Até dia {dia_ontem:02d}"],
                        horizontal=True,
                        key="opcao_mensal"
                    )
                    df_grafico['periodo'] = df_grafico['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
                    if opcao_mensal != "Total":
                        df_grafico = df_grafico[df_grafico['data_venda_apenas'].apply(lambda x: x.day <= dia_ontem)]
                    df_agg = df_grafico.groupby('periodo')[coluna_valor].sum().reset_index()
                    x_col = 'periodo'

                fig_vendas = px.bar(
                    df_agg,
                    x=x_col,
                    y=coluna_valor,
                    text=coluna_valor,
                    color_discrete_sequence=["steelblue"]
                )

                def format_k(v):
                    if pd.isna(v):
                        return ""
                    if abs(v) >= 1000:
                        return f"{v/1000:.0f}k"
                    else:
                        return f"{int(v)}"
                fig_vendas.update_traces(
                    text=[format_k(v) for v in df_agg[coluna_valor]],
                    textposition='outside'
                )

                # Remover títulos dos eixos
                fig_vendas.update_layout(
                    xaxis_title=None,
                    yaxis_title=None,
                    yaxis=dict(showticklabels=False),
                    margin=dict(t=20, b=120, l=20, r=20),
                    title=f"Vendas Totais ({tipo_agrupamento}) - {tipo_valor}"
                )
                st.plotly_chart(fig_vendas, use_container_width=True)
            elif selected_grafico == "Mix":
                # Filtro só de período
                tipo_agrupamento_mix = st.radio("Período", ["Diário", "Semanal", "Mensal"], horizontal=True, key="tipo_agrupamento_grafico_mix")
                if tipo_agrupamento_mix == "Diário":
                    # Apenas mês corrente
                    data_inicio = DATA_ATUAL_SIMULADA.replace(day=1)
                elif tipo_agrupamento_mix == "Semanal":
                    # Mês corrente e dois anteriores
                    data_inicio = (DATA_ATUAL_SIMULADA.replace(day=1) - relativedelta(months=2))
                elif tipo_agrupamento_mix == "Mensal":
                    # Até seis meses, incluindo o mês corrente
                    data_inicio = (DATA_ATUAL_SIMULADA.replace(day=1) - relativedelta(months=5))

                data_fim = DATA_ATUAL_SIMULADA
                data_inicio = pd.Timestamp(data_inicio)
                data_fim = pd.Timestamp(DATA_ATUAL_SIMULADA)

                # Filtrar o DataFrame pelo período definido
                df_mix = df_filtrado[
                    (df_filtrado['data_venda_apenas'] >= data_inicio) &
                    (df_filtrado['data_venda_apenas'] <= data_fim)
                ].copy()
                
                # Agrupamento por período (igual ao gráfico anterior)
                if tipo_agrupamento_mix == "Diário":
                    df_mix['periodo'] = df_mix['data_venda_apenas']
                    df_agg_mix = df_mix.groupby('periodo')['embalagem_codigobarras'].nunique().reset_index()
                    df_agg_mix['label_x'] = df_agg_mix['periodo'].apply(lambda x: x.strftime("%d"))
                    x_col_mix = 'label_x'
                elif tipo_agrupamento_mix == "Semanal":
                    df_mix['periodo'] = df_mix['data_venda_apenas'].apply(lambda x: x.isocalendar()[1])
                    df_agg_mix = df_mix.groupby('periodo')['embalagem_codigobarras'].nunique().reset_index()
                    x_col_mix = 'periodo'
                elif tipo_agrupamento_mix == "Mensal":
                    df_mix['periodo'] = df_mix['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
                    df_agg_mix = df_mix.groupby('periodo')['embalagem_codigobarras'].nunique().reset_index()
                    x_col_mix = 'periodo'

                fig_mix = px.bar(
                    df_agg_mix,
                    x=x_col_mix,
                    y='embalagem_codigobarras',
                    text='embalagem_codigobarras',
                    color_discrete_sequence=["mediumseagreen"]
                )

                fig_mix.update_traces(
                    textposition='outside'
                )
                fig_mix.update_layout(
                    xaxis_title=None,
                    yaxis_title=None,
                    yaxis=dict(showticklabels=False),
                    margin=dict(t=20, b=120, l=20, r=20),
                    title="Evolução do Mix (Produtos Diferentes Vendidos)"
                )
                st.plotly_chart(fig_mix, use_container_width=True)
            
            # Agrupar por mês e forma de pagamento
            
        with col22:
            fig_ticket = grafico_ticket_medio(df_filtrado)
            fig_desc = grafico_desc_medio(df_filtrado)
            fig_cmv = grafico_cmv(df_filtrado)
            fig_rb = grafico_resultado_bruto(df_filtrado)

            with st.container():
                st.subheader("Gráficos de Indicadores")
                selected_indicador = option_menu(
                    menu_title="",
                    options=["Ticket Médio", "Desconto Médio", "CMV", "Resultado Bruto"],
                    icons=["cash-coin", "percent", "graph-up-arrow", "bar-chart-line"],
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
                        "icon": {
                            "font-size": "14px",
                            "margin-bottom": "0",
                        },
                        "nav-link": {
                            "font-size": "14px",
                            "color": "white",
                            "padding": "4px",
                            "margin": "2px 6px 2px 0",
                            "width": "120px",
                            "height": "80px",
                            "text-align": "center",
                            "display": "flex",
                            "flex-direction": "column",
                            "align-items": "center",
                            "justify-content": "center",
                            "border": "2px solid #7FDBFF",
                            "border-radius": "5px",
                            "background-color": "lightgray"
                        },
                        "nav-link:hover": {
                            "background-color": "gray",
                            "border-color": "#7FDBFF"
                        },
                        "nav-link-selected": {
                            "background-color": "gray",
                        },
                    }
                )

            if selected_indicador == "Ticket Médio":
                st.plotly_chart(fig_ticket, use_container_width=True)
            elif selected_indicador == "Desconto Médio":
                st.plotly_chart(fig_desc, use_container_width=True)
            elif selected_indicador == "CMV":
                st.plotly_chart(fig_cmv, use_container_width=True)
            elif selected_indicador == "Resultado Bruto":
                st.plotly_chart(fig_rb, use_container_width=True)
        
            with col23:
                df_filtrado['mes'] = df_filtrado['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
                df_pagto_grouped = df_filtrado.groupby(['mes', 'nome'])['item_valortotal'].sum().reset_index()

                # Calcular o percentual de cada forma de pagamento por mês
                df_pagto_grouped['percent'] = df_pagto_grouped.groupby('mes')['item_valortotal'].transform(lambda x: 100 * x / x.sum())

                # Ordenar para o maior segmento ficar embaixo
                df_pagto_grouped = df_pagto_grouped.sort_values(['mes', 'percent'], ascending=[True, False])

                # Gráfico de barras empilhadas normalizadas
                fig_pagto = px.bar(
                    df_pagto_grouped,
                    x='mes',
                    y='percent',
                    color='nome',
                    text_auto='.1f',
                    category_orders={"nome": df_pagto_grouped.groupby('nome')['percent'].sum().sort_values(ascending=False).index.tolist()},
                    labels={'mes': '', 'percent': '', 'nome': ''},
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )

                df_pagto_grouped['text_percent'] = df_pagto_grouped['percent'].apply(lambda x: f"{x:.0f}%" if x >= 5 else "")

                fig_pagto = px.bar(
                    df_pagto_grouped,
                    x='mes',
                    y='percent',
                    color='nome',
                    text='text_percent',
                    category_orders={"nome": df_pagto_grouped.groupby('nome')['percent'].sum().sort_values(ascending=False).index.tolist()},
                    labels={'mes': '', 'percent': '', 'nome': ''},
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )

                fig_pagto.update_traces(
                    textposition='inside',
                    insidetextanchor='middle'
                )
                fig_pagto.update_layout(
                    yaxis=dict(showticklabels=False, range=[0, 100]),
                    yaxis_title=None,
                    bargap=0.15,
                    legend_title_text='',
                    showlegend=True,
                    xaxis_title=None,
                    margin=dict(t=120, b=10, l=20, r=20),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=1.2,
                        xanchor="center",
                        x=0.5,
                        title=None
                    )
                )

                # Criar coluna de mês/ano
                df_clientes = df_filtrado.copy()
                df_clientes['mes'] = df_clientes['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")

                # Criar coluna de tipo de cliente
                df_clientes['tipo_cliente'] = df_clientes['orcamento_pessoaid'].apply(lambda x: "Cadastrado" if pd.notna(x) else "Não cadastrado")

                # Agrupar por mês e tipo de cliente, contando vendas únicas
                df_clientes_grouped = (
                    df_clientes.groupby(['mes', 'tipo_cliente'])['venda_coo']
                    .nunique()
                    .reset_index()
                    .rename(columns={'venda_coo': 'num_vendas'})
                )

                # Calcular percentual por mês
                df_clientes_grouped['percent'] = df_clientes_grouped.groupby('mes')['num_vendas'].transform(lambda x: 100 * x / x.sum())
                df_clientes_grouped['text_percent'] = df_clientes_grouped['percent'].apply(lambda x: f"{x:.0f}%" if x >= 5 else "")

                # Gráfico de barras empilhadas normalizadas
                fig_clientes = px.bar(
                    df_clientes_grouped,
                    x='mes',
                    y='percent',
                    color='tipo_cliente',
                    text='text_percent',
                    labels={'mes': '', 'percent': '', 'tipo_cliente': ''},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )

                fig_clientes.update_traces(
                    textposition='inside',
                    insidetextanchor='middle'
                )
                fig_clientes.update_layout(
                    yaxis=dict(showticklabels=False, range=[0, 100]),
                    yaxis_title=None,
                    bargap=0.15,
                    legend_title_text='',
                    showlegend=True,
                    xaxis_title=None,
                    margin=dict(t=120, b=10, l=20, r=20),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=1.2,
                        xanchor="center",
                        x=0.5,
                        title=None
                    )
                )
                st.subheader("Pagamentos e Clientes")
                # Exemplo de alternância com o gráfico de formas de pagamento:
                selected_bar = option_menu(
                    menu_title="",
                    options=["Formas de Pagamento", "Clientes Cadastrados"],
                    icons=["credit-card", "person-lines-fill"],
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
                        "icon": {
                            "font-size": "14px",
                            "margin-bottom": "0",
                        },
                        "nav-link": {
                            "font-size": "14px",
                            "color": "white",
                            "padding": "4px",
                            "margin": "2px 6px 2px 0",
                            "width": "180px",
                            "height": "80px",
                            "text-align": "center",
                            "display": "flex",
                            "flex-direction": "column",
                            "align-items": "center",
                            "justify-content": "center",
                            "border": "2px solid #7FDBFF",
                            "border-radius": "5px",
                            "background-color": "lightgray"
                        },
                        "nav-link:hover": {
                            "background-color": "gray",
                            "border-color": "#7FDBFF"
                        },
                        "nav-link-selected": {
                            "background-color": "gray",
                        },
                    }
                )
                
                if selected_bar == "Formas de Pagamento":
                    st.plotly_chart(fig_pagto, use_container_width=True)
                else:
                    st.plotly_chart(fig_clientes, use_container_width=True)

    else:
        st.error("Não foi possível carregar os dados de vendas. Verifique o console para mais detalhes.")
