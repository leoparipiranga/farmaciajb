"""
Componentes de gráficos de barras reutilizáveis
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def criar_grafico_disponibilidade_historico(df_hist, titulo="Disponibilidade Mensal"):
    """
    Gráfico histórico mensal de disponibilidade.
    Espera colunas:
        ano_mes (formato 'YYYY-MM') ou datetime em 'ano_mes'
        disponibilidade
    Opcionalmente pode trazer outras colunas; serão ignoradas.
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title_text=f'{titulo} (Sem dados)')

    df = df_hist.copy()

    # Normaliza ano_mes -> label 'MM-YYYY'
    if not pd.api.types.is_datetime64_any_dtype(df['ano_mes']):
        # Se vier 'YYYY-MM' ou 'YYYY-MM-DD'
        df['ano_mes'] = pd.to_datetime(df['ano_mes'].astype(str).str[:7] + "-01", errors='coerce')
    df = df.dropna(subset=['ano_mes'])
    if df.empty:
        return go.Figure().update_layout(title_text=f'{titulo} (Sem dados)')

    df['mes_label'] = df['ano_mes'].dt.strftime("%m-%Y")
    df = df.sort_values('ano_mes')

    # Garante coluna disponibilidade_percent numérica
    df['disponibilidade_percent'] = pd.to_numeric(df['disponibilidade_percent'], errors='coerce')
    df = df.dropna(subset=['disponibilidade_percent'])
    if df.empty:
        return go.Figure().update_layout(title_text=f'{titulo} (Sem dados)')

    max_val = df['disponibilidade_percent'].max()
    if max_val <= 0:
        max_val = 1.0  # evita threshold 0

    # Cores (>=92 bom)
    bar_colors = ['DeepSkyBlue' if v >= 92 else 'CadetBlue' for v in df['disponibilidade_percent']]

    threshold = max_val * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['disponibilidade_percent']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['mes_label'],
        y=df['disponibilidade_percent'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))

    fig.update_layout(
        title_text=titulo,
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=800,
        height=280,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, automargin=True),
        margin=dict(t=30, b=40, l=10, r=10),
        bargap=0.15,
        autosize=True
    )
    return fig

def criar_grafico_giro_historico(df_hist: pd.DataFrame, titulo="Giro de Estoque (%)"):
    """
    Aceita DataFrame já agregado (1 linha por ano_mes) ou detalhado.
    Se detalhado (múltiplas linhas por ano_mes), agrega automaticamente.
    Necessita colunas:
      - ano_mes
      - (total_valor_estoque, valor_estoque_com_giro) ou giro_percent já calculado
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title=titulo + " (Sem dados)")

    df = df_hist.copy()

    # Normaliza ano_mes
    df["ano_mes"] = df["ano_mes"].astype(str).str[:7]

    if "giro_percent" not in df.columns:
        # tentar agregar pelas colunas de valor
        required = {"total_valor_estoque", "valor_estoque_com_giro"}
        if required.issubset(df.columns):
            agg = (
                df.groupby("ano_mes", as_index=False)
                  .agg(
                      total_valor_estoque=("total_valor_estoque", "sum"),
                      valor_estoque_com_giro=("valor_estoque_com_giro", "sum")
                  )
            )
            agg["giro_percent"] = (
                (agg["valor_estoque_com_giro"] * 100.0 / agg["total_valor_estoque"])
                .where(agg["total_valor_estoque"] > 0, 0)
                .round(2)
            )
            df = agg
        else:
            # não há como calcular
            return go.Figure().update_layout(title=titulo + " (Dados insuficientes)")

    df = df.sort_values("ano_mes")
    cores = ["DeepSkyBlue" if v >= 72 else "CadetBlue" for v in df["giro_percent"]]
    threshold = max(df["giro_percent"].max(), 1) * 0.4
    text_pos = ["inside" if v >= threshold else "outside" for v in df["giro_percent"]]
    text_colors = ["white" if p == "inside" else "darkgrey" for p in text_pos]

    fig = go.Figure(go.Bar(
        x=df["ano_mes"].str[5:7] + "-" + df["ano_mes"].str[:4],  # MM-YYYY
        y=df["giro_percent"],
        marker_color=cores,
        texttemplate="%{y:.2f}%",
        textposition=text_pos,
        textfont_color=text_colors,
        textfont_size=12,
        cliponaxis=False
    ))

    fig.update_layout(
        title=titulo,
        title_x=0,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False),
        margin=dict(t=30, l=10, r=10, b=40),
        bargap=0.15,
        height=280
    )
    return fig


def criar_grafico_cobertura_historico(df_hist: pd.DataFrame, titulo="Fator de Cobertura (%)"):
    """
    Aceita DataFrame já agregado (1 linha por ano_mes) ou detalhado.
    Se detalhado (múltiplas linhas por ano_mes), agrega automaticamente.
    Necessita colunas:
      - ano_mes
      - "stock_cmv" / "cmv_vendido_30d" = "cobertura_ratio"
      
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title=titulo + " (Sem dados)")

    df = df_hist.copy()

    # Normaliza ano_mes
    df["ano_mes"] = df["ano_mes"].astype(str).str[:7]

    if "cobertura_ratio" not in df.columns:
        # tentar agregar pelas colunas de valor
        required = {"stock_cmv", "cmv_vendido_30d"}
        if required.issubset(df.columns):
            agg = (
                df.groupby("ano_mes", as_index=False)
                  .agg(
                      stock_cmv=("stock_cmv", "sum"),
                      cmv_vendido_30d=("cmv_vendido_30d", "sum")
                  )
            )
            agg["cobertura_ratio"] = (
                (agg["stock_cmv"] / agg["cmv_vendido_30d"])
                .where(agg["cmv_vendido_30d"] > 0, 0)
                .round(2)
            )
            df = agg
        else:
            # não há como calcular
            return go.Figure().update_layout(title=titulo + " (Dados insuficientes)")

    df = df.sort_values("ano_mes")
    cores = ["DeepSkyBlue" if v >= 2 else "CadetBlue" for v in df["cobertura_ratio"]]
    
    threshold = max(df["cobertura_ratio"].max(), 1) * 0.4
    text_pos = ["inside" if v >= threshold else "outside" for v in df["cobertura_ratio"]]
    text_colors = ["white" if p == "inside" else "darkgrey" for p in text_pos]

    fig = go.Figure(go.Bar(
        x=df["ano_mes"].str[5:7] + "-" + df["ano_mes"].str[:4],  # MM-YYYY
        y=df["cobertura_ratio"],
        marker_color=cores,
        texttemplate="%{y:.2f}",
        textposition=text_pos,
        textfont_color=text_colors,
        textfont_size=12,
        cliponaxis=False
    ))

    fig.update_layout(
        title=titulo,
        title_x=0,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False),
        margin=dict(t=30, l=10, r=10, b=40),
        bargap=0.15,
        height=280
    )
    return fig

def criar_grafico_gmroi_historico(df_hist: pd.DataFrame, titulo="Retorno da Margem Bruta - GMROI (%)"):
    """
    Aceita DataFrame já agregado (1 linha por ano_mes) ou detalhado.
    Se detalhado (múltiplas linhas por ano_mes), agrega automaticamente.
    Necessita colunas:
      - ano_mes
      - "margem_bruta_vendas" / "valor_medio_estoque" = "gmroi_ratio"
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title=titulo + " (Sem dados)")

    df = df_hist.copy()

    # Normaliza ano_mes
    df["ano_mes"] = df["ano_mes"].astype(str).str[:7]

    if "gmroi_ratio" not in df.columns:
        # tentar agregar pelas colunas de valor
        required = {"margem_bruta_vendas", "valor_medio_estoque"}
        if required.issubset(df.columns):
            agg = (
                df.groupby("ano_mes", as_index=False)
                  .agg(
                      margem_bruta_vendas=("margem_bruta_vendas", "sum"),
                      valor_medio_estoque=("valor_medio_estoque", "sum")
                  )
            )
            agg["gmroi_ratio"] = (
                (agg["margem_bruta_vendas"] / agg["valor_medio_estoque"])
                .where(agg["valor_medio_estoque"] > 0, 0)
                .round(2)
            )
            df = agg
        else:
            # não há como calcular
            return go.Figure().update_layout(title=titulo + " (Dados insuficientes)")

    df = df.sort_values("ano_mes")
    cores = ["DeepSkyBlue" if v >= 0.6 else "CadetBlue" for v in df["gmroi_ratio"]]

    threshold = max(df["gmroi_ratio"].max(), 1) * 0.4
    text_pos = ["inside" if v >= threshold else "outside" for v in df["gmroi_ratio"]]
    text_colors = ["white" if p == "inside" else "darkgrey" for p in text_pos]

    fig = go.Figure(go.Bar(
        x=df["ano_mes"].str[5:7] + "-" + df["ano_mes"].str[:4],  # MM-YYYY
        y=df["gmroi_ratio"],
        marker_color=cores,
        texttemplate="%{y:.2f}",
        textposition=text_pos,
        textfont_color=text_colors,
        textfont_size=12,
        cliponaxis=False
    ))

    fig.update_layout(
        title=titulo,
        title_x=0,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False),
        margin=dict(t=30, l=10, r=10, b=40),
        bargap=0.15,
        height=280
    )
    return fig

def criar_grafico_curvad_historico(df_hist: pd.DataFrame, titulo="Conversão para Curva D (%)"):
    """
    Aceita DataFrame já agregado (1 linha por ano_mes) ou detalhado.
    Se detalhado (múltiplas linhas por ano_mes), agrega automaticamente.
    Necessita colunas:
      - ano_mes
      - "total_val_all","total_val_curva_d","indice_curva_d"
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title=titulo + " (Sem dados)")

    df = df_hist.copy()

    # Normaliza ano_mes
    df["ano_mes"] = df["ano_mes"].astype(str).str[:7]

    if "indice_curva_d" not in df.columns:
        # não há como calcular
        return go.Figure().update_layout(title=titulo + " (Dados insuficientes)")

    df = df.sort_values("ano_mes")
    cores = ["DeepSkyBlue" if v <= 8 else "CadetBlue" for v in df["indice_curva_d"]]

    threshold = max(df["indice_curva_d"].max(), 1) * 0.4
    text_pos = ["inside" if v <= threshold else "outside" for v in df["indice_curva_d"]]
    text_colors = ["white" if p == "inside" else "darkgrey" for p in text_pos]

    fig = go.Figure(go.Bar(
        x=df["ano_mes"].str[5:7] + "-" + df["ano_mes"].str[:4],  # MM-YYYY
        y=df["indice_curva_d"],
        marker_color=cores,
        texttemplate="%{y:.2f}%",
        textposition=text_pos,
        textfont_color=text_colors,
        textfont_size=12,
        cliponaxis=False
    ))

    fig.update_layout(
        title=titulo,
        title_x=0,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False),
        margin=dict(t=30, l=10, r=10, b=40),
        bargap=0.15,
        height=280
    )
    return fig

def criar_grafico_desfazimento_historico(df_hist: pd.DataFrame, titulo="Venda Curva D (30 dias) (%)"):
    """
    Aceita DataFrame já agregado (1 linha por ano_mes) ou detalhado.
    Se detalhado (múltiplas linhas por ano_mes), agrega automaticamente.
    Necessita colunas:
      - ano_mes
      - "total_denom","total_numer","indice_30d_pct"
    """
    if df_hist is None or df_hist.empty:
        return go.Figure().update_layout(title=titulo + " (Sem dados)")

    df = df_hist.copy()

    # Normaliza ano_mes
    df["ano_mes"] = df["ano_mes"].astype(str).str[:7]

    if "indice_30d_pct" not in df.columns:
        # não há como calcular
        return go.Figure().update_layout(title=titulo + " (Dados insuficientes)")

    df = df.sort_values("ano_mes")
    cores = ["DeepSkyBlue" if v >= 5 else "CadetBlue" for v in df["indice_30d_pct"]]

    threshold = max(df["indice_30d_pct"].max(), 1) * 0.4
    text_pos = ["inside" if v >= threshold else "outside" for v in df["indice_30d_pct"]]
    text_colors = ["white" if p == "inside" else "darkgrey" for p in text_pos]

    fig = go.Figure(go.Bar(
        x=df["ano_mes"].str[5:7] + "-" + df["ano_mes"].str[:4],  # MM-YYYY
        y=df["indice_30d_pct"],
        marker_color=cores,
        texttemplate="%{y:.2f}%",
        textposition=text_pos,
        textfont_color=text_colors,
        textfont_size=12,
        cliponaxis=False
    ))

    fig.update_layout(
        title=titulo,
        title_x=0,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False),
        margin=dict(t=30, l=10, r=10, b=40),
        bargap=0.15,
        height=280
    )
    return fig