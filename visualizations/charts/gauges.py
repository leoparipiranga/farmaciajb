"""
Componentes de gráficos gauge (medidor circular)
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from business_logic.estoque.curva_d import (
    calcular_indice_curva_d_geral,
    calcular_indice_desfazimento_curva_d
)
from business_logic.estoque.giro import (calcular_primeira_venda_geral
)

from utils.formatters import formatar_moeda, formatar_numero, formatar_numero_uma_casa


def criar_gauge_disponibilidade_unico_duck(df_ruptura, meta=94):
    """
    Cria gauge de disponibilidade baseado no DataFrame de ruptura.
    """
    if df_ruptura.empty:
        value = 0
    else:
        linha_geral = df_ruptura[
            (df_ruptura['filial_codigo'] == 'Geral')
        ]
        if not linha_geral.empty:
            value = linha_geral['disponibilidade_percent'].iloc[0]
        else:
            value = 0

    # Garantir que value é um número válido
    if pd.isna(value) or not isinstance(value, (int, float)): 
        value = 0
    value = round(float(value), 2)

    # cor da barra: verde se alcançou a meta, amarelo caso contrário
    bar_color = "DeepSkyBlue" if value >= meta else "CadetBlue"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        align="center",
        value=value,
        title={'text': "% Disponibilidade<br>de Estoque",
               'font': {'size': 12}, 'align': 'center'},
        number={'valueformat': '.1f', 'suffix': "%", 'font': {'size': 20}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [0, 100],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 100],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
    fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig

def criar_gauge_giro_unico_duck(df_giros, meta=70):
    """
    Cria gauge de giro baseado no DataFrame de giros.
    Prioriza a métrica do universo 90d ('Geral_90d'); se ausente, usa 'Geral'.
    """
    if df_giros.empty:
        perc_giro = 0.0
    else:
        # tentar primeiro 'Geral_90d'
        linha_90d = df_giros[(df_giros['filial_codigo'] == 'Geral_90d')]
        if not linha_90d.empty:
            row = linha_90d.iloc[0]
            total_valor = float(row.get('total_valor_estoque') or 0)
            valor_com_giro = float(row.get('valor_estoque_com_giro') or 0)
        else:
            # fallback para 'Geral' (todo o estoque)
            linha_geral = df_giros[
                (df_giros['filial_codigo'] == 'Geral') &
                (df_giros['classificacao_n1'] == 'Geral')
            ]
            if not linha_geral.empty:
                row = linha_geral.iloc[0]
                total_valor = float(row.get('total_valor_estoque') or 0)
                valor_com_giro = float(row.get('valor_estoque_com_giro') or 0)
            else:
                total_valor = 0.0
                valor_com_giro = 0.0

        perc_giro = (valor_com_giro / total_valor * 100) if total_valor > 0 else 0.0

    # garantir número válido e arredondar
    if pd.isna(perc_giro) or not isinstance(perc_giro, (int, float)):
        perc_giro = 0.0
    perc_giro = round(float(perc_giro), 2)

    # cor da barra: verde se alcançou a meta, amarelo caso contrário
    bar_color = "DeepSkyBlue" if perc_giro >= meta else "CadetBlue"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        align="center",
        value=perc_giro,
        title={'text': "Estoque<br>com Giro (90d)", 'font': {'size': 12}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.1f', 'suffix': "%", 'font': {'size': 20}},
        gauge={'axis': {'range': [0, 100],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 100],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
    # mesma aparência/dimensões do gauge de disponibilidade
    fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig

def criar_gauge_fator_cobertura_duck(df_cobertura, meta=2.1):
    """
    Cria gauge de fator de cobertura (aparência igual ao gauge de disponibilidade).
    """
    if df_cobertura.empty:
        cobertura_media = 0
    else:
        cobertura_media = float(df_cobertura['cobertura_ratio'].iloc[0])

    # garantir número válido e arredondar
    if pd.isna(cobertura_media) or not isinstance(cobertura_media, (int, float)):
        cobertura_media = 0
    cobertura_media = round(float(cobertura_media), 2)

    # cor da barra: verde se alcançou a meta, amarelo caso contrário
    bar_color = "DeepSkyBlue" if cobertura_media >= meta else "CadetBlue"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        align="center",
        value=cobertura_media,
        title={'text': "Fator de<br>Cobertura", 'font': {'size': 12}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.1f', 'font': {'size': 20}},
        gauge={'axis': {'range': [0, 4],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 4],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
    # mesma aparência/dimensões do gauge de disponibilidade
    fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig

def criar_gauge_dias_venda(meta=20):
    """
    Cria gauge para o indicador Dias para Venda, que é a média de quantos dias após a compra
    uma unidade é vendida.
    Meta padrão: 20 dias. Barra amarela se acima da meta.
    """
    try:
        # calcular o indicador (usa hoje como referência; a função internamente considera "ontem")
        kpi, _, _ = calcular_primeira_venda_geral(pd.Timestamp.today())
        value = float(kpi.get('tempo_primeira_venda_geral', 0.0) or 0.0)

        # garantir número válido e arredondar
        if pd.isna(value) or not isinstance(value, (int, float)):
            value = 0.0
        value = round(float(value), 2)

        # cor invertida: verde se abaixo ou igual à meta (bom), amarelo se acima da meta (ruim)
        bar_color = "DeepSkyBlue" if value <= meta else "CadetBlue"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            align="center",
            value=value,
            title={'text': "Primeira<br>Venda", 'font': {'size': 12}},
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'valueformat': '.1f', 'suffix': "d", 'font': {'size': 18}},
            gauge={'axis': {'range': [0, 15],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 15],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig
    except Exception as e:
        try:
            st.error(f"Erro ao criar gauge Curva D: {e}")
        except Exception:
            pass
        fig = go.Figure()
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig

def criar_gauge_dias_venda_apos_30d(meta=55):
    """
    Cria gauge para o indicador Dias para Venda após 30, que é a média de quantos dias após a compra
    uma unidade é vendida, se ela não foi vendida nos primeiros 30 dias.
    Meta padrão: 55 dias. Barra amarela se acima da meta.
    """
    try:
        # calcular o indicador (usa hoje como referência; a função internamente considera "ontem")
        kpi, _, _ = calcular_primeira_venda_geral(pd.Timestamp.today())
        value = float(kpi.get('tempo_primeira_venda_apos_30d', 0.0) or 0.0)

        # garantir número válido e arredondar
        if pd.isna(value) or not isinstance(value, (int, float)):
            value = 0.0
        value = round(float(value), 2)

        # cor invertida: verde se abaixo ou igual à meta (bom), amarelo se acima da meta (ruim)
        bar_color = "DeepSkyBlue" if value <= meta else "CadetBlue"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            align="center",
            value=value,
            title={'text': "Primeira Venda<br>(Após 30d)", 'font': {'size': 12}},
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'valueformat': '.1f', 'suffix': "d", 'font': {'size': 18}},
            gauge={'axis': {'range': [0, 90],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 90],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig
    except Exception as e:
        try:
            st.error(f"Erro ao criar gauge Curva D: {e}")
        except Exception:
            pass
        fig = go.Figure()
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig
    
def criar_gauge_curvad(meta=3):
    """
    Cria gauge para o indicador Curva D (índice acumulado 30d) — valor exibido é o KPI
    'indice_30d_pct' retornado por calcular_indice_curva_d. Meta padrão: 3 (%).
    Observação: quanto menor melhor — se value > meta, pintar amarelo; caso contrário verde.
    """
    try:
        # calcular o indicador (usa hoje como referência; a função internamente considera "ontem")
        kpi, _, _ = calcular_indice_curva_d_geral(pd.Timestamp.today())
        value = float(kpi.get('pct_value', 0.0) or 0.0)

        # garantir número válido e arredondar
        if pd.isna(value) or not isinstance(value, (int, float)):
            value = 0.0
        value = round(float(value), 2)

        # cor invertida: verde se abaixo ou igual à meta (bom), amarelo se acima da meta (ruim)
        bar_color = "DeepSkyBlue" if value <= meta else "CadetBlue"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            align="center",
            value=value,
            title={'text': "Conversão para<br>Curva D", 'font': {'size': 12}},
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'valueformat': '.2f', 'suffix': "%", 'font': {'size': 18}},
            gauge={'axis': {'range': [0, 12],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 12],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig
    except Exception as e:
        try:
            st.error(f"Erro ao criar gauge Curva D: {e}")
        except Exception:
            pass
        fig = go.Figure()
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig

def criar_gauge_desfazimento_curvad(meta=8):
    """
    Cria gauge para o indicador de desfazimento da Curva D (índice acumulado 30d).
    Busca o KPI 'indice_30d_pct' retornado por calcular_indice_desfazimento_curva_d.
    Meta padrão: 4 (%). Barra amarela se abaixo da meta.
    """
    try:
        kpi, _, _ = calcular_indice_desfazimento_curva_d(pd.Timestamp.today())
        
        value = float(kpi.get('pct_value', 0.0) or 0.0)

        if pd.isna(value) or not isinstance(value, (int, float)):
            value = 0.0
        value = round(float(value), 2)

        # cor da barra: verde se alcançou a meta, amarelo caso contrário
        bar_color = "DeepSkyBlue" if value >= meta else "CadetBlue"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            align="center",
            value=value,
            title={'text': "Venda Curva D<br>(30 dias)", 'font': {'size': 12}},
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'valueformat': '.2f', 'suffix': "%", 'font': {'size': 18}},
            gauge={'axis': {'range': [0, 15],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 15],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig
    except Exception as e:
        try:
            st.error(f"Erro ao criar gauge Desfazimento Curva D: {e}")
        except Exception:
            pass
        fig = go.Figure()
        fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
        return fig


def criar_gauge_plot(valor_atual, valor_maximo, titulo, formato_numero="{value:,.0f}"):
    """
    Cria um gráfico de gauge com Plotly, com a meta no topo (12h).
    Esquema de cores padronizado aos demais gauges (DeepSkyBlue / CadetBlue).
    """
    eixo_maximo = valor_maximo * 2 if valor_maximo > 0 else 1

    is_conversao = "Conversão Vitaminas" in titulo or "Conversão Vit." in titulo
    is_currency = "Meta Mensal" in titulo or "Dezena" in titulo
    is_percent = "%" in titulo and not is_conversao

    if is_currency:
        numero_format = ".3s"
        meta_formatada = formatar_moeda(valor_maximo)
        titulo = titulo.replace("Meta Mensal Total", "Meta Mensal")
        titulo = titulo.replace(" (1-10)", "").replace(" (11-20)", "").replace(" (21-Fim)", "")
    elif is_conversao:
        numero_format = ".1f"
        meta_formatada = formatar_numero_uma_casa(valor_maximo)
        titulo = "Conversão Vit."
    elif is_percent:
        numero_format = ".1f"
        meta_formatada = f"{valor_maximo:.1f}%"
    else:
        numero_format = ".1f"
        meta_formatada = formatar_numero(valor_maximo)

    # lógica de desempenho (mantida)
    ok = (valor_atual <= valor_maximo) if is_conversao else (valor_atual >= valor_maximo)

    # ESQUEMA DE CORES UNIFICADO
    bar_color = "DeepSkyBlue" if ok else "CadetBlue"
    bg_step_color = "AliceBlue"
    threshold_line_color = "MidnightBlue"
    border_color = "DodgerBlue"

    fig = go.Figure(go.Indicator(
        mode="number+gauge",
        value=valor_atual,
        number={'valueformat': numero_format,
                'suffix': "%" if is_percent else "",
                'font': {'size': 18}},
        title={
            'text': f"{titulo}<br><span style='font-size:0.8em;color:MidnightBlue'>Meta: {meta_formatada}</span>",
            'font': {'size': 12}
        },
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, eixo_maximo], 'showticklabels': False,
                     'tickfont': {'size': 9}},
            'bar': {'color': bar_color, 'thickness': 0.5},
            'steps': [{'range': [0, eixo_maximo], 'color': bg_step_color}],
            'threshold': {
                'line': {'color': threshold_line_color, 'width': 3},
                'thickness': 0.7,
                'value': valor_maximo
            },
            'borderwidth': 1,
            'bordercolor': border_color,
            'bgcolor': "white"
        }
    ))
    fig.update_layout(
        height=100,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def criar_gauge_invertido_plot(valor_atual, meta, titulo, formato_numero="{value:,.1f}%"):
    """
    Gauge invertido (menor é melhor) com esquema de cores unificado (DeepSkyBlue / CadetBlue).
    """
    eixo_maximo = meta * 2 if meta > 0 else 1

    # Menor ou igual à meta = bom
    bar_color = "DeepSkyBlue" if valor_atual <= meta else "CadetBlue"
    bg_step_color = "AliceBlue"
    threshold_line_color = "MidnightBlue"
    border_color = "DodgerBlue"

    fig = go.Figure(go.Indicator(
        mode="number+gauge",
        value=valor_atual,
        number={'valueformat': '.1f', 'suffix': '%', 'font': {'size': 18}},
        title={
            'text': f"{titulo}<br><span style='font-size:0.8em;color:{threshold_line_color}'>Meta: {meta:.1f}%</span>",
            'font': {'size': 12}
        },
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, eixo_maximo], 'showticklabels': False,
                     'tickfont': {'size': 9}},
            'bar': {'color': bar_color, 'thickness': 0.5},
            'steps': [{'range': [0, eixo_maximo], 'color': bg_step_color}],
            'threshold': {
                'line': {'color': threshold_line_color, 'width': 3},
                'thickness': 0.7,
                'value': meta
            },
            'borderwidth': 1,
            'bordercolor': border_color,
            'bgcolor': "white"
        }
    ))
    fig.update_layout(
        height=100,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def criar_gauge_gmroi_geral(df_gmroi, meta=1):
    """
    Cria gauge com GMROI geral (aparência igual ao gauge de disponibilidade).
    """
    if df_gmroi.empty:
        gmroi_ratio = 0.0
    else:
        # tentar primeiro 'Geral_90d'
        gmroi_geral = df_gmroi[(df_gmroi['filial_codigo'] == 'Geral')]
        if not gmroi_geral.empty:
            row = gmroi_geral.iloc[0]
            gmroi_ratio = float(row.get('gmroi_ratio') or 0)
    
    gmroi_ratio = round(float(gmroi_ratio), 2)

    # cor da barra: verde se alcançou a meta, amarelo caso contrário
    bar_color = "DeepSkyBlue" if gmroi_ratio >= meta else "CadetBlue"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        align="center",
        value=gmroi_ratio,
        title={'text': "GMROI<br>(1 Ano)", 'font': {'size': 12}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.2f', 'font': {'size': 18}},
        gauge={'axis': {'range': [0, 3],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 3],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
    # mesma aparência/dimensões do gauge de disponibilidade
    fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig

def criar_gauge_gmroi_vendas_geral(df_gmroi, meta=1):
    """
    Cria gauge com GMROI geral baseado nas vendas dos últimos 90 dias 
    (aparência igual ao gauge de disponibilidade).
    """
    if df_gmroi.empty:
        gmroi_ratio = 0.0
    else:
        # tentar primeiro 'Geral_90d'
        gmroi_geral = df_gmroi[(df_gmroi['filial_codigo'] == 'Geral')]
        if not gmroi_geral.empty:
            row = gmroi_geral.iloc[0]
            gmroi_ratio = float(row.get('gmroi_ratio') or 0)
    
    gmroi_ratio = round(float(gmroi_ratio), 2)

    # cor da barra: verde se alcançou a meta, amarelo caso contrário
    bar_color = "DeepSkyBlue" if gmroi_ratio >= meta else "CadetBlue"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        align="center",
        value=gmroi_ratio,
        title={'text': "GMROI<br>(90 Dias)", 'font': {'size': 12}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.2f', 'font': {'size': 18}},
        gauge={'axis': {'range': [0, 2],
                        'tickfont': {'size': 9}},
               'bar': {'color': bar_color, 'thickness': 0.5},
               'steps': [{'range': [0, 2],
                          'color': "AliceBlue"}],
               'threshold': {'line': {'color': "MidnightBlue", 'width': 3},
                             'thickness': 0.7, 'value': meta},
                'borderwidth': 1, 'bordercolor': "DodgerBlue"},
    ))
    # mesma aparência/dimensões do gauge de disponibilidade
    fig.update_layout(width=120, height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig