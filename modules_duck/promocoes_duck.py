import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Imports da nova estrutura
from data_processing.promocoes.queries import (
    get_promocoes_periodo_duck,
    get_vendas_promocao_duck,
    get_filiais_promocao_duck,
    get_classificacoes_promocao_duck,
    get_top_produtos_promocao_duck,
    calcular_vendas_por_periodo_duck,
        
)
from data_processing.promocoes.calculations import (
    calcular_metricas_promocao,
    calcular_totais_loja_durante_fora_duck,
    calcular_totais_loja_qtd_durante_fora_duck,
    preparar_dados_visualizacao
)
from visualizations.charts.promocoes_charts import (
    render_card_comparativo_vendas,
    render_graficos_timeline_promocoes
)
from utils.formatters import formatar_moeda


def main():
    """Função principal do módulo de promoções"""
    st.subheader("Análise de Impacto das Promoções")
    
    # Seção 1: Filtros de período e seleção
    _render_filtros_periodo()
    

def _render_filtros_periodo():
    """Renderiza os filtros de período e seleção de promoções"""
    st.markdown("##### Filtro de Período para Promoções")
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        filtro_data_inicio = st.date_input(
            "Data inicial do filtro:", 
            value=datetime.today() - timedelta(days=30)
        )
    
    with col_filtro2:
        filtro_data_fim = st.date_input(
            "Data final do filtro:", 
            value=datetime.today() + timedelta(days=30)
        )
    
    # Carregar promoções do período
    caderno_filtrado = get_promocoes_periodo_duck(
        filtro_data_inicio.strftime('%Y-%m-%d'),
        filtro_data_fim.strftime('%Y-%m-%d')
    )
    
    if caderno_filtrado.empty:
        st.warning("⚠️ Nenhuma promoção encontrada no período selecionado.")
        return
    
    with col_filtro3:
        st.write("\n\n")
        st.write("\n\n")
        st.write(f"✅ {len(caderno_filtrado)} promoções encontradas no período")
    
    # Prosseguir com seleção de promoções
    _render_selecao_promocoes(caderno_filtrado)


def _render_selecao_promocoes(caderno_filtrado):
    """Renderiza a seleção de promoções e análise"""
    st.markdown("##### 1. Selecione uma ou mais Promoções")
    promocoes = caderno_filtrado['nome'].unique()
    selected_promocoes = st.multiselect(
        "Escolha as promoções:", 
        promocoes, 
        default=[],
        help="Selecione uma ou mais promoções para análise"
    )
    
    if not selected_promocoes:
        st.info("👆 Selecione uma ou mais promoções para continuar a análise.")
        return
    
    # Validar promoções selecionadas
    promocoes_info = caderno_filtrado[caderno_filtrado['nome'].isin(selected_promocoes)].copy()
    
    if promocoes_info['datahorainicial'].nunique() != 1 or promocoes_info['datahorafinal'].nunique() != 1:
        st.error("❌ Todas as promoções selecionadas devem ter a mesma data inicial e final.")
        return
    
    # Extrair dados das promoções
    data_inicio_promo = pd.to_datetime(promocoes_info['datahorainicial'].iloc[0]).date()
    data_fim_promo = pd.to_datetime(promocoes_info['datahorafinal'].iloc[0]).date()
    promocao_ids = promocoes_info['id'].tolist()
    dias_promocao = (data_fim_promo - data_inicio_promo).days + 1
    
    st.markdown(f"**Período da promoção:** {data_inicio_promo} a {data_fim_promo} ({dias_promocao} dias)")
    
    # Prosseguir com análise
    _render_analise_promocoes(promocao_ids, data_inicio_promo, data_fim_promo, dias_promocao, selected_promocoes)


def _render_analise_promocoes(promocao_ids, data_inicio_promo, data_fim_promo, dias_promocao, selected_promocoes):
    """Renderiza a análise completa das promoções"""
    # Buscar dados base
    vendas_durante_promo = get_vendas_promocao_duck(promocao_ids)
    
    if vendas_durante_promo.empty:
        st.warning("⚠️ Nenhuma venda encontrada para as promoções selecionadas.")
        return
    
    embalagens_promo = vendas_durante_promo['item_embalagemid'].unique().tolist()
    
    # Filtro por filial
    filiais_promocao = get_filiais_promocao_duck(promocao_ids)
    selected_filial = st.selectbox(
        "Filtrar por filial:", 
        ["Todas as Filiais"] + [str(f) for f in filiais_promocao]
    )
    
    # Status das promoções
    col_mens1, col_mens2 = st.columns(2)
    with col_mens1:
        st.success(f"✅ {len(selected_promocoes)} promoção(ões) selecionada(s)")
    with col_mens2:
        st.info(f"📦 {len(embalagens_promo)} produtos únicos encontrados na promoção")
    
    # Calcular dados para análise
    vendas_por_periodo = calcular_vendas_por_periodo_duck(
        embalagens_promo, 
        promocao_ids,
        data_inicio_promo.strftime('%Y-%m-%d'),
        data_fim_promo.strftime('%Y-%m-%d'),
        dias_promocao,
        selected_filial
    )
    
    if not vendas_por_periodo:
        st.warning("⚠️ Nenhuma venda encontrada para análise de período.")
        return
    
    # Calcular métricas consolidadas
    metricas = calcular_metricas_promocao(
        vendas_por_periodo,
        promocao_ids,
        data_inicio_promo,
        data_fim_promo,
        dias_promocao,
        selected_filial
    )
    
    if not metricas:
        st.warning("⚠️ Erro ao calcular métricas da promoção.")
        return
    
    # Renderizar resultados
    _render_resultados_promocao(metricas, vendas_por_periodo, data_inicio_promo, data_fim_promo, dias_promocao, promocao_ids)


def _render_resultados_promocao(metricas, vendas_por_periodo, data_inicio_promo, data_fim_promo, dias_promocao, promocao_ids):
    """Renderiza os resultados da análise de promoção"""
    graficos, tabela = st.tabs(["Resultado Geral", "Top Produtos da Promoção"])
    
    with graficos:
        # Títulos das seções
        col_parcial, col_total = st.columns(2)
        with col_parcial:
            st.markdown("##### Médias Diárias - Produtos em Promoção")
        with col_total:
            st.markdown("##### Médias Diárias - Toda a Loja")

        # Cards comparativos (4 cards)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_card_comparativo_vendas(
                fora=metricas['media_valor_sem_diaria'],
                durante=metricas['media_valor_promocao'],
                variacao=metricas['variacao_valor_parcial'],
                titulo="Vendas (R$)",
                colors=["#636362", "#947E03"]
            )
        
        with col2:
            render_card_comparativo_vendas(
                fora=metricas['media_qtd_sem_diaria'],
                durante=metricas['media_qtd_promocao'],
                variacao=metricas['variacao_qtd_parcial'],
                titulo="Unidades Vendidas",
                colors=["#636362", "#947E03"]
            )
        
        with col3:
            render_card_comparativo_vendas(
                fora=metricas['media_valor_sem_diaria_total'],
                durante=metricas['media_valor_promocao_total'],
                variacao=metricas['variacao_valor_total'],
                titulo="Vendas Totais (R$)",
                colors=["#90a5e4", "#2c2a9e"]
            )
        
        with col4:
            render_card_comparativo_vendas(
                fora=metricas['media_qtd_sem_diaria_total'],
                durante=metricas['media_qtd_promocao_total'],
                variacao=metricas['variacao_qtd_total'],
                titulo="Unidades Vendidas",
                colors=["#90a5e4", "#2c2a9e"]
            )

        # Gráficos de timeline (3 gráficos)
        render_graficos_timeline_promocoes(
            vendas_por_periodo, 
            data_inicio_promo, 
            data_fim_promo, 
            dias_promocao
        )
    
    with tabela:
        _render_tabela_top_produtos(promocao_ids)


def _render_tabela_top_produtos(promocao_ids):
    """Renderiza a tabela de top produtos da promoção"""
    st.markdown("#### Top 10 Produtos Mais Vendidos da Promoção")
    
    # Filtro por classificação
    classificacoes = get_classificacoes_promocao_duck(promocao_ids)
    classificacao_detalhe = st.selectbox(
        "Filtrar por classificação N1:", 
        ["Todas"] + classificacoes, 
        key="class_detalhe"
    )
    
    # Buscar top produtos
    top_produtos = get_top_produtos_promocao_duck(promocao_ids, classificacao_detalhe, 10)
    
    if top_produtos.empty:
        st.warning("⚠️ Nenhum produto encontrado com os filtros selecionados.")
    else:
        st.markdown("**Top 10 - por Valor (R$)**")
        st.dataframe(
            top_produtos.sort_values('valor_total', ascending=False).head(10).copy(), 
            hide_index=True, 
            use_container_width=False
        )


if __name__ == "__main__":
    main()