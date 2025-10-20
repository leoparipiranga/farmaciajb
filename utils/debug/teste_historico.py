import streamlit as st
import pandas as pd
from data_processing.estoque.historico import build_or_update_hist_disponibilidade, load_hist_disponibilidade
from visualizations.charts.historico_charts import criar_grafico_disponibilidade_historico

st.set_page_config(page_title="Histórico Disponibilidade (Teste)", layout="wide")

st.title("Histórico - Disponibilidade de Estoque (Teste)")

col1, col2 = st.columns(2)
with col1:
    if st.button("Atualizar / Construir Histórico"):
        hist = build_or_update_hist_disponibilidade()
        st.success(f"Histórico carregado: {len(hist)} linhas.")
with col2:
    include_current = st.checkbox("Incluir mês corrente (parcial)", value=False)

hist = load_hist_disponibilidade(include_current_partial=include_current)
if hist.empty:
    st.warning("Histórico vazio. Clique em 'Atualizar / Construir Histórico'.")
    st.stop()

# Normalizar valores 'Geral' ausentes
for col in ["filial_codigo", "curvaABC", "classificacao_n1", "classificacao_n2"]:
    if col in hist.columns:
        hist[col] = hist[col].fillna("Geral")

# Identificar coluna de métrica (ajuste conforme schema real)
# Supondo que calcular_disponibilidade_duck retorna coluna 'disponibilidade' (%)
metric_col = None
for candidate in ["disponibilidade", "disponibilidade_percent", "perc_disponibilidade"]:
    if candidate in hist.columns:
        metric_col = candidate
        break
if metric_col is None:
    st.error("Coluna de métrica de disponibilidade não encontrada.")
    st.dataframe(hist.head())
    st.stop()

filiais = ["Geral"] + sorted([f for f in hist["filial_codigo"].unique() if f != "Geral"])
curvas = ["Geral"] + sorted([c for c in hist["curvaABC"].unique() if c not in ("Geral", None)])
class_n1 = ["Geral"] + sorted([c for c in hist["classificacao_n1"].unique() if c not in ("Geral", None)])
class_n2 = ["Geral"] + sorted([c for c in hist["classificacao_n2"].unique() if c not in ("Geral", None)])

fcol1, fcol2, fcol3, fcol4 = st.columns(4)
with fcol1:
    filial_sel = st.selectbox("Filial", filiais)
with fcol2:
    curva_sel = st.selectbox("Curva ABC", curvas)
with fcol3:
    n1_sel = st.selectbox("Classificação N1", class_n1)
with fcol4:
    n2_sel = st.selectbox("Classificação N2", class_n2)

df = hist.copy()
if filial_sel != "Geral":
    df = df[df.filial_codigo == filial_sel]
if curva_sel != "Geral":
    df = df[df.curvaABC == curva_sel]
if n1_sel != "Geral":
    df = df[df.classificacao_n1 == n1_sel]
if n2_sel != "Geral":
    df = df[df.classificacao_n2 == n2_sel]

if df.empty:
    st.warning("Sem dados para os filtros.")
    st.stop()

# Agregar (se múltiplas linhas por mês devido a dimensões detalhadas)
agg = df.groupby("ano_mes", as_index=False)[metric_col].mean()

st.subheader("Evolução Mensal")
import plotly.express as px
agg_sorted = agg.sort_values("ano_mes")
try:

    try:
        # tenta chamada positional (se a função aceitar df, metric_col)
        fig = criar_grafico_disponibilidade_historico(agg_sorted, metric_col)
    except TypeError:
        # tenta chamada por kwargs (se a função usar outros nomes)
        fig = criar_grafico_disponibilidade_historico(df=agg_sorted, metric_col=metric_col)
except Exception:
    import plotly.express as px
    fig = px.line(agg_sorted, x="ano_mes", y=metric_col, markers=True, title="Disponibilidade Mensal")
    fig.update_layout(xaxis_title="Mês", yaxis_title="Disponibilidade")

st.plotly_chart(fig, use_container_width=True)

st.dataframe(agg.sort_values("ano_mes"), use_container_width=True)