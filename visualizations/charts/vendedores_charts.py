"""
Componentes de gráficos específicos para análise de vendedores
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def render_heatmap_vendedores(df_data: pd.DataFrame, titulo: str, valor_col: str, top_names: list, 
                             periodo_type: str = "horas") -> None:
    """
    Renderiza heatmap padrão para vendedores (usado em vários popovers)
    
    Args:
        df_data: DataFrame com dados para heatmap
        titulo: Título do gráfico
        valor_col: Nome da coluna com valores
        top_names: Lista de nomes dos vendedores
        periodo_type: "horas" ou "dias"
    """
    if periodo_type == "horas":
        x_labels = list(range(7, 23))
        x_title = "Hora do dia"
    else:  # dias
        x_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        x_title = "Dia da semana"
    
    # Preparar matrizes
    z_norm = df_data.values.astype(float)
    raw_vals = np.array(df_data.values, dtype=float)
    z_main = np.where(raw_vals > 0, z_norm, np.nan)
    z_zero = np.where(raw_vals == 0, 1.0, np.nan)
    
    altura = max(300, min(750, 22 * len(df_data.index) + 140))
    
    fig = go.Figure()
    # Heatmap principal
    fig.add_trace(go.Heatmap(
        z=z_main, x=x_labels, y=list(df_data.index),
        colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
        zmin=0, zmax=1, colorbar=dict(title="Baixo ↔ Alto"), 
        hoverongaps=False, showscale=True
    ))
    # Overlay para zeros
    fig.add_trace(go.Heatmap(
        z=z_zero, x=x_labels, y=list(df_data.index),
        colorscale=[[0, "lightgray"], [1, "gray"]], 
        zmin=0, zmax=1, showscale=False, hoverongaps=False
    ))
    
    # Customdata para hover
    fig.data[0].customdata = raw_vals[..., np.newaxis]
    fig.data[0].hovertemplate = f"Linha: %{{y}}<br>{x_title}: %{{x}}<br>{titulo}: %{{customdata[0]:.2f}}<extra></extra>"
    fig.data[1].customdata = raw_vals[..., np.newaxis]
    fig.data[1].hovertemplate = f"Linha: %{{y}}<br>{x_title}: %{{x}}<br>{titulo}: %{{customdata[0]:.2f}}<extra></extra>"
    
    fig.update_layout(
        height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
        xaxis_title=x_title, yaxis=dict(
            title="", tickfont=dict(size=10), autorange='reversed',
            categoryorder='array', categoryarray=top_names
        )
    )
    fig.update_traces(xgap=1, ygap=2)
    if periodo_type == "dias":
        fig.update_xaxes(side="top")
    
    st.plotly_chart(fig, use_container_width=True)

def render_bar_chart_vendedores(df_data: pd.DataFrame, x_col: str, y_col: str, titulo: str, 
                               cor: str = "darkslateblue", formato_texto: str = ".2s",
                               scatter_data: pd.DataFrame = None, scatter_col: str = None) -> None:
    """
    Renderiza gráfico de barras padrão para vendedores com opção de scatter overlay
    """
    fig = px.bar(df_data, x=x_col, y=y_col, orientation='h', text_auto=formato_texto)
    fig.update_traces(marker_color=cor, textangle=0, textposition="inside", 
                     textfont=dict(color='white', size=10))
    
    # Adicionar scatter se fornecido
    if scatter_data is not None and scatter_col is not None:
        fig.add_trace(go.Scatter(
            x=scatter_data[scatter_col], y=scatter_data[y_col], mode='markers',
            marker=dict(symbol='line-ns', size=12, color='black', 
                       line=dict(width=2, color='orange')),
            name='Média 90d', showlegend=True,
            hovertemplate=f"Vendedor: %{{y}}<br>Média 90d: %{{x{formato_texto}}}<extra></extra>"
        ))
    
    fig.update_layout(
        height=max(300, min(800, 28 * len(df_data) + 120)),
        showlegend=False, template="plotly_white",
        margin=dict(t=20, b=20, l=30, r=30),
        xaxis=dict(title=titulo, tickfont=dict(size=10)),
        yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
        bargap=0.35
    )
    st.plotly_chart(fig, use_container_width=True)