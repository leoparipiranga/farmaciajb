"""
Componentes visuais para cards KPI
"""
import streamlit as st

def render_kpi_card_duck(titulo: str, valor: str, variante: str | None = None):
    """Renderiza card KPI padrão com variantes de cor"""
    cls = "kpi-card-duck" + (" is-alt" if (variante == "alt") else "")
    st.markdown(f"""
      <div class="{cls}">
        <p class="kpi-card-title">{titulo}</p>
        <p class="kpi-card-value">{valor}</p>
      </div>
    """, unsafe_allow_html=True)

def render_kpi_card(label, valor, perc=None):
    perc_html = f"<div class='kpi-perc'>{perc}</div>" if perc is not None else "<div class='kpi-perc'>&nbsp;</div>"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>{label}</div>
        <div class='kpi-value'>{valor}</div>
        {perc_html}
    </div>
    """, unsafe_allow_html=True)

# Adicionar ao arquivo existente:

def render_kpi_card_estoque(title: str, value: str, subtitle: str = "", variant: str = "default"):
    """
    Renderiza card KPI específico para estoque com CSS inline
    
    Args:
        title: Título do card
        value: Valor principal
        subtitle: Subtítulo opcional
        variant: "default" ou "brown" para cor da borda
    """
    border_color = "#5c4033" if variant == "brown" else "#0b3b73"
    subtitle_html = f'<div class="sub">{subtitle}</div>' if subtitle else '<div class="sub"></div>'
    
    css = """
    <style>
    .local-kpi {
        background:#ffffff;
        box-shadow:0 2px 6px rgba(0,0,0,0.08);
        border-left:6px solid #0b3b73;
        padding:10px 12px;
        border-radius:6px;
        font-family:inherit;
        text-align:center;
        display:flex;
        flex-direction:column;
        box-sizing:border-box;
        min-height:72px;
        margin-bottom:10px;
    }
    .local-kpi .title {
        color:#495057;
        font-size:12px;
        margin:0 0 4px 0;
        line-height:1;
    }
    .local-kpi .value {
        color:#5c4033;
        font-size:16px;
        font-weight:600;
        text-align:center;    
        margin:0;
        line-height:1.1;
    }
    .local-kpi .sub {
        color:#6c757d;
        font-size:12px;
        text-align:center;
        margin:0;
        line-height:1;
        margin-top:auto;
    }
    </style>
    """
    
    html = f"""
    {css}
    <div class="local-kpi" style="border-left-color: {border_color};">
        <div class="title">{title}</div>
        <div class="value">{value}</div>
        {subtitle_html}
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)