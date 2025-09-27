"""
Componentes de gráficos específicos para análise de promoções
"""
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from data_processing.promocoes.calculations import preparar_dados_visualizacao

def render_card_comparativo_vendas(fora: float, durante: float, variacao: float, 
                                 titulo: str, colors: list):
    """
    Renderiza um card comparativo com barras horizontais (FORA vs DURANTE)
    
    Args:
        fora: Valor do período fora da promoção
        durante: Valor do período durante a promoção
        variacao: Variação percentual
        titulo: Título do card
        colors: Lista com 2 cores [fora, durante]
    """
    max_x = max(fora, durante, 1) * 1.12
    
    fig, ax = plt.subplots(figsize=(3.2, 0.75))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('none')
    ax.patch.set_visible(False)
    
    # Barras horizontais
    y_pos = [0.65, 0.25]
    values = [fora, durante]
    bars = ax.barh(y_pos, values, color=colors, height=0.3, zorder=2)
    ax.set_xlim(0, max_x)
    ax.set_ylim(0, 0.9)
    
    # Título
    ax.text(0, 1.05, titulo, transform=ax.transAxes,
            fontsize=9, fontweight='600', color='#555', va='center')
    
    # Labels das barras
    ax.set_yticks(y_pos)
    ax.set_yticklabels(['FORA', 'DURANTE'], fontsize=7, fontweight='500', color='#666')
    ax.invert_yaxis()
    
    # Remover eixos desnecessários
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.xaxis.set_visible(False)
    
    # Valores nas barras
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_x * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"R$ {val:,.0f}",
                va='center', fontsize=7, fontweight='500', color='#333')
    
    plt.tight_layout(pad=0.2)
    
    # Variação colorida
    color_val = "#107427" if variacao >= 0 else "#cf2828"
    ax.text(0.01, -0.02, "Variação:", transform=ax.transAxes,
            fontsize=8, color='#6c757d', va='top', ha='left')
    ax.text(0.2, -0.02, f"{variacao:+.1f}%", transform=ax.transAxes,
            fontsize=8, color=color_val, va='top', ha='left', fontweight='600')
    
    fig.subplots_adjust(bottom=0.20, top=0.92, left=0.08, right=0.98)
    st.pyplot(fig, clear_figure=True)


def render_graficos_timeline_promocoes(vendas_por_periodo: dict, data_inicio_promo, 
                                     data_fim_promo, dias_promocao: int):
    """
    Renderiza os 3 gráficos de timeline (Vendas, Unidades, Resultado)
    """
    dados_viz = preparar_dados_visualizacao(vendas_por_periodo, data_inicio_promo, 
                                          data_fim_promo, dias_promocao)
    
    if not dados_viz:
        st.warning("⚠️ Nenhum dado disponível para gráficos.")
        return
    
    col_graf1, col_graf2, col_graf3 = st.columns(3)
    
    # Gráfico 1: Vendas (R$)
    with col_graf1:
        _render_grafico_barras(
            labels=dados_viz['labels'],
            valores=dados_viz['valores'],
            periodos=dados_viz['periodos_com_dados'],
            titulo="**Vendas (R$)**",
            cores_base=["#f070ba", "#b81e72"],
            formato=lambda x: f'R$ {x:,.0f}'
        )
    
    # Gráfico 2: Unidades Vendidas
    with col_graf2:
        _render_grafico_barras(
            labels=dados_viz['labels'],
            valores=dados_viz['quantidades'],
            periodos=dados_viz['periodos_com_dados'],
            titulo="**Unidades Vendidas**",
            cores_base=["#0ab993", "#056d5c"],
            formato=lambda x: f'{int(x)}'
        )
    
    # Gráfico 3: Resultado (R$)
    with col_graf3:
        _render_grafico_barras(
            labels=dados_viz['labels'],
            valores=dados_viz['resultados'],
            periodos=dados_viz['periodos_com_dados'],
            titulo="**Resultado (R$)**",
            cores_base=["#d9e669", "#53920b"],
            formato=lambda x: f'R$ {x:,.2f}'
        )


def _render_grafico_barras(labels: list, valores: list, periodos: list, titulo: str, 
                          cores_base: list, formato):
    """Renderiza um gráfico de barras individual"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Definir cores (destaque para período de promoção)
    cores = [cores_base[1] if periodo == 'Promoção' else cores_base[0] for periodo in periodos]
    
    # Criar barras
    bars = ax.bar(labels, valores, color=cores)
    
    # Remover bordas desnecessárias
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.yaxis.set_visible(False)
    
    # Rotacionar labels
    ax.set_xticklabels(labels, rotation=45, ha='right')
    
    # Adicionar valores nas barras
    for bar, valor in zip(bars, valores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + abs(height)*0.01, 
               formato(valor), ha='center', va='bottom')
    
    st.write(titulo)
    st.pyplot(fig)