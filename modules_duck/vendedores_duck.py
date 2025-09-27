import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date, timedelta

# Imports da nova estrutura
from data_processing.vendedores.calculations import (
    ticket_medio_vendedor_mes_atual,
    itens_por_nota_vendedor_mes_atual,
    venda_total_vendedor_mes_atual,
    percentuais_classificacao_vendedor_mes_atual,
    kpis_vendedor_mes_atual,
    kpis_vendedor_dia_anterior,
    calcular_kpis_vendedores_comparativo_duck
)
from data_processing.vendedores.queries import (
    dados_completos_vendedor_individual_duck,
    dados_completos_vendedores_comparativo_duck,
    obter_vendedores_por_filial,
    obter_filiais_disponiveis,
    vendas_por_dia_mes_atual,
    verificar_vendas_existe_data,
    obter_ultima_data_vendas,
    gerar_series_mensais_vendedor_duck
)
from visualizations.components.vendedores_popovers import (
    criar_conteudo_popover_vendas_vendedores_duck,
    criar_conteudo_popover_num_vendas_vendedores_duck,
    criar_conteudo_popover_ticket_vendedores_duck,
    criar_conteudo_popover_itens_vendedores_duck,
    criar_conteudo_popover_vitaminas_vendedores_duck,
    criar_conteudo_popover_taxa_conversao_vendedores_duck,
    criar_conteudo_popover_vendas_identificadas_vendedores_duck
)
from visualizations.charts.vendedores_charts import (
    render_heatmap_vendedores,
    render_bar_chart_vendedores
)
from visualizations.styling.css_components import (
    aplicar_css_header,
    aplicar_css_html,
    css_popovers_ruptura,
    css_pills_vendedores
)
from visualizations.components.cards import render_kpi_card
from visualizations.charts.gauges import criar_gauge_plot
from visualizations.charts.bar_charts import render_bar
from utils.formatters import (
    formatar_moeda,
    formatar_numero,
    formatar_numero_uma_casa,
    formatar_percentual
)


def main():
    """Função principal do módulo de vendedores"""
    # Aplicar estilos
    aplicar_css_header()
    aplicar_css_html()
    
    # Renderizar filtros
    filial_selecionada, vendedor_selecionado = _render_filtros()
    
    # Renderizar visões
    _render_visoes(filial_selecionada, vendedor_selecionado)


def _render_filtros():
    """Renderiza os filtros de filial e vendedor"""
    col_filtro_filial, col_filtro_vendedor, col_spacer, col_data_info = st.columns([2, 2, 4, 2], gap="small")
    
    with col_filtro_filial:
        filial_selecionada = _render_filtro_filial()
    
    with col_filtro_vendedor:
        vendedor_selecionado = _render_filtro_vendedor(filial_selecionada)
    
    with col_data_info:
        data_ref = date.today() - timedelta(days=1)
        st.markdown(f"""
        <div style="color:#6b7280; font-size:12px; text-align:right; padding-top:8px;">
            Dados atualizados até {data_ref.strftime('%d/%m/%Y')}
        </div>
        """, unsafe_allow_html=True)
    
    return filial_selecionada, vendedor_selecionado


def _render_filtro_filial():
    """Renderiza o filtro de filial"""
    filiais = obter_filiais_disponiveis()
    filiais_disponiveis = ["Todas as Filiais"] + filiais
    
    # Definir filial padrão como "01" se existir
    filial_padrao = "01"
    if filial_padrao in filiais:
        index_padrao_filial = filiais_disponiveis.index(filial_padrao)
    else:
        index_padrao_filial = 0
    
    # Usar session_state para controlar a filial selecionada
    filial_key = "filial_selecionada_duck"
    if filial_key not in st.session_state:
        st.session_state[filial_key] = filiais_disponiveis[index_padrao_filial]
    
    filial_selecionada = st.selectbox(
        "🏪 Selecione a Filial:",
        options=filiais_disponiveis,
        index=filiais_disponiveis.index(st.session_state[filial_key]),
        key="filial_vendedores_duck",
        on_change=lambda: st.session_state.update({filial_key: st.session_state.filial_vendedores_duck})
    )
    
    st.session_state[filial_key] = filial_selecionada
    return filial_selecionada


def _render_filtro_vendedor(filial_selecionada):
    """Renderiza o filtro de vendedor"""
    top_vendedores = obter_vendedores_por_filial(filial_selecionada, top_n=10)
    
    if top_vendedores:
        vendedores_disponiveis = ["Todos os Vendedores"] + top_vendedores
        label_vendedor = f"👤 Top {len(top_vendedores)} Vendedores (Mês Atual):"
        index_padrao_vendedor = 1 if len(vendedores_disponiveis) > 1 else 0
    else:
        vendedores_disponiveis = ["Todos os Vendedores"]
        label_vendedor = "👤 Selecione o Vendedor:"
        index_padrao_vendedor = 0
    
    return st.selectbox(
        label_vendedor,
        options=vendedores_disponiveis,
        index=index_padrao_vendedor,
        key="vendedor_sel_duck"
    )


def _render_visoes(filial_selecionada, vendedor_selecionado):
    """Renderiza as diferentes visões (Individual/Comparativa)"""
    visoes = ["Individual", "Comparativa"]
    visao_key = "visao_vendedores_mode_duck"
    if visao_key not in st.session_state:
        st.session_state[visao_key] = visoes[0]
    
    visao_escolhida = st.pills("Modo de Visualização:", visoes, key=visao_key)
    
    if visao_escolhida == "Individual":
        _render_visao_individual(filial_selecionada, vendedor_selecionado)
    else:
        _render_visao_comparativa(filial_selecionada, vendedor_selecionado)


def _render_visao_individual(filial_selecionada, vendedor_selecionado):
    """Renderiza a visão individual do vendedor"""
    if vendedor_selecionado == "Todos os Vendedores":
        st.info("Selecione um vendedor específico para visualizar os KPIs individuais.")
        return
    
    # Obter dados do vendedor
    dados_vendedor = dados_completos_vendedor_individual_duck(filial_selecionada, vendedor_selecionado)
    
    # Renderizar seções
    _render_gauges_individuais(dados_vendedor)
    _render_kpis_dia_anterior(dados_vendedor)
    _render_series_mensais(dados_vendedor)


def _render_gauges_individuais(dados_vendedor):
    """Renderiza os gauges de KPIs do mês atual"""
    kpis_mes = dados_vendedor['kpis_mes_atual']
    
    # Extrair valores dos KPIs
    ticket_medio_mes = kpis_mes['ticket_medio']
    itens_por_nota_mes = kpis_mes['itens_por_nota']
    percentuais = kpis_mes['percentuais_classificacao']

    # Renderizar gauges em 6 colunas
    cols_gauges = st.columns(6)

    # Metas fixas
    metas = {
        'ticket_medio': 55,
        'itens_por_nota': 2.5,
        'indicacao': 31,
        'prescricao': 36,
        'sbb': 5,
        'varejo': 10
    }

    with cols_gauges[0]:
        fig_ticket = criar_gauge_plot(ticket_medio_mes, metas['ticket_medio'], "Ticket Médio")
        st.plotly_chart(fig_ticket, use_container_width=True)

    with cols_gauges[1]:
        fig_itens = criar_gauge_plot(itens_por_nota_mes, metas['itens_por_nota'], "Itens por Nota")
        st.plotly_chart(fig_itens, use_container_width=True)

    with cols_gauges[2]:
        fig_indicacao = criar_gauge_plot(percentuais['INDICAÇÃO'], metas['indicacao'], "Indicação %")
        st.plotly_chart(fig_indicacao, use_container_width=True)

    with cols_gauges[3]:
        fig_prescricao = criar_gauge_plot(percentuais['PRESCRIÇÃO'], metas['prescricao'], "Prescrição %")
        st.plotly_chart(fig_prescricao, use_container_width=True)

    with cols_gauges[4]:
        fig_sbb = criar_gauge_plot(percentuais['SBB'], metas['sbb'], "SBB %")
        st.plotly_chart(fig_sbb, use_container_width=True)

    with cols_gauges[5]:
        fig_varejo = criar_gauge_plot(percentuais['VAREJO'], metas['varejo'], "Varejo %")
        st.plotly_chart(fig_varejo, use_container_width=True)


def _render_kpis_dia_anterior(dados_vendedor):
    """Renderiza KPIs do dia anterior + gráfico diário"""
    css_popovers_ruptura()
    
    kpis_dia = dados_vendedor['kpis_dia_anterior']
    vendas_diarias = dados_vendedor['vendas_por_dia']
    
    cols_dia = st.columns([6, 1, 1, 1, 1])
    
    with cols_dia[0]:
        _render_grafico_vendas_diarias(vendas_diarias)
    
    with cols_dia[1]:
        render_kpi_card("Nº de Vendas Ontem", f"{kpis_dia['num_vendas']}")
    
    with cols_dia[2]:
        render_kpi_card("Vitaminas Vendidas Ontem", f"{kpis_dia['vitaminas_vendidas']}")
    
    with cols_dia[3]:
        render_kpi_card("Vendas Identificadas Ontem", f"{kpis_dia['vendas_identificadas_perc']:.1f}%")
    
    with cols_dia[4]:
        render_kpi_card("CMV Ontem", f"{kpis_dia['cmv']:.1f}%")


def _render_grafico_vendas_diarias(vendas_diarias):
    """Renderiza o gráfico de vendas por dia do mês"""
    if not vendas_diarias.empty:
        fig_diario = px.bar(
            vendas_diarias,
            x='dia',
            y='item_valortotal',
            text=vendas_diarias['item_valortotal'].apply(lambda v: f"R$ {v:,.0f}"),
            color_discrete_sequence=['steelblue']
        )
        fig_diario.update_traces(
            textposition="outside",
            cliponaxis=False,
            marker_line_color='steelblue',
            marker_line_width=1
        )
        fig_diario.update_layout(
            height=150,
            margin=dict(t=32, b=10, l=25, r=5),
            showlegend=False,
            xaxis=dict(title="", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10)),
            title=dict(text="VENDAS POR DIA", x=0, font=dict(size=14))
        )
        st.plotly_chart(fig_diario, use_container_width=True)
    else:
        st.info("Sem dados de vendas para o mês atual.")


def _render_series_mensais(dados_vendedor):
    """Renderiza os gráficos de série mensal"""
    df_series = dados_vendedor['series_mensais']
    
    if df_series.empty:
        st.warning("Sem dados históricos para o período selecionado.")
        return
    
    css_pills_vendedores()
    
    # Configuração dos grupos de métricas
    col_groups = [
        [
            ('venda_acumulada', 'Venda Total (R$)', 'moeda'),
            ('num_vitaminas', 'Vitaminas Vendidas', 'int')
        ],
        [
            ('num_vendas', 'Nº Vendas', 'int'),
            ('taxa_conversao_vitaminas', 'Taxa Conversão', 'num1')
        ],
        [
            ('ticket_medio', 'Ticket Médio (R$)', 'moeda'),
            ('vendas_identificadas_perc', 'Vendas Identificadas (%)', 'perc1')
        ]
    ]
    
    # Estado de destaque
    highlight_key = "vendedores_ind_highlight_col_duck"
    if highlight_key not in st.session_state:
        st.session_state[highlight_key] = None
    
    # Definir larguras condicionais
    if st.session_state[highlight_key] is None:
        widths = [1, 1, 1]
    else:
        h = st.session_state[highlight_key]
        widths = [2 if i == h else 1 for i in range(3)]
    
    st.caption(f"Período: últimos {len(df_series)} meses (inclui mês atual parcial).")
    
    # Renderização das três colunas
    cols_top = st.columns(widths, gap="small")
    cols_bottom = st.columns(widths, gap="small")
    
    for col_idx, group in enumerate(col_groups):
        expanded = (st.session_state[highlight_key] == col_idx)
        col_color = ['#2563eb', '#0d9488', "#723C47"][col_idx % 3]
        altura_chart = 260 if expanded else 180
        
        with cols_top[col_idx]:
            # Botão de expansão
            pill_class = "pill-btn active" if expanded else "pill-btn"
            st.markdown(f"<div class='{pill_class}' style='display:flex; justify-content:flex-end;'>", unsafe_allow_html=True)
            btn_label = "✖" if expanded else "🔍"
            btn_help = "Fechar destaque" if expanded else "Ampliar"
            if st.button(btn_label, key=f"highlight_toggle_duck_{col_idx}", help=btn_help):
                st.session_state[highlight_key] = None if expanded else col_idx
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Primeiro gráfico
            y1, title1, fmt1 = group[0]
            st.markdown(f"**{title1}**")
            fig1 = render_bar(df_series, y1, fmt1, col_color, altura_chart)
            st.plotly_chart(fig1, use_container_width=True)
        
        with cols_bottom[col_idx]:
            y2, title2, fmt2 = group[1]
            st.markdown(f"**{title2}**")
            fig2 = render_bar(df_series, y2, fmt2, col_color, altura_chart)
            st.plotly_chart(fig2, use_container_width=True)


def _render_visao_comparativa(filial_selecionada, vendedor_selecionado):
    """Renderiza a visão comparativa dos vendedores"""
    data_ref = date.today() - timedelta(days=1)
    
    # Calcular KPIs
    kpis = calcular_kpis_vendedores_comparativo_duck(
        filial_selecionada, 
        [vendedor_selecionado], 
        data_ref
    )
    
    # Renderizar cards em duas linhas
    _render_cards_comparativo_linha1(kpis, filial_selecionada, vendedor_selecionado, data_ref)
    _render_cards_comparativo_linha2(kpis, filial_selecionada, vendedor_selecionado, data_ref)


def _render_cards_comparativo_linha1(kpis, filial_selecionada, vendedor_selecionado, data_ref):
    """Renderiza a primeira linha de cards da visão comparativa"""
    col1, col2, col3, col4 = st.columns(4, gap='small')
    
    with col1:
        label = f"💰 VENDA ACUMULADA\n\n{formatar_moeda(kpis['venda_acumulada'])}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            criar_conteudo_popover_vendas_vendedores_duck(
                None, 
                filial_selecionada,
                top_n=10
            )
        
    with col2:
        label = f"🛒 NÚMERO DE VENDAS\n\n{formatar_numero(kpis['num_vendas'])}"
        with st.popover(label=label, use_container_width=True):
            criar_conteudo_popover_num_vendas_vendedores_duck(
                None,
                filial_selecionada,
                top_n=10                    
            )
    
    with col3:
        label = f"🎯 TICKET MÉDIO\n\n{formatar_moeda(kpis['ticket_medio'])}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            criar_conteudo_popover_ticket_vendedores_duck(
                filial_selecionada,
                [vendedor_selecionado],
                top_n=10,
                data_ref=data_ref
            )
    
    with col4:
        label = f"📦 ITENS POR NOTA\n\n{formatar_numero_uma_casa(kpis['itens_por_nota'])}"
        with st.popover(label=label, use_container_width=True):
            criar_conteudo_popover_itens_vendedores_duck(
                filial_selecionada,
                [vendedor_selecionado],
                top_n=10,
                data_ref=data_ref
            )


def _render_cards_comparativo_linha2(kpis, filial_selecionada, vendedor_selecionado, data_ref):
    """Renderiza a segunda linha de cards da visão comparativa"""
    col5, col6, col7, col8 = st.columns(4, gap='small')
    
    with col5:
        label = f"💊 VITAMINAS VENDIDAS\n\n{formatar_numero(kpis['num_vitaminas'])}"
        with st.popover(label=label, use_container_width=True):
            criar_conteudo_popover_vitaminas_vendedores_duck(
                filial_selecionada,
                [vendedor_selecionado],
                top_n=10,
                data_ref=data_ref
            )
    
    with col6:
        label = f"🔄 TAXA DE CONVERSÃO\n\n{formatar_numero_uma_casa(kpis['taxa_conversao_vitaminas'])}"
        with st.popover(label=label, use_container_width=True):
            criar_conteudo_popover_taxa_conversao_vendedores_duck(
                filial_selecionada,
                [vendedor_selecionado],
                top_n=10,
                data_ref=data_ref
            )

    with col7:
        label = f"🆔 VENDAS IDENTIF.\n\n{formatar_percentual(kpis['vendas_identificadas_perc'])}"
        with st.popover(label=label, use_container_width=True):
            criar_conteudo_popover_vendas_identificadas_vendedores_duck(
                filial_selecionada,
                [vendedor_selecionado],
                top_n=10,
                data_ref=data_ref
            )

    with col8:
        label = f"💸 DESCONTO\n\n{formatar_percentual(kpis['desconto_medio'])}"
        with st.popover(label=label, use_container_width=True):
            st.info("🚧 Em desenvolvimento")


if __name__ == "__main__":
    main()