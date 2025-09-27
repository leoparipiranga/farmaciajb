
import streamlit as st
import pandas as pd
from datetime import timedelta, date
import numpy as np
import plotly.graph_objects as go

# Imports da nova estrutura
from visualizations.styling.css_components import aplicar_css_header
from data_processing.estoque.calculations import (
    calcular_disponibilidade_duck,
    calcular_giro_geral_e_combinacoes_duck,
    calcular_fator_cobertura_duck
)
from business_logic.estoque.gmroi import (
    calcular_gmroi_baseado_vendas_duck
                                          )
from visualizations.charts.gauges import (
    criar_gauge_disponibilidade_unico_duck,
    criar_gauge_giro_unico_duck,
    criar_gauge_fator_cobertura_duck,
    criar_gauge_curvad,
    criar_gauge_desfazimento_curvad,
    criar_gauge_dias_venda,
    criar_gauge_dias_venda_apos_30d,
    criar_gauge_gmroi_geral,
    criar_gauge_gmroi_vendas_geral
)
from interfaces.estoque_interface import render_interface_indicadores_estoque
from visualizations.components.cards import render_kpi_card_estoque

# Aplicar CSS global
aplicar_css_header()

def render_tab_ruptura_duck(data_ontem):
    """Renderiza a aba de Análise de Ruptura e Giro usando DuckDB."""
        
    st.caption(f"Análise baseada em movimentações até {data_ontem.strftime('%d/%m/%Y')}")
    
    # Buscar dados
    df_todas_combinacoes = calcular_disponibilidade_duck(data_ontem)
    df_todos_giros, kpis_giro = calcular_giro_geral_e_combinacoes_duck(data_ontem)
    df_cobertura = calcular_fator_cobertura_duck(data_ontem)
    df_gmroi_geral = calcular_gmroi_baseado_vendas_duck(data_ontem, periodo_vendas=360)
    df_gmroi_vendas = calcular_gmroi_baseado_vendas_duck(data_ontem, periodo_vendas=90)
    
    cols_gauge = st.columns(7)

    # Gauges principais
    with cols_gauge[0]:
        fig_disp = criar_gauge_disponibilidade_unico_duck(df_todas_combinacoes, meta=94)
        st.plotly_chart(fig_disp, use_container_width=False)

    with cols_gauge[1]:
        fig_giro = criar_gauge_giro_unico_duck(df_todos_giros, meta=70)
        st.plotly_chart(fig_giro, use_container_width=False)

    with cols_gauge[2]:
        fig_cov = criar_gauge_fator_cobertura_duck(df_cobertura)
        st.plotly_chart(fig_cov, use_container_width=False)
    
    with cols_gauge[3]:
        fig_cov = criar_gauge_gmroi_geral(df_gmroi_geral, meta=1)
        st.plotly_chart(fig_cov, use_container_width=False)
    
    with cols_gauge[4]:
        fig_cov = criar_gauge_gmroi_vendas_geral(df_gmroi_vendas, meta=1)
        st.plotly_chart(fig_cov, use_container_width=False)
    
    with cols_gauge[5]:
        fig_curva_d = criar_gauge_curvad(meta=6)
        st.plotly_chart(fig_curva_d, use_container_width=False)


    with cols_gauge[6]:
        fig_desf = criar_gauge_desfazimento_curvad(meta=4)
        st.plotly_chart(fig_desf, use_container_width=False)
    
    # KPI Cards usando componente reutilizável
    cols_cards = st.columns(6)

    total = kpis_giro.get('total_cmv', 0)
    total90 = kpis_giro.get('total_cmv_90d', 0)
    cmv_giro = kpis_giro.get('total_cmv_giro', 0)
    perc = (cmv_giro / total * 100) if total > 0 else 0
    cmv_giro_90d = kpis_giro.get('total_cmv_90d_giro', 0)
    perc90 = kpis_giro.get('perc_giro_90d', 0)
    cmv_sem_giro = total - cmv_giro
    perc_sem_giro = (cmv_sem_giro / total * 100) if total > 0 else 0
    cmv_sem_giro_90d = kpis_giro.get('total_cmv_90d_sem_giro', 0)
    perc_sem_giro_90d = 100.0 - perc90

    with cols_cards[0]:
        render_kpi_card_estoque("Estoque Total", f"R$ {total:,.0f}")
    with cols_cards[1]:
        render_kpi_card_estoque("Estoque com Giro", f"R$ {cmv_giro:,.0f}", subtitle=f"{perc:.1f}%")
    with cols_cards[2]:
        render_kpi_card_estoque("Estoque sem Giro", f"R$ {cmv_sem_giro:,.0f}", 
                               subtitle=f"{perc_sem_giro:.1f}%")
    with cols_cards[3]:
        render_kpi_card_estoque("Estoque 90d", f"R$ {total90:,.0f}", variant="brown")
    with cols_cards[4]:
        render_kpi_card_estoque("Estoque com Giro 90d", f"R$ {cmv_giro_90d:,.0f}", 
                               subtitle=f"{perc90:.1f}%", variant="brown")
    with cols_cards[5]:
        render_kpi_card_estoque("Estoque sem Giro 90d", f"R$ {cmv_sem_giro_90d:,.0f}", 
                               subtitle=f"{perc_sem_giro_90d:.1f}%", variant="brown")


    # Interface de indicadores
    render_interface_indicadores_estoque(data_ontem)
    

def main():
    """Função principal do módulo de estoque."""
    # Usar data atual como padrão
    data_ontem = date.today() - timedelta(days=1)
    render_tab_ruptura_duck(data_ontem)


if __name__ == "__main__":
    main()